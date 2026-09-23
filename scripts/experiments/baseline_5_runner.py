"""
HALO Baseline 5 — Hybrid RAG + Cross-Encoder Reranker Runner
============================================================
Protocol: v1.0-FROZEN
System ID: B5_HYBRID_CROSS_ENCODER

Implements the single-variable ablation from Baseline 4:
  Query
    ├──> Dense (BGE-Large-en-v1.5) -> Top-5
    └──> BM25 (BM25Okapi, legal tokenizer) -> Top-5
           │
           ▼
      RRF (k=60) Candidate Union (5 <= |C| <= 10 max)
           │
           ▼
      Cross-Encoder Reranker (ms-marco-MiniLM-L-6-v2)
      Scoring: (query, original passage text)
      Deterministic Tie-Breaking: (-ce_score, passage_id ascending)
           │
           ▼
      Final Top-5 Passages
           │
           ▼
      LLM Generation (qwen/qwen3.8-27b, temp=0.0, seed=42)
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
from transformers import AutoTokenizer, AutoModel, AutoModelForSequenceClassification

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scripts.experiments.baseline_3_runner import tokenize_legal_text
CONFIG_PATH = os.path.join(BASE_DIR, "experiments", "configs", "b5_reranker_config.json")
RUNS_DIR = os.path.join(BASE_DIR, "experiments", "runs", "b5_reranker")
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


def log_execution_event(event_type: str, details: Dict[str, Any]):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "system_id": "B5_HYBRID_CROSS_ENCODER",
        "event_type": event_type,
        "details": details
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


class Baseline5Runner:
    def __init__(self, config_path: str = CONFIG_PATH):
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.system_id = self.config["system_id"]
        assert self.system_id == "B5_HYBRID_CROSS_ENCODER"

        # Dense params
        self.dense_config = self.config["retrieval"]["dense"]
        self.dense_top_k = self.dense_config["top_k"]
        self.embedding_model_name = self.dense_config["model_name"]
        self.query_instruction = self.dense_config["query_instruction"]

        # Sparse params
        self.sparse_config = self.config["retrieval"]["sparse"]
        self.bm25_top_k = self.sparse_config["top_k"]

        # RRF params
        self.fusion_config = self.config["retrieval"]["fusion"]
        self.rrf_k = self.fusion_config["k"]
        self.candidate_pool_max = self.fusion_config.get("candidate_pool_max", 10)

        # Cross-Encoder params
        self.ce_config = self.config["retrieval"]["cross_encoder"]
        self.ce_model_name = self.ce_config["model_name"]
        self.final_top_k = self.ce_config.get("final_top_k", 5)

        # Generation params
        self.gen_config = self.config["generation"]
        self.model_name = self.gen_config["model"]
        self.temperature = self.gen_config["temperature"]
        self.top_p = self.gen_config["top_p"]
        self.seed = self.gen_config["seed"]
        self.max_tokens = self.gen_config["max_tokens"]

        # API keys from environment
        env_key = os.environ.get("GROQ_API_KEY", "") or os.environ.get("GROQ_API_KEYS", "")
        self.groq_api_keys: List[str] = []
        if "," in env_key:
            self.groq_api_keys = [k.strip() for k in env_key.split(",") if k.strip()]
        elif env_key.strip():
            self.groq_api_keys = [env_key.strip()]

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

        # Cross-encoder model
        self.cross_encoder_tokenizer = None
        self.cross_encoder_model = None

    def verify_and_load_indices(self):
        """Loads and strictly verifies frozen dense, BM25, and Cross-Encoder components."""
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

        print(f"[+] Loaded frozen corpora: 2,773 passages verified.")

    def _ensure_embedding_model(self):
        """Loads dense query bi-encoder model on CPU."""
        if self.embedding_model is None or self.embedding_tokenizer is None:
            print(f"[*] Loading bi-encoder model: {self.embedding_model_name}...")
            self.embedding_tokenizer = AutoTokenizer.from_pretrained(self.embedding_model_name)
            self.embedding_model = AutoModel.from_pretrained(self.embedding_model_name)
            self.embedding_model.eval()

    def _ensure_cross_encoder_model(self):
        """Loads Cross-Encoder model on CPU."""
        if self.cross_encoder_model is None or self.cross_encoder_tokenizer is None:
            print(f"[*] Loading cross-encoder model: {self.ce_model_name}...")
            self.cross_encoder_tokenizer = AutoTokenizer.from_pretrained(self.ce_model_name)
            self.cross_encoder_model = AutoModelForSequenceClassification.from_pretrained(self.ce_model_name)
            self.cross_encoder_model.eval()

    def retrieve_dense(self, query_text: str) -> Tuple[List[Dict[str, Any]], float]:
        """Encodes query and retrieves Top-5 dense passages via cosine similarity."""
        self.verify_and_load_indices()
        self._ensure_embedding_model()

        t_start = time.perf_counter()
        formatted_query = self.query_instruction + query_text.strip()
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
    ) -> Tuple[List[Dict[str, Any]], float]:
        """
        Computes standard Reciprocal Rank Fusion (RRF) with k=60 across the Top-5 Dense + Top-5 BM25 candidates.
        RRF(d) = sum_{m in {dense, bm25}} (1 / (60 + rank_m(d)))
        Deterministic tie-breaking: (-rrf_score, passage_id ascending).
        Returns: (rrf_candidate_union, rrf_time_ms)
        """
        t_start = time.perf_counter()

        dense_map = {c["passage_id"]: (c["rank"], c["index"]) for c in dense_candidates}
        bm25_map = {c["passage_id"]: (c["rank"], c["index"]) for c in bm25_candidates}

        all_unique_ids = set(dense_map.keys()) | set(bm25_map.keys())
        assert len(all_unique_ids) <= self.candidate_pool_max, f"Candidate pool exceeds max {self.candidate_pool_max}!"

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

            if d_rank is not None and b_rank is not None:
                source = "both"
            elif d_rank is not None:
                source = "dense_only"
            else:
                source = "bm25_only"

            rrf_candidates.append({
                "passage_id": p_id,
                "dense_rank": d_rank,
                "bm25_rank": b_rank,
                "rrf_score": round(score, 6),
                "retrieval_source": source,
                "index": idx
            })

        # Deterministic sorting: descending by rrf_score, then ascending by passage_id
        rrf_candidates.sort(key=lambda item: (-item["rrf_score"], item["passage_id"]))

        for rrf_rank, item in enumerate(rrf_candidates, 1):
            item["original_rrf_rank"] = rrf_rank

        t_rrf_ms = (time.perf_counter() - t_start) * 1000.0
        return rrf_candidates, round(t_rrf_ms, 2)

    def cross_encoder_rerank(
        self,
        query_text: str,
        candidate_pool: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], float]:
        """
        Reranks candidates using cross-encoder/ms-marco-MiniLM-L-6-v2.
        Input pairs: (query_text, original passage text).
        Deterministic sort: (-cross_encoder_score, passage_id ascending).
        Returns: (final_top5_passages, ce_candidate_traces, rerank_time_ms)
        """
        self._ensure_cross_encoder_model()
        t_start = time.perf_counter()

        if not candidate_pool:
            return [], [], 0.0

        # Construct pairs with verbatim original text
        pairs = []
        for item in candidate_pool:
            passage_obj = self.dense_metadata[item["index"]]
            p_text = passage_obj.get("text", "")
            pairs.append([query_text, p_text])

        inputs = self.cross_encoder_tokenizer(
            pairs,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )

        with torch.no_grad():
            outputs = self.cross_encoder_model(**inputs)
            logits = outputs.logits.squeeze(-1).tolist()
            if isinstance(logits, float):
                logits = [logits]

        ce_candidates = []
        for item, score in zip(candidate_pool, logits):
            ce_candidates.append({
                "passage_id": item["passage_id"],
                "index": item["index"],
                "cross_encoder_score": round(float(score), 5),
                "original_rrf_rank": item["original_rrf_rank"],
                "dense_rank": item["dense_rank"],
                "bm25_rank": item["bm25_rank"],
                "retrieval_source": item["retrieval_source"],
                "rrf_score": item["rrf_score"]
            })

        # Deterministic sort: (-cross_encoder_score, passage_id ascending)
        ce_candidates.sort(key=lambda x: (-x["cross_encoder_score"], x["passage_id"]))

        for ce_rank, item in enumerate(ce_candidates, 1):
            item["cross_encoder_rank"] = ce_rank

        final_top = ce_candidates[:self.final_top_k]
        final_passages = [self.dense_metadata[item["index"]] for item in final_top]

        t_ce_ms = (time.perf_counter() - t_start) * 1000.0
        return final_passages, ce_candidates, round(t_ce_ms, 2)

    def construct_context_prompt(self, query_text: str, passages: List[Dict[str, Any]]) -> str:
        """Constructs identical prompt as B2/B3/B4 with clearly delimited authoritative evidence."""
        lines = [
            "AUTHORITATIVE LEGAL EVIDENCE",
            "=" * 50
        ]

        for i, p in enumerate(passages, 1):
            p_id = p["passage_id"]
            d_set = "Dataset 1 (Statutory - Companies Act, 2013)" if p.get("dataset") == "dataset1" else "Dataset 2 (Judicial Precedent)"
            lines.append(f"\n[EVIDENCE PASSAGE {i}]")
            lines.append(f"Passage ID: {p_id}")
            lines.append(f"Source: {d_set}")
            if p.get("section_id"):
                lines.append(f"Statutory Section: {p['section_id']}")
            if p.get("heading"):
                lines.append(f"Heading: {p['heading']}")
            if p.get("case_title"):
                lines.append(f"Case: {p['case_title']}")
            if p.get("citation"):
                lines.append(f"Citation: {p['citation']}")
            lines.append(f"Text:\n{p['text'].strip()}")

        lines.append("=" * 50)
        lines.append("END AUTHORITATIVE LEGAL EVIDENCE\n")
        lines.append(f"User Legal Inquiry: {query_text.strip()}\n")
        lines.append(
            "Instructions: Based SOLELY on the authoritative legal evidence provided above, synthesize a complete, "
            "precise, and accurate answer to the inquiry. Cite relevant sections, clauses, and judicial precedents "
            "explicitly. If the provided evidence is silent or insufficient on any point, state that explicitly. "
            "Do NOT extrapolate beyond the supplied text."
        )
        return "\n".join(lines)

    def _select_next_key_idx(self) -> int:
        now = time.time()
        for offset in range(len(self.groq_api_keys)):
            idx = (self.current_key_idx + offset) % len(self.groq_api_keys)
            if self.key_cooldowns.get(idx, 0.0) <= now:
                self.current_key_idx = idx
                return idx
        min_idx = min(self.key_cooldowns, key=lambda i: self.key_cooldowns[i])
        self.current_key_idx = min_idx
        return min_idx

    def _mark_key_rate_limited(self, idx: int, wait_seconds: float = 60.0):
        self.key_cooldowns[idx] = time.time() + wait_seconds
        print(f"    [!] Groq Key {idx+1}/{len(self.groq_api_keys)} rate limited. Cooldown: {wait_seconds:.1f}s.")

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
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) HALO-Baseline5/1.0"
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
        """Executes full hybrid retrieval, RRF fusion, Cross-Encoder reranking, and generation."""
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

        # 3. Reciprocal Rank Fusion (Candidate Pool <= 10)
        rrf_cands, t_rrf = self.reciprocal_rank_fusion(dense_cands, bm25_cands)

        # 4. Cross-Encoder Reranking
        if mock_fn is not None and "mock_cross_encoder" in mock_fn:
            final_passages, ce_cands, t_ce = mock_fn["mock_cross_encoder"](query_text, rrf_cands)
        else:
            final_passages, ce_cands, t_ce = self.cross_encoder_rerank(query_text, rrf_cands)

        t_total_retrieval = round(t_dense + t_bm25 + t_rrf + t_ce, 2)
        final_top5_ids = [p["passage_id"] for p in final_passages]

        # 5. Context Prompt Formulation
        augmented_prompt = self.construct_context_prompt(query_text, final_passages)

        # 6. LLM Generation
        t_gen_start = time.perf_counter()
        if mock_fn is not None and "mock_llm" in mock_fn:
            ans = mock_fn["mock_llm"](augmented_prompt)
            gen_latency = (time.perf_counter() - t_gen_start) * 1000.0
            return {
                "dense_candidates": dense_cands,
                "bm25_candidates": bm25_cands,
                "rrf_candidates": rrf_cands,
                "cross_encoder_candidates": ce_cands,
                "final_top5_passage_ids": final_top5_ids,
                "final_passages": final_passages,
                "dense_retrieval_ms": t_dense,
                "bm25_retrieval_ms": t_bm25,
                "rrf_ms": t_rrf,
                "cross_encoder_ms": t_ce,
                "total_retrieval_ms": t_total_retrieval,
                "predicted_answer": ans,
                "generation_latency_ms": round(gen_latency, 2),
                "status": "SUCCESS",
                "error": None
            }

        attempt = 0
        base_delay = 2.0

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
                        "cross_encoder_candidates": ce_cands,
                        "final_top5_passage_ids": final_top5_ids,
                        "final_passages": final_passages,
                        "dense_retrieval_ms": t_dense,
                        "bm25_retrieval_ms": t_bm25,
                        "rrf_ms": t_rrf,
                        "cross_encoder_ms": t_ce,
                        "total_retrieval_ms": t_total_retrieval,
                        "predicted_answer": "[EMPTY_RESPONSE]",
                        "generation_latency_ms": round(gen_latency, 2),
                        "status": "EMPTY_RESPONSE",
                        "error": "Empty completion returned"
                    }
                return {
                    "dense_candidates": dense_cands,
                    "bm25_candidates": bm25_cands,
                    "rrf_candidates": rrf_cands,
                    "cross_encoder_candidates": ce_cands,
                    "final_top5_passage_ids": final_top5_ids,
                    "final_passages": final_passages,
                    "dense_retrieval_ms": t_dense,
                    "bm25_retrieval_ms": t_bm25,
                    "rrf_ms": t_rrf,
                    "cross_encoder_ms": t_ce,
                    "total_retrieval_ms": t_total_retrieval,
                    "predicted_answer": text,
                    "generation_latency_ms": round(gen_latency, 2),
                    "status": "SUCCESS",
                    "error": None
                }
            except urllib.error.HTTPError as e:
                attempt += 1
                if e.code == 429:
                    headers = dict(e.headers) if hasattr(e, "headers") and e.headers else {}
                    retry_after = headers.get("retry-after")
                    wait_s = float(retry_after) if retry_after else (base_delay * (2 ** min(attempt, 4)))
                    self._mark_key_rate_limited(active_idx, wait_seconds=wait_s)
                    if len(self.groq_api_keys) > 1:
                        print(f"    [!] Rotating to next key (Key {active_idx+1} 429)...")
                        time.sleep(1.0)
                        continue
                    else:
                        print(f"    [!] Rate limited. Waiting {wait_s:.1f}s before retry...")
                        time.sleep(wait_s)
                        continue
                elif e.code in (500, 502, 503, 504):
                    wait_s = base_delay * (2 ** min(attempt, 4))
                    print(f"    [!] Server error {e.code}. Waiting {wait_s:.1f}s...")
                    time.sleep(wait_s)
                    continue
                else:
                    err_msg = f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}"
                    print(f"    [!] Permanent HTTP error: {err_msg}")
                    return {
                        "dense_candidates": dense_cands,
                        "bm25_candidates": bm25_cands,
                        "rrf_candidates": rrf_cands,
                        "cross_encoder_candidates": ce_cands,
                        "final_top5_passage_ids": final_top5_ids,
                        "final_passages": final_passages,
                        "dense_retrieval_ms": t_dense,
                        "bm25_retrieval_ms": t_bm25,
                        "rrf_ms": t_rrf,
                        "cross_encoder_ms": t_ce,
                        "total_retrieval_ms": t_total_retrieval,
                        "predicted_answer": f"[API_ERROR: {err_msg}]",
                        "generation_latency_ms": round((time.perf_counter() - t_gen_start) * 1000.0, 2),
                        "status": "API_ERROR",
                        "error": err_msg
                    }
            except Exception as ex:
                attempt += 1
                wait_s = base_delay * (2 ** min(attempt, 4))
                print(f"    [!] Unexpected error: {ex}. Retrying in {wait_s:.1f}s...")
                time.sleep(wait_s)
                if attempt > 5:
                    return {
                        "dense_candidates": dense_cands,
                        "bm25_candidates": bm25_cands,
                        "rrf_candidates": rrf_cands,
                        "cross_encoder_candidates": ce_cands,
                        "final_top5_passage_ids": final_top5_ids,
                        "final_passages": final_passages,
                        "dense_retrieval_ms": t_dense,
                        "bm25_retrieval_ms": t_bm25,
                        "rrf_ms": t_rrf,
                        "cross_encoder_ms": t_ce,
                        "total_retrieval_ms": t_total_retrieval,
                        "predicted_answer": f"[FATAL_ERROR: {str(ex)}]",
                        "generation_latency_ms": round((time.perf_counter() - t_gen_start) * 1000.0, 2),
                        "status": "FATAL_ERROR",
                        "error": str(ex)
                    }

    def load_queries_for_split(self, split: str) -> List[Dict[str, Any]]:
        """Loads canonical Dataset 3 queries for the target split (64 DEV, 168 TEST)."""
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
            f"B5 Protocol Violation: Expected {expected_count} {split.upper()} records, found {len(filtered)}"
        )
        return filtered

    def run_split(self, split: str = "dev", limit: Optional[int] = None, dry_run: bool = False):
        """Executes full evaluation split under Baseline 5 with checkpointing and trace logging."""
        assert split in ("dev", "test"), f"Invalid split: {split}"
        os.makedirs(RUNS_DIR, exist_ok=True)
        out_path = os.path.join(RUNS_DIR, f"{split}_run_output.jsonl")

        queries = self.load_queries_for_split(split)
        if limit is not None:
            queries = queries[:limit]

        completed_records: Dict[str, Dict[str, Any]] = {}
        if os.path.exists(out_path):
            with open(out_path, "r", encoding="utf-8") as f:
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

        exp_id = f"EXP_B5_HYBRID_CE_{split.upper()}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_v1.0"
        print("=" * 70)
        print(f"  HALO BASELINE 5 (HYBRID + CROSS-ENCODER RERANKER) EXECUTION: {split.upper()} SPLIT")
        print(f"  System ID: {self.system_id}")
        print(f"  Reranker Model: {self.ce_model_name}")
        print(f"  Dense: {self.embedding_model_name} (Top-5)")
        print(f"  Sparse: BM25Okapi (Top-5)")
        print(f"  Fusion: RRF (k={self.rrf_k}, Pool<={self.candidate_pool_max}) -> CE -> Top-{self.final_top_k}")
        print(f"  LLM: groq | {self.model_name} (Temp=0.0, Seed=42)")
        print(f"  Total Queries: {len(queries)} | Completed: {len(completed_records)} | Remaining: {len(remaining_queries)}")
        print("=" * 70)

        successes = len(completed_records)
        failures = 0
        start_time = time.perf_counter()

        for idx, q_data in enumerate(remaining_queries, 1):
            prog = len(completed_records) + 1
            raw = q_data.get("raw_record", {})
            q_text = raw.get("query") or raw.get("claim") or q_data.get("query_or_claim", "")
            q_id = q_data.get("record_id")
            q_fam = q_data.get("benchmark_family", "UNKNOWN")

            print(f"[{prog:04d}/{len(queries):04d}] Query ID: {q_id} ({q_fam})... ", end="", flush=True)

            if dry_run:
                gen_result = {
                    "dense_candidates": [{"passage_id": f"DUMMY_{i}", "rank": i, "score": 1.0 - i*0.1} for i in range(1, 6)],
                    "bm25_candidates": [{"passage_id": f"DUMMY_{i}", "rank": i, "score": 10.0 - i} for i in range(1, 6)],
                    "rrf_candidates": [{"passage_id": f"DUMMY_{i}", "dense_rank": i, "bm25_rank": i, "rrf_score": 0.03, "retrieval_source": "both", "original_rrf_rank": i} for i in range(1, 6)],
                    "cross_encoder_candidates": [{"passage_id": f"DUMMY_{i}", "cross_encoder_score": 5.0 - i, "original_rrf_rank": i, "cross_encoder_rank": i} for i in range(1, 6)],
                    "final_top5_passage_ids": [f"DUMMY_{i}" for i in range(1, 6)],
                    "dense_retrieval_ms": 10.0,
                    "bm25_retrieval_ms": 5.0,
                    "rrf_ms": 0.1,
                    "cross_encoder_ms": 20.0,
                    "total_retrieval_ms": 35.1,
                    "predicted_answer": "[MOCK_DRY_RUN_ANSWER]",
                    "generation_latency_ms": 0.0,
                    "status": "SUCCESS",
                    "error": None
                }
            else:
                gen_result = self.generate_single_query(q_text)

            status = gen_result["status"]
            if status == "SUCCESS":
                successes += 1
                print(f"DONE (Dense: {gen_result['dense_retrieval_ms']:.1f}ms, BM25: {gen_result['bm25_retrieval_ms']:.1f}ms, RRF: {gen_result['rrf_ms']:.1f}ms, CE: {gen_result['cross_encoder_ms']:.1f}ms, Gen: {gen_result['generation_latency_ms']:.1f}ms)")
            else:
                failures += 1
                print(f"[{status}]: {gen_result['error']}")

            tot_lat = round(gen_result["total_retrieval_ms"] + gen_result["generation_latency_ms"], 2)

            record = {
                "experiment_id": exp_id,
                "system_id": self.system_id,
                "query_id": q_id,
                "benchmark_family": q_fam,
                "split": split,
                "query": q_text,
                "retrieval": {
                    "enabled": True,
                    "method": "hybrid_rrf_cross_encoder",
                    "top_k": self.final_top_k,
                    "rrf_k": self.rrf_k,
                    "dense_candidates": gen_result["dense_candidates"],
                    "bm25_candidates": gen_result["bm25_candidates"],
                    "rrf_candidates": gen_result["rrf_candidates"],
                    "cross_encoder_candidates": gen_result["cross_encoder_candidates"],
                    "retrieved_passage_ids": gen_result["final_top5_passage_ids"],
                    "dense_retrieval_latency_ms": gen_result["dense_retrieval_ms"],
                    "bm25_retrieval_latency_ms": gen_result["bm25_retrieval_ms"],
                    "rrf_latency_ms": gen_result["rrf_ms"],
                    "cross_encoder_latency_ms": gen_result["cross_encoder_ms"],
                    "retrieval_latency_ms": gen_result["total_retrieval_ms"]
                },
                "generation": {
                    "model": self.model_name,
                    "provider": "groq",
                    "predicted_answer": gen_result["predicted_answer"],
                    "generation_latency_ms": gen_result["generation_latency_ms"]
                },
                "verification": {
                    "enabled": False,
                    "verification_status": "SKIPPED_DISALLOWED_IN_BASELINE_5",
                    "fail_closed_triggered": False
                },
                "total_latency_ms": tot_lat,
                "timestamp_utc": datetime.now(timezone.utc).isoformat()
            }

            # Atomic append to file
            with open(out_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

            completed_records[q_id] = record

            # Rate limit pacing
            if not dry_run:
                time.sleep(1.8)

        total_elapsed = round(time.perf_counter() - start_time, 2)
        print(f"[+] Completed {split.upper()} run. Successes: {successes}, Failures: {failures}, Elapsed: {total_elapsed}s.")
        print(f"[+] Output sealed at: {os.path.relpath(out_path, BASE_DIR)}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run HALO Baseline 5 (Hybrid RAG + Cross-Encoder Reranking)")
    parser.add_argument("--split", choices=["dev", "test"], default="dev", help="Dataset split to evaluate")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of queries")
    parser.add_argument("--dry_run", action="store_true", help="Execute dry run without LLM API calls")
    args = parser.parse_args()

    runner = Baseline5Runner()
    runner.run_split(split=args.split, limit=args.limit, dry_run=args.dry_run)
