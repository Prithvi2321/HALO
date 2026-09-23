"""
Unit Tests for Phase 5: TemporalVerifier
========================================
Protocol: v1.0-FROZEN
Tests version awareness, amendment enforceability, and repeal detection.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from halo.temporal_verifier.verifier import TemporalVerifier


class TestTemporalVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.verifier = TemporalVerifier()
        cls.benchmark_path = "halo_datasets/temporal/temporal_verification.jsonl"
        cls.test_records = []
        if os.path.exists(cls.benchmark_path):
            with open(cls.benchmark_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        cls.test_records.append(json.loads(line))

    def test_benchmark_temporal_cases(self):
        """Tests temporal amendment, repeal, and historical hallucination detection."""
        self.assertGreaterEqual(len(self.test_records), 5)
        for rec in self.test_records:
            case_id = rec["case_id"]
            claim = rec["generated_claim"]
            citation = rec["citation"]
            expected = rec["expected_status"]

            result = self.verifier.verify(citation=citation, claim_text=claim, case_id=case_id)
            self.assertEqual(
                result.status,
                expected,
                f"Failed on case {case_id}: expected {expected}, got {result.status}. Explanation: {result.explanation}"
            )


if __name__ == "__main__":
    unittest.main()
