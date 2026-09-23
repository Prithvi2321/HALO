"""
Unit Tests for Phase 4: EvidenceVerifier
========================================
Protocol: v1.0-FROZEN
Tests passage-level NLI verification and threshold checking.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from halo.evidence_verifier.verifier import EvidenceVerifier


class TestPassageVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.verifier = EvidenceVerifier()
        cls.benchmark_path = "halo_datasets/passage_verification/passage_verification.jsonl"
        cls.test_records = []
        if os.path.exists(cls.benchmark_path):
            with open(cls.benchmark_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        cls.test_records.append(json.loads(line))

    def test_benchmark_passage_cases(self):
        """Tests evidence entailment, contradiction, and unsupported cases against benchmark."""
        self.assertGreaterEqual(len(self.test_records), 8)
        for rec in self.test_records:
            case_id = rec.get("case_id") or rec.get("id")
            claim = rec["generated_claim"]
            evidence = rec["evidence_passage"]
            expected = rec["expected_status"]

            result = self.verifier.verify(
                claim=claim,
                evidence_passage=evidence,
                case_id=case_id,
                authoritative_passage_id=rec.get("authoritative_passage_id")
            )
            self.assertEqual(
                result.status,
                expected,
                f"Failed on case {case_id}: expected {expected}, got {result.status}. Explanation: {result.explanation}"
            )


if __name__ == "__main__":
    unittest.main()
