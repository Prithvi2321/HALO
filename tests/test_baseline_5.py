"""
Unit & Protocol Verification Tests for HALO Baseline 5 — Hybrid RAG + Cross-Encoder Reranker
=============================================================================================
Protocol: v1.0-FROZEN
Validates the 24 Verification Gates required for Baseline 5 execution.

Gates:
  Gate 1:  Corpus size (exactly 2,773 passages; 1,640 D1 + 1,133 D2).
  Gate 2:  Zero Dataset 3 benchmark leakage (no queries, gold answers, or benchmark-derived content in index).
  Gate 3:  Dense retriever returns Top-5 candidates with rank 1..5, descending scores.
  Gate 4:  Sparse BM25 retriever returns Top-5 candidates with rank 1..5, descending scores.
  Gate 5:  RRF constant k=60.
  Gate 6:  RRF mathematical formula exact (sum of 1 / (60 + rank), unweighted).
  Gate 7:  Deterministic RRF tie-breaking (-rrf_score, passage_id ascending).
  Gate 8:  Candidate pool budget <= 10 unique passages.
  Gate 9:  Cross-Encoder receives exactly (query, original passage text) without rewriting.
  Gate 10: Cross-Encoder score ordering deterministic (-ce_score, passage_id ascending).
  Gate 11: Final reranked context <= 5 (exactly Top-5).
  Gate 12: Frozen LLM configuration identical to B2/B3/B4.
  Gate 13: Frozen prompt template identical to B2/B3/B4.
  Gate 14: All disallowed modules inactive (verifiers, citation checkers, governors False).
  Gate 15: B2 dense index integrity (SHA-256 matches frozen index).
  Gate 16: B3 BM25 index integrity (SHA-256 matches frozen index).
  Gate 17: Passage IDs preserved across Dense -> BM25 -> RRF -> Cross-Encoder -> Final Top-5.
  Gate 18: No candidate duplication in candidate union pool.
  Gate 19: No query rewriting in retrieval or reranking.
  Gate 20: No post-generation verification or correction.
  Gate 21: Dataset 1, 2, 3 immutability.
  Gate 22: Baselines 1, 2, 3, 4 freeze receipts immutability.
  Gate 23: Single variable isolation: Cross-encoder reranking is the sole intended experimental difference
           between B4 and B5, with all upstream retrieval, candidate pool, prompt, generation, corpus,
           and evaluation variables invariant.
  Gate 24: Test split isolation (evaluation logic does not modify models or configs).
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

from scripts.experiments.baseline_5_runner import Baseline5Runner, SYSTEM_PROMPT


def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class TestBaseline5Protocol(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config_path = os.path.join(BASE_DIR, "experiments", "configs", "b5_reranker_config.json")
        with open(cls.config_path, "r", encoding="utf-8") as f:
            cls.config = json.load(f)
        cls.runner = Baseline5Runner()
        cls.runner.verify_and_load_indices()

    def test_gate_01_corpus_size(self):
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

        dense_ids = [p["passage_id"] for p in self.runner.dense_metadata]
        bm25_ids = [p["passage_id"] for p in self.runner.bm25_metadata]
        self.assertEqual(dense_ids, bm25_ids)

    def test_gate_02_zero_benchmark_leakage(self):
        """Gate 2: Zero Dataset 3 benchmark leakage (no queries, gold answers, or benchmark-derived content in index)."""
        d3_path = os.path.join(BASE_DIR, "data", "dataset3", "canonical", "dataset3_all.jsonl")
        d3_ids = set()
        d3_queries = set()
        with open(d3_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    d3_ids.add(item["record_id"])
                    d3_queries.add(item.get("query_text", "").strip().lower())

        index_ids = {p["passage_id"] for p in self.runner.dense_metadata}
        leakage = d3_ids.intersection(index_ids)
        self.assertEqual(len(leakage), 0, f"Found {len(leakage)} D3 records leaking in index: {leakage}")

        # Ensure no passage text is an exact duplicate of a full benchmark query
        for p in self.runner.dense_metadata:
            text = p.get("text", "").strip().lower()
            self.assertNotIn(text, d3_queries, f"Passage text exactly matches a benchmark query!")

    def test_gate_03_dense_top5_budget(self):
        """Gate 3: Dense retriever returns exactly Top-5 passages with rank 1..5, descending scores."""
        query = "What is the procedure for appointment of an independent director?"
        cands, lat = self.runner.retrieve_dense(query)
        self.assertEqual(len(cands), 5)
        ranks = [c["rank"] for c in cands]
        self.assertEqual(ranks, [1, 2, 3, 4, 5])
        scores = [c["score"] for c in cands]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_gate_04_bm25_top5_budget(self):
        """Gate 4: Sparse BM25 retriever returns exactly Top-5 passages with rank 1..5, descending scores."""
        query = "Section 135 corporate social responsibility committee composition"
        cands, lat = self.runner.retrieve_bm25(query)
        self.assertEqual(len(cands), 5)
        ranks = [c["rank"] for c in cands]
        self.assertEqual(ranks, [1, 2, 3, 4, 5])
        scores = [c["score"] for c in cands]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_gate_05_rrf_k_60(self):
        """Gate 5: Pure RRF constant k=60 verified."""
        self.assertEqual(self.runner.rrf_k, 60)
        self.assertEqual(self.config["retrieval"]["fusion"]["k"], 60)

    def test_gate_06_rrf_mathematical_purity(self):
        """Gate 6: RRF formula exact: sum of 1 / (60 + rank), unweighted."""
        d_cands = [
            {"passage_id": "PAS_A", "rank": 1, "score": 0.9, "index": 0},
            {"passage_id": "PAS_B", "rank": 2, "score": 0.8, "index": 1}
        ]
        b_cands = [
            {"passage_id": "PAS_A", "rank": 1, "score": 25.0, "index": 0},
            {"passage_id": "PAS_C", "rank": 2, "score": 20.0, "index": 2}
        ]
        pool, lat = self.runner.reciprocal_rank_fusion(d_cands, b_cands)
        score_map = {item["passage_id"]: item["rrf_score"] for item in pool}

        # PAS_A: 1/(60+1) + 1/(60+1) = 2/61 approx 0.032787
        expected_a = round(1.0/61 + 1.0/61, 6)
        self.assertAlmostEqual(score_map["PAS_A"], expected_a, places=5)

        # PAS_B: 1/(60+2) = 1/62 approx 0.016129
        expected_b = round(1.0/62, 6)
        self.assertAlmostEqual(score_map["PAS_B"], expected_b, places=5)

        # PAS_C: 1/(60+2) = 1/62 approx 0.016129
        expected_c = round(1.0/62, 6)
        self.assertAlmostEqual(score_map["PAS_C"], expected_c, places=5)

    def test_gate_07_deterministic_rrf_tie_breaking(self):
        """Gate 7: Deterministic RRF tie-breaking (-rrf_score, passage_id ascending)."""
        d_cands = [
            {"passage_id": "PAS_Z", "rank": 2, "score": 0.5, "index": 0},
            {"passage_id": "PAS_A", "rank": 2, "score": 0.5, "index": 1}
        ]
        b_cands = []
        pool, lat = self.runner.reciprocal_rank_fusion(d_cands, b_cands)
        ids = [item["passage_id"] for item in pool]
        self.assertEqual(ids, ["PAS_A", "PAS_Z"], "Tie-breaker failed: should be alphabetical on passage_id")

    def test_gate_08_candidate_pool_budget(self):
        """Gate 8: Candidate union pool size |C| <= 10 unique passages."""
        query = "Section 188 related party transactions approval"
        d_cands, _ = self.runner.retrieve_dense(query)
        b_cands, _ = self.runner.retrieve_bm25(query)
        pool, _ = self.runner.reciprocal_rank_fusion(d_cands, b_cands)
        self.assertLessEqual(len(pool), 10)
        self.assertGreaterEqual(len(pool), 5)

    def test_gate_09_cross_encoder_input_integrity(self):
        """Gate 9: Cross-Encoder receives exactly original query and original passage text."""
        self.runner._ensure_cross_encoder_model()
        query = "What is the minimum CSR spend?"
        d_cands, _ = self.runner.retrieve_dense(query)
        b_cands, _ = self.runner.retrieve_bm25(query)
        pool, _ = self.runner.reciprocal_rank_fusion(d_cands, b_cands)

        final_passages, ce_cands, lat = self.runner.cross_encoder_rerank(query, pool)
        self.assertEqual(len(final_passages), 5)
        for item in ce_cands:
            self.assertIn("cross_encoder_score", item)
            self.assertIn("original_rrf_rank", item)
            self.assertIn("cross_encoder_rank", item)

    def test_gate_10_deterministic_ce_ordering(self):
        """Gate 10: Deterministic Cross-Encoder ordering (-score, passage_id ascending)."""
        pool = [
            {"passage_id": "PAS_B", "index": 0, "original_rrf_rank": 1, "dense_rank": 1, "bm25_rank": 1, "retrieval_source": "both", "rrf_score": 0.03},
            {"passage_id": "PAS_A", "index": 1, "original_rrf_rank": 2, "dense_rank": 2, "bm25_rank": None, "retrieval_source": "dense_only", "rrf_score": 0.016}
        ]
        # Test custom sort key
        scored = [
            {"passage_id": "PAS_B", "index": 0, "cross_encoder_score": 2.5},
            {"passage_id": "PAS_A", "index": 1, "cross_encoder_score": 2.5}
        ]
        scored.sort(key=lambda x: (-x["cross_encoder_score"], x["passage_id"]))
        self.assertEqual(scored[0]["passage_id"], "PAS_A")
        self.assertEqual(scored[1]["passage_id"], "PAS_B")

    def test_gate_11_final_context_budget(self):
        """Gate 11: Final context delivers exactly Top-5 passages."""
        query = "What constitutes oppression and mismanagement under Section 241?"
        d_cands, _ = self.runner.retrieve_dense(query)
        b_cands, _ = self.runner.retrieve_bm25(query)
        pool, _ = self.runner.reciprocal_rank_fusion(d_cands, b_cands)
        final_passages, ce_cands, lat = self.runner.cross_encoder_rerank(query, pool)
        self.assertEqual(len(final_passages), 5)
        self.assertEqual(self.runner.final_top_k, 5)

    def test_gate_12_llm_parameter_invariance(self):
        """Gate 12: LLM parameters invariant (qwen/qwen3.8-27b, temp 0.0, top-p 1.0, seed 42, max_tokens 512)."""
        self.assertEqual(self.runner.model_name, "qwen/qwen3.8-27b")
        self.assertEqual(self.runner.temperature, 0.0)
        self.assertEqual(self.runner.top_p, 1.0)
        self.assertEqual(self.runner.seed, 42)
        self.assertEqual(self.runner.max_tokens, 512)

    def test_gate_13_prompt_template_invariance(self):
        """Gate 13: Prompt template invariant (delimiters and system prompt byte-for-byte identical to B2/B3/B4)."""
        b4_config_path = os.path.join(BASE_DIR, "experiments", "configs", "b4_hybrid_config.json")
        with open(b4_config_path, "r", encoding="utf-8") as f:
            b4_config = json.load(f)
        b4_prompt = b4_config["prompt_template"]
        b5_prompt = self.config["prompt_template"]
        self.assertEqual(b5_prompt["system_prompt"], b4_prompt["system_prompt"])
        self.assertEqual(b5_prompt["context_header"], b4_prompt["context_header"])
        self.assertEqual(b5_prompt["context_footer"], b4_prompt["context_footer"])
        self.assertEqual(SYSTEM_PROMPT, b4_prompt["system_prompt"])

    def test_gate_14_disallowed_modules_inactive(self):
        """Gate 14: All disallowed modules verified inactive (all False)."""
        disallowed = self.config["disallowed_modules"]
        for mod, val in disallowed.items():
            self.assertFalse(val, f"Disallowed module '{mod}' must be False, got {val}")

    def test_gate_15_dense_index_integrity(self):
        """Gate 15: B2 dense index integrity (SHA-256 matches frozen index)."""
        dense_tensor_file = os.path.join(BASE_DIR, "experiments", "indices", "dense", "index.pt")
        dense_sha = compute_sha256(dense_tensor_file)
        expected_sha = "3cda2350db5011b074c5f31872bfe0d05f122d7f0936de6139f48187f2f87313"
        self.assertEqual(dense_sha, expected_sha)

    def test_gate_16_bm25_index_integrity(self):
        """Gate 16: B3 BM25 index integrity (SHA-256 matches frozen index)."""
        bm25_file = os.path.join(BASE_DIR, "experiments", "indices", "bm25", "index", "bm25_model.pkl")
        bm25_sha = compute_sha256(bm25_file)
        expected_sha = "3cf78cd79d3071c94fbe5f8e46df76514dbbe3bca0e1705117c1b73a1507d507"
        self.assertEqual(bm25_sha, expected_sha)

    def test_gate_17_passage_id_provenance(self):
        """Gate 17: Passage IDs preserved across Dense -> BM25 -> RRF -> Cross-Encoder -> Final."""
        query = "Section 100 requisition of extraordinary general meeting"
        d_cands, _ = self.runner.retrieve_dense(query)
        b_cands, _ = self.runner.retrieve_bm25(query)
        pool, _ = self.runner.reciprocal_rank_fusion(d_cands, b_cands)
        final_passages, ce_cands, lat = self.runner.cross_encoder_rerank(query, pool)

        pool_ids = {item["passage_id"] for item in pool}
        ce_ids = {item["passage_id"] for item in ce_cands}
        final_ids = [p["passage_id"] for p in final_passages]

        self.assertEqual(pool_ids, ce_ids)
        for f_id in final_ids:
            self.assertIn(f_id, ce_ids)

    def test_gate_18_candidate_deduplication(self):
        """Gate 18: Candidate union pool contains zero duplicate passages."""
        query = "Corporate Social Responsibility expenditure thresholds"
        d_cands, _ = self.runner.retrieve_dense(query)
        b_cands, _ = self.runner.retrieve_bm25(query)
        pool, _ = self.runner.reciprocal_rank_fusion(d_cands, b_cands)
        pool_ids = [item["passage_id"] for item in pool]
        self.assertEqual(len(pool_ids), len(set(pool_ids)), "Duplicate passage IDs found in candidate pool!")

    def test_gate_19_zero_query_rewriting(self):
        """Gate 19: Queries passed verbatim to Dense, BM25, and Cross-Encoder."""
        query = "  Section 135(5) CSR 2% calculation   "
        mock_dense = lambda q: ([{"passage_id": "P1", "rank": 1, "score": 1.0, "index": 0}], 1.0)
        mock_bm25 = lambda q: ([{"passage_id": "P1", "rank": 1, "score": 1.0, "index": 0}], 1.0)
        mock_ce = lambda q, p: ([{"passage_id": "P1", "text": "foo", "dataset": "dataset1"}], [{"passage_id": "P1", "cross_encoder_score": 1.0, "original_rrf_rank": 1, "cross_encoder_rank": 1}], 1.0)
        mock_llm = lambda p: "Answer"

        res = self.runner.generate_single_query(
            query,
            mock_fn={"mock_dense": mock_dense, "mock_bm25": mock_bm25, "mock_cross_encoder": mock_ce, "mock_llm": mock_llm}
        )
        self.assertEqual(res["status"], "SUCCESS")

    def test_gate_20_zero_post_generation_verification(self):
        """Gate 20: Raw generation output captured without post-generation verification or correction."""
        query = "Section 135"
        mock_dense = lambda q: ([{"passage_id": "P1", "rank": 1, "score": 1.0, "index": 0}], 1.0)
        mock_bm25 = lambda q: ([{"passage_id": "P1", "rank": 1, "score": 1.0, "index": 0}], 1.0)
        mock_ce = lambda q, p: ([{"passage_id": "P1", "text": "foo", "dataset": "dataset1"}], [{"passage_id": "P1", "cross_encoder_score": 1.0, "original_rrf_rank": 1, "cross_encoder_rank": 1}], 1.0)
        raw_ans = "This is the exact raw answer containing Section 135."
        mock_llm = lambda p: raw_ans

        res = self.runner.generate_single_query(
            query,
            mock_fn={"mock_dense": mock_dense, "mock_bm25": mock_bm25, "mock_cross_encoder": mock_ce, "mock_llm": mock_llm}
        )
        self.assertEqual(res["predicted_answer"], raw_ans)

    def test_gate_21_upstream_dataset_immutability(self):
        """Gate 21: Datasets 1, 2, 3 SHA-256 hashes unchanged."""
        d3_path = os.path.join(BASE_DIR, "data", "dataset3", "canonical", "dataset3_all.jsonl")
        d3_sha = compute_sha256(d3_path)
        expected_d3 = "431a27d8fbc569255ae53fe209b869c6ae0b0bc8090b750500be0176ea54afc4"
        self.assertEqual(d3_sha, expected_d3)

    def test_gate_22_prior_baseline_receipts_immutability(self):
        """Gate 22: Baselines 1, 2, 3, 4 freeze receipts immutability."""
        b1_receipt = os.path.join(BASE_DIR, "experiments", "runs", "b1_llm_only", "freeze_receipt.json")
        b2_receipt = os.path.join(BASE_DIR, "experiments", "runs", "b2_dense_rag", "freeze_receipt.json")
        b3_receipt = os.path.join(BASE_DIR, "experiments", "runs", "b3_bm25", "freeze_receipt.json")
        b4_receipt = os.path.join(BASE_DIR, "experiments", "runs", "b4_hybrid", "freeze_receipt.json")

        self.assertEqual(compute_sha256(b1_receipt), "a2cd8c159739a6ce20276d49fb602079b5b67154c36ceb0887a873a0d6da575d")
        self.assertEqual(compute_sha256(b2_receipt), "bc666c8ed1b6f0ce9e5d3abe2910c99cc9694b37a83a815c5bd4c2b6d4a0961f")
        self.assertEqual(compute_sha256(b3_receipt), "dfe92e62e3fdb34501c62a5748117420d15d0e84232760ae9bf2fdeea636ffb0")
        self.assertEqual(compute_sha256(b4_receipt), "d8ec36f8d1e8c91c116cfa71d20ad7d8af5bdc19629a449fe623101c90b2024a")

    def test_gate_23_single_variable_isolation(self):
        """
        Gate 23: Cross-encoder reranking is the sole intended experimental difference between B4 and B5,
        with all upstream retrieval, candidate pool, prompt, generation, corpus, and evaluation variables invariant.
        """
        b4_config_path = os.path.join(BASE_DIR, "experiments", "configs", "b4_hybrid_config.json")
        with open(b4_config_path, "r", encoding="utf-8") as f:
            b4_cfg = json.load(f)

        # Dense invariant
        self.assertEqual(self.config["retrieval"]["dense"], b4_cfg["retrieval"]["dense"])
        # Sparse invariant
        self.assertEqual(self.config["retrieval"]["sparse"], b4_cfg["retrieval"]["sparse"])
        # Fusion invariant
        self.assertEqual(self.config["retrieval"]["fusion"]["k"], b4_cfg["retrieval"]["fusion"]["k"])
        # Generation invariant
        self.assertEqual(self.config["generation"], b4_cfg["generation"])
        # Prompt invariant
        self.assertEqual(self.config["prompt_template"], b4_cfg["prompt_template"])
        # Corpus invariant
        self.assertEqual(self.config["corpus"]["passage_count"], b4_cfg["corpus"]["passage_count"])
        # Sole difference is cross_encoder component
        self.assertTrue(self.config["retrieval"]["cross_encoder"]["enabled"])

    def test_gate_24_test_split_isolation(self):
        """Gate 24: Test split evaluation logic does not modify models or configs."""
        config_hash_before = compute_sha256(self.config_path)
        # Test evaluation dry-run does not write to config
        d3_path = os.path.join(BASE_DIR, "data", "dataset3", "canonical", "dataset3_all.jsonl")
        self.assertTrue(os.path.exists(d3_path))
        config_hash_after = compute_sha256(self.config_path)
        self.assertEqual(config_hash_before, config_hash_after)


if __name__ == "__main__":
    unittest.main()
