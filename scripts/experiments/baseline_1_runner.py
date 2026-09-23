"""
HALO Baseline 1 — LLM-Only Runner
==================================
Executes the frozen Baseline 1 evaluation protocol with checkpointing & resume support.

Strict Protocol Guarantees:
  - Zero retrieval: No BM25, no vector search, no corpus passage injection.
  - Zero reranking.
  - Zero verification.
  - Zero fail-closed logic.
  - The model receives ONLY the standardized system prompt and the query.
  - Dataset 3 is consumed strictly as an evaluation query input.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(BASE_DIR, "experiments", "configs", "b1_llm_config.json")
CANONICAL_D3_PATH = os.path.join(BASE_DIR, "data", "dataset3", "canonical", "dataset3_all.jsonl")
RUNS_DIR = os.path.join(BASE_DIR, "experiments", "runs", "b1_llm_only")
LOG_PATH = os.path.join(BASE_DIR, "experiments", "logs", "execution_audit.log")
CHECKPOINT_PATH = os.path.join(RUNS_DIR, "checkpoint.json")

SYSTEM_PROMPT = (
    "You are an authoritative Indian Legal Research Assistant specializing in the Companies Act, 2013 "
    "and Indian corporate jurisprudence. Answer the inquiry factually, accurately, and with precise statutory "
    "and judicial citations. If the provided context is insufficient or the proposition is unsupported, state so explicitly."
)


class Baseline1Runner:
    def __init__(self, config_path: str = CONFIG_PATH, api_key: Optional[str] = None):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.system_id = self.config.get("system_id", "B1_LLM")
        self.provider = self.config.get("provider", "groq")
        self.model_name = self.config.get("model", "qwen/qwen3.8-27b")
        self.temperature = float(self.config.get("temperature", 0.0))
        self.top_p = float(self.config.get("top_p", 1.0))
        self.max_tokens = int(self.config.get("max_tokens", 512))
        self.seed = int(self.config.get("seed", 42))

        # Enforce strict zero-retrieval protocol invariants
        assert self.config.get("retrieval_enabled") is False, "Protocol violation: retrieval_enabled must be false"
        assert self.config.get("reranking_enabled") is False, "Protocol violation: reranking_enabled must be false"
        assert self.config.get("verification_enabled") is False, "Protocol violation: verification_enabled must be false"
        assert self.config.get("fail_closed_enabled") is False, "Protocol violation: fail_closed_enabled must be false"

        self.groq_api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.gemini_api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self._genai_model = None

    def _call_groq_api(self, query_text: str) -> str:
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY is not set.")

        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query_text}
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
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json",
                "User-Agent": "HALO-Baseline1/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            choices = resp_data.get("choices", [])
            if not choices:
                return ""
            msg = choices[0].get("message", {})
            return msg.get("content", "").strip()

    def _call_gemini_api(self, query_text: str) -> str:
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set.")

        if self._genai_model is None:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_api_key)
            self._genai_model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=SYSTEM_PROMPT,
                generation_config={
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "max_output_tokens": self.max_tokens,
                }
            )

        resp = self._genai_model.generate_content(query_text)
        return resp.text.strip() if resp and resp.text else ""

    def generate_single_query(self, query_text: str, mock_fn=None) -> Dict[str, Any]:
        """
        Executes a single query with zero retrieval.
        Returns dict containing predicted_answer, latency_ms, status, error.
        """
        assert "PAS_" not in query_text, "Query text must not contain passage context"

        t_start = time.perf_counter()

        if mock_fn is not None:
            ans = mock_fn(query_text)
            t_elapsed = (time.perf_counter() - t_start) * 1000.0
            return {
                "predicted_answer": ans,
                "latency_ms": round(t_elapsed, 2),
                "status": "SUCCESS",
                "error": None
            }

        max_retries = 5
        base_delay = 3.0

        for attempt in range(max_retries):
            try:
                if self.provider == "groq":
                    text = self._call_groq_api(query_text)
                else:
                    text = self._call_gemini_api(query_text)

                t_elapsed = (time.perf_counter() - t_start) * 1000.0
                if not text:
                    return {
                        "predicted_answer": "[EMPTY_RESPONSE]",
                        "latency_ms": round(t_elapsed, 2),
                        "status": "EMPTY_RESPONSE",
                        "error": "Model returned empty response"
                    }
                return {
                    "predicted_answer": text,
                    "latency_ms": round(t_elapsed, 2),
                    "status": "SUCCESS",
                    "error": None
                }
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "rate" in err_str.lower() or "quota" in err_str.lower():
                    sleep_time = max(base_delay * (2 ** attempt), 4.0)
                    if hasattr(e, "headers") and e.headers and e.headers.get("retry-after"):
                        try:
                            sleep_time = float(e.headers.get("retry-after")) + 0.5
                        except Exception:
                            pass
                    print(f"    [!] Rate limited. Backing off for {sleep_time:.1f}s (attempt {attempt+1}/{max_retries})...")
                    time.sleep(sleep_time)
                else:
                    t_elapsed = (time.perf_counter() - t_start) * 1000.0
                    return {
                        "predicted_answer": f"[API_ERROR: {err_str}]",
                        "latency_ms": round(t_elapsed, 2),
                        "status": "FAILED",
                        "error": err_str
                    }

        t_elapsed = (time.perf_counter() - t_start) * 1000.0
        return {
            "predicted_answer": "[RATE_LIMIT_EXHAUSTED]",
            "latency_ms": round(t_elapsed, 2),
            "status": "RATE_LIMITED",
            "error": "Exhausted retries due to quota rate limits."
        }

    def load_queries_for_split(self, split: str) -> List[Dict[str, Any]]:
        """
        Loads queries strictly belonging to the requested split from Dataset 3.
        """
        if split not in ["dev", "test"]:
            raise ValueError(f"Invalid split '{split}'. Must be 'dev' or 'test'.")

        records = []
        with open(CANONICAL_D3_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                rec_split = item.get("split")
                if split == "dev" and rec_split == "dev":
                    records.append(item)
                elif split == "test" and rec_split == "test":
                    records.append(item)
        return records

    def load_existing_completed_ids(self, filepath: str) -> Set[str]:
        completed = set()
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        rec = json.loads(line)
                        qid = rec.get("query_id")
                        if qid:
                            completed.add(qid)
                    except Exception:
                        pass
        return completed

    def run(self, split: str, max_queries: Optional[int] = None, resume: bool = True, mock_fn=None) -> Dict[str, Any]:
        """
        Executes Baseline 1 on the designated split with resume support.
        """
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
        exp_id = f"EXP_B1_LLM_{split.upper()}_{timestamp}_v1.0"

        print("=" * 70)
        print(f"  HALO BASELINE 1 (LLM-ONLY) EXECUTION: {split.upper()} SPLIT")
        print(f"  Experiment ID: {exp_id}")
        print(f"  Provider: {self.provider} | Model: {self.model_name}")
        print(f"  Total Split Queries: {len(queries)} | Previously Completed: {len(existing_ids)} | Remaining: {len(remaining_queries)}")
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
                    print(f"DONE ({gen_res['latency_ms']:.1f}ms)")
                else:
                    failures += 1
                    print(f"[{gen_res['status']}]: {gen_res['error']}")

                record = {
                    "experiment_id": exp_id,
                    "system_id": self.system_id,
                    "query_id": q_id,
                    "benchmark_family": b_family,
                    "split": split,
                    "query": q_text,
                    "retrieval": {
                        "enabled": False,
                        "retrieved_passage_ids": [],
                        "retrieval_latency_ms": 0.0
                    },
                    "generation": {
                        "predicted_answer": gen_res["predicted_answer"],
                        "generation_latency_ms": gen_res["latency_ms"]
                    },
                    "verification": {
                        "enabled": False,
                        "verification_status": "NOT_APPLICABLE",
                        "fail_closed_triggered": False
                    },
                    "total_latency_ms": gen_res["latency_ms"],
                    "timestamp_utc": datetime.now(timezone.utc).isoformat()
                }

                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                out_f.flush()

                # Save checkpoint update
                self.save_checkpoint(split, len(queries), prog, q_id)

                if mock_fn is None:
                    time.sleep(3.5)

        end_time = datetime.now(timezone.utc)

        # Append to audit log
        log_entry = (
            f"[{end_time.isoformat()}] Experiment: {exp_id} | System: {self.system_id} | "
            f"Provider: {self.provider} | Model: {self.model_name} | Split: {split} | "
            f"Processed: {len(remaining_queries)} | Successes: {successes} | Failures: {failures} | "
            f"Duration: {(end_time - start_time).total_seconds():.2f}s\n"
        )
        with open(LOG_PATH, "a", encoding="utf-8") as lf:
            lf.write(log_entry)

        print("\n" + "=" * 70)
        print(f"  RUN FINISHED. Outputs saved to: {os.path.relpath(out_filepath, BASE_DIR)}")
        print(f"  Processed in this run: {len(remaining_queries)} | Successes: {successes} | Failures: {failures}")
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

    def save_checkpoint(self, current_split: str, total_split_queries: int, completed_count: int, last_query_id: str):
        checkpoint_data = {
            "system_id": self.system_id,
            "current_split": current_split,
            "status": "CHECKPOINT_SAVED",
            "last_saved_utc": datetime.now(timezone.utc).isoformat(),
            "split_progress": {
                "total_queries": total_split_queries,
                "completed_queries": completed_count,
                "remaining_queries": total_split_queries - completed_count,
                "last_processed_query_id": last_query_id
            },
            "output_files": {
                "dev": os.path.join("experiments", "runs", "b1_llm_only", "dev_run_output.jsonl"),
                "test": os.path.join("experiments", "runs", "b1_llm_only", "test_run_output.jsonl")
            },
            "resume_command": f"python -m scripts.experiments.baseline_1_runner {current_split} --resume"
        }
        with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, indent=2)


if __name__ == "__main__":
    split_arg = sys.argv[1] if len(sys.argv) > 1 else "dev"
    resume_flag = "--resume" in sys.argv or "-r" in sys.argv or True
    runner = Baseline1Runner()
    runner.run(split_arg, resume=resume_flag)
