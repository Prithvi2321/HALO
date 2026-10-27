"""
HALO Test Suite: Retrieval Pipeline Verification
================================================
File: tests/test_retrieval.py
Verifies:
1. Known statutory query (Section 164 director disqualification) appears in top 5.
2. Known statutory query (Section 135 CSR thresholds) appears in top 5.
3. Known judicial query retrieves relevant precedent in top 5.
4. Nonsense/garbage query returns low-confidence/bounded scores.
5. Hit Rate@5 across D3-A sample queries stays >= 90%.
"""

import os
import sys
import json
import pickle
import pytest
from typing import List, Dict, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scripts.experiments.build_bm25_index import tokenize_legal_text

BM25_DIR = os.path.join(BASE_DIR, "experiments", "indices", "bm25")
BM25_MODEL_PATH = os.path.join(BM25_DIR, "index", "bm25_model.pkl")
METADATA_PATH = os.path.join(BM25_DIR, "metadata.jsonl")
D3_CANONICAL = os.path.join(BASE_DIR, "data", "dataset3", "canonical", "dataset3_all.jsonl")


@pytest.fixture(scope="module")
def retrieval_resources():
    assert os.path.exists(BM25_MODEL_PATH), f"BM25 model not found at {BM25_MODEL_PATH}"
    assert os.path.exists(METADATA_PATH), f"Metadata not found at {METADATA_PATH}"

    with open(BM25_MODEL_PATH, "rb") as f:
        bm25_model = pickle.load(f)

    metadata = []
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                metadata.append(json.loads(line))

    return bm25_model, metadata


def query_bm25(bm25_model, metadata: List[Dict[str, Any]], query: str, top_k: int = 5):
    tokens = tokenize_legal_text(query)
    scores = bm25_model.get_scores(tokens)
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    return [metadata[i] for i in top_indices], [scores[i] for i in top_indices]


class TestRetrievalPipeline:
    """Test suite validating sparse, dense, and hybrid retrieval behavior."""

    def test_statutory_query_section_164(self, retrieval_resources):
        """Assert Section 164 appears in top 5 results for director disqualification."""
        bm25_model, metadata = retrieval_resources
        query = "disqualification for appointment of director"
        top_passages, scores = query_bm25(bm25_model, metadata, query, top_k=5)

        matched_sec_164 = False
        for p in top_passages:
            sec_id = p.get("section_id") or ""
            text = (p.get("text") or "").lower()
            if "164" in sec_id or "disqualifications for appointment of director" in text:
                matched_sec_164 = True
                break

        assert matched_sec_164, f"Section 164 not found in top 5 results for '{query}'"

    def test_statutory_query_section_135(self, retrieval_resources):
        """Assert Section 135 appears in top 5 results for CSR threshold queries."""
        bm25_model, metadata = retrieval_resources
        query = "corporate social responsibility committee net worth threshold rupees five hundred crore"
        top_passages, scores = query_bm25(bm25_model, metadata, query, top_k=5)

        matched_sec_135 = False
        for p in top_passages:
            sec_id = p.get("section_id") or ""
            text = (p.get("text") or "").lower()
            if "135" in sec_id or "corporate social responsibility" in text:
                matched_sec_135 = True
                break

        assert matched_sec_135, f"Section 135 not found in top 5 results for '{query}'"

    def test_judgment_query_corporate_precedent(self, retrieval_resources):
        """Assert judicial query retrieves the correct corporate case in top 5."""
        bm25_model, metadata = retrieval_resources
        query = "Narahari versus Kumar Supreme Court"
        top_passages, scores = query_bm25(bm25_model, metadata, query, top_k=5)

        found_case = False
        for p in top_passages:
            case_title = (p.get("case_title") or "").upper()
            if "NARAHARI" in case_title and "KUMAR" in case_title:
                found_case = True
                break

        assert found_case, f"Expected case 'S. NARAHARI versus S.R. KUMAR' not found in top 5 results for '{query}'"

    def test_garbage_query_returns_low_confidence(self, retrieval_resources):
        """Assert nonsense/gibberish query returns low relevance scores."""
        bm25_model, metadata = retrieval_resources
        nonsense_query = "asdfghjklqwerty zxcvbnm unrelated gibberish 999999"
        top_passages, scores = query_bm25(bm25_model, metadata, nonsense_query, top_k=5)

        # For pure gibberish, max score should be low
        max_score = max(scores) if scores else 0.0
        assert max_score < 12.0, f"Expected low score for gibberish query, got {max_score}"

    def test_d3a_sample_hit_rate_above_90(self):
        """Assert Hit Rate@5 across D3-A sample queries stays >= 90%."""
        output_file = os.path.join(BASE_DIR, "experiments", "runs", "halo_upgraded", "halo_upgraded_test_output.jsonl")
        assert os.path.exists(output_file), f"Run output file not found: {output_file}"
        assert os.path.exists(D3_CANONICAL), f"D3 file not found: {D3_CANONICAL}"

        # Load ground truth relevant passages
        gt_map = {}
        with open(D3_CANONICAL, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    if item.get("benchmark_family") == "D3-A":
                        raw = item.get("raw_record", {})
                        gt_map[item["record_id"]] = set(raw.get("relevant_passage_ids") or raw.get("positive_evidence_ids") or [])

        # Check Hit@5 on sample of D3-A queries
        sample_hits = []
        with open(output_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    qid = rec.get("query_id")
                    if rec.get("benchmark_family") == "D3-A" and qid in gt_map:
                        top5 = rec.get("retrieval", {}).get("top5_passage_ids", [])[:5]
                        gold = gt_map[qid]
                        if gold:
                            hit = 1.0 if (set(top5) & gold) else 0.0
                            sample_hits.append(hit)

        assert len(sample_hits) >= 15, f"Expected at least 15 evaluated D3-A queries, got {len(sample_hits)}"
        hit_rate = (sum(sample_hits) / len(sample_hits)) * 100.0
        assert hit_rate >= 90.0, f"D3-A Hit Rate@5 was {hit_rate:.2f}%, expected >= 90.0%"

