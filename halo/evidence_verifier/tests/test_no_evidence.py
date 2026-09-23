"""
Unit Tests for Gate EV6: No-Evidence Policy & Case D
====================================================
Protocol: v1.0-FROZEN
Tests fail-safe property: no evidence, empty evidence, or unverified citation
MUST emit UNRESOLVED. Never emits SUPPORTED or CONTRADICTED.
"""

import pytest
from halo.evidence_verifier.verifier import EvidenceVerifier
from halo.evidence_verifier.schemas import (
    EvidenceVerdictStatus,
    CitationReferenceInput,
    ClaimVerificationInput,
)


@pytest.fixture(scope="module")
def verifier():
    return EvidenceVerifier()


def test_case_d_no_evidence_emits_unresolved(verifier):
    """
    Case D — No Evidence:
    Claim exists. Evidence: none.
    Expected: UNRESOLVED.
    """
    claim_input = ClaimVerificationInput(
        answer_id="ANS_NO_EV_001",
        claim_id="CASE_D_001",
        claim_text="The company must hold four board meetings every calendar year.",
        citation_refs=[],
    )

    verdict = verifier.verify_claim(claim_input)

    assert verdict.status == EvidenceVerdictStatus.UNRESOLVED.value
    assert len(verdict.evidence_items) == 0
    assert verdict.best_evidence_id is None
    assert "No verified authoritative evidence passage" in verdict.decision_reason


def test_empty_evidence_string_emits_unresolved(verifier):
    """Direct empty string evidence must emit UNRESOLVED."""
    res = verifier.verify(
        claim="The company must file its annual returns.",
        evidence_passage="",
        case_id="CLM_EMPTY_EV",
    )
    assert res.status == EvidenceVerdictStatus.UNRESOLVED.value


def test_unverified_citation_blocked_by_acceptance_gate(verifier):
    """
    User Correction #16: Citation Verifier Acceptance Gate.
    If citation status != EXISTS, citation is rejected and UNRESOLVED is emitted.
    """
    claim_input = ClaimVerificationInput(
        answer_id="ANS_UNVERIF_001",
        claim_id="CLM_UNVERIF_001",
        claim_text="Section 999 mandates quarterly filing.",
        citation_refs=[
            CitationReferenceInput(
                citation_id="CIT_FABRICATED",
                passage_id="PAS_NONEXISTENT",
                verification_status="NOT_FOUND",  # Blocked by gate
            )
        ],
    )

    verdict = verifier.verify_claim(claim_input)
    assert verdict.status == EvidenceVerdictStatus.UNRESOLVED.value
