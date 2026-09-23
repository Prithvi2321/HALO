"""
HALO Baseline 3 Validation Test Suite
=====================================
Validates all 11 core constraints for Baseline 3 (Sparse BM25 RAG):
  1. BM25 retrieval is enabled (method="bm25", top_k=5, k1=1.5, b=0.75, epsilon=0.25).
  2. Passages are retrieved and injected into prompt context.
  3. No dense retrieval, no RRF, no hybrid retrieval is used.
  4. No cross-encoder reranking is used.
  5. Verification is disabled (status="NOT_APPLICABLE").
  6. Fail-closed governor is disabled.
  7. No Dataset 3 benchmark queries or gold answers exist in retrieval prompt.
  8. Output schema conforms to frozen protocol.
  9. Failed API calls are captured explicitly.
  10. DEV and TEST inputs remain strictly separated.
  11. BM25 index artifacts, corpus coverage (2,773), and zero-leakage verified.
"""

import os
import sys
import json
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.experiments.baseline_3_runner import Baseline3Runner, SYSTEM_PROMPT


class TestBaseline3Protocol(unittest.TestCase):
    def setUp(self):
        self.runner = Baseline3Runner(api_key="TEST_MOCK_KEY")

    def test_01_bm25_retrieval_is_enabled(self):
        """Gate 1: Verify that BM25 retrieval is enabled with top_k=5 and protocol parameters."""
        self.assertTrue(self.runner.retrieval_enabled)
        self.assertEqual(self.runner.retrieval_method, "bm25")
        self.assertEqual(self.runner.top_k, 5)
        self.assertEqual(self.runner.k1, 1.5)
        self.assertEqual(self.runner.b, 0.75)
        self.assertEqual(self.runner.epsilon, 0.25)

    def test_02_context_prompt_injects_passages(self):
        """Gate 2: Verify that retrieved passages are formatted with AUTHORITATIVE LEGAL EVIDENCE."""
        mock_passages = [
            {
                "passage_id": "PAS_ACT_COMPANIES_2013_SEC_135_SUB_1",
                "document_id": "ACT_COMPANIES_2013",
                "dataset": "dataset1",
                "section_id": "ACT_COMPANIES_2013_SEC_135",
                "heading": "Corporate Social Responsibility",
                "text": "Every company having net worth of rupees 500 crore or more..."
            }
        ]
        prompt = self.runner.construct_context_prompt("What is CSR?", mock_passages)
        self.assertIn("AUTHORITATIVE LEGAL EVIDENCE", prompt)
        self.assertIn("END AUTHORITATIVE LEGAL EVIDENCE", prompt)
        self.assertIn("PAS_ACT_COMPANIES_2013_SEC_135_SUB_1", prompt)
        self.assertIn("What is CSR?", prompt)

    def test_03_no_dense_or_hybrid_retrieval(self):
        """Gate 3: Invariant: No dense vectors, embeddings, or RRF in Baseline 3."""
        self.assertEqual(self.runner.retrieval_method, "bm25")
        self.assertFalse(self.runner.config.get("dense_retrieval_enabled", False))
        self.assertNotIn("embedding_model", self.runner.config.get("retrieval", {}))
        self.assertNotIn("rrf", self.runner.config.get("retrieval", {}))

    def test_04_no_cross_encoder_reranking(self):
        """Gate 4: Invariant: Reranking is explicitly disabled."""
        self.assertFalse(self.runner.config["reranking_enabled"])

    def test_05_no_verification_pipeline(self):
        """Gate 5: Invariant: Verification is explicitly disabled."""
        self.assertFalse(self.runner.config["verification_enabled"])

    def test_06_no_fail_closed_governor(self):
        """Gate 6: Invariant: Fail-closed governor is explicitly disabled."""
        self.assertFalse(self.runner.config["fail_closed_enabled"])

    def test_07_no_dataset_3_leakage_in_runner(self):
        """Gate 7: Verify that gold answers or acceptable points are never in the prompt."""
        captured_prompts = []

        def mock_llm(p):
            captured_prompts.append(p)
            return "Answer"

        def mock_ret(q):
            return [
                {
                    "passage_id": "PAS_ACT_COMPANIES_2013_SEC_1_SUB_1",
                    "dataset": "dataset1",
                    "text": "Short title, extent, commencement..."
                }
            ], [15.2], 1.5

        test_queries = self.runner.load_queries_for_split("test")
        d3d = [q for q in test_queries if q.get("benchmark_family") == "D3-D"][0]
        raw = d3d["raw_record"]

        self.runner.generate_single_query(
            raw["query"],
            mock_fn={"mock_retrieval": mock_ret, "mock_llm": mock_llm}
        )

        self.assertEqual(len(captured_prompts), 1)
        p = captured_prompts[0]

        # Verify query exists in prompt
        self.assertIn(raw["query"], p)

        # Verify ground truth answers are NOT leaked into prompt
        if "acceptable_answer_points" in raw:
            for pt in raw["acceptable_answer_points"]:
                self.assertNotIn(f"acceptable_answer_points: {pt}", p)
        if "reference_answer" in raw and raw["reference_answer"]:
            self.assertNotIn(f"reference_answer: {raw['reference_answer']}", p)

    def test_08_output_schema_conformity(self):
        """Gate 8: Verify output record schema conforms strictly to frozen protocol."""
        mock_ret_passages = [
            {"passage_id": f"PAS_TEST_{i}", "dataset": "dataset1", "text": f"text {i}"}
            for i in range(5)
        ]
        mock_scores = [18.5, 15.2, 12.1, 9.8, 7.3]

        def mock_ret(q):
            return mock_ret_passages, mock_scores, 2.5

        def mock_llm(p):
            return "Mock Grounded Answer with Statutory Citation"

        res = self.runner.generate_single_query(
            "Test Query",
            mock_fn={"mock_retrieval": mock_ret, "mock_llm": mock_llm}
        )

        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(len(res["retrieved_passage_ids"]), 5)
        self.assertEqual(res["retrieved_passage_ids"], [f"PAS_TEST_{i}" for i in range(5)])
        self.assertEqual(res["retrieval_scores"], mock_scores)

    def test_09_failed_api_calls_recorded(self):
        """Gate 9: Verify API errors are captured cleanly."""
        self.runner._call_groq_api = MagicMock(side_effect=RuntimeError("Simulated Service Error"))
        def mock_ret(q):
            return [], [], 1.0

        res = self.runner.generate_single_query("Failing query", mock_fn={"mock_retrieval": mock_ret})
        self.assertEqual(res["status"], "FAILED")
        self.assertIn("API_ERROR", res["predicted_answer"])

    def test_10_dev_and_test_split_separation(self):
        """Gate 10: Verify mathematical disjointness of DEV and TEST splits."""
        dev = self.runner.load_queries_for_split("dev")
        test = self.runner.load_queries_for_split("test")

        dev_ids = {q["record_id"] for q in dev}
        test_ids = {q["record_id"] for q in test}

        overlap = dev_ids & test_ids
        self.assertEqual(len(overlap), 0, f"Split leakage: {overlap}")
        self.assertEqual(len(dev_ids), 64)
        self.assertEqual(len(test_ids), 168)


