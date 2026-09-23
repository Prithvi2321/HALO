"""
Unit Tests for Phase 3: CitationVerifier
========================================
Protocol: v1.0-FROZEN
Tests 3-tier citation verification against benchmark suite.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from halo.citation_verifier.verifier import CitationVerifier


class TestCitationVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.verifier = CitationVerifier()
        cls.benchmark_path = "halo_datasets/citation_verification/citation_verification.jsonl"
        cls.test_records = []
        if os.path.exists(cls.benchmark_path):
            with open(cls.benchmark_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        cls.test_records.append(json.loads(line))

    def test_benchmark_cases(self):
        """Runs verification across all canonical benchmark citation test cases."""
        self.assertGreaterEqual(len(self.test_records), 10)
        for rec in self.test_records:
            case_id = rec["case_id"]
            cit = rec["citation"]
            claim = rec["generated_claim"]
            expected = rec["expected_status"]

            result = self.verifier.verify(citation=cit, claim_text=claim, case_id=case_id)
            self.assertEqual(
                result.status,
                expected,
                f"Failed on case {case_id}: expected {expected}, got {result.status}. Explanation: {result.explanation}"
            )


if __name__ == "__main__":
    unittest.main()
