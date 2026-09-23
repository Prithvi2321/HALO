"""
Unit Tests for Gate EV8: Clause-Aware Modality Mismatch
========================================================
Protocol: v1.0-FROZEN
Tests deontic modality mutation detection (Case C) and hard safety override (User Correction #4).
"""

import pytest
from halo.evidence_verifier.verifier import EvidenceVerifier
from halo.evidence_verifier.modality_checker import ModalityChecker
from halo.evidence_verifier.schemas import (
    CheckStatus,
    ModalityType,
    EvidenceVerdictStatus,
)


@pytest.fixture(scope="module")
def checker():
    return ModalityChecker()


@pytest.fixture(scope="module")
def verifier():
    return EvidenceVerifier()


def test_case_c_modality_mutation_override(verifier):
    """
    Case C — Modality Mutation:
    Evidence: The company shall file the statement within 30 days.
    Claim: The company may file the statement within 30 days.
    Expected: MODALITY_MISMATCH (MANDATORY vs PERMITTED) and CONTRADICTED status.
    """
    evidence = "The company shall file the statement within 30 days."
    claim = "The company may file the statement within 30 days."

    verdict = verifier.verify_claim(
        claim_input={"claim_id": "CASE_C_001", "claim_text": claim},
        direct_evidence_text=evidence,
        direct_passage_id="PAS_CASE_C",
    )

    assert verdict.modality_check.status == CheckStatus.MISMATCH.value
    assert verdict.modality_check.evidence_modality == ModalityType.MANDATORY.value
    assert verdict.modality_check.claim_modality == ModalityType.PERMITTED.value
    assert verdict.status == EvidenceVerdictStatus.CONTRADICTED.value


def test_csr_mandatory_vs_voluntary_mutation(verifier):
    """Benchmark Case PAS_SUPP_002: 'shall constitute' mutated to 'may voluntarily choose'."""
    evidence = (
        "(1) Every company having net worth of rupees five hundred crore or more "
        "shall constitute a Corporate Social Responsibility Committee of the Board."
    )
    claim = "Companies with turnover exceeding ₹1,000 crore may voluntarily choose whether to constitute CSR Committee."

    verdict = verifier.verify_claim(
        claim_input={"claim_id": "PAS_SUPP_002", "claim_text": claim},
        direct_evidence_text=evidence,
        direct_passage_id="PAS_ACT_COMPANIES_2013_SEC_135_SUB_1",
    )

    assert verdict.modality_check.status == CheckStatus.MISMATCH.value
    assert verdict.status == EvidenceVerdictStatus.CONTRADICTED.value


def test_multi_word_prohibition_patterns(checker):
    """User Correction #4: 'may not' and 'shall not' recognized as PROHIBITED."""
    assert checker.detect_modality("The company may not disclose confidential documents.") == ModalityType.PROHIBITED
    assert checker.detect_modality("No director shall vote on this contract.") == ModalityType.PROHIBITED
    assert checker.detect_modality("The board is prohibited from approving the sale.") == ModalityType.PROHIBITED
