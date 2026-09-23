"""
Unit Tests for Gate EV11: Evidence Conflict & Case G
====================================================
Protocol: v1.0-FROZEN
Tests multi-evidence conflict: strong support + strong contradiction from DISTINCT passages
emits CONFLICTED and preserves all items without averaging (Case G & User Correction #7).
"""

import pytest
from halo.evidence_verifier.verifier import EvidenceVerifier
from halo.evidence_verifier.schemas import (
    EvidenceVerdictStatus,
    CitationReferenceInput,
    ClaimVerificationInput,
)
from halo.evidence_verifier.evidence_store import EvidenceStore, CanonicalPassageRecord


@pytest.fixture(scope="module")
def verifier():
    return EvidenceVerifier()


def test_case_g_conflict_across_distinct_passages(verifier):
    """
    Case G — Conflict:
    Passage A strongly supports.
    Passage B strongly contradicts.
    Expected: CONFLICTED, with both evidence items preserved in output.
    """
    store = EvidenceStore.get_instance()
    pid_supp = "PAS_CONFLICT_TEST_SUPP"
    pid_contra = "PAS_CONFLICT_TEST_CONTRA"

    # Supporting passage: explicitly allows removal by ordinary resolution
    store._passages[pid_supp] = CanonicalPassageRecord(
        passage_id=pid_supp,
        text="A company may remove an independent director before expiry of tenure by passing an ordinary resolution.",
        dataset="D1",
        source="Companies Act, 2013",
        authority_id="ACT_COMPANIES_2013_SEC_169",
        section_id="169",
    )
    # Contradicting passage: explicitly mandates special resolution and prohibits ordinary resolution
    store._passages[pid_contra] = CanonicalPassageRecord(
        passage_id=pid_contra,
        text="An independent director shall not be removed by ordinary resolution and strictly requires a special resolution.",
        dataset="D1",
        source="Companies Act, 2013",
        authority_id="ACT_COMPANIES_2013_SEC_169",
        section_id="169",
    )

    claim_input = ClaimVerificationInput(
        answer_id="ANS_CONFLICT_001",
        claim_id="CASE_G_001",
        claim_text="A company may remove an independent director by ordinary resolution.",
        claim_atomicity="ATOMIC",
        citation_refs=[
            CitationReferenceInput(citation_id="CIT_1", passage_id=pid_supp, verification_status="EXISTS"),
            CitationReferenceInput(citation_id="CIT_2", passage_id=pid_contra, verification_status="EXISTS"),
        ],
    )

    verdict = verifier.verify_claim(claim_input)

    # Gate EV11: Must emit CONFLICTED
    assert verdict.status == EvidenceVerdictStatus.CONFLICTED.value
    assert verdict.aggregation.conflict is True
    # Both items must remain in the output
    assert len(verdict.evidence_items) == 2
    item_statuses = {it.passage_id: it.local_status for it in verdict.evidence_items}
    assert item_statuses[pid_supp] == EvidenceVerdictStatus.SUPPORTED.value
    assert item_statuses[pid_contra] == EvidenceVerdictStatus.CONTRADICTED.value


def test_single_passage_cannot_conflict_with_itself(verifier):
    """
    User Correction #7: A single evidence passage can never produce CONFLICTED.
    """
    store = EvidenceStore.get_instance()
    pid = "PAS_SINGLE_TEST"
    store._passages[pid] = CanonicalPassageRecord(
        passage_id=pid,
        text="The company shall maintain the reserve of ₹500 crore.",
        dataset="D1",
        source="Companies Act, 2013",
    )

    claim_input = ClaimVerificationInput(
        answer_id="ANS_SINGLE_001",
        claim_id="CLM_SINGLE",
        claim_text="The company shall maintain the reserve of ₹500 crore.",
        citation_refs=[
            CitationReferenceInput(citation_id="CIT_1", passage_id=pid, verification_status="EXISTS"),
        ],
    )

    verdict = verifier.verify_claim(claim_input)
    assert verdict.status != EvidenceVerdictStatus.CONFLICTED.value
