"""
Unit Tests for Gate EV12 & EV13: Citation & Temporal Leakage Prevention
======================================================================
Protocol: v1.0-FROZEN
Tests epistemic separation:
EV12: Citation metadata / truth labels cannot influence Evidence Verdict.
EV13: Temporal metadata cannot influence Evidence Verdict.
Forbidden truth-bearing fields raise TruthLabelLeakageError.
"""

import pytest
from halo.evidence_verifier.verifier import EvidenceVerifier
from halo.evidence_verifier.schemas import (
    CitationReferenceInput,
    ClaimVerificationInput,
    EvidenceVerdictStatus,
)
from halo.evidence_verifier.exceptions import TruthLabelLeakageError


@pytest.fixture(scope="module")
def verifier():
    return EvidenceVerifier()


def test_ev12_citation_metadata_leakage_invariance(verifier):
    """
    Gate EV12: Same claim and evidence passage, but altered citation metadata.
    Evidence Verdict MUST remain strictly identical.
    """
    claim = "Under Section 135(1), companies must establish a CSR Committee."
    evidence = "Every company having net worth of ₹500 crore shall constitute a Corporate Social Responsibility Committee."

    # Run 1: Standard citation reference
    res1 = verifier.verify_claim(
        claim_input={"claim_id": "CLM_LEAK_01", "claim_text": claim, "citation_metadata": {"court": "Supreme Court", "year": 2017}},
        direct_evidence_text=evidence,
        direct_passage_id="PAS_COMMON_01",
    )

    # Run 2: Completely altered citation metadata (High Court, different year, different case name)
    res2 = verifier.verify_claim(
        claim_input={"claim_id": "CLM_LEAK_01", "claim_text": claim, "citation_metadata": {"court": "Delhi High Court", "year": 1999, "case_name": "Fictional vs Union"}},
        direct_evidence_text=evidence,
        direct_passage_id="PAS_COMMON_01",
    )

    assert res1.status == res2.status
    assert res1.nli.entailment == res2.nli.entailment
    assert res1.nli.contradiction == res2.nli.contradiction
    assert res1.decision_reason == res2.decision_reason


def test_ev13_temporal_metadata_leakage_invariance(verifier):
    """
    Gate EV13: Same claim and evidence passage, but altered temporal enforceability metadata.
    Evidence Verifier evaluates semantic entailment only, leaving temporal validity to TemporalVerifier.
    Verdict MUST remain unchanged regardless of historical/amended/repealed tags.
    """
    claim = "The minimum number of directors for a public company is three."
    evidence = "Every company shall have a minimum number of three directors in the case of a public company."

    # Run 1: Active current statute
    res1 = verifier.verify_claim(
        claim_input={"claim_id": "CLM_TEMP_01", "claim_text": claim, "temporal_status": "CURRENT", "effective_from": "2013-08-29"},
        direct_evidence_text=evidence,
        direct_passage_id="PAS_TEMP_01",
    )

    # Run 2: Historical / Repealed tag in metadata
    res2 = verifier.verify_claim(
        claim_input={"claim_id": "CLM_TEMP_01", "claim_text": claim, "temporal_status": "REPEALED", "effective_to": "2015-05-25"},
        direct_evidence_text=evidence,
        direct_passage_id="PAS_TEMP_01",
    )

    assert res1.status == res2.status
    assert res1.nli.entailment == res2.nli.entailment
    assert res1.decision_reason == res2.decision_reason


def test_forbidden_truth_label_injection_rejected(verifier):
    """Validator must immediately reject input containing forbidden ground-truth labels."""
    with pytest.raises(TruthLabelLeakageError):
        verifier.verify_claim({
            "claim_id": "CLM_LEAK_TEST",
            "claim_text": "Public companies must have three directors.",
            "ground_truth_status": "SUPPORTED",  # Forbidden leakage field
        })
