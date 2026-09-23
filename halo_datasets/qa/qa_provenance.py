"""
HALO Verification Benchmark QA: Provenance Validation
=====================================================
Gate G3: Verifies that every authoritative passage ID is traceable to Dataset 1 or Dataset 2.
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D1_PASSAGES = os.path.join(BASE_DIR, "data", "dataset_1", "final", "companies_act_2013_passages.jsonl")
D2_PASSAGES = os.path.join(BASE_DIR, "data", "dataset2", "canonical", "passages.jsonl")


def validate_provenance(benchmark_path: str) -> dict:
    d1_ids = set()
    if os.path.exists(D1_PASSAGES):
        with open(D1_PASSAGES, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    d1_ids.add(json.loads(line)["passage_id"])

    d2_ids = set()
    if os.path.exists(D2_PASSAGES):
        with open(D2_PASSAGES, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    d2_ids.add(json.loads(line)["passage_id"])

    valid_corpus_ids = d1_ids.union(d2_ids)

    errors = []
    untraceable = []
    total = 0
    grounded_count = 0
    fail_closed_count = 0

    with open(benchmark_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            total += 1
            rec = json.loads(line)
            cid = rec["id"]
            pid = rec.get("authoritative_passage_id")

            if pid == "NONE":
                fail_closed_count += 1
                # Fail-closed / fabricated citations must have source explicitly documented
                if not rec.get("source"):
                    errors.append(f"Record {cid}: pid is NONE but source description missing")
            else:
                grounded_count += 1
                if pid not in valid_corpus_ids:
                    untraceable.append({"case_id": cid, "passage_id": pid})
                    errors.append(f"Record {cid}: passage_id '{pid}' not found in D1 or D2")

    return {
        "gate": "G3_PROVENANCE_VALIDATION",
        "passed": len(untraceable) == 0,
        "total_records": total,
        "grounded_records": grounded_count,
        "unsupported_fail_closed_records": fail_closed_count,
        "untraceable_ids": untraceable,
        "errors": errors,
    }


if __name__ == "__main__":
    b_file = os.path.join(os.path.dirname(__file__), "..", "claim_evidence", "claim_evidence.jsonl")
    res = validate_provenance(b_file)
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["passed"] else 1)
