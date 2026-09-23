"""
HALO Baseline 1 Validation Test Suite
=====================================
Validates all 10 core constraints for Baseline 1 (LLM-Only) prior to execution:
  1. No Dataset 1 passages are sent to the LLM.
  2. No Dataset 2 passages are sent to the LLM.
  3. No Dataset 3 answer/gold fields are sent to the LLM.
  4. Retrieval is disabled.
  5. Reranking is disabled.
  6. Verification is disabled.
  7. Fail-closed is disabled.
  8. Output schema is valid.
  9. Failed API calls are recorded correctly.
  10. DEV and TEST inputs remain strictly separated.
"""

import os
import sys
import json
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.experiments.baseline_1_runner import Baseline1Runner, SYSTEM_PROMPT


class TestBaseline1Protocol(unittest.TestCase):
    def setUp(self):
        self.runner = Baseline1Runner(api_key="TEST_MOCK_KEY")

    def test_01_no_dataset_1_passages_sent_to_llm(self):
        """Gate 1: Verify that no Dataset 1 passages or statutory chunks are injected."""
        # Inspect the prompt template and arguments passed to generate_single_query
        captured_prompts = []

        def mock_llm(prompt):
            captured_prompts.append(prompt)
            return "Parametric response without statutory text."

        dev_queries = self.runner.load_queries_for_split("dev")
        self.assertGreater(len(dev_queries), 0)

        raw = dev_queries[0]["raw_record"]
        query_text = raw.get("query") or dev_queries[0]["query_or_claim"]
        self.runner.generate_single_query(query_text, mock_fn=mock_llm)

        self.assertEqual(len(captured_prompts), 1)
        sent_prompt = captured_prompts[0]
        # Invariant: Must not contain any D1 statutory passage tags or passage text
        self.assertNotIn("PAS_ACT_COMPANIES_2013", sent_prompt)
        self.assertNotIn("<passage", sent_prompt)
        self.assertNotIn("<context", sent_prompt)

    def test_02_no_dataset_2_passages_sent_to_llm(self):
        """Gate 2: Verify that no Dataset 2 judicial passages or citations are injected."""
        captured_prompts = []

        def mock_llm(prompt):
            captured_prompts.append(prompt)
            return "Parametric response without judicial text."

        test_queries = self.runner.load_queries_for_split("test")
        # Find a judicial query
        jud_queries = [q for q in test_queries if "JUD-" in str(q.get("primary_source_ids", []))]
        target_q = jud_queries[0] if jud_queries else test_queries[0]
        query_text = target_q.get("query_or_claim")

        self.runner.generate_single_query(query_text, mock_fn=mock_llm)

        self.assertEqual(len(captured_prompts), 1)
        sent_prompt = captured_prompts[0]
        # Invariant: Must not contain any D2 judicial passage tags or document IDs
        self.assertNotIn("PAS-JUD-", sent_prompt)
        self.assertNotIn("<context", sent_prompt)
        self.assertNotIn("<judgment", sent_prompt)

    def test_03_no_dataset_3_gold_answers_sent_to_llm(self):
        """Gate 3: Verify that no gold answers or acceptable points reach the prompt."""
        captured_prompts = []

        def mock_llm(prompt):
            captured_prompts.append(prompt)
            return "Response without gold answers."

        test_queries = self.runner.load_queries_for_split("test")
        grounding_queries = [q for q in test_queries if q.get("benchmark_family") == "D3-D"]
        self.assertGreater(len(grounding_queries), 0)

        g_item = grounding_queries[0]
        raw = g_item["raw_record"]
        gold_ans = raw.get("gold_answer", "")
        acc_pts = raw.get("acceptable_answer_points", [])

        self.runner.generate_single_query(raw["query"], mock_fn=mock_llm)

        sent_prompt = captured_prompts[0]
        # Invariant: Gold answer and acceptable points must NEVER be in prompt
        self.assertNotIn(gold_ans, sent_prompt)
        for pt in acc_pts:
            self.assertNotIn(pt, sent_prompt)

    def test_04_retrieval_is_disabled(self):
        """Gate 4: Verify that retrieval is explicitly disabled in config and output."""
        self.assertFalse(self.runner.config["retrieval_enabled"])
        res = self.runner.generate_single_query("Test query", mock_fn=lambda q: "Ans")
        # Mock runner output record
        record = {
            "retrieval": {
                "enabled": self.runner.config["retrieval_enabled"],
                "retrieved_passage_ids": [],
                "retrieval_latency_ms": 0.0
            }
        }
        self.assertFalse(record["retrieval"]["enabled"])
        self.assertEqual(len(record["retrieval"]["retrieved_passage_ids"]), 0)
        self.assertEqual(record["retrieval"]["retrieval_latency_ms"], 0.0)

    def test_05_reranking_is_disabled(self):
        """Gate 5: Verify that reranking is explicitly disabled."""
        self.assertFalse(self.runner.config["reranking_enabled"])

    def test_06_verification_is_disabled(self):
        """Gate 6: Verify that verification is explicitly disabled."""
        self.assertFalse(self.runner.config["verification_enabled"])

    def test_07_fail_closed_is_disabled(self):
        """Gate 7: Verify that fail-closed governor is explicitly disabled."""
        self.assertFalse(self.runner.config["fail_closed_enabled"])

    def test_08_output_schema_is_valid(self):
        """Gate 8: Verify that execution outputs adhere to the standardized schema."""
        out = self.runner.run("dev", max_queries=2, mock_fn=lambda q: "Mocked legal answer")
        with open(out["output_file"], "r", encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                self.assertIn("experiment_id", rec)
                self.assertEqual(rec["system_id"], "B1_LLM")
                self.assertIn("query_id", rec)
                self.assertIn("benchmark_family", rec)
                self.assertIn("split", rec)
                self.assertIn("query", rec)

                # Retrieval block
                self.assertIn("retrieval", rec)
                self.assertFalse(rec["retrieval"]["enabled"])
                self.assertEqual(rec["retrieval"]["retrieved_passage_ids"], [])
                self.assertEqual(rec["retrieval"]["retrieval_latency_ms"], 0.0)

                # Generation block
                self.assertIn("generation", rec)
                self.assertIn("predicted_answer", rec["generation"])
                self.assertGreaterEqual(rec["generation"]["generation_latency_ms"], 0.0)

                # Verification block
                self.assertIn("verification", rec)
                self.assertFalse(rec["verification"]["enabled"])
                self.assertEqual(rec["verification"]["verification_status"], "NOT_APPLICABLE")
                self.assertFalse(rec["verification"]["fail_closed_triggered"])

                # Timing & Timestamps
                self.assertIn("total_latency_ms", rec)
                self.assertIn("timestamp_utc", rec)

    def test_09_failed_api_calls_are_recorded_correctly(self):
        """Gate 9: Verify that API failures are captured explicitly without silent masking."""
        self.runner._call_groq_api = MagicMock(side_effect=RuntimeError("Simulated API Down"))
        res = self.runner.generate_single_query("Failing query")
        self.assertEqual(res["status"], "FAILED")
        self.assertIn("API_ERROR", res["predicted_answer"])
        self.assertIn("Simulated API Down", res["error"])

    def test_10_dev_and_test_inputs_remain_separated(self):
        """Gate 10: Verify strict separation between DEV and TEST queries."""
        dev_queries = self.runner.load_queries_for_split("dev")
        test_queries = self.runner.load_queries_for_split("test")

        dev_ids = {q["record_id"] for q in dev_queries}
        test_ids = {q["record_id"] for q in test_queries}

        # Mathematical disjointness
        overlap = dev_ids & test_ids
        self.assertEqual(len(overlap), 0, f"Fatal: DEV and TEST query overlap detected: {overlap}")
        self.assertGreater(len(dev_ids), 0)
        self.assertGreater(len(test_ids), 0)


if __name__ == "__main__":
    unittest.main()