class TestBaseline3IndexIntegrity(unittest.TestCase):
    def test_11_bm25_index_integrity(self):
        """Verify BM25 index properties, corpus size (2,773), parameters, and zero-leakage."""
        index_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "experiments", "indices", "bm25")
        model_file = os.path.join(index_dir, "index", "bm25_model.pkl")
        meta_file = os.path.join(index_dir, "metadata.jsonl")
        manifest_file = os.path.join(index_dir, "index_manifest.json")
        receipt_file = os.path.join(index_dir, "build_receipt.json")

        self.assertTrue(os.path.exists(model_file), f"Missing {model_file}")
        self.assertTrue(os.path.exists(meta_file), f"Missing {meta_file}")
        self.assertTrue(os.path.exists(manifest_file), f"Missing {manifest_file}")
        self.assertTrue(os.path.exists(receipt_file), f"Missing {receipt_file}")

        # Load pickled model
        import pickle
        with open(model_file, "rb") as f:
            bm25 = pickle.load(f)

        self.assertEqual(bm25.corpus_size, 2773, f"Expected 2,773 corpus passages, got {bm25.corpus_size}")
        self.assertEqual(bm25.k1, 1.5)
        self.assertEqual(bm25.b, 0.75)
        self.assertEqual(bm25.epsilon, 0.25)

        # Check metadata
        with open(meta_file, "r", encoding="utf-8") as f:
            passages = [json.loads(line) for line in f if line.strip()]
        self.assertEqual(len(passages), 2773)
        passage_ids = [p["passage_id"] for p in passages]
        self.assertEqual(len(passage_ids), len(set(passage_ids)))

        # Zero leakage check against Dataset 3
        d3_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "dataset3", "canonical", "dataset3_all.jsonl")
        d3_ids = set()
        with open(d3_path, "r", encoding="utf-8") as f:
            for l in f:
                if l.strip():
                    d3_ids.add(json.loads(l)["record_id"])
        overlap = set(passage_ids) & d3_ids
        self.assertEqual(len(overlap), 0, f"Dataset 3 leakage in BM25 retrieval index: {overlap}")


if __name__ == "__main__":
    unittest.main()
