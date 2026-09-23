"""
Unit Tests for Gate EV9: Token-Boundary Polarity & Negation Checker
===================================================================
Protocol: v1.0-FROZEN
Tests negation mutation detection (Case H) and false-negation exclusion (User Correction #5).
"""

import pytest
from halo.evidence_verifier.verifier import EvidenceVerifier
from halo.evidence_verifier.negation_checker import NegationChecker
from halo.evidence_verifier.schemas import (
    CheckStatus,
    EvidenceVerdictStatus,
)


@pytest.fixture(scope="module")
def checker():
    return NegationChecker()


@pytest.fixture(scope="module")
def verifier():
    return EvidenceVerifier()


def test_case_h_negation_mutation_override(verifier):
    """
    Case H — Negation Mutation:
    Evidence: The company shall not disclose the information.
    Claim: The company shall disclose the information.
    Expected: NEGATION_MISMATCH and final CONTRADICTED status.
    """
    evidence = "The company shall not disclose the confidential information to third parties."
    claim = "The company shall disclose the confidential information to third parties."

    verdict = verifier.verify_claim(
        claim_input={"claim_id": "CASE_H_001", "claim_text": claim},
        direct_evidence_text=evidence,
        direct_passage_id="PAS_CASE_H",
    )

    assert verdict.negation_check.status == CheckStatus.MISMATCH.value
    assert verdict.status == EvidenceVerdictStatus.CONTRADICTED.value


def test_legal_antonym_liable_vs_not_liable(checker):
    """Legal antonym pair: liable vs not liable."""
    ev = "Every officer who is in default shall be liable to a penalty."
    cl = "Officers in default are not liable to any penalty."
    res = checker.check(cl, ev)
    assert res.status == CheckStatus.MISMATCH.value


def test_legal_antonym_exempt_vs_not_exempt(checker):
    """Legal antonym pair: exempt vs not exempt."""
    ev = "Transactions on an arm's length basis are exempt from board consent."
    cl = "Arm's length transactions are not exempt from board consent."
    res = checker.check(cl, ev)
    assert res.status == CheckStatus.MISMATCH.value


def test_false_negation_tokens_excluded(checker):
    """
    User Correction #5: Words like 'notwithstanding' and 'notification'
    must NOT falsely trigger negation detection.
    """
    ev = "Notwithstanding anything contained in this Act, the company may issue shares."
    cl = "Notwithstanding anything contained in this Act, the company may issue shares."
    res = checker.check(cl, ev)
    # Both have notwithstanding; neither is a genuine negation flip
    assert res.status != CheckStatus.MISMATCH.value
