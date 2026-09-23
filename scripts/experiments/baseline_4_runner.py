"""
HALO Baseline 4 — Hybrid RAG Runner (Dense + Sparse BM25 via Reciprocal Rank Fusion)
===================================================================================
Protocol: v1.0-FROZEN
Architecture:
  Query
    ├── Dense Retriever (BAAI/bge-large-en-v1.5) ──► Top-5
    └── Sparse BM25 (rank_bm25.BM25Okapi) ──────────► Top-5
                    │
                    ▼
          Reciprocal Rank Fusion (RRF, k=60)
                    │
                    ▼
               Final Top-5
                    │
                    ▼
             qwen/qwen3.8-27b (Groq API, Temp=0.0, Seed=42)

Invariants:
  - Disallowed modules: Zero reranker, Zero verifier, Zero fail-closed, Zero score normalization.
  - Fusion: Pure rank-based fusion (RRF with k=60).
  - Deterministic tie-breaking: (-rrf_score, passage_id ascending).
  - Full retrieval trace recording: dense_candidates, bm25_candidates, rrf_candidates, final_top5.
  - Corpus: Exactly 2,773 passages (1,640 D1 + 1,133 D2).
  - Checkpointing and multi-key rotation enabled.
"""

import os
import sys
import json
import time
import pickle
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple, Optional, Set

import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel

from scripts.experiments.baseline_3_runner import tokenize_legal_text

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(BASE_DIR, "experiments", "configs", "b4_hybrid_config.json")
RUNS_DIR = os.path.join(BASE_DIR, "experiments", "runs", "b4_hybrid")
CHECKPOINT_PATH = os.path.join(RUNS_DIR, "checkpoint.json")
LOG_PATH = os.path.join(BASE_DIR, "experiments", "logs", "execution_audit.log")

DENSE_INDEX_DIR = os.path.join(BASE_DIR, "experiments", "indices", "dense")
BM25_INDEX_DIR = os.path.join(BASE_DIR, "experiments", "indices", "bm25")
CANONICAL_D3_PATH = os.path.join(BASE_DIR, "data", "dataset3", "canonical", "dataset3_all.jsonl")

SYSTEM_PROMPT = (
    "You are an authoritative Indian Legal Research Assistant specializing in the Companies Act, 2013 "
    "and Indian corporate jurisprudence. Answer the inquiry factually, accurately, and with precise statutory "
    "and judicial citations using the authoritative legal evidence provided below. "
    "If the provided context is insufficient or the proposition is unsupported, state so explicitly."
)


