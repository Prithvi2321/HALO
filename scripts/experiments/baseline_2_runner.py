"""
HALO Baseline 2 — Dense Vector RAG Runner
==========================================
Executes Baseline 2 (Dense Retrieval + LLM Generation) under the frozen HALO Experiment Protocol v1.0.

Pipeline:
  User Query
      ↓
  BAAI/bge-large-en-v1.5 Query Encoding (with query instruction prefix)
      ↓
  Cosine Similarity Search against Frozen Corpus Index (2,773 passages)
      ↓
  Top-5 Retrieved Evidence Passages
      ↓
  Context-Augmented Prompt Construction (Delimited Authoritative Evidence)
      ↓
  Groq LLM Generation (qwen/qwen3.8-27b, temp=0.0, seed=42)
      ↓
  Live JSONL Streaming & Checkpoint Persistence

Strict Invariants:
  - Retrieval: Enabled (dense bi-encoder, Top-K=5).
  - Reranking: Disabled.
  - Verification: Disabled (verification_status="NOT_APPLICABLE").
  - Fail-Closed: Disabled (fail_closed_triggered=false).
  - Zero Leakage: Dataset 3 is strictly an evaluation query input.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(BASE_DIR, "experiments", "configs", "b2_dense_config.json")
INDEX_DIR = os.path.join(BASE_DIR, "experiments", "indices", "dense")
CANONICAL_D3_PATH = os.path.join(BASE_DIR, "data", "dataset3", "canonical", "dataset3_all.jsonl")
RUNS_DIR = os.path.join(BASE_DIR, "experiments", "runs", "b2_dense_rag")
LOG_PATH = os.path.join(RUNS_DIR, "execution.log")
CHECKPOINT_PATH = os.path.join(RUNS_DIR, "checkpoint.json")
RUN_MANIFEST_PATH = os.path.join(RUNS_DIR, "run_manifest.json")

SYSTEM_PROMPT = (
    "You are an authoritative Indian Legal Research Assistant specializing in the Companies Act, 2013 "
    "and Indian corporate jurisprudence. Answer the inquiry factually, accurately, and with precise statutory "
    "and judicial citations using the authoritative legal evidence provided below. If the provided context is "
    "insufficient or the proposition is unsupported, state so explicitly."
)


class Baseline2Runner:
    def __init__(self, config_path: str = CONFIG_PATH, api_key: Optional[str] = None):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.system_id = self.config.get("system_id", "B2_DENSE_RAG")
        self.provider = self.config.get("provider", "groq")
        self.model_name = self.config.get("model", "qwen/qwen3.8-27b")
        self.temperature = float(self.config.get("temperature", 0.0))
        self.top_p = float(self.config.get("top_p", 1.0))
        self.max_tokens = int(self.config.get("max_tokens", 512))
        self.seed = int(self.config.get("seed", 42))

        ret_cfg = self.config.get("retrieval", {})
        self.retrieval_enabled = ret_cfg.get("enabled", True)
        self.retrieval_method = ret_cfg.get("method", "dense")
        self.top_k = int(ret_cfg.get("top_k", 5))
        self.embedding_model_name = ret_cfg.get("embedding_model", "BAAI/bge-large-en-v1.5")
        self.query_instruction = ret_cfg.get("query_instruction", "Represent this sentence for searching relevant passages: ")

        # Enforce strict protocol invariants
        assert self.retrieval_enabled is True, "B2 Protocol error: retrieval must be enabled"
        assert self.retrieval_method == "dense", "B2 Protocol error: retrieval method must be dense"
        assert self.top_k == 5, "B2 Protocol error: Top-K must be 5"
        assert self.config.get("reranking_enabled") is False, "B2 Protocol error: reranking must be false"
        assert self.config.get("verification_enabled") is False, "B2 Protocol error: verification must be false"
        assert self.config.get("fail_closed_enabled") is False, "B2 Protocol error: fail-closed must be false"

        raw_key = api_key or os.environ.get("GROQ_API_KEY", "")
        if "," in raw_key:
            self.groq_api_keys = [k.strip() for k in raw_key.split(",") if k.strip()]
        elif raw_key.strip():
            self.groq_api_keys = [raw_key.strip()]
        else:
            self.groq_api_keys = []
        self.current_key_idx = 0
        self.groq_api_key = self.groq_api_keys[0] if self.groq_api_keys else None

        # In-memory index objects
        self.index_tensor = None
        self.passages_metadata: List[Dict[str, Any]] = []
        self.embedding_tokenizer = None
        self.embedding_model = None

    def load_dense_index(self):
        """Loads precomputed dense index tensor and metadata into memory."""
        if self.index_tensor is not None:
            return

        import torch
        index_file = os.path.join(INDEX_DIR, "index.pt")
        meta_file = os.path.join(INDEX_DIR, "metadata.jsonl")

        if not os.path.exists(index_file) or not os.path.exists(meta_file):
            raise FileNotFoundError(
                f"Dense index not found in {INDEX_DIR}. Run 'python -m scripts.experiments.build_dense_index' first!"
            )

        print(f"[*] Loading dense index tensor from: {os.path.relpath(index_file, BASE_DIR)}...")
        self.index_tensor = torch.load(index_file, map_location="cpu")
        print(f"    [+] Index tensor loaded: shape {self.index_tensor.shape}")

        print(f"[*] Loading passage metadata from: {os.path.relpath(meta_file, BASE_DIR)}...")
        self.passages_metadata = []
        with open(meta_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    self.passages_metadata.append(json.loads(line))
        print(f"    [+] Loaded {len(self.passages_metadata)} passage metadata records.")
        assert len(self.passages_metadata) == self.index_tensor.shape[0]

    def init_embedding_model(self):
        """Initializes the query embedding model on demand."""
        if self.embedding_model is not None:
            return

        from transformers import AutoTokenizer, AutoModel
        print(f"[*] Initializing query encoder: {self.embedding_model_name}...")
        self.embedding_tokenizer = AutoTokenizer.from_pretrained(self.embedding_model_name)
        self.embedding_model = AutoModel.from_pretrained(self.embedding_model_name)
        self.embedding_model.eval()
        print("    [+] Query encoder loaded into memory.")

    def retrieve(self, query_text: str) -> Tuple[List[Dict[str, Any]], List[float], float]:
        """
        Encodes query with prefix instruction and retrieves Top-K passages via cosine similarity.
        Returns: (top_passages, top_scores, retrieval_latency_ms)
        """
        self.load_dense_index()
        self.init_embedding_model()

        import torch
        import torch.nn.functional as F

        t_start = time.perf_counter()

        # Format with query instruction
        formatted_query = f"{self.query_instruction}{query_text}"

        inputs = self.embedding_tokenizer(
            [formatted_query],
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )

        with torch.no_grad():
            out = self.embedding_model(**inputs)
            q_emb = out[0][:, 0]
            q_norm = F.normalize(q_emb, p=2, dim=1)

            # Dot-product cosine similarity against normalized index
            scores = torch.matmul(q_norm, self.index_tensor.T).squeeze(0)
            top_scores_t, top_indices_t = torch.topk(scores, k=self.top_k)

        t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        top_indices = top_indices_t.tolist()
        top_scores = [round(float(s), 4) for s in top_scores_t.tolist()]
        top_passages = [self.passages_metadata[idx] for idx in top_indices]

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

    def _call_groq_api(self, prompt_text: str) -> str:
        if not self.groq_api_keys:
            raise ValueError("GROQ_API_KEY is not set.")
        active_key = self.groq_api_keys[self.current_key_idx]

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
                "User-Agent": "HALO-Baseline2/1.0"
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
        """Executes retrieval and generation for a single query."""
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
        consecutive_rotations = 0
        base_delay = 3.0

        while True:
            try:
                text = self._call_groq_api(augmented_prompt)
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
                    sleep_time = max(base_delay * (2 ** min(attempt, 4)), 4.0)
                    if hasattr(e, "headers") and e.headers and e.headers.get("retry-after"):
                        try:
                            sleep_time = float(e.headers.get("retry-after")) + 0.5
                        except Exception:
                            pass

                    # If sleep_time indicates rolling daily quota pause (>45s) and we have multiple keys
                    if sleep_time > 45.0 and len(self.groq_api_keys) > 1 and consecutive_rotations < len(self.groq_api_keys):
                        old_idx = self.current_key_idx
                        self.current_key_idx = (self.current_key_idx + 1) % len(self.groq_api_keys)
                        consecutive_rotations += 1
                        print(f"    [!] Quota pause on key {old_idx+1} ({sleep_time:.1f}s). Rotating to key {self.current_key_idx+1}/{len(self.groq_api_keys)}...")
                        time.sleep(2.0)
                        continue

                    # If all keys have quota pause or rate limit, wait the required sleep_time
                    consecutive_rotations = 0
                    attempt += 1
                    print(f"    [!] Rate limit reached. Backing off for {sleep_time:.1f}s (attempt {attempt})...")
                    time.sleep(sleep_time)
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

    def load_existing_completed_ids(self, filepath: str) -> Set[str]:
        completed = set()
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            rec = json.loads(line)
                            qid = rec.get("query_id")
                            if qid:
                                completed.add(qid)
                        except Exception:
                            pass
        return completed

    def run(self, split: str, max_queries: Optional[int] = None, resume: bool = True, mock_fn=None) -> Dict[str, Any]:
        queries = self.load_queries_for_split(split)
        if max_queries is not None:
            queries = queries[:max_queries]

        out_filename = f"{split}_run_output.jsonl"
        out_filepath = os.path.join(RUNS_DIR, out_filename)

        os.makedirs(RUNS_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

        existing_ids = self.load_existing_completed_ids(out_filepath) if resume else set()
        remaining_queries = [q for q in queries if q.get("record_id") not in existing_ids]

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        exp_id = f"EXP_B2_DENSE_{split.upper()}_{timestamp}_v1.0"

        print("=" * 70)
        print(f"  HALO BASELINE 2 (DENSE VECTOR RAG) EXECUTION: {split.upper()} SPLIT")
        print(f"  Experiment ID: {exp_id}")
        print(f"  Retriever: {self.embedding_model_name} (Top-K={self.top_k})")
        print(f"  LLM: {self.provider} | {self.model_name}")
        print(f"  Total Queries: {len(queries)} | Completed: {len(existing_ids)} | Remaining: {len(remaining_queries)}")
        print("=" * 70)

        if not remaining_queries:
            print(f"[*] All {len(queries)} queries for {split} split are already completed in {out_filename}!")
            return {
                "experiment_id": exp_id,
                "split": split,
                "total_queries": len(queries),
                "completed": len(queries),
                "remaining": 0,
                "output_file": out_filepath
            }

        successes = 0
        failures = 0
        start_time = datetime.now(timezone.utc)

        file_mode = "a" if resume and os.path.exists(out_filepath) else "w"
        with open(out_filepath, file_mode, encoding="utf-8") as out_f:
            for i, q_item in enumerate(remaining_queries, 1):
                raw = q_item.get("raw_record", {})
                q_text = raw.get("query") or raw.get("claim") or q_item.get("query_or_claim", "")
                q_id = q_item.get("record_id")
                b_family = q_item.get("benchmark_family")

                prog = len(existing_ids) + i
                print(f"[{prog:04d}/{len(queries):04d}] Query ID: {q_id} ({b_family})...", end=" ", flush=True)

                gen_res = self.generate_single_query(q_text, mock_fn=mock_fn)

                if gen_res["status"] == "SUCCESS":
                    successes += 1
                    tot_lat = gen_res["retrieval_latency_ms"] + gen_res["generation_latency_ms"]
                    print(f"DONE (Ret: {gen_res['retrieval_latency_ms']:.1f}ms, Gen: {gen_res['generation_latency_ms']:.1f}ms)")
                else:
                    failures += 1
                    tot_lat = gen_res["retrieval_latency_ms"] + gen_res["generation_latency_ms"]
                    print(f"[{gen_res['status']}]: {gen_res['error']}")

                record = {
                    "experiment_id": exp_id,
                    "system_id": self.system_id,
                    "query_id": q_id,
                    "benchmark_family": b_family,
                    "split": split,
                    "query": q_text,
                    "retrieval": {
                        "enabled": True,
                        "method": "dense",
                        "top_k": self.top_k,
                        "retrieved_passage_ids": gen_res["retrieved_passage_ids"],
                        "retrieval_scores": gen_res["retrieval_scores"],
                        "retrieval_latency_ms": gen_res["retrieval_latency_ms"]
                    },
                    "generation": {
                        "model": self.model_name,
                        "provider": self.provider,
                        "predicted_answer": gen_res["predicted_answer"],
                        "generation_latency_ms": gen_res["generation_latency_ms"]
                    },
                    "verification": {
                        "enabled": False,
                        "verification_status": "NOT_APPLICABLE",
                        "fail_closed_triggered": False
                    },
                    "total_latency_ms": round(tot_lat, 2),
                    "timestamp_utc": datetime.now(timezone.utc).isoformat()
                }

                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                out_f.flush()

                # Live checkpoint
                self.save_checkpoint(split, len(queries), prog, q_id)

                if mock_fn is None:
                    time.sleep(3.5)

        end_time = datetime.now(timezone.utc)

        # Append to audit log
        log_entry = (
            f"[{end_time.isoformat()}] Experiment: {exp_id} | System: {self.system_id} | "
            f"Retriever: {self.embedding_model_name} (Top-5) | LLM: {self.model_name} | Split: {split} | "
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
                "dev": os.path.join("experiments", "runs", "b2_dense_rag", "dev_run_output.jsonl"),
                "test": os.path.join("experiments", "runs", "b2_dense_rag", "test_run_output.jsonl")
            },
            "resume_command": f"python -m scripts.experiments.baseline_2_runner {current_split} --resume"
        }
        with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, indent=2)


if __name__ == "__main__":
    split_arg = sys.argv[1] if len(sys.argv) > 1 else "dev"
    resume_flag = "--resume" in sys.argv or "-r" in sys.argv or True
    runner = Baseline2Runner()
    runner.run(split_arg, resume=resume_flag)
