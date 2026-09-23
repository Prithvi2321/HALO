"""
Unit & Protocol Verification Tests for HALO Baseline 4 — Hybrid RAG
===================================================================
Protocol: v1.0-FROZEN
Validates the 13 Verification Gates required for Baseline 4 execution.

Gates:
  Gate 1:  Corpus integrity (exactly 2,773 passages; 1,640 D1 + 1,133 D2).
  Gate 2:  Zero Dataset 3 benchmark leakage into retrieval indices.
  Gate 3:  Dense retriever returns Top-5 candidates with rank 1..5, descending scores.
  Gate 4:  Sparse BM25 retriever returns Top-5 candidates with rank 1..5, descending scores.
  Gate 5:  Manual RRF calculation verification (k=60).
  Gate 6:  Missing rank RRF handling: absent retriever contributes 0.0, rank-1 single retriever = 1/61.
  Gate 7:  Dual-retriever sum: present in both at r1, r2 -> score = 1/(60+r1) + 1/(60+r2).
  Gate 8:  Deterministic tie-breaking: ties broken by passage_id ascending.
  Gate 9:  Fusion output truncation: exactly Top-5 passages returned.
  Gate 10: Config constants: method='hybrid_rrf', fusion.k=60, top_k=5.
  Gate 11: Disallowed modules: all 8 disallowed modules explicitly disabled.
  Gate 12: Corpus mapping integrity: retrieved passages resolve back to original corpus text.
  Gate 13: Generation invariance: Assert generation configuration and prompt template
           identical to the frozen B2/B3 generation configuration and prompt template.
"""

import os
import sys
import json
import unittest
import hashlib
from typing import Dict, List, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scripts.experiments.baseline_4_runner import Baseline4Runner, SYSTEM_PROMPT


