"""
Unit Tests for Phase 8: FailClosedGovernor
==========================================
Protocol: v1.0-FROZEN
Tests claim filtering, quarantine, purging, and reconstruction.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from halo.governor.governor import FailClosedGovernor


class TestGovernor(unittest.TestCase):
    def setUp(self):
        self.governor = FailClosedGovernor()

    def test_unsupported_claim_purging(self):
        """Verifies that contradicted and fabricated claims are 100% purged from verified findings."""
        query = "What are the rules regarding CSR and director imprisonment?"
        claims = [
            {"claim_id": "C1", "claim_text": "Section 135 requires companies meeting threshold to spend 2% of net profits."},
            {"claim_id": "C2", "claim_text": "Failure to spend CSR funds results in automatic criminal imprisonment under Section 999."},
        ]
        verifications = [
            {"status": "SUPPORTED", "explanation": "Supported by 135(5)", "authoritative_passage_id": "PAS_ACT_COMPANIES_2013_SEC_135_SUB_5"},
            {"status": "FABRICATED_CITATION", "explanation": "Section 999 does not exist", "tier_failed": "EXISTENCE"},
        ]

        verdict = self.governor.govern(query, "raw answer", claims, verifications)
        self.assertTrue(verdict.is_accepted)
        self.assertFalse(verdict.fail_closed)
        self.assertEqual(len(verdict.verified_claims), 1)
        self.assertEqual(len(verdict.rejected_claims), 1)

        # Ensure C2 is NOT in verified findings
        self.assertIn("Section 135 requires companies", verdict.final_answer)
        self.assertIn("Purged", verdict.final_answer)
        self.assertIn("Section 999 does not exist", verdict.final_answer)

    def test_complete_fail_closed_when_no_support(self):
        """Verifies fail-closed refusal when zero claims are verified."""
        query = "What is the penalty under quantum computing statute?"
        claims = [
            {"claim_id": "C1", "claim_text": "Under Section 999, unauthorized quantum tokenization carries ₹10 crore fine."},
        ]
        verifications = [
            {"status": "FABRICATED_CITATION", "explanation": "Statute does not exist", "tier_failed": "EXISTENCE"},
        ]

        verdict = self.governor.govern(query, "raw answer", claims, verifications)
        self.assertFalse(verdict.is_accepted)
        self.assertTrue(verdict.fail_closed)
        self.assertIn("FAIL-CLOSED ADVISORY", verdict.final_answer)
        self.assertIn("Zero Authoritative Evidence", verdict.final_answer)


if __name__ == "__main__":
    unittest.main()
