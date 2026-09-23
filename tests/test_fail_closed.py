"""
Unit Tests for Phase 8: FailClosed Benchmark Suite
==================================================
Protocol: v1.0-FROZEN
Tests fail-closed behavior on missing evidence, fabricated statutes, and out-of-domain queries.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from halo.citation_verifier.verifier import CitationVerifier
from halo.evidence_verifier.verifier import EvidenceVerifier
from halo.governor.governor import FailClosedGovernor


class TestFailClosedBenchmark(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.citation_verifier = CitationVerifier()
        cls.evidence_verifier = EvidenceVerifier()
        cls.governor = FailClosedGovernor()
        cls.benchmark_path = "halo_datasets/fail_closed/fail_closed_cases.jsonl"
        cls.test_records = []
        if os.path.exists(cls.benchmark_path):
            with open(cls.benchmark_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        cls.test_records.append(json.loads(line))

    def test_fail_closed_cases(self):
        """Verifies that all 4 fail-closed cases trigger quarantine/refusal."""
        self.assertGreaterEqual(len(self.test_records), 4)
        for rec in self.test_records:
            case_id = rec["case_id"]
            query = rec["query"]
            claim = rec["generated_claim"]
            cit = rec["citation"]

            # Run citation verification
            cit_res = self.citation_verifier.verify(citation=cit, claim_text=claim, case_id=case_id)
            ev_res = self.evidence_verifier.verify(
                claim=claim, evidence_passage=rec.get("evidence_passage", ""), case_id=case_id
            )

            # Determine composite status
            if cit_res.status in {"FABRICATED_CITATION", "FLAGGED"}:
                status = "FLAGGED"
            elif ev_res.status in {"UNSUPPORTED", "CONTRADICTED"}:
                status = "FLAGGED"
            else:
                status = "SUPPORTED"

            self.assertEqual(
                status,
                "FLAGGED",
                f"Fail-closed case {case_id} was improperly accepted! Explanation: {rec['explanation']}"
            )

            # Governor test: ensure claim is not treated as accepted fact
            verdict = self.governor.govern(
                query=query,
                raw_answer=claim,
                claims=[{"claim_id": "CLM_1", "claim_text": claim}],
                verification_results=[{"status": status, "explanation": rec["explanation"]}],
            )
            # Either fail_closed is True or the claim is qualified/quarantined
            self.assertTrue(
                verdict.fail_closed or len(verdict.qualified_claims) > 0 or len(verdict.rejected_claims) > 0,
                f"Governor failed to quarantine unverified assertion for {case_id}"
            )


if __name__ == "__main__":
    unittest.main()
