"""
HALO Baseline 3 — Sparse BM25 RAG Runner
========================================
Executes Baseline 3 under the frozen HALO Experiment Protocol v1.0.

Pipeline:
  User Query
      ↓
  BM25 Sparse Retrieval (Top-K=5)
      ↓
  Delimited Authoritative Context Injection
      ↓
  LLM Generation (qwen/qwen3.8-27b via Groq, temp=0.0, top-p=1.0, seed=42)
      ↓
  Answer

Invariants:
  - Retrieval method strictly 'bm25' (BM25Okapi, k1=1.5, b=0.75, epsilon=0.25).
  - Exactly Top-K=5 passages retrieved.
  - Zero dense retrieval, zero RRF, zero reranking, zero verification, zero fail-closed.
  - Granular live checkpointing & automatic multi-key rotation across Groq keys.
"""

import os
import sys
import json
import time
import pickle
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from scripts.experiments.build_bm25_index import (
    tokenize_legal_text,
    TOKEN_PATTERN,
    EFFECTIVE_STOPWORDS
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(BASE_DIR, "experiments", "configs", "b3_bm25_config.json")
RUNS_DIR = os.path.join(BASE_DIR, "experiments", "runs", "b3_bm25")
INDEX_DIR = os.path.join(BASE_DIR, "experiments", "indices", "bm25")
CHECKPOINT_PATH = os.path.join(RUNS_DIR, "checkpoint.json")
LOG_PATH = os.path.join(RUNS_DIR, "execution.log")

CANONICAL_D3_PATH = os.path.join(BASE_DIR, "data", "dataset3", "canonical", "dataset3_all.jsonl")

SYSTEM_PROMPT = (
    "You are an authoritative Indian Legal Research Assistant specializing in the Companies Act, 2013 "
    "and Indian corporate jurisprudence. Answer the inquiry factually, accurately, and with precise statutory "
    "and judicial citations using the authoritative legal evidence provided below. "
    "If the provided context is insufficient or the proposition is unsupported, state so explicitly."
)


class Baseline3Runner:
    def __init__(self, config_path: str = CONFIG_PATH, api_key: Optional[str] = None):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.system_id = self.config.get("system_id", "B3_SPARSE_BM25")
        self.provider = self.config.get("provider", "groq")
        self.model_name = self.config.get("model", "qwen/qwen3.8-27b")
        self.temperature = float(self.config.get("temperature", 0.0))
        self.top_p = float(self.config.get("top_p", 1.0))
        self.max_tokens = int(self.config.get("max_tokens", 512))
        self.seed = int(self.config.get("seed", 42))

        ret_cfg = self.config.get("retrieval", {})
        self.retrieval_enabled = ret_cfg.get("enabled", True)
        self.retrieval_method = ret_cfg.get("method", "bm25")
        self.top_k = int(ret_cfg.get("top_k", 5))
        self.k1 = float(ret_cfg.get("k1", 1.5))
        self.b = float(ret_cfg.get("b", 0.75))
        self.epsilon = float(ret_cfg.get("epsilon", 0.25))

        # Enforce strict protocol invariants
        assert self.retrieval_enabled is True, "B3 Protocol error: retrieval must be enabled"
        assert self.retrieval_method == "bm25", "B3 Protocol error: retrieval method must be bm25"
        assert self.top_k == 5, "B3 Protocol error: Top-K must be 5"
        assert self.config.get("dense_retrieval_enabled") is False, "B3 Protocol error: dense retrieval must be false"
        assert self.config.get("reranking_enabled") is False, "B3 Protocol error: reranking must be false"
        assert self.config.get("verification_enabled") is False, "B3 Protocol error: verification must be false"
        assert self.config.get("fail_closed_enabled") is False, "B3 Protocol error: fail-closed must be false"

        raw_key = api_key or os.environ.get("GROQ_API_KEY", "")
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
        self.bm25_model = None
        self.passages_metadata: List[Dict[str, Any]] = []

    def load_bm25_index(self):
        """Loads precomputed BM25 index and metadata into memory."""
        if self.bm25_model is not None:
            return

        model_file = os.path.join(INDEX_DIR, "index", "bm25_model.pkl")
        meta_file = os.path.join(INDEX_DIR, "metadata.jsonl")

        if not os.path.exists(model_file) or not os.path.exists(meta_file):
            raise FileNotFoundError(
                f"BM25 index not found in {INDEX_DIR}. Run 'python -m scripts.experiments.build_bm25_index' first!"
            )

        print(f"[*] Loading BM25 index model from: {os.path.relpath(model_file, BASE_DIR)}...")
        with open(model_file, "rb") as f:
            self.bm25_model = pickle.load(f)
        print("    [+] BM25 model loaded into memory.")

        print(f"[*] Loading passage metadata from: {os.path.relpath(meta_file, BASE_DIR)}...")
        self.passages_metadata = []
        with open(meta_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    self.passages_metadata.append(json.loads(line))
        print(f"    [+] Loaded {len(self.passages_metadata)} passage metadata records.")
        assert len(self.passages_metadata) == self.bm25_model.corpus_size

    def retrieve(self, query_text: str) -> Tuple[List[Dict[str, Any]], List[float], float]:
        """
        Tokenizes query with legal tokenizer and scores all 2,773 passages using BM25Okapi.
        Ties are broken deterministically by passage_id ascending.
        Returns: (top_passages, top_scores, retrieval_latency_ms)
        """
        self.load_bm25_index()

        t_start = time.perf_counter()
        query_tokens = tokenize_legal_text(query_text)

        scores = self.bm25_model.get_scores(query_tokens)

        # Pair scores with passage index and passage_id for deterministic tie-breaking
        scored_candidates = []
        for idx, s in enumerate(scores):
            p_id = self.passages_metadata[idx]["passage_id"]
            scored_candidates.append((float(s), p_id, idx))

        # Sort descending by score, then ascending by passage_id
        scored_candidates.sort(key=lambda item: (-item[0], item[1]))

        top_candidates = scored_candidates[:self.top_k]
        t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        top_passages = [self.passages_metadata[idx] for _, _, idx in top_candidates]
        top_scores = [round(score, 4) for score, _, _ in top_candidates]

        return top_passages, top_scores, round(t_elapsed_ms, 2)

    def construct_context_prompt(self, query_text: str, passages: List[Dict[str, Any]]) -> str:
        """Constructs the augmented prompt with clearly delimited authoritative evidence."""
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
        """Selects the next available key index, or the key with shortest remaining cooldown."""
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
                "User-Agent": "HALO-Baseline3/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            choices = resp_data.get("choices", [])
            if not choices:
                return ""
            msg = choices[0].get("message", {})
            return msg.get("content", "").strip()

    def generate_single_query(self, query_text: str, mock_fn=None) -> Dict[str, Any]:
        """Executes sparse retrieval and generation for a single query."""
        # 1. Retrieval
        if mock_fn is not None and "mock_retrieval" in mock_fn:
            passages, scores, ret_latency = mock_fn["mock_retrieval"](query_text)
        else:
            passages, scores, ret_latency = self.retrieve(query_text)

        passage_ids = [p["passage_id"] for p in passages]

        # 2. Context Injection
        augmented_prompt = self.construct_context_prompt(query_text, passages)

        # 3. LLM Generation
        t_gen_start = time.perf_counter()
        if mock_fn is not None and "mock_llm" in mock_fn:
            ans = mock_fn["mock_llm"](augmented_prompt)
            gen_latency = (time.perf_counter() - t_gen_start) * 1000.0
            return {
                "retrieved_passage_ids": passage_ids,
                "retrieval_scores": scores,
                "retrieval_latency_ms": ret_latency,
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
                sleep_duration = min(cooldown_left + 0.5, 30.0)
                print(f"    [!] Keys cooling down. Waiting {sleep_duration:.1f}s for key {active_idx+1}...")
                time.sleep(sleep_duration)

            try:
                text = self._call_groq_api(augmented_prompt, key_idx=active_idx)
                gen_latency = (time.perf_counter() - t_gen_start) * 1000.0
                if not text:
                    return {
                        "retrieved_passage_ids": passage_ids,
                        "retrieval_scores": scores,
                        "retrieval_latency_ms": ret_latency,
                        "predicted_answer": "[EMPTY_RESPONSE]",
                        "generation_latency_ms": round(gen_latency, 2),
                        "status": "EMPTY_RESPONSE",
                        "error": "Model returned empty response"
                    }
                if len(self.groq_api_keys) > 1:
                    self.current_key_idx = (active_idx + 1) % len(self.groq_api_keys)
                return {
                    "retrieved_passage_ids": passage_ids,
                    "retrieval_scores": scores,
                    "retrieval_latency_ms": ret_latency,
                    "predicted_answer": text,
                    "generation_latency_ms": round(gen_latency, 2),
                    "status": "SUCCESS",
                    "error": None
                }
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "rate" in err_str.lower() or "quota" in err_str.lower():
                    sleep_time = max(base_delay * (2 ** min(attempt, 4)), 5.0)
                    if hasattr(e, "headers") and e.headers and e.headers.get("retry-after"):
                        try:
                            sleep_time = float(e.headers.get("retry-after")) + 0.5
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
                        min_wait = min(max(0.0, self.key_cooldowns.get(i, 0.0) - now) for i in self.key_cooldowns)
                        wait_time = min(min_wait + 0.5, 30.0)
                        if wait_time > 0:
                            print(f"    [!] All keys cooling down. Sleeping shortest cooldown: {wait_time:.1f}s...")
                            time.sleep(wait_time)
                        continue
                elif ("11001" in err_str or "getaddrinfo" in err_str) and attempt < 3:
                    attempt += 1
                    print(f"    [!] DNS lookup error ({err_str}). Backing off for 10.0s before retrying (attempt {attempt}/3)...")
                    time.sleep(10.0)
                else:
                    gen_latency = (time.perf_counter() - t_gen_start) * 1000.0
                    return {
                        "retrieved_passage_ids": passage_ids,
                        "retrieval_scores": scores,
                        "retrieval_latency_ms": ret_latency,
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
                if not line.strip():
                    continue
                item = json.loads(line)
                if item.get("split") == split:
                    records.append(item)
        return records

    def run(self, split: str = "dev", resume: bool = True, mock_fn=None) -> Dict[str, Any]:
        os.makedirs(RUNS_DIR, exist_ok=True)
        queries = self.load_queries_for_split(split)
        out_filename = f"{split}_run_output.jsonl"
        out_filepath = os.path.join(RUNS_DIR, out_filename)

        existing_ids = set()
        if resume and os.path.exists(out_filepath):
            with open(out_filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            item = json.loads(line)
                            ans = item.get("generation", {}).get("predicted_answer", "")
                            # Only treat genuinely valid responses as completed
                            if not ans.startswith("[API_ERROR") and ans not in ["[RATE_LIMITED]", "[EMPTY_RESPONSE]"]:
                                existing_ids.add(item["query_id"])
                        except Exception:
                            pass

        remaining_queries = [q for q in queries if q["record_id"] not in existing_ids]

        exp_id = f"EXP_B3_BM25_{split.upper()}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_v1.0"
        print("=" * 70)
        print(f"  HALO BASELINE 3 (SPARSE BM25 RAG) EXECUTION: {split.upper()} SPLIT")
        print(f"  Experiment ID: {exp_id}")
        print(f"  Retriever: BM25Okapi (k1={self.k1}, b={self.b}, Top-K={self.top_k})")
        print(f"  LLM: {self.provider} | {self.model_name}")
        print(f"  Total Queries: {len(queries)} | Completed: {len(existing_ids)} | Remaining: {len(remaining_queries)}")
        print("=" * 70)

        successes = 0
        failures = 0
        start_time = datetime.now(timezone.utc)

        mode = "a" if resume and os.path.exists(out_filepath) else "w"
        with open(out_filepath, mode, encoding="utf-8") as out_f:
            for idx, q_data in enumerate(remaining_queries, 1):
                prog = len(existing_ids) + idx
                raw = q_data.get("raw_record", {})
                q_text = raw.get("query") or raw.get("claim") or q_data.get("query_or_claim", "")
                q_id = q_data.get("record_id")
                q_fam = q_data.get("benchmark_family", "UNKNOWN")

                print(f"[{prog:04d}/{len(queries):04d}] Query ID: {q_id} ({q_fam})... ", end="", flush=True)

                res = self.generate_single_query(q_text, mock_fn=mock_fn)

                status = res["status"]
                if status == "SUCCESS":
                    successes += 1
                    print(f"DONE (Ret: {res['retrieval_latency_ms']:.1f}ms, Gen: {res['generation_latency_ms']:.1f}ms)")
                else:
                    failures += 1
                    print(f"[{status}]: {res['error']}")

                tot_lat = round(res["retrieval_latency_ms"] + res["generation_latency_ms"], 2)

                record = {
                    "experiment_id": exp_id,
                    "system_id": self.system_id,
                    "query_id": q_id,
                    "benchmark_family": q_fam,
                    "split": split,
                    "query": q_text,
                    "retrieval": {
                        "enabled": True,
                        "method": "bm25",
                        "top_k": self.top_k,
                        "bm25_params": {
                            "algorithm": "BM25Okapi",
                            "k1": self.k1,
                            "b": self.b,
                            "epsilon": self.epsilon
                        },
                        "retrieved_passage_ids": res["retrieved_passage_ids"],
                        "retrieval_scores": res["retrieval_scores"],
                        "retrieval_latency_ms": res["retrieval_latency_ms"]
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

                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                out_f.flush()

                # Live checkpoint
                self.save_checkpoint(split, len(queries), prog, q_id)

                if mock_fn is None:
                    time.sleep(1.0 if len(self.groq_api_keys) > 1 else 3.5)

        end_time = datetime.now(timezone.utc)

        # Append to audit log
        log_entry = (
            f"[{end_time.isoformat()}] Experiment: {exp_id} | System: {self.system_id} | "
            f"Retriever: BM25Okapi (Top-5) | LLM: {self.model_name} | Split: {split} | "
            f"Processed: {len(remaining_queries)} | Successes: {successes} | Failures: {failures} | "
            f"Duration: {(end_time - start_time).total_seconds():.2f}s\n"
        )
        with open(LOG_PATH, "a", encoding="utf-8") as lf:
            lf.write(log_entry)

        # Checkpoint completion status
        if len(existing_ids) + len(remaining_queries) == len(queries):
            self.save_checkpoint(split, len(queries), len(queries), remaining_queries[-1].get("record_id"), status="COMPLETED")

        print("\n" + "=" * 70)
        print(f"  RUN FINISHED. Outputs saved to: {os.path.relpath(out_filepath, BASE_DIR)}")
        print(f"  Processed: {len(remaining_queries)} | Successes: {successes} | Failures: {failures}")
        print("=" * 70)

        return {
            "experiment_id": exp_id,
            "split": split,
            "total_queries": len(queries),
            "completed": len(existing_ids) + len(remaining_queries),
            "successes": successes,
            "failures": failures,
            "output_file": out_filepath
        }

    def save_checkpoint(self, current_split: str, total_split_queries: int, completed_count: int, last_query_id: str, status: str = "CHECKPOINT_SAVED"):
        checkpoint_data = {
            "system_id": self.system_id,
            "current_split": current_split,
            "status": status,
            "last_saved_utc": datetime.now(timezone.utc).isoformat(),
            "split_progress": {
                "total_queries": total_split_queries,
                "completed_queries": completed_count,
                "remaining_queries": total_split_queries - completed_count,
                "last_processed_query_id": last_query_id
            },
            "output_files": {
                "dev": os.path.join("experiments", "runs", "b3_bm25", "dev_run_output.jsonl"),
                "test": os.path.join("experiments", "runs", "b3_bm25", "test_run_output.jsonl")
            },
            "resume_command": f"python -m scripts.experiments.baseline_3_runner {current_split} --resume"
        }
        with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, indent=2)


if __name__ == "__main__":
    split_arg = sys.argv[1] if len(sys.argv) > 1 else "dev"
    resume_flag = "--resume" in sys.argv or "-r" in sys.argv or True
    runner = Baseline3Runner()
    runner.run(split_arg, resume=resume_flag)
