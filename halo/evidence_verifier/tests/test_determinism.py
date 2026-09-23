"""
Unit Tests for Gate EV5: Deterministic Inference & Numerical Reproducibility
============================================================================
Protocol: v1.0-FROZEN
Tests semantic determinism and numerical reproducibility within epsilon tolerance (User Correction #13).
"""

import pytest
from halo.evidence_verifier.verifier import EvidenceVerifier


@pytest.fixture(scope="module")
def verifier():
    return EvidenceVerifier()


def test_semantic_determinism_across_runs(verifier):
    """
    Gate EV5 / User Correction #13:
    Repeated identical inputs must produce identical verdicts, statuses, and reasons.
    """
    claim = "The company shall maintain the required reserve of ₹500 crore."
    evidence = "The company shall maintain the required reserve of ₹500 crore."

    runs = []
    for _ in range(5):
        verdict = verifier.verify_claim(
            claim_input={"claim_id": "DET_001", "claim_text": claim},
            direct_evidence_text=evidence,
            direct_passage_id="PAS_DET_001",
        )
        runs.append(verdict)

    first = runs[0]
    for other in runs[1:]:
        # Semantic determinism
        assert other.status == first.status
        assert other.decision_reason == first.decision_reason
        assert other.best_evidence_id == first.best_evidence_id
        assert other.numerical_check.status == first.numerical_check.status
        assert other.modality_check.status == first.modality_check.status
        assert other.negation_check.status == first.negation_check.status

        # Numerical reproducibility within tolerance: |p1 - p2| <= 1e-5
        assert abs(other.nli.entailment - first.nli.entailment) <= 1e-5
        assert abs(other.nli.contradiction - first.nli.contradiction) <= 1e-5
        assert abs(other.nli.neutral - first.nli.neutral) <= 1e-5
