"""
HALO Verification Benchmark QA: Schema Validation
=================================================
Gate G1 & G2: Verifies schema conformance and required fields across all records.
"""

import json
import os
import sys
from typing import Dict, Any

REQUIRED_FIELDS = [
    "id", "query", "generated_claim", "citation", "expected_status",
    "authoritative_passage_id", "evidence_passage", "verification_tier",
    "difficulty", "source", "source_dataset", "case_type", "mutation_type",
    "mutation_details", "expected_behavior", "explanation", "content_hash"
]

VALID_STATUSES = {
    "SUPPORTED", "PARTIALLY_SUPPORTED", "CONTRADICTED",
    "UNSUPPORTED", "FABRICATED_CITATION", "FLAGGED"
}

VALID_TIERS = {
    "EXISTENCE", "METADATA", "PASSAGE_SUPPORT", "TEMPORAL", "CONFLICT", "FAIL_CLOSED"
}

VALID_DIFFICULTIES = {"easy", "medium", "hard"}


def validate_schema(file_path: str) -> Dict[str, Any]:
    errors = []
    total = 0

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            total += 1
            try:
                rec = json.loads(line)
            except Exception as e:
                errors.append(f"Line {line_num}: JSON decode error: {e}")
                continue

            for rf in REQUIRED_FIELDS:
                if rf not in rec:
                    errors.append(f"Line {line_num} (ID: {rec.get('id')}): missing required field '{rf}'")

            st = rec.get("expected_status")
            if st not in VALID_STATUSES:
                errors.append(f"Line {line_num}: invalid expected_status '{st}'")

            tier = rec.get("verification_tier")
            if tier not in VALID_TIERS:
                errors.append(f"Line {line_num}: invalid verification_tier '{tier}'")

            diff = rec.get("difficulty")
            if diff not in VALID_DIFFICULTIES:
                errors.append(f"Line {line_num}: invalid difficulty '{diff}'")

            cit = rec.get("citation")
            if not isinstance(cit, dict):
                errors.append(f"Line {line_num}: citation must be an object/dict")

    return {
        "gate": "G1_G2_SCHEMA_VALIDITY",
        "passed": len(errors) == 0,
        "total_records_checked": total,
        "errors": errors
    }


if __name__ == "__main__":
    benchmark_file = os.path.join(os.path.dirname(__file__), "..", "claim_evidence", "claim_evidence.jsonl")
    res = validate_schema(benchmark_file)
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["passed"] else 1)
