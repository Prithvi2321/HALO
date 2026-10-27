"""
HALO Test Suite: Corpus Integrity & Data Cleanliness
===================================================
File: tests/test_corpus_integrity.py
Verifies:
1. Total passage count is exactly 12,223 across BM25 metadata and Dense metadata.
2. No passage has empty or whitespace-only text.
3. Every individual source dataset has 100% unique passage IDs.
4. Every passage has required metadata fields (passage_id, text, dataset).
5. Companies Act 2013 contains all 470 sections (1 to 470) in Dataset 1.
"""

import os
import sys
import json
import pytest
from typing import List, Dict, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

BM25_METADATA_PATH = os.path.join(BASE_DIR, "experiments", "indices", "bm25", "metadata.jsonl")
DENSE_METADATA_PATH = os.path.join(BASE_DIR, "experiments", "indices", "dense", "metadata.jsonl")
D1_PATH = os.path.join(BASE_DIR, "data", "dataset_1", "final", "companies_act_2013_passages.jsonl")
D2_PATH = os.path.join(BASE_DIR, "data", "dataset2", "canonical", "passages.jsonl")
SC_2023_PATH = os.path.join(BASE_DIR, "Data", "sc_judgments", "2023", "sc_2023_corporate_passages.jsonl")


@pytest.fixture(scope="module")
def corpus_metadata() -> List[Dict[str, Any]]:
    assert os.path.exists(BM25_METADATA_PATH), f"BM25 metadata missing at {BM25_METADATA_PATH}"
    records = []
    with open(BM25_METADATA_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


class TestCorpusIntegrity:
    """Test suite verifying corpus cleanliness, completeness, and metadata integrity."""

    def test_total_corpus_count(self, corpus_metadata):
        """Assert total passage count is exactly 12,223 in both BM25 and Dense metadata."""
        assert len(corpus_metadata) == 12223, (
            f"Expected 12,223 passages in BM25 metadata, found {len(corpus_metadata)}"
        )

        assert os.path.exists(DENSE_METADATA_PATH), f"Dense metadata missing at {DENSE_METADATA_PATH}"
        dense_count = 0
        with open(DENSE_METADATA_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    dense_count += 1

        assert dense_count == 12223, (
            f"Expected 12,223 passages in Dense metadata, found {dense_count}"
        )

    def test_no_passage_has_empty_text(self, corpus_metadata):
        """Assert that no passage has an empty string or whitespace-only text."""
        empty_indices = []
        for idx, p in enumerate(corpus_metadata):
            txt = (p.get("text") or "").strip()
            if not txt:
                empty_indices.append(idx)

        assert len(empty_indices) == 0, (
            f"Found {len(empty_indices)} passages with empty text at indices: {empty_indices[:5]}"
        )

    def test_source_datasets_uniqueness(self):
        """Assert that each constituent source dataset has 100% unique passage IDs."""
        # 1. Dataset 1: Statutory (1,640)
        assert os.path.exists(D1_PATH), f"Dataset 1 file missing at {D1_PATH}"
        d1_pids = []
        with open(D1_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    d1_pids.append(json.loads(line)["passage_id"])
        assert len(d1_pids) == 1640, f"Expected 1,640 D1 passages, got {len(d1_pids)}"
        assert len(d1_pids) == len(set(d1_pids)), "Found duplicate passage IDs in Dataset 1"

        # 2. Dataset 2: Landmark Precedents (1,133)
        assert os.path.exists(D2_PATH), f"Dataset 2 file missing at {D2_PATH}"
        d2_pids = []
        with open(D2_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    d2_pids.append(json.loads(line)["passage_id"])
        assert len(d2_pids) == 1133, f"Expected 1,133 D2 passages, got {len(d2_pids)}"
        assert len(d2_pids) == len(set(d2_pids)), "Found duplicate passage IDs in Dataset 2"

        # 3. SC 2023 Corporate Corpus (9,450)
        assert os.path.exists(SC_2023_PATH), f"SC 2023 file missing at {SC_2023_PATH}"
        sc_pids = []
        with open(SC_2023_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    sc_pids.append(json.loads(line)["passage_id"])
        assert len(sc_pids) == 9450, f"Expected 9,450 SC 2023 passages, got {len(sc_pids)}"
        assert len(sc_pids) == len(set(sc_pids)), "Found duplicate passage IDs in SC 2023"

    def test_required_metadata_fields(self, corpus_metadata):
        """Assert every passage record contains required core metadata fields."""
        required_fields = ["passage_id", "dataset", "text"]
        missing_records = []

        for p in corpus_metadata:
            for field in required_fields:
                if field not in p or p[field] is None:
                    missing_records.append((p.get("passage_id"), field))
                    break

        assert len(missing_records) == 0, (
            f"Found {len(missing_records)} records missing required fields: {missing_records[:5]}"
        )

    def test_companies_act_all_470_sections_present(self):
        """Assert Companies Act 2013 has all 470 sections (1 to 470) present in Dataset 1."""
        assert os.path.exists(D1_PATH), f"Dataset 1 file missing at {D1_PATH}"
        sections_found = set()

        with open(D1_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    sec_id = item.get("section_id") or ""
                    if "SEC_" in sec_id:
                        sec_num = sec_id.split("SEC_")[-1]
                        sections_found.add(sec_num)

        # Check all 470 integer sections 1 through 470
        missing_sections = [i for i in range(1, 471) if str(i) not in sections_found]
        assert len(missing_sections) == 0, (
            f"Missing {len(missing_sections)} Companies Act sections: {missing_sections[:10]}"
        )
        assert len(sections_found) >= 470, (
            f"Expected at least 470 sections, found {len(sections_found)}"
        )
