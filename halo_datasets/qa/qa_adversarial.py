"""
HALO Verification Benchmark QA: Adversarial Case Validation
===========================================================
Gate G13: Verifies adversarial attack metadata, original case ID, and expected behavior.
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BENCHMARK_PATH = os.path.join(BASE_DIR, "halo_datasets", "claim_evidence", "claim_evidence.jsonl")


def validate_adversarial(benchmark_path: str = BENCHMARK_PATH) -> dict:
    adv_cases = []
    errors = []

    with open(benchmark_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("case_type") == "adversarial_cases":
                adv_cases.append(rec)
                mut = rec.get("mutation_details") or {}
                if not mut.get("attack_type"):
                    errors.append(f"Case {rec['id']}: missing attack_type in mutation_details")
                if rec.get("expected_status") not in {"CONTRADICTED", "FLAGGED", "UNSUPPORTED", "FABRICATED_CITATION"}:
                    errors.append(f"Case {rec['id']}: adversarial case cannot have expected_status '{rec.get('expected_status')}'")
                if rec.get("expected_behavior") != "REJECT":
                    errors.append(f"Case {rec['id']}: adversarial expected_behavior must be REJECT")

    passed = (len(adv_cases) >= 10 and len(errors) == 0)

    return {
        "gate": "G13_ADVERSARIAL_PROVENANCE",
        "passed": passed,
        "total_adversarial_cases": len(adv_cases),
        "errors": errors
    }


if __name__ == "__main__":
    res = validate_adversarial()
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["passed"] else 1)
