"""
HALO Verification Benchmark QA: Split Leakage Validation
========================================================
Gate G9: Verifies passage-family disjointness and zero source passage leakage.
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPLITS_DIR = os.path.join(BASE_DIR, "halo_datasets", "splits")


def get_passage_families(filepath: str):
    pids = set()
    records = []
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    records.append(r)
                    pid = r.get("authoritative_passage_id")
                    if pid and pid != "NONE":
                        pids.add(pid)
    return pids, records


def validate_splits() -> dict:
    train_file = os.path.join(SPLITS_DIR, "train.jsonl")
    dev_file = os.path.join(SPLITS_DIR, "dev.jsonl")
    test_file = os.path.join(SPLITS_DIR, "test.jsonl")

    train_pids, train_recs = get_passage_families(train_file)
    dev_pids, dev_recs = get_passage_families(dev_file)
    test_pids, test_recs = get_passage_families(test_file)

    train_test_overlap = train_pids.intersection(test_pids)
    train_dev_overlap = train_pids.intersection(dev_pids)
    dev_test_overlap = dev_pids.intersection(test_pids)

    has_leakage = bool(train_test_overlap or train_dev_overlap or dev_test_overlap)

    total_split_recs = len(train_recs) + len(dev_recs) + len(test_recs)

    report = {
        "gate": "G9_SPLIT_LEAKAGE",
        "passed": not has_leakage,
        "train_count": len(train_recs),
        "dev_count": len(dev_recs),
        "test_count": len(test_recs),
        "total_split_count": total_split_recs,
        "unique_passage_families_train": len(train_pids),
        "unique_passage_families_dev": len(dev_pids),
        "unique_passage_families_test": len(test_pids),
        "train_test_passage_overlap": list(train_test_overlap),
        "train_dev_passage_overlap": list(train_dev_overlap),
        "dev_test_passage_overlap": list(dev_test_overlap),
        "leakage_status": "ZERO_LEAKAGE" if not has_leakage else "LEAKAGE_DETECTED"
    }
    return report


if __name__ == "__main__":
    res = validate_splits()
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["passed"] else 1)
