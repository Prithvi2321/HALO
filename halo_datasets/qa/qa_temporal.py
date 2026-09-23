"""
HALO Verification Benchmark QA: Temporal Validation
===================================================
Gate G14: Verifies temporal provenance, amendment operation, and status consistency.
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BENCHMARK_PATH = os.path.join(BASE_DIR, "halo_datasets", "claim_evidence", "claim_evidence.jsonl")

VALID_TEMPORAL_STATUSES = {"CURRENT", "HISTORICAL", "AMENDED", "REPEALED", "SUPERSEDED"}


def validate_temporal(benchmark_path: str = BENCHMARK_PATH) -> dict:
    temporal_cases = []
    errors = []

    with open(benchmark_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("case_type") == "temporal_verification" or rec.get("verification_tier") == "TEMPORAL":
                temporal_cases.append(rec)
                mut = rec.get("mutation_details") or {}
                tstat = mut.get("temporal_status")
                if not tstat or tstat not in VALID_TEMPORAL_STATUSES:
                    errors.append(f"Case {rec['id']}: missing or invalid temporal_status '{tstat}'")

    passed = (len(temporal_cases) >= 10 and len(errors) == 0)

    return {
        "gate": "G14_TEMPORAL_PROVENANCE",
        "passed": passed,
        "total_temporal_cases": len(temporal_cases),
        "errors": errors
    }


if __name__ == "__main__":
    res = validate_temporal()
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["passed"] else 1)
