"""
HALO Verification Benchmark QA: Contamination Audit
===================================================
Gate G5 & G6: Audits for zero data leakage or contamination against:
- Dataset 3 canonical benchmark queries and answers (data/dataset3/canonical/dataset3_all.jsonl)
- Baseline 1-5 evaluation query logs
Outputs qa/contamination_report.json.
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BENCHMARK_PATH = os.path.join(BASE_DIR, "halo_datasets", "claim_evidence", "claim_evidence.jsonl")
D3_CANONICAL_PATH = os.path.join(BASE_DIR, "data", "dataset3", "canonical", "dataset3_all.jsonl")
REPORT_PATH = os.path.join(BASE_DIR, "halo_datasets", "qa", "contamination_report.json")


def load_d3_queries():
    d3_queries = set()
    if os.path.exists(D3_CANONICAL_PATH):
        with open(D3_CANONICAL_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    raw = r.get("raw_record") if isinstance(r.get("raw_record"), dict) else {}
                    q = r.get("query_or_claim") or r.get("query") or raw.get("query", "")
                    q = q.strip().lower() if isinstance(q, str) else ""
                    if q:
                        d3_queries.add(q)
    return d3_queries


def load_baseline_queries():
    b_queries = set()
    runs_dir = os.path.join(BASE_DIR, "experiments", "runs")
    if os.path.exists(runs_dir):
        for root, _, files in os.walk(runs_dir):
            for file in files:
                if file.endswith("_run_output.jsonl"):
                    fp = os.path.join(root, file)
                    with open(fp, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                try:
                                    r = json.loads(line)
                                    q = r.get("query", "").strip().lower()
                                    if q:
                                        b_queries.add(q)
                                except Exception:
                                    continue
    return b_queries


def validate_contamination(benchmark_path: str = BENCHMARK_PATH) -> dict:
    d3_queries = load_d3_queries()
    b_queries = load_baseline_queries()

    d3_overlaps = []
    baseline_overlaps = []
    total_checked = 0

    with open(benchmark_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            total_checked += 1
            rec = json.loads(line)
            cid = rec["id"]
            bq = rec.get("query", "").strip().lower()

            if bq in d3_queries:
                d3_overlaps.append({"id": cid, "query": bq})

            if bq in b_queries:
                baseline_overlaps.append({"id": cid, "query": bq})

    is_clean = (len(d3_overlaps) == 0 and len(baseline_overlaps) == 0)

    report = {
        "gate": "G5_G6_CONTAMINATION_AUDIT",
        "passed": is_clean,
        "total_benchmark_records_checked": total_checked,
        "d3_canonical_queries_indexed": len(d3_queries),
        "baseline_evaluation_queries_indexed": len(b_queries),
        "d3_overlap_count": len(d3_overlaps),
        "d3_overlaps": d3_overlaps,
        "baseline_overlap_count": len(baseline_overlaps),
        "baseline_overlaps": baseline_overlaps,
        "contamination_status": "ZERO_CONTAMINATION" if is_clean else "CONTAMINATION_DETECTED"
    }

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    res = validate_contamination()
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["passed"] else 1)
