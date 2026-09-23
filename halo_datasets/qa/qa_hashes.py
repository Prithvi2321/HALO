"""
HALO Verification Benchmark QA: Content Hash Validation
=======================================================
Gate G15: Validates that every content_hash matches canonical SHA-256 computation byte-for-byte.
"""

import hashlib
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BENCHMARK_PATH = os.path.join(BASE_DIR, "halo_datasets", "claim_evidence", "claim_evidence.jsonl")

CANONICAL_KEYS = [
    "id", "query", "generated_claim", "citation", "expected_status",
    "authoritative_passage_id", "evidence_passage", "verification_tier",
    "difficulty", "source", "source_dataset", "case_type", "mutation_type",
    "mutation_details", "expected_behavior", "explanation"
]


def compute_expected_hash(rec: dict) -> str:
    payload = {k: rec.get(k) for k in CANONICAL_KEYS}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_hashes(benchmark_path: str = BENCHMARK_PATH) -> dict:
    total = 0
    mismatches = []

    with open(benchmark_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            total += 1
            rec = json.loads(line)
            cid = rec["id"]
            actual_hash = rec.get("content_hash")
            expected_hash = compute_expected_hash(rec)

            if actual_hash != expected_hash:
                mismatches.append({
                    "line": line_num,
                    "id": cid,
                    "actual": actual_hash,
                    "expected": expected_hash
                })

    passed = (len(mismatches) == 0 and total > 0)
    return {
        "gate": "G15_HASH_DETERMINISM",
        "passed": passed,
        "total_records_checked": total,
        "mismatches_count": len(mismatches),
        "mismatches": mismatches
    }


if __name__ == "__main__":
    res = validate_hashes()
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["passed"] else 1)
