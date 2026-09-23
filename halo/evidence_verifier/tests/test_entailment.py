"""
Unit Tests for Substantive Semantic Entailment & Case A (Supported)
===================================================================
Protocol: v1.0-FROZEN
Tests semantic evidence entailment where authoritative passage corroborates atomic claim.
"""

import pytest
from halo.evidence_verifier.verifier import EvidenceVerifier
from halo.evidence_verifier.schemas import EvidenceVerdictStatus, CheckStatus


@pytest.fixture(scope="module")
def verifier():
    return EvidenceVerifier()


def test_case_a_exact_supported(verifier):
    """
    Case A — Supported:
    Evidence: The company shall maintain the required reserve of ₹500 crore.
    Claim: The company shall maintain the required reserve of ₹500 crore.
    Expected: SUPPORTED
    """
    evidence = "The company shall maintain the required reserve of ₹500 crore."
    claim = "The company shall maintain the required reserve of ₹500 crore."

    verdict = verifier.verify_claim(
        claim_input={"claim_id": "CASE_A_001", "claim_text": claim},
        direct_evidence_text=evidence,
        direct_passage_id="PAS_CASE_A",
    )

    assert verdict.status == EvidenceVerdictStatus.SUPPORTED.value
    assert verdict.best_evidence_id == "PAS_CASE_A"
    assert verdict.nli.entailment >= 0.75
    assert verdict.nli.contradiction < 0.15
    assert verdict.numerical_check.status in (CheckStatus.MATCH.value, CheckStatus.NOT_APPLICABLE.value)


def test_statutory_csr_threshold_entailment(verifier):
    """Benchmark Case PAS_SUPP_001: CSR ₹5 crore net profit threshold."""
    evidence = (
        "(1) Every company having net worth of rupees five hundred crore or more, "
        "or turnover of rupees one thousand crore or more or a net profit of rupees five crore or more "
        "during the immediately preceding financial year shall constitute a Corporate Social Responsibility Committee."
    )
    claim = (
        "A company with a net profit of rupees five crore or more during the immediately preceding "
        "financial year must constitute a CSR Committee."
    )

    verdict = verifier.verify_claim(
        claim_input={"claim_id": "PAS_SUPP_001", "claim_text": claim},
        direct_evidence_text=evidence,
        direct_passage_id="PAS_ACT_COMPANIES_2013_SEC_135_SUB_1",
    )

    assert verdict.status == EvidenceVerdictStatus.SUPPORTED.value
    assert verdict.nli.entailment >= 0.75


def test_public_company_minimum_directors_entailment(verifier):
    """Benchmark Case PAS_SUPP_009: Minimum 3 directors for public company."""
    evidence = (
        "(1) Every company shall have a Board of Directors consisting of individuals as directors and shall have— "
        "(a) a minimum number of three directors in the case of a public company, two directors in the case of a private company."
    )
    claim = "Under Section 149(1)(a), every public company shall have a minimum number of three directors."

    verdict = verifier.verify_claim(
        claim_input={"claim_id": "PAS_SUPP_009", "claim_text": claim},
        direct_evidence_text=evidence,
        direct_passage_id="PAS_ACT_COMPANIES_2013_SEC_149_SUB_1",
    )

    assert verdict.status == EvidenceVerdictStatus.SUPPORTED.value
    assert verdict.nli.entailment >= 0.75
