"""
Unit Tests for Neutral / Tangential Evidence & Case E
=====================================================
Protocol: v1.0-FROZEN
Tests handling of tangential or insufficient evidence where premise neither entails nor refutes hypothesis.
"""

import pytest
from halo.evidence_verifier.verifier import EvidenceVerifier
from halo.evidence_verifier.schemas import EvidenceVerdictStatus


@pytest.fixture(scope="module")
def verifier():
    return EvidenceVerifier()


def test_case_e_neutral_tangential(verifier):
    """
    Case E — Neutral:
    Evidence concerns: appointment of directors.
    Claim concerns: minimum reserve requirement.
    Expected: NEUTRAL
    """
    evidence = (
        "Every company shall have a Board of Directors consisting of individuals as directors "
        "and shall have a minimum number of three directors in the case of a public company."
    )
    claim = "The company must maintain a mandatory minimum liquid cash reserve under banking regulations."

    verdict = verifier.verify_claim(
        claim_input={"claim_id": "CASE_E_001", "claim_text": claim},
        direct_evidence_text=evidence,
        direct_passage_id="PAS_CASE_E",
    )

    assert verdict.status == EvidenceVerdictStatus.NEUTRAL.value
    assert verdict.nli.neutral > 0.40


def test_unrelated_statutory_topics_neutral(verifier):
    """Evidence about director resignation vs claim about share certificate stamping."""
    evidence = "A director may resign from his office by giving a notice in writing to the company under Section 168."
    claim = "Share certificates must be stamped with official seal within 60 days of allotment."

    verdict = verifier.verify_claim(
        claim_input={"claim_id": "NEUT_002", "claim_text": claim},
        direct_evidence_text=evidence,
        direct_passage_id="PAS_NEUT_002",
    )

    assert verdict.status == EvidenceVerdictStatus.NEUTRAL.value
