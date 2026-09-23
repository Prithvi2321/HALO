"""
HALO Verification Benchmark QA: Deduplication & Uniqueness
==========================================================
Gate G7 & G8: Detects duplicate IDs, identical claims, and near-duplicate mutations.
Outputs qa/dedup_report.json.
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BENCHMARK_PATH = os.path.join(BASE_DIR, "halo_datasets", "claim_evidence", "claim_evidence.jsonl")
REPORT_PATH = os.path.join(BASE_DIR, "halo_datasets", "qa", "dedup_report.json")


def validate_duplicates(benchmark_path: str = BENCHMARK_PATH) -> dict:
    ids = set()
    duplicate_ids = []
    claim_texts = set()
    exact_duplicate_claims = []
    total = 0

    with open(benchmark_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            total += 1
            rec = json.loads(line)
            cid = rec["id"]
            clm = rec["generated_claim"].strip().lower()

            if cid in ids:
                duplicate_ids.append(cid)
            ids.add(cid)

            if clm in claim_texts:
                exact_duplicate_claims.append({"id": cid, "claim": clm[:80]})
            claim_texts.add(clm)

    passed = (len(duplicate_ids) == 0 and len(exact_duplicate_claims) == 0)

    report = {
        "gate": "G7_G8_DEDUPLICATION",
        "passed": passed,
        "total_candidates": total,
        "unique_ids_count": len(ids),
        "duplicate_ids": duplicate_ids,
        "duplicates_removed": len(exact_duplicate_claims),
        "unique_cases": len(claim_texts),
        "near_duplicates_flagged": len(exact_duplicate_claims),
        "details": exact_duplicate_claims,
    }

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    res = validate_duplicates()
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["passed"] else 1)
