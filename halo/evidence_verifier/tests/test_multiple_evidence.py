"""
Unit Tests for Gate EV10: Multi-Evidence Aggregation & Case F
=============================================================
Protocol: v1.0-FROZEN
Tests multi-evidence evaluation: multiple supporting evidence items are preserved
without averaging or dropping candidate passages (Case F).
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


def test_case_f_multiple_supporting_evidence_preserved(verifier):
    """
    Case F — Multiple Supporting Evidence:
    Passage A supports.
    Passage B supports.
    Expected: SUPPORTED, with both evidence items preserved in the output.
    """
    store = EvidenceStore.get_instance()
    pid_a = "PAS_MULTI_TEST_A"
    pid_b = "PAS_MULTI_TEST_B"

    store._passages[pid_a] = CanonicalPassageRecord(
        passage_id=pid_a,
        text="Every public company shall have a minimum number of three directors on its Board of Directors.",
        dataset="D1",
        source="Companies Act, 2013",
        authority_id="ACT_COMPANIES_2013_SEC_149",
        section_id="149",
    )
    store._passages[pid_b] = CanonicalPassageRecord(
        passage_id=pid_b,
        text="A public company must have at least three directors under statutory governance requirements.",
        dataset="D1",
        source="Companies Act, 2013",
        authority_id="ACT_COMPANIES_2013_SEC_149",
        section_id="149",
    )

    claim_input = ClaimVerificationInput(
        answer_id="ANS_MULTI_001",
        claim_id="CASE_F_001",
        claim_text="Every public company must have at least three directors.",
        claim_atomicity="ATOMIC",
        citation_refs=[
            CitationReferenceInput(citation_id="CIT_A", passage_id=pid_a, verification_status="EXISTS"),
            CitationReferenceInput(citation_id="CIT_B", passage_id=pid_b, verification_status="EXISTS"),
        ],
    )

    verdict = verifier.verify_claim(claim_input)

    assert verdict.status == EvidenceVerdictStatus.SUPPORTED.value
    # Gate EV10: Both evidence items must remain in the output
    assert len(verdict.evidence_items) == 2
    item_pids = {it.passage_id for it in verdict.evidence_items}
    assert item_pids == {pid_a, pid_b}
    assert verdict.aggregation.support_count == 2
    assert not verdict.aggregation.conflict
