"""
Unit Tests for Substantive Contradiction
========================================
Protocol: v1.0-FROZEN
Tests semantic evidence contradiction where authoritative passage refutes the claim.
"""

import pytest
from halo.evidence_verifier.verifier import EvidenceVerifier
from halo.evidence_verifier.schemas import EvidenceVerdictStatus


@pytest.fixture(scope="module")
def verifier():
    return EvidenceVerifier()


def test_special_vs_ordinary_resolution_contradiction(verifier):
    """Benchmark Case PAS_SUPP_008: Special resolution vs Ordinary resolution."""
    evidence = (
        "(1) A company may, by ordinary resolution, remove a director, not being a director "
        "appointed by the Tribunal under section 242, before the expiry of the period of his office."
    )
    claim = "Section 169(1) requires a special resolution to remove an independent director prior to completion of term."

    verdict = verifier.verify_claim(
        claim_input={"claim_id": "PAS_SUPP_008", "claim_text": claim},
        direct_evidence_text=evidence,
        direct_passage_id="PAS_ACT_COMPANIES_2013_SEC_169_SUB_1",
    )

    assert verdict.status == EvidenceVerdictStatus.CONTRADICTED.value


def test_fraud_compounding_contradiction(verifier):
    """Benchmark Case PAS_SUPP_017: Fraud under Section 447 punishable with imprisonment, not 5000 fine."""
    evidence = (
        "447. Punishment for fraud.—any person who is found to be guilty of fraud involving an amount "
        "of at least ten lakh rupees shall be punishable with imprisonment for a term which shall not be less than six months."
    )
    claim = "Fraud under Section 447 is compoundable at the discretion of the registrar upon payment of ₹5,000."

    verdict = verifier.verify_claim(
        claim_input={"claim_id": "PAS_SUPP_017", "claim_text": claim},
        direct_evidence_text=evidence,
        direct_passage_id="PAS_ACT_COMPANIES_2013_SEC_447",
    )

    assert verdict.status == EvidenceVerdictStatus.CONTRADICTED.value
