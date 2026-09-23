"""
Unit Tests for Gate EV7: Numerical Mismatch & Substantive Number Separation
==========================================================================
Protocol: v1.0-FROZEN
Tests numerical mutation detection (Case B), substantive vs citation separation (User Correction #3),
and hard safety override blocking SUPPORTED (User Correction #2).
"""

import pytest
from halo.evidence_verifier.verifier import EvidenceVerifier
from halo.evidence_verifier.numerical_checker import NumericalChecker
from halo.evidence_verifier.schemas import (
    CheckStatus,
    NumericalMismatchType,
    EvidenceVerdictStatus,
)


@pytest.fixture(scope="module")
def checker():
    return NumericalChecker()


@pytest.fixture(scope="module")
def verifier():
    return EvidenceVerifier()


def test_case_b_numerical_mutation_override(verifier):
    """
    Case B — Numerical Mutation:
    Evidence: The company shall maintain a reserve of ₹500 crore.
    Claim: The company shall maintain a reserve of ₹50 crore.
    Expected: Numerical MISMATCH (AMOUNT_CHANGE) and final CONTRADICTED status.
    """
    evidence = "The company shall maintain a reserve of ₹500 crore."
    claim = "The company shall maintain a reserve of ₹50 crore."

    verdict = verifier.verify_claim(
        claim_input={"claim_id": "CASE_B_001", "claim_text": claim},
        direct_evidence_text=evidence,
        direct_passage_id="PAS_CASE_B",
    )

    assert verdict.numerical_check.status == CheckStatus.MISMATCH.value
    assert verdict.numerical_check.mismatch_type == NumericalMismatchType.AMOUNT_CHANGE.value
    assert verdict.status == EvidenceVerdictStatus.CONTRADICTED.value


def test_csr_net_worth_mutation_benchmark(verifier):
    """Benchmark Case PAS_SUPP_003: ₹500 crore statutory threshold mutated to ₹50 crore."""
    evidence = (
        "(1) Every company having net worth of rupees five hundred crore or more, "
        "or turnover of rupees one thousand crore or more shall constitute a CSR Committee."
    )
    claim = "Under Section 135(1), a company must have a net worth of rupees fifty crore or more to trigger mandatory CSR."

    verdict = verifier.verify_claim(
        claim_input={"claim_id": "PAS_SUPP_003", "claim_text": claim},
        direct_evidence_text=evidence,
        direct_passage_id="PAS_ACT_COMPANIES_2013_SEC_135_SUB_1",
    )

    assert verdict.numerical_check.status == CheckStatus.MISMATCH.value
    assert verdict.status == EvidenceVerdictStatus.CONTRADICTED.value


def test_private_company_directors_count_mutation(verifier):
    """Benchmark Case PAS_SUPP_010: Private company minimum 2 directors mutated to 5."""
    evidence = (
        "Every company shall have a minimum number of three directors in the case of a public company, "
        "two directors in the case of a private company."
    )
    claim = "Section 149(1)(a) requires every private company to have at least five directors."

    verdict = verifier.verify_claim(
        claim_input={"claim_id": "PAS_SUPP_010", "claim_text": claim},
        direct_evidence_text=evidence,
        direct_passage_id="PAS_ACT_COMPANIES_2013_SEC_149_SUB_1",
    )

    assert verdict.numerical_check.status == CheckStatus.MISMATCH.value
    assert verdict.status == EvidenceVerdictStatus.CONTRADICTED.value


def test_citation_numbers_ignored_by_checker(checker):
    """
    User Correction #3: Citation identifiers (Section 135, Rule 12) must NOT
    be treated as substantive numerical quantities.
    """
    text_with_cits = "Under Section 135(1) and Rule 4(a) of the Companies Act, the company filed its report."
    quantities = checker._extract_quantities(text_with_cits)
    # No substantive amounts or counts should be extracted
    assert len(quantities) == 0


def test_matching_numbers_do_not_imply_support(verifier):
    """
    Critical Invariant: Matching numbers do NOT imply entailment.
    Evidence: The penalty shall not exceed ₹500 crore.
    Claim: The penalty is ₹500 crore.
    """
    evidence = "The penalty shall not exceed ₹500 crore."
    claim = "The penalty is fixed at ₹500 crore in all cases."

    verdict = verifier.verify_claim(
        claim_input={"claim_id": "NUM_MATCH_NOT_SUPP", "claim_text": claim},
        direct_evidence_text=evidence,
        direct_passage_id="PAS_PENALTY",
    )

    # Numerical check matches the 500 crore, but final verdict cannot be blindly SUPPORTED
    assert verdict.numerical_check.status == CheckStatus.MATCH.value
    assert verdict.status != EvidenceVerdictStatus.SUPPORTED.value