def compute_file_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class Baseline4Runner:
    def __init__(self, api_key: Optional[str] = None):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.system_id = self.config["system_id"]
        self.retrieval_method = self.config["retrieval"]["method"]
        self.top_k = self.config["retrieval"]["top_k"]
        self.rrf_k = self.config["retrieval"]["fusion"]["k"]

        # Assert protocol invariants
        assert self.retrieval_method == "hybrid_rrf", f"Invalid retrieval method: {self.retrieval_method}"
        assert self.top_k == 5, f"Top-K must be 5, got {self.top_k}"
        assert self.rrf_k == 60, f"RRF k must be 60, got {self.rrf_k}"
        disallowed = self.config.get("disallowed_modules", {})
        assert disallowed.get("cross_encoder_reranking") is False
        assert disallowed.get("legal_verifier") is False
        assert disallowed.get("fail_closed_governor") is False
        assert disallowed.get("score_normalization") is False

        # Dense params
        self.embedding_model_name = self.config["retrieval"]["dense"]["model_name"]
        self.query_instruction = self.config["retrieval"]["dense"]["query_instruction"]
        self.dense_top_k = self.config["retrieval"]["dense"]["top_k"]

        # Sparse params
        self.bm25_top_k = self.config["retrieval"]["sparse"]["top_k"]

        # LLM params
        gen_conf = self.config["generation"]
        self.provider = gen_conf["provider"]
        self.model_name = gen_conf.get("model", gen_conf.get("model_name"))
        self.temperature = gen_conf["temperature"]
        self.top_p = gen_conf["top_p"]
        self.max_tokens = gen_conf["max_tokens"]
        self.seed = gen_conf["seed"]

        raw_key = api_key or os.environ.get("GROQ_API_KEY", "") or os.environ.get("GROQ_API_KEYS", "")
        if "," in raw_key:
            self.groq_api_keys = [k.strip() for k in raw_key.split(",") if k.strip()]
        elif raw_key.strip():
            self.groq_api_keys = [raw_key.strip()]
        else:
            self.groq_api_keys = []
        self.current_key_idx = 0
        self.groq_api_key = self.groq_api_keys[0] if self.groq_api_keys else None
        self.key_cooldowns: Dict[int, float] = {i: 0.0 for i in range(len(self.groq_api_keys))}

        # In-memory index objects
        self.dense_tensor = None
        self.dense_metadata: List[Dict[str, Any]] = []
        self.embedding_tokenizer = None
        self.embedding_model = None

        self.bm25_model = None
        self.bm25_metadata: List[Dict[str, Any]] = []

    def verify_and_load_indices(self):
        """Loads and strictly verifies frozen dense and BM25 indices against manifest."""
        if self.dense_tensor is not None and self.bm25_model is not None:
            return

        # 1. Load Dense Index
        dense_tensor_file = os.path.join(DENSE_INDEX_DIR, "index.pt")
        dense_meta_file = os.path.join(DENSE_INDEX_DIR, "metadata.jsonl")
        if not os.path.exists(dense_tensor_file) or not os.path.exists(dense_meta_file):
            raise FileNotFoundError(f"Dense index missing in {DENSE_INDEX_DIR}")

        print(f"[*] Loading Dense index tensor from: {os.path.relpath(dense_tensor_file, BASE_DIR)}...")
        self.dense_tensor = torch.load(dense_tensor_file, map_location="cpu")
        assert self.dense_tensor.shape == (2773, 1024), f"Dense tensor shape invalid: {self.dense_tensor.shape}"

        self.dense_metadata = []
        with open(dense_meta_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    self.dense_metadata.append(json.loads(line))
        assert len(self.dense_metadata) == 2773

        # 2. Load BM25 Index
        bm25_model_file = os.path.join(BM25_INDEX_DIR, "index", "bm25_model.pkl")
        bm25_meta_file = os.path.join(BM25_INDEX_DIR, "metadata.jsonl")
        if not os.path.exists(bm25_model_file) or not os.path.exists(bm25_meta_file):
            raise FileNotFoundError(f"BM25 index missing in {BM25_INDEX_DIR}")

        print(f"[*] Loading BM25 model from: {os.path.relpath(bm25_model_file, BASE_DIR)}...")
        with open(bm25_model_file, "rb") as f:
            self.bm25_model = pickle.load(f)
        assert self.bm25_model.corpus_size == 2773

        self.bm25_metadata = []
        with open(bm25_meta_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    self.bm25_metadata.append(json.loads(line))
        assert len(self.bm25_metadata) == 2773

        # 3. Assert 1-to-1 passage ID alignment between Dense and BM25
        dense_ids = [p["passage_id"] for p in self.dense_metadata]
        bm25_ids = [p["passage_id"] for p in self.bm25_metadata]
        assert dense_ids == bm25_ids, "Passage ID order mismatch between Dense and BM25 indices!"
        print(f"    [+] Indices verified and loaded: 2,773 passages aligned byte-for-byte.")

    def init_embedding_model(self):
        """Initializes dense query encoder on demand."""
        if self.embedding_model is not None:
            return
        print(f"[*] Initializing query encoder: {self.embedding_model_name}...")
        self.embedding_tokenizer = AutoTokenizer.from_pretrained(self.embedding_model_name)
        self.embedding_model = AutoModel.from_pretrained(self.embedding_model_name)
        self.embedding_model.eval()
        print("    [+] Query encoder loaded into memory.")

    def retrieve_dense(self, query_text: str) -> Tuple[List[Dict[str, Any]], float]:
        """Encodes query and retrieves Top-5 dense passages via cosine similarity."""
        self.verify_and_load_indices()
        self.init_embedding_model()

        t_start = time.perf_counter()
        formatted_query = f"{self.query_instruction}{query_text}"
        inputs = self.embedding_tokenizer(
            [formatted_query],
            max_length=512,
            padding=True,
            truncation=True,
            return_tensors="pt"
        )
        with torch.no_grad():
            outputs = self.embedding_model(**inputs)
            q_vec = outputs[0][:, 0]  # CLS pool
            q_norm = F.normalize(q_vec, p=2, dim=1)

        scores = torch.matmul(q_norm, self.dense_tensor.T).squeeze(0)
        topk = torch.topk(scores, k=self.dense_top_k)
        top_indices = topk.indices.tolist()
        top_scores = topk.values.tolist()

        t_dense_ms = (time.perf_counter() - t_start) * 1000.0

        candidates = []
        for rank, (idx, s) in enumerate(zip(top_indices, top_scores), 1):
            p_id = self.dense_metadata[idx]["passage_id"]
            candidates.append({
                "passage_id": p_id,
                "rank": rank,
                "score": round(float(s), 5),
                "index": idx
            })
        return candidates, round(t_dense_ms, 2)

    def retrieve_bm25(self, query_text: str) -> Tuple[List[Dict[str, Any]], float]:
        """Tokenizes query with legal tokenizer and retrieves Top-5 BM25 passages."""
        self.verify_and_load_indices()

        t_start = time.perf_counter()
        query_tokens = tokenize_legal_text(query_text)
        scores = self.bm25_model.get_scores(query_tokens)

        scored = []
        for idx, s in enumerate(scores):
            p_id = self.bm25_metadata[idx]["passage_id"]
            scored.append((float(s), p_id, idx))

        # Deterministic sort by (-score, passage_id ascending)
        scored.sort(key=lambda item: (-item[0], item[1]))
        top_candidates = scored[:self.bm25_top_k]

        t_bm25_ms = (time.perf_counter() - t_start) * 1000.0

        candidates = []
        for rank, (s, p_id, idx) in enumerate(top_candidates, 1):
            candidates.append({
                "passage_id": p_id,
                "rank": rank,
                "score": round(float(s), 5),
                "index": idx
            })
        return candidates, round(t_bm25_ms, 2)

    def reciprocal_rank_fusion(
        self,
        dense_candidates: List[Dict[str, Any]],
        bm25_candidates: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], float]:
        """
        Computes standard Reciprocal Rank Fusion (RRF) with k=60.
        RRF(d) = sum_{m in {dense, bm25}} (1 / (60 + rank_m(d)))
        Deterministic tie-breaking: (-rrf_score, passage_id ascending).
        Returns: (final_top5_passages, rrf_candidate_traces, rrf_time_ms)
        """
        t_start = time.perf_counter()

        dense_map = {c["passage_id"]: (c["rank"], c["index"]) for c in dense_candidates}
        bm25_map = {c["passage_id"]: (c["rank"], c["index"]) for c in bm25_candidates}

        all_unique_ids = set(dense_map.keys()) | set(bm25_map.keys())
        rrf_candidates = []

        for p_id in all_unique_ids:
            d_rank = dense_map[p_id][0] if p_id in dense_map else None
            b_rank = bm25_map[p_id][0] if p_id in bm25_map else None

            idx = dense_map[p_id][1] if p_id in dense_map else bm25_map[p_id][1]

            score = 0.0
            if d_rank is not None:
                score += 1.0 / (self.rrf_k + d_rank)
            if b_rank is not None:
                score += 1.0 / (self.rrf_k + b_rank)

            rrf_candidates.append({
                "passage_id": p_id,
                "dense_rank": d_rank,
                "bm25_rank": b_rank,
                "rrf_score": round(score, 6),
                "index": idx
            })

        # Deterministic sorting: descending by rrf_score, then ascending by passage_id
        rrf_candidates.sort(key=lambda item: (-item["rrf_score"], item["passage_id"]))

        top_fused = rrf_candidates[:self.top_k]
        t_rrf_ms = (time.perf_counter() - t_start) * 1000.0

        final_passages = [self.dense_metadata[item["index"]] for item in top_fused]
        return final_passages, rrf_candidates, round(t_rrf_ms, 2)

    def construct_context_prompt(self, query_text: str, passages: List[Dict[str, Any]]) -> str:
        """Constructs identical prompt as B2/B3 with clearly delimited authoritative evidence."""
        lines = [
            "AUTHORITATIVE LEGAL EVIDENCE",
            "=" * 50
        ]

        for i, p in enumerate(passages, 1):
            p_id = p["passage_id"]
            d_set = "Dataset 1 (Statutory - Companies Act, 2013)" if p["dataset"] == "dataset1" else "Dataset 2 (Judicial Precedent)"
            lines.append(f"\n[EVIDENCE PASSAGE {i}]")
            lines.append(f"Passage ID: {p_id}")
            lines.append(f"Source: {d_set}")
            if p.get("section_id"):
                lines.append(f"Statutory Section: {p['section_id']}")
            if p.get("heading"):
                lines.append(f"Title / Heading: {p['heading']}")
            if p.get("court"):
                lines.append(f"Court: {p['court']}")
            if p.get("citation"):
                lines.append(f"Citation: {p['citation']}")
            lines.append(f"Passage Content:\n{p['text']}")

        lines.append("\n" + "=" * 50)
        lines.append("END AUTHORITATIVE LEGAL EVIDENCE\n")
        lines.append(f"INQUIRY: {query_text}")
        lines.append("Provide a comprehensive, accurate legal answer grounded in the authoritative evidence above.")

        return "\n".join(lines)

    def _select_next_key_idx(self) -> int:
        num_keys = len(self.groq_api_keys)
        if num_keys <= 1:
            return 0
        now = time.time()
        for offset in range(num_keys):
            cand_idx = (self.current_key_idx + offset) % num_keys
            if self.key_cooldowns.get(cand_idx, 0.0) <= now:
                self.current_key_idx = cand_idx
                return cand_idx
        earliest_idx = min(self.key_cooldowns.keys(), key=lambda i: self.key_cooldowns.get(i, 0.0))
        self.current_key_idx = earliest_idx
        return earliest_idx

    def _call_groq_api(self, prompt_text: str, key_idx: Optional[int] = None) -> str:
        if not self.groq_api_keys:
            raise ValueError("GROQ_API_KEY is not set.")
        idx = key_idx if key_idx is not None else self.current_key_idx
        active_key = self.groq_api_keys[idx]

        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt_text}
            ],
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
            "seed": self.seed
        }
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "Authorization": f"Bearer {active_key}",
                "Content-Type": "application/json",
                "User-Agent": "HALO-Baseline4/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=75) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            choices = resp_data.get("choices", [])
            if not choices:
                return ""
            msg = choices[0].get("message", {})
            return msg.get("content", "").strip()

    def generate_single_query(self, query_text: str, mock_fn=None) -> Dict[str, Any]:
        """Executes full hybrid retrieval, RRF fusion, and generation for a single query."""
        # 1. Dense Retrieval
        if mock_fn is not None and "mock_dense" in mock_fn:
            dense_cands, t_dense = mock_fn["mock_dense"](query_text)
        else:
            dense_cands, t_dense = self.retrieve_dense(query_text)

        # 2. Sparse BM25 Retrieval
        if mock_fn is not None and "mock_bm25" in mock_fn:
            bm25_cands, t_bm25 = mock_fn["mock_bm25"](query_text)
        else:
            bm25_cands, t_bm25 = self.retrieve_bm25(query_text)

        # 3. Reciprocal Rank Fusion
        final_passages, rrf_cands, t_rrf = self.reciprocal_rank_fusion(dense_cands, bm25_cands)
        t_total_retrieval = round(t_dense + t_bm25 + t_rrf, 2)
        final_top5_ids = [p["passage_id"] for p in final_passages]

        # 4. Context Prompt Formulation
        augmented_prompt = self.construct_context_prompt(query_text, final_passages)

        # 5. LLM Generation
        t_gen_start = time.perf_counter()
        if mock_fn is not None and "mock_llm" in mock_fn:
            ans = mock_fn["mock_llm"](augmented_prompt)
            gen_latency = (time.perf_counter() - t_gen_start) * 1000.0
            return {
                "dense_candidates": dense_cands,
                "bm25_candidates": bm25_cands,
                "rrf_candidates": rrf_cands,
                "final_top5_passage_ids": final_top5_ids,
                "dense_retrieval_ms": t_dense,
                "bm25_retrieval_ms": t_bm25,
                "rrf_ms": t_rrf,
                "total_retrieval_ms": t_total_retrieval,
                "predicted_answer": ans,
                "generation_latency_ms": round(gen_latency, 2),
                "status": "SUCCESS",
                "error": None
            }

        attempt = 0
        base_delay = 3.0

        while True:
            active_idx = self._select_next_key_idx()
            now = time.time()
            cooldown_left = self.key_cooldowns.get(active_idx, 0.0) - now
            if cooldown_left > 0.1:
                print(f"    [!] Key {active_idx+1} cooling down ({cooldown_left:.1f}s remaining). Waiting...")
                time.sleep(cooldown_left + 0.5)

            try:
                text = self._call_groq_api(augmented_prompt, key_idx=active_idx)
                gen_latency = (time.perf_counter() - t_gen_start) * 1000.0
                if not text:
                    return {
                        "dense_candidates": dense_cands,
                        "bm25_candidates": bm25_cands,
                        "rrf_candidates": rrf_cands,
                        "final_top5_passage_ids": final_top5_ids,
                        "dense_retrieval_ms": t_dense,
                        "bm25_retrieval_ms": t_bm25,
                        "rrf_ms": t_rrf,
                        "total_retrieval_ms": t_total_retrieval,
                        "predicted_answer": "[EMPTY_RESPONSE]",
                        "generation_latency_ms": round(gen_latency, 2),
                        "status": "EMPTY_RESPONSE",
                        "error": "Model returned empty response"
                    }
                self.key_cooldowns[active_idx] = time.time() + 18.0
                if len(self.groq_api_keys) > 1:
                    self.current_key_idx = (active_idx + 1) % len(self.groq_api_keys)
                return {
                    "dense_candidates": dense_cands,
                    "bm25_candidates": bm25_cands,
                    "rrf_candidates": rrf_cands,
                    "final_top5_passage_ids": final_top5_ids,
                    "dense_retrieval_ms": t_dense,
                    "bm25_retrieval_ms": t_bm25,
                    "rrf_ms": t_rrf,
                    "total_retrieval_ms": t_total_retrieval,
                    "predicted_answer": text,
                    "generation_latency_ms": round(gen_latency, 2),
                    "status": "SUCCESS",
                    "error": None
                }
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "rate" in err_str.lower() or "quota" in err_str.lower():
                    sleep_time = max(base_delay * (2 ** min(attempt, 4)), 10.0)
                    if hasattr(e, "headers") and e.headers:
                        hdr = e.headers.get("retry-after") or e.headers.get("Retry-After")
                        if hdr:
                            try:
                                sleep_time = float(hdr) + 0.5
                            except Exception:
                                pass
                    self.key_cooldowns[active_idx] = time.time() + sleep_time
                    attempt += 1
                    print(f"    [!] Key {active_idx+1} rate limit (cooldown {sleep_time:.1f}s).")

                    now = time.time()
                    other_ready = [i for i in range(len(self.groq_api_keys)) if i != active_idx and self.key_cooldowns.get(i, 0.0) <= now]
                    if other_ready:
                        self.current_key_idx = other_ready[0]
                        print(f"    [!] Switching to key {self.current_key_idx+1} immediately...")
                        time.sleep(0.5)
                        continue
                    else:
                        earliest_wait = min(max(0.0, self.key_cooldowns[i] - now) for i in self.key_cooldowns)
                        if earliest_wait > 0:
                            print(f"    [!] All keys cooling down. Sleeping shortest cooldown: {earliest_wait+0.5:.1f}s...")
                            time.sleep(earliest_wait + 0.5)
                        continue
                elif ("11001" in err_str or "getaddrinfo" in err_str or "ssl" in err_str.lower() or "timeout" in err_str.lower() or "eof" in err_str.lower()) and attempt < 5:
                    attempt += 1
                    print(f"    [!] Transient network error ({err_str}). Backing off 5.0s (attempt {attempt}/5)...")
                    time.sleep(5.0)
                    continue
                else:
                    gen_latency = (time.perf_counter() - t_gen_start) * 1000.0
                    return {
                        "dense_candidates": dense_cands,
                        "bm25_candidates": bm25_cands,
                        "rrf_candidates": rrf_cands,
                        "final_top5_passage_ids": final_top5_ids,
                        "dense_retrieval_ms": t_dense,
                        "bm25_retrieval_ms": t_bm25,
                        "rrf_ms": t_rrf,
                        "total_retrieval_ms": t_total_retrieval,
                        "predicted_answer": f"[API_ERROR: {err_str}]",
                        "generation_latency_ms": round(gen_latency, 2),
                        "status": "FAILED",
                        "error": err_str
                    }

    def load_queries_for_split(self, split: str) -> List[Dict[str, Any]]:
        if split not in ["dev", "test"]:
            raise ValueError(f"Invalid split '{split}'. Must be 'dev' or 'test'.")

        records = []
        with open(CANONICAL_D3_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    if item.get("split") == split:
                        records.append(item)

        target_families = ["D3-A", "D3-B", "D3-C", "D3-D"]
        filtered = [r for r in records if r.get("benchmark_family") in target_families]

        expected_count = 64 if split == "dev" else 168
        assert len(filtered) == expected_count, (
            f"B4 Protocol Violation: Expected {expected_count} {split.upper()} records, found {len(filtered)}"
        )
        return filtered

    def save_checkpoint(self, split: str, total_queries: int, completed: int, last_qid: str):
        os.makedirs(RUNS_DIR, exist_ok=True)
        ckpt_data = {
            "system_id": self.system_id,
            "current_split": split,
            "status": "CHECKPOINT_SAVED" if completed < total_queries else "SPLIT_COMPLETED",
            "last_saved_utc": datetime.now(timezone.utc).isoformat(),
            "split_progress": {
                "total_queries": total_queries,
                "completed_queries": completed,
                "remaining_queries": total_queries - completed,
                "last_processed_query_id": last_qid
            },
            "output_files": {
                "dev": os.path.join(RUNS_DIR, "dev_run_output.jsonl"),
                "test": os.path.join(RUNS_DIR, "test_run_output.jsonl")
            },
            "resume_command": f"python -m scripts.experiments.baseline_4_runner {split} --resume"
        }
        with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
            json.dump(ckpt_data, f, indent=2)

    def run_experiment(self, split: str, resume: bool = False, mock_fn=None):
        queries = self.load_queries_for_split(split)
        os.makedirs(RUNS_DIR, exist_ok=True)
        out_filename = f"{split}_run_output.jsonl"
        out_filepath = os.path.join(RUNS_DIR, out_filename)

        completed_records: Dict[str, Dict[str, Any]] = {}
        if resume and os.path.exists(out_filepath):
            with open(out_filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            item = json.loads(line)
                            ans = item.get("generation", {}).get("predicted_answer", "")
                            if not ans.startswith("[API_ERROR") and ans not in ["[RATE_LIMITED]", "[EMPTY_RESPONSE]"]:
                                completed_records[item["query_id"]] = item
                        except Exception:
                            pass

        remaining_queries = [q for q in queries if q["record_id"] not in completed_records]

        exp_id = f"EXP_B4_HYBRID_{split.upper()}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_v1.0"
        print("=" * 70)
        print(f"  HALO BASELINE 4 (HYBRID RAG: DENSE + BM25 via RRF) EXECUTION: {split.upper()} SPLIT")
        print(f"  Experiment ID: {exp_id}")
        print(f"  Fusion: Reciprocal Rank Fusion (k={self.rrf_k}, Top-K={self.top_k})")
        print(f"  Dense: {self.embedding_model_name} (Top-5)")
        print(f"  Sparse: BM25Okapi (Top-5)")
        print(f"  LLM: {self.provider} | {self.model_name}")
        print(f"  Total Queries: {len(queries)} | Completed: {len(completed_records)} | Remaining: {len(remaining_queries)}")
        print("=" * 70)

        successes = len(completed_records)
        failures = 0
        start_time = datetime.now(timezone.utc)

        for idx, q_data in enumerate(remaining_queries, 1):
            prog = len(completed_records) + 1
            raw = q_data.get("raw_record", {})
            q_text = raw.get("query") or raw.get("claim") or q_data.get("query_or_claim", "")
            q_id = q_data.get("record_id")
            q_fam = q_data.get("benchmark_family", "UNKNOWN")

            print(f"[{prog:04d}/{len(queries):04d}] Query ID: {q_id} ({q_fam})... ", end="", flush=True)

            res = self.generate_single_query(q_text, mock_fn=mock_fn)

            status = res["status"]
            if status == "SUCCESS":
                successes += 1
                print(f"DONE (Dense: {res['dense_retrieval_ms']:.1f}ms, BM25: {res['bm25_retrieval_ms']:.1f}ms, RRF: {res['rrf_ms']:.1f}ms, Gen: {res['generation_latency_ms']:.1f}ms)")
            else:
                failures += 1
                print(f"[{status}]: {res['error']}")

            tot_lat = round(res["total_retrieval_ms"] + res["generation_latency_ms"], 2)

            record = {
                "experiment_id": exp_id,
                "system_id": self.system_id,
                "query_id": q_id,
                "benchmark_family": q_fam,
                "split": split,
                "query": q_text,
                "retrieval": {
                    "enabled": True,
                    "method": "hybrid_rrf",
                    "top_k": self.top_k,
                    "rrf_k": self.rrf_k,
                    "dense_candidates": res["dense_candidates"],
                    "bm25_candidates": res["bm25_candidates"],
                    "rrf_candidates": res["rrf_candidates"],
                    "retrieved_passage_ids": res["final_top5_passage_ids"],
                    "dense_retrieval_latency_ms": res["dense_retrieval_ms"],
                    "bm25_retrieval_latency_ms": res["bm25_retrieval_ms"],
                    "rrf_latency_ms": res["rrf_ms"],
                    "retrieval_latency_ms": res["total_retrieval_ms"]
                },
                "generation": {
                    "model": self.model_name,
                    "provider": self.provider,
                    "predicted_answer": res["predicted_answer"],
                    "generation_latency_ms": res["generation_latency_ms"]
                },
                "verification": {
                    "enabled": False,
                    "verification_status": "NOT_APPLICABLE",
                    "fail_closed_triggered": False
                },
                "total_latency_ms": tot_lat,
                "timestamp_utc": datetime.now(timezone.utc).isoformat()
            }

            if status == "SUCCESS":
                completed_records[q_id] = record
            else:
                # Still record failed attempts if fatal
                completed_records[q_id] = record

            # Live flush in canonical query order so far
            with open(out_filepath, "w", encoding="utf-8") as out_f:
                for q in queries:
                    if q["record_id"] in completed_records:
                        out_f.write(json.dumps(completed_records[q["record_id"]], ensure_ascii=False) + "\n")

            # Live checkpoint
            self.save_checkpoint(split, len(queries), len(completed_records), q_id)

            if mock_fn is None:
                time.sleep(2.5 if len(self.groq_api_keys) > 1 else 15.0)

        end_time = datetime.now(timezone.utc)

        log_entry = (
            f"[{end_time.isoformat()}] Experiment: {exp_id} | System: {self.system_id} | "
            f"Retriever: Hybrid RRF (Top-5) | LLM: {self.model_name} | Split: {split} | "
            f"Processed: {len(remaining_queries)} | Successes: {successes} | Failures: {failures} | "
            f"Duration: {(end_time - start_time).total_seconds():.2f}s\n"
        )
        with open(LOG_PATH, "a", encoding="utf-8") as lf:
            lf.write(log_entry)

        print("\n" + "=" * 70)
        print(f"  RUN FINISHED. Outputs saved to: {out_filepath}")
        print(f"  Total In File: {len(completed_records)}/{len(queries)}")
        print("=" * 70)
        return {
            "split": split,
            "output_file": out_filepath,
            "total_queries": len(queries),
            "processed": len(remaining_queries),
            "successes": successes,
            "failures": failures
        }


if __name__ == "__main__":
    split_arg = "dev"
    resume_flag = False

    if len(sys.argv) > 1:
        split_arg = sys.argv[1].lower()
    if "--resume" in sys.argv:
        resume_flag = True

    runner = Baseline4Runner()
    runner.run_experiment(split=split_arg, resume=resume_flag)
