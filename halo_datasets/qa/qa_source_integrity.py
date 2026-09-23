"""
HALO Verification Benchmark QA: Source Integrity
================================================
Gate G4: Verifies source corpora file integrity against official cryptographic receipts.
"""

import hashlib
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

EXPECTED_HASHES = {
    "dataset_1_passages": {
        "path": "data/dataset_1/final/companies_act_2013_passages.jsonl",
        "sha256": "37c5ced49fc3925342a7eebfc84eb2988f863166b60c0a8cf527aefae0e8c27c"
    },
    "dataset_2_passages": {
        "path": "data/dataset2/canonical/passages.jsonl",
        "sha256": "43af9b6ed2df7be5489a71e81cf1f0125469d0cbe4443d0e536edb35703d3996"
    },
    "dataset_2_judgments": {
        "path": "data/dataset2/canonical/judgments.jsonl",
        "sha256": "fe75dee7ee7a5c115f41dd7d3a9f8ca44edb068cefb9a9a69c299a22d77d9935"
    }
}


def sha256_file(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def validate_source_integrity() -> dict:
    results = {}
    all_passed = True

    for name, item in EXPECTED_HASHES.items():
        fp = os.path.join(BASE_DIR, item["path"])
        if not os.path.exists(fp):
            results[name] = {"status": "MISSING", "error": f"File not found: {fp}"}
            all_passed = False
            continue

        actual = sha256_file(fp)
        matched = (actual == item["sha256"])
        if not matched:
            all_passed = False

        results[name] = {
            "status": "VERIFIED" if matched else "HASH_MISMATCH",
            "expected_sha256": item["sha256"],
            "actual_sha256": actual,
            "path": item["path"]
        }

    return {
        "gate": "G4_SOURCE_INTEGRITY",
        "passed": all_passed,
        "details": results
    }


if __name__ == "__main__":
    res = validate_source_integrity()
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["passed"] else 1)
