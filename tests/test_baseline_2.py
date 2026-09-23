"""
HALO Baseline 2 Validation Test Suite
=====================================
Validates all 10 core constraints for Baseline 2 (Dense Vector RAG):
  1. Dense retrieval is enabled (method="dense", top_k=5).
  2. Passages are retrieved and injected into prompt context.
  3. No BM25, no RRF, no hybrid retrieval is used.
  4. No cross-encoder reranking is used.
  5. Verification is disabled (status="NOT_APPLICABLE").
  6. Fail-closed governor is disabled.
  7. No Dataset 3 benchmark queries or gold answers exist in retrieval corpus.
  8. Output schema conforms to frozen protocol.
  9. Failed API calls are captured explicitly.
  10. DEV and TEST inputs remain strictly separated.
"""

import os
import sys
import json
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.experiments.baseline_2_runner import Baseline2Runner, SYSTEM_PROMPT


class TestBaseline2Protocol(unittest.TestCase):
    def setUp(self):
        self.runner = Baseline2Runner(api_key="TEST_MOCK_KEY")

    def test_01_dense_retrieval_is_enabled(self):
        """Gate 1: Verify that dense retrieval is enabled with top_k=5."""
        self.assertTrue(self.runner.retrieval_enabled)
        self.assertEqual(self.runner.retrieval_method, "dense")
        self.assertEqual(self.runner.top_k, 5)

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

    def test_03_no_hybrid_or_bm25_retrieval(self):
        """Gate 3: Invariant: No BM25 or RRF in Baseline 2."""
        self.assertEqual(self.runner.retrieval_method, "dense")
        self.assertNotIn("bm25", self.runner.config.get("retrieval", {}))
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
            ], [0.95], 10.0

        test_queries = self.runner.load_queries_for_split("test")
        d3d = [q for q in test_queries if q.get("benchmark_family") == "D3-D"][0]
        raw = d3d["raw_record"]

        self.runner.generate_single_query(
            raw["query"],
            mock_fn={"mock_retrieval": mock_ret, "mock_llm": mock_llm}
        )

        self.assertEqual(len(captured_prompts), 1)
        p = captured_prompts[0]
        # Invariant: Gold answer and acceptable points must not be leaked into prompt
        self.assertNotIn(raw.get("gold_answer", "xyz_nonexistent"), p)
        for pt in raw.get("acceptable_answer_points", []):
            self.assertNotIn(pt, p)

    def test_08_output_schema_adherence(self):
        """Gate 8: Verify that execution outputs adhere to standardized B2 schema."""
        def mock_llm(p):
            return "Sample generated answer grounded in evidence."

        def mock_ret(q):
            return [
                {
                    "passage_id": "PAS_ACT_COMPANIES_2013_SEC_1_SUB_1",
                    "dataset": "dataset1",
                    "text": "Short title text..."
                }
            ], [0.88], 15.2

        res = self.runner.generate_single_query(
            "Test query",
            mock_fn={"mock_retrieval": mock_ret, "mock_llm": mock_llm}
        )

        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["retrieved_passage_ids"], ["PAS_ACT_COMPANIES_2013_SEC_1_SUB_1"])
        self.assertEqual(res["retrieval_scores"], [0.88])
        self.assertGreater(res["retrieval_latency_ms"], 0.0)
        self.assertGreaterEqual(res["generation_latency_ms"], 0.0)

    def test_09_failed_api_calls_recorded(self):
        """Gate 9: Verify API errors are captured cleanly."""
        self.runner._call_groq_api = MagicMock(side_effect=RuntimeError("Simulated Network Error"))
        def mock_ret(q):
            return [], [], 5.0

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


class TestBaseline2IndexIntegrity(unittest.TestCase):
    def test_11_dense_index_integrity(self):
        """Verify dense index properties, dimensions, normalization, and zero-leakage."""
        index_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "experiments", "indices", "dense")
        index_file = os.path.join(index_dir, "index.pt")
        meta_file = os.path.join(index_dir, "metadata.jsonl")
        manifest_file = os.path.join(index_dir, "index_manifest.json")
        receipt_file = os.path.join(index_dir, "build_receipt.json")

        if not os.path.exists(index_file):
            self.skipTest("Dense index not constructed yet.")

        import torch
        tensor = torch.load(index_file, map_location="cpu")
        self.assertEqual(tensor.shape, (2773, 1024))
        norms = torch.norm(tensor, p=2, dim=1)
        self.assertTrue(torch.allclose(norms, torch.ones_like(norms), atol=1e-4))

        # Check metadata
        passages = [json.loads(line) for line in open(meta_file, encoding="utf-8") if line.strip()]
        self.assertEqual(len(passages), 2773)
        passage_ids = [p["passage_id"] for p in passages]
        self.assertEqual(len(passage_ids), len(set(passage_ids)))

        # Zero leakage check
        d3_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "dataset3", "canonical", "dataset3_all.jsonl")
        d3_ids = set()
        with open(d3_path, encoding="utf-8") as f:
            for l in f:
                if l.strip():
                    d3_ids.add(json.loads(l)["record_id"])
        overlap = set(passage_ids) & d3_ids
        self.assertEqual(len(overlap), 0, f"Dataset 3 leakage in retrieval index: {overlap}")


if __name__ == "__main__":
    unittest.main()
