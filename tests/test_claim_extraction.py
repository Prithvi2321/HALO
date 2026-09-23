"""
Unit Tests for Phase 2: ClaimExtractor
======================================
Protocol: v1.0-FROZEN
Tests deterministic atomic legal claim extraction.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from halo.claim_extractor.extractor import ClaimExtractor, extract_claims


class TestClaimExtraction(unittest.TestCase):
    def setUp(self):
        self.extractor = ClaimExtractor()

    def test_compound_sentence_atomicity(self):
        """Tests decomposition of compound penalty/obligation sentence."""
        text = "Section 135 requires companies to spend 2% of average net profits on CSR, and failure results in criminal imprisonment."
        claims = self.extractor.extract_claims(text)
        self.assertGreaterEqual(len(claims), 2)
        c_texts = [c.claim_text for c in claims]
        self.assertTrue(any("2%" in c for c in c_texts))
        self.assertTrue(any("criminal imprisonment" in c.lower() for c in c_texts))

    def test_paragraph_not_single_claim(self):
        """Verifies that a multi-sentence paragraph is NOT treated as a single claim."""
        paragraph = (
            "Under Section 135(1) of the Companies Act, 2013, companies having a net worth of ₹500 crore must constitute a CSR Committee. "
            "Furthermore, Section 135(5) mandates spending at least 2% of average net profits. "
            "Failure to spend must be explained in the Board report."
        )
        claims = self.extractor.extract_claims(paragraph)
        self.assertGreaterEqual(len(claims), 3)
        for c in claims:
            self.assertEqual(c.atomicity_status, "ATOMIC")

    def test_abbreviation_preservation(self):
        """Verifies that legal abbreviations like v., Sec., w.e.f. do not trigger false sentence breaks."""
        text = "In Bhushan Power & Steel Ltd. v. Mr. S.L. Seal, reported at [2016] 11 S.C.R. 149, the Hon'ble Supreme Court interpreted Sec. 10A w.e.f. 2015."
        claims = self.extractor.extract_claims(text)
        self.assertEqual(len(claims), 1)
        self.assertIn("Bhushan Power", claims[0].claim_text)
        self.assertIn("11 S.C.R. 149", claims[0].claim_text)

    def test_type_classification(self):
        """Verifies claim type assignment."""
        thresh = "A turnover of rupees 1,000 crore or more triggers the statutory requirement."
        pen = "Every officer who is in default shall be liable to a penalty of ₹50,000."
        ratio = "The Supreme Court held that moratorium applies to corporate debtor assets."

        c1 = self.extractor.extract_claims(thresh)[0]
        c2 = self.extractor.extract_claims(pen)[0]
        c3 = self.extractor.extract_claims(ratio)[0]

        self.assertEqual(c1.claim_type, "NUMERICAL_THRESHOLD")
        self.assertEqual(c2.claim_type, "PENALTY_SANCTION")
        self.assertEqual(c3.claim_type, "JUDICIAL_RATIO")


if __name__ == "__main__":
    unittest.main()