class TestBaseline4Protocol(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config_path = os.path.join(BASE_DIR, "experiments", "configs", "b4_hybrid_config.json")
        with open(cls.config_path, "r", encoding="utf-8") as f:
            cls.config = json.load(f)
        cls.runner = Baseline4Runner()
        cls.runner.verify_and_load_indices()

    def test_gate_01_corpus_integrity(self):
        """Gate 1: Corpus integrity (exactly 2,773 passages: 1,640 D1 + 1,133 D2)."""
        self.assertEqual(len(self.runner.dense_metadata), 2773)
        self.assertEqual(len(self.runner.bm25_metadata), 2773)
        self.assertEqual(self.runner.dense_tensor.shape, (2773, 1024))
        self.assertEqual(self.runner.bm25_model.corpus_size, 2773)

        d1_count = sum(1 for p in self.runner.dense_metadata if p.get("dataset") == "dataset1")
        d2_count = sum(1 for p in self.runner.dense_metadata if p.get("dataset") == "dataset2")
        self.assertEqual(d1_count, 1640)
        self.assertEqual(d2_count, 1133)
        self.assertEqual(d1_count + d2_count, 2773)

        # Dense and BM25 order alignment
        dense_ids = [p["passage_id"] for p in self.runner.dense_metadata]
        bm25_ids = [p["passage_id"] for p in self.runner.bm25_metadata]
        self.assertEqual(dense_ids, bm25_ids)

    def test_gate_02_zero_d3_leakage(self):
        """Gate 2: Zero Dataset 3 benchmark leakage into retrieval indices."""
        d3_path = os.path.join(BASE_DIR, "data", "dataset3", "canonical", "dataset3_all.jsonl")
        d3_ids = set()
        with open(d3_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    d3_ids.add(item["record_id"])

        index_ids = {p["passage_id"] for p in self.runner.dense_metadata}
        leakage = d3_ids.intersection(index_ids)
        self.assertEqual(len(leakage), 0, f"Found {len(leakage)} D3 records leaking in index: {leakage}")

    def test_gate_03_dense_top5_candidate_generation(self):
        """Gate 3: Dense retriever returns Top-5 candidates with rank 1..5, descending scores."""
        query = "What is the procedure for appointment of an independent director?"
        cands, lat = self.runner.retrieve_dense(query)
        self.assertEqual(len(cands), 5)
        ranks = [c["rank"] for c in cands]
        self.assertEqual(ranks, [1, 2, 3, 4, 5])
        scores = [c["score"] for c in cands]
        self.assertEqual(scores, sorted(scores, reverse=True))
        for c in cands:
            self.assertIn("passage_id", c)
            self.assertIn("score", c)
            self.assertIn("rank", c)
            self.assertIn("index", c)

    def test_gate_04_sparse_bm25_top5_candidate_generation(self):
        """Gate 4: Sparse BM25 retriever returns Top-5 candidates with rank 1..5, descending scores."""
        query = "Section 135 corporate social responsibility committee composition"
        cands, lat = self.runner.retrieve_bm25(query)
        self.assertEqual(len(cands), 5)
        ranks = [c["rank"] for c in cands]
        self.assertEqual(ranks, [1, 2, 3, 4, 5])
        scores = [c["score"] for c in cands]
        self.assertEqual(scores, sorted(scores, reverse=True))
        for c in cands:
            self.assertIn("passage_id", c)
            self.assertIn("score", c)
            self.assertIn("rank", c)
            self.assertIn("index", c)

    def test_gate_05_manual_rrf_calculation_verification(self):
        """Gate 5: Manual RRF calculation verification (k=60)."""
        # Manual simulation:
        # P1: dense rank 1, bm25 rank 1 -> 1/(60+1) + 1/(60+1) = 2/61 = 0.032786885... -> round(0.032787, 6)
        dense_c = [{"passage_id": "P1", "rank": 1, "score": 0.85, "index": 0}]
        bm25_c = [{"passage_id": "P1", "rank": 1, "score": 15.2, "index": 0}]
        _, rrf_cands, _ = self.runner.reciprocal_rank_fusion(dense_c, bm25_c)
        self.assertEqual(len(rrf_cands), 1)
        expected_score = round(1.0 / 61.0 + 1.0 / 61.0, 6)
        self.assertAlmostEqual(rrf_cands[0]["rrf_score"], expected_score, places=5)

    def test_gate_06_missing_rank_rrf_handling(self):
        """Gate 6: Missing rank RRF handling: absent retriever contributes 0.0, rank-1 single retriever = 1/61."""
        dense_c = [{"passage_id": "P_DENSE_ONLY", "rank": 1, "score": 0.90, "index": 0}]
        bm25_c = [{"passage_id": "P_BM25_ONLY", "rank": 2, "score": 12.0, "index": 1}]
        _, rrf_cands, _ = self.runner.reciprocal_rank_fusion(dense_c, bm25_c)
        cand_map = {c["passage_id"]: c for c in rrf_cands}

        # Dense-only item: rank 1, missing in BM25 -> 1/(60+1) + 0.0 = 1/61
        d_item = cand_map["P_DENSE_ONLY"]
        self.assertEqual(d_item["dense_rank"], 1)
        self.assertIsNone(d_item["bm25_rank"])
        self.assertAlmostEqual(d_item["rrf_score"], round(1.0 / 61.0, 6), places=5)

        # BM25-only item: rank 2, missing in Dense -> 0.0 + 1/(60+2) = 1/62
        b_item = cand_map["P_BM25_ONLY"]
        self.assertIsNone(b_item["dense_rank"])
        self.assertEqual(b_item["bm25_rank"], 2)
        self.assertAlmostEqual(b_item["rrf_score"], round(1.0 / 62.0, 6), places=5)

    def test_gate_07_dual_retriever_sum(self):
        """Gate 7: Dual-retriever sum: present in both at r1, r2 -> score = 1/(60+r1) + 1/(60+r2)."""
        dense_c = [{"passage_id": "P_BOTH", "rank": 2, "score": 0.88, "index": 0}]
        bm25_c = [{"passage_id": "P_BOTH", "rank": 4, "score": 11.5, "index": 0}]
        _, rrf_cands, _ = self.runner.reciprocal_rank_fusion(dense_c, bm25_c)
        item = rrf_cands[0]
        expected = round(1.0 / (60 + 2) + 1.0 / (60 + 4), 6)
        self.assertAlmostEqual(item["rrf_score"], expected, places=5)

    def test_gate_08_deterministic_tie_breaking(self):
        """Gate 8: Deterministic tie-breaking: ties broken by passage_id ascending."""
        # Both passages appear at rank 1 in Dense only, so equal RRF score = 1/61
        dense_c = [
            {"passage_id": "PASSAGE_Z", "rank": 1, "score": 0.90, "index": 0},
            {"passage_id": "PASSAGE_A", "rank": 1, "score": 0.90, "index": 1}
        ]
        bm25_c = []
        _, rrf_cands, _ = self.runner.reciprocal_rank_fusion(dense_c, bm25_c)
        self.assertEqual(len(rrf_cands), 2)
        self.assertEqual(rrf_cands[0]["rrf_score"], rrf_cands[1]["rrf_score"])
        # Must be PASSAGE_A then PASSAGE_Z
        self.assertEqual(rrf_cands[0]["passage_id"], "PASSAGE_A")
        self.assertEqual(rrf_cands[1]["passage_id"], "PASSAGE_Z")

    def test_gate_09_output_candidate_truncation(self):
        """Gate 9: Fusion output truncation: exactly Top-5 passages returned."""
        dense_c = [{"passage_id": f"D_{i}", "rank": i, "score": 1.0 - i * 0.1, "index": i} for i in range(1, 6)]
        bm25_c = [{"passage_id": f"B_{i}", "rank": i, "score": 20.0 - i * 2.0, "index": i + 5} for i in range(1, 6)]
        final_p, rrf_cands, _ = self.runner.reciprocal_rank_fusion(dense_c, bm25_c)
        self.assertEqual(len(rrf_cands), 10)  # Total 10 candidates
        self.assertEqual(len(final_p), 5)     # Exactly Top-5 returned

    def test_gate_10_config_constants(self):
        """Gate 10: Config constants: method='hybrid_rrf', fusion.k=60, top_k=5."""
        self.assertEqual(self.config["retrieval"]["method"], "hybrid_rrf")
        self.assertEqual(self.config["retrieval"]["top_k"], 5)
        self.assertEqual(self.config["retrieval"]["fusion"]["method"], "RRF")
        self.assertEqual(self.config["retrieval"]["fusion"]["k"], 60)
        self.assertEqual(self.config["retrieval"]["fusion"]["top_k"], 5)
        self.assertEqual(self.config["retrieval"]["fusion"]["tie_breaker"], "passage_id_ascending")

    def test_gate_11_disallowed_modules(self):
        """Gate 11: Disallowed modules: all disallowed modules explicitly disabled."""
        disallowed = self.config.get("disallowed_modules", {})
        self.assertFalse(disallowed.get("cross_encoder_reranking", True))
        self.assertFalse(disallowed.get("legal_verifier", True))
        self.assertFalse(disallowed.get("citation_verification", True))
        self.assertFalse(disallowed.get("temporal_verification", True))
        self.assertFalse(disallowed.get("fail_closed_governor", True))
        self.assertFalse(disallowed.get("score_normalization", True))
        self.assertFalse(disallowed.get("weighted_fusion", True))
        self.assertFalse(disallowed.get("llm_mediated_fusion", True))

    def test_gate_12_corpus_mapping_integrity(self):
        """Gate 12: Corpus mapping integrity: retrieved passages resolve back to original corpus text."""
        query = "Corporate Social Responsibility under Section 135"
        dense_c, _ = self.runner.retrieve_dense(query)
        bm25_c, _ = self.runner.retrieve_bm25(query)
        final_p, _, _ = self.runner.reciprocal_rank_fusion(dense_c, bm25_c)

        for p in final_p:
            p_id = p["passage_id"]
            matched = [item for item in self.runner.dense_metadata if item["passage_id"] == p_id]
            self.assertEqual(len(matched), 1)
            self.assertEqual(p["text"], matched[0]["text"])
            self.assertIn("dataset", p)
            self.assertIn(p["dataset"], ["dataset1", "dataset2"])

    def test_gate_13_generation_invariance(self):
        """Gate 13: Generation invariance: Assert generation configuration and prompt template
        identical to the frozen B2/B3 generation configuration and prompt template."""
        b2_path = os.path.join(BASE_DIR, "experiments", "configs", "b2_dense_config.json")
        b3_path = os.path.join(BASE_DIR, "experiments", "configs", "b3_bm25_config.json")
        with open(b2_path, "r", encoding="utf-8") as f:
            b2_cfg = json.load(f)
        with open(b3_path, "r", encoding="utf-8") as f:
            b3_cfg = json.load(f)

        gen_keys = ["provider", "model", "temperature", "top_p", "max_tokens", "seed", "prompt_template"]
        for k in gen_keys:
            b2_val = b2_cfg[k]
            b3_val = b3_cfg[k]
            b4_val = self.config[k]
            self.assertEqual(b2_val, b3_val, f"B2 and B3 mismatch for {k}")
            self.assertEqual(b4_val, b2_val, f"B4 generation config mismatch with frozen B2/B3 for {k}")

        # Assert SYSTEM_PROMPT string matches frozen prompt_template
        frozen_prompt = b2_cfg["prompt_template"]["system_prompt"]
        self.assertEqual(
            " ".join(SYSTEM_PROMPT.split()),
            " ".join(frozen_prompt.split()),
            "B4 runner SYSTEM_PROMPT does not match frozen B2/B3 system_prompt"
        )


if __name__ == "__main__":
    unittest.main()
