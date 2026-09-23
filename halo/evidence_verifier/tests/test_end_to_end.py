"""
Unit Tests for Gate EV16: End-to-End Subsystem Integration
==========================================================
Protocol: v1.0-FROZEN
Tests integration flow: Extracted Claims -> Citation Verifier -> Evidence Verifier.
Verifies seamless schema compatibility and answer-level aggregation.
"""

import pytest
from halo.evidence_verifier.verifier import EvidenceVerifier
from halo.evidence_verifier.schemas import (
    EvidenceVerdictStatus,
    ClaimVerificationInput,
    CitationReferenceInput,
)
from halo.evidence_verifier.evidence_store import EvidenceStore, CanonicalPassageRecord


@pytest.fixture(scope="module")
def verifier():
    return EvidenceVerifier()


def test_end_to_end_answer_payload_verification(verifier):
    """
    Gate EV16: Answers containing multiple claims and associated verified citations
    are verified end-to-end without schema breakdown.
    """
    store = EvidenceStore.get_instance()
    pid1 = "PAS_E2E_001"
    pid2 = "PAS_E2E_002"

    store._passages[pid1] = CanonicalPassageRecord(
        passage_id=pid1,
        text="Every public company shall have a minimum number of three directors.",
        dataset="D1",
        source="Companies Act, 2013",
    )
    store._passages[pid2] = CanonicalPassageRecord(
        passage_id=pid2,
        text="The penalty for failure shall not exceed ₹500 crore.",
        dataset="D1",
        source="Companies Act, 2013",
    )

    answer_payload = {
        "schema_version": "1.0.0",
        "answer_id": "ANS_E2E_999",
        "claims": [
            {
                "claim_id": "CLM_E2E_001",
                "claim_text": "Public companies must have at least three directors.",
                "claim_atomicity": "ATOMIC",
                "citation_refs": [
                    {"citation_id": "CIT_001", "passage_id": pid1, "verification_status": "EXISTS"}
                ],
            },
            {
                "claim_id": "CLM_E2E_002",
                "claim_text": "The penalty for failure is ₹50 crore.",
                "claim_atomicity": "ATOMIC",
                "citation_refs": [
                    {"citation_id": "CIT_002", "passage_id": pid2, "verification_status": "EXISTS"}
                ],
            },
        ],
    }

    result = verifier.verify_answer(answer_payload)

    assert result.success is True
    assert result.total_claims == 2
    assert len(result.verdicts) == 2

    v1 = result.verdicts[0]
    v2 = result.verdicts[1]

    # Claim 1 should be SUPPORTED
    assert v1.status == EvidenceVerdictStatus.SUPPORTED.value
    # Claim 2 should be CONTRADICTED (50 crore vs 500 crore)
    assert v2.status == EvidenceVerdictStatus.CONTRADICTED.value

    # Check metrics
    assert result.metrics["total_claims"] == 2
    assert result.metrics["status_counts"]["SUPPORTED"] == 1
    assert result.metrics["status_counts"]["CONTRADICTED"] == 1
    assert len(result.output_hash) == 64
