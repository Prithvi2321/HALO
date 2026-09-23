"""
HALO Verification Benchmark QA: Balance & Source Coverage
=========================================================
Gate G10, G11, G12: Audits class distribution, category balance, and difficulty balance.
Outputs qa/source_coverage.json.
"""

import json
import os
import sys
from collections import Counter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BENCHMARK_PATH = os.path.join(BASE_DIR, "halo_datasets", "claim_evidence", "claim_evidence.jsonl")
COVERAGE_REPORT_PATH = os.path.join(BASE_DIR, "halo_datasets", "qa", "source_coverage.json")


def validate_balance_and_coverage(benchmark_path: str = BENCHMARK_PATH) -> dict:
    classes = Counter()
    categories = Counter()
    difficulties = Counter()
    sources = Counter()
    source_datasets = Counter()
    unique_passages = set()
    total = 0

    with open(benchmark_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            total += 1
            r = json.loads(line)
            classes[r.get("expected_status")] += 1
            categories[r.get("case_type")] += 1
            difficulties[r.get("difficulty")] += 1
            sources[r.get("source")] += 1
            source_datasets[r.get("source_dataset")] += 1
            pid = r.get("authoritative_passage_id")
            if pid and pid != "NONE":
                unique_passages.add(pid)

    # Acceptance threshold checks
    has_all_classes = (len(classes) >= 5)
    has_all_categories = (len(categories) >= 8)
    has_all_difficulties = (len(difficulties) == 3)

    passed = (has_all_classes and has_all_categories and has_all_difficulties and total >= 100)

    report = {
        "gate": "G10_G11_G12_COVERAGE_AND_DISTRIBUTION",
        "passed": passed,
        "total_records": total,
        "class_distribution": dict(classes),
        "category_distribution": dict(categories),
        "difficulty_distribution": dict(difficulties),
        "source_dataset_distribution": dict(source_datasets),
        "unique_source_passages_covered": len(unique_passages),
        "top_sources": dict(sources.most_common(10)),
    }

    os.makedirs(os.path.dirname(COVERAGE_REPORT_PATH), exist_ok=True)
    with open(COVERAGE_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    res = validate_balance_and_coverage()
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["passed"] else 1)
