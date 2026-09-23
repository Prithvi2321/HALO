"""
End-to-End Integration Tests for HALO Pipeline
==============================================
Protocol: v1.0-FROZEN
Tests full pipeline flow from raw answer through claim extraction, verifications,
governor quarantine, and cryptographic audit persistence.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from halo.pipeline import HaloPipeline


class TestHaloEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_log_path = "experiments/runs/halo/test_audit_store.jsonl"
        cls.pipeline = HaloPipeline(log_path=cls.test_log_path)

    def test_supported_statutory_flow(self):
        """Tests that a factual statutory claim passes all verifications and is accepted."""
        query = "What is the net profit threshold for CSR?"
        raw_answer = "Section 135(1) mandates that every company having net profit of rupees five crore or more during the immediately preceding financial year shall constitute a Corporate Social Responsibility Committee."
        explicit_citations = [{"type": "STATUTORY", "act": "Companies Act, 2013", "section": "135", "subsection": "1"}]

        result = self.pipeline.process(
            query=query,
            raw_answer=raw_answer,
            explicit_citations=explicit_citations,
        )

        self.assertTrue(result["is_authoritative"])
        self.assertFalse(result["fail_closed"])
        self.assertGreaterEqual(result["overall_confidence"], 0.75)
        self.assertIn("Verified Legal Findings", result["final_answer"])
        self.assertIn("PAS_ACT_COMPANIES_2013_SEC_135_SUB_1", result["final_answer"])
        self.assertTrue(result["audit_id"].startswith("AUD-"))
        self.assertIsNotNone(result["content_hash"])

    def test_fabricated_citation_fail_closed(self):
        """Tests that an answer based on a fabricated section triggers fail-closed."""
        query = "What are the quantum computing rules under Section 999?"
        raw_answer = "Section 999 of the Companies Act, 2013 imposes strict liability on companies deploying unauthorized neural algorithms."
        explicit_citations = [{"type": "STATUTORY", "act": "Companies Act, 2013", "section": "999"}]

        result = self.pipeline.process(
            query=query,
            raw_answer=raw_answer,
            explicit_citations=explicit_citations,
        )

        self.assertFalse(result["is_authoritative"])
        self.assertTrue(result["fail_closed"])
        self.assertIn("FAIL-CLOSED ADVISORY", result["final_answer"])
        self.assertEqual(result["quarantine_report"]["rejected_count"], 1)

    def test_temporal_amendment_quarantine(self):
        """Tests that an obsolete threshold (₹1 lakh minimum capital) is caught and purged."""
        query = "What is the minimum capital for a private company?"
        raw_answer = "Under Section 2(68) of the Companies Act, 2013, a private company must maintain a minimum paid-up share capital of ₹1,00,000 at all times."
        explicit_citations = [{"type": "STATUTORY", "act": "Companies Act, 2013", "section": "2", "subsection": "68"}]

        result = self.pipeline.process(
            query=query,
            raw_answer=raw_answer,
            explicit_citations=explicit_citations,
        )

        self.assertTrue(result["fail_closed"])
        self.assertEqual(result["quarantine_report"]["rejected_count"], 1)
        self.assertIn("FAIL-CLOSED ADVISORY", result["final_answer"])

    def test_audit_retrieval(self):
        """Tests audit trail retrieval using audit_id."""
        query = "What resolution removes an independent director?"
        raw_answer = "Under Section 169(1), a company may remove a director by ordinary resolution before the expiry of their term."
        explicit_citations = [{"type": "STATUTORY", "act": "Companies Act, 2013", "section": "169", "subsection": "1"}]

        result = self.pipeline.process(
            query=query,
            raw_answer=raw_answer,
            explicit_citations=explicit_citations,
        )
        aid = result["audit_id"]

        retrieved = self.pipeline.audit_logger.get_audit_record(aid)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.audit_id, aid)
        self.assertEqual(retrieved.query, query)


if __name__ == "__main__":
    unittest.main()
