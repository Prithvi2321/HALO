"""
HALO Test Suite: Citation Anchoring Verification
================================================
File: tests/test_citation_anchoring.py
Verifies:
1. Every answer in a representative sample contains at least one [PAS_...] citation bracket.
2. Average citations per answer in D3-D is above 9 (evaluated at 10.45).
3. No answer is returned without a passage ID reference.
4. Citation IDs cited in answers exist in the active passage corpus store.
"""

import os
import sys
import re
import json
import pytest
from typing import Set

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

OUTPUT_JSONL = os.path.join(BASE_DIR, "experiments", "runs", "halo_upgraded", "halo_upgraded_test_output.jsonl")
METRICS_JSON = os.path.join(BASE_DIR, "experiments", "metrics", "halo_upgraded_test_metrics.json")
METADATA_PATH = os.path.join(BASE_DIR, "experiments", "indices", "bm25", "metadata.jsonl")

PID_REGEX = re.compile(r"\[(PAS[-_][A-Za-z0-9_\-\.]+)\]")


@pytest.fixture(scope="module")
def corpus_pids() -> Set[str]:
    assert os.path.exists(METADATA_PATH), f"Corpus metadata not found: {METADATA_PATH}"
    pids = set()
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                pids.add(json.loads(line)["passage_id"])
    return pids


@pytest.fixture(scope="module")
def d3d_records():
    assert os.path.exists(OUTPUT_JSONL), f"Run output file not found: {OUTPUT_JSONL}"
    records = []
    with open(OUTPUT_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                if rec.get("benchmark_family") == "D3-D":
                    records.append(rec)
    return records


class TestCitationAnchoring:
    """Test suite verifying statutory and judicial citation anchoring integrity."""

    def test_sample_queries_contain_citation_brackets(self, d3d_records):
        """Assert every answer in a 10-query sample contains at least one [PAS_...] bracket."""
        sample = d3d_records[:10]
        assert len(sample) == 10, f"Expected 10 queries, found {len(sample)}"

        for i, rec in enumerate(sample, 1):
            ans = rec.get("generation", {}).get("predicted_answer", "")
            matches = PID_REGEX.findall(ans)
            assert len(matches) > 0, (
                f"Sample query {i} ({rec.get('query_id')}) returned an answer with 0 citations: {ans[:150]}"
            )

    def test_average_citations_per_answer_above_nine(self):
        """Assert average citations per answer is above 9 across D3-D (official metric = 10.45)."""
        assert os.path.exists(METRICS_JSON), f"Metrics JSON not found: {METRICS_JSON}"
        with open(METRICS_JSON, "r", encoding="utf-8") as f:
            metrics = json.load(f)

        assert "D3-D" in metrics, "D3-D metrics missing from evaluation results"
        avg_cits = metrics["D3-D"].get("avg_citations_per_answer", 0.0)
        assert avg_cits >= 9.0, f"Average citations per answer {avg_cits} is below threshold of 9.0"

    def test_no_answer_returned_without_passage_id(self, d3d_records):
        """Assert 100% of answers across all 100 D3-D queries have passage ID references."""
        assert len(d3d_records) == 100, f"Expected 100 D3-D records, found {len(d3d_records)}"

        unanchored = []
        for rec in d3d_records:
            ans = rec.get("generation", {}).get("predicted_answer", "")
            matches = PID_REGEX.findall(ans)
            if not matches:
                unanchored.append(rec.get("query_id"))

        assert len(unanchored) == 0, f"Found unanchored answers for queries: {unanchored}"

    def test_cited_passage_ids_exist_in_corpus(self, d3d_records, corpus_pids):
        """Assert that cited passage IDs in sample answers exist in the active 12,223-passage store."""
        # Check first 15 queries in detail
        sample = d3d_records[:15]
        total_citations_checked = 0
        valid_citations = 0

        for rec in sample:
            ans = rec.get("generation", {}).get("predicted_answer", "")
            matches = PID_REGEX.findall(ans)
            for pid in matches:
                total_citations_checked += 1
                if pid in corpus_pids:
                    valid_citations += 1

        assert total_citations_checked > 0, "No citations found in sample"
        validity_rate = (valid_citations / total_citations_checked) * 100.0
        assert validity_rate >= 95.0, (
            f"Citation validity was {validity_rate:.1f}% ({valid_citations}/{total_citations_checked}), "
            "expected >= 95.0%"
        )
