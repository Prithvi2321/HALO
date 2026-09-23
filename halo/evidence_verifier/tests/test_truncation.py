"""
Unit Tests for Passage Chunking & Truncation Handling
=====================================================
Protocol: v1.0-FROZEN
Tests deterministic sliding-window chunking when legal evidence exceeds model window
(User Correction #14). Proves dispositive clauses at the end of long passages are NOT silently lost.
"""

import pytest
from halo.evidence_verifier.nli_engine import NLIEngine
from halo.evidence_verifier.verifier import EvidenceVerifier
from halo.evidence_verifier.schemas import EvidenceVerdictStatus


@pytest.fixture(scope="module")
def verifier():
    return EvidenceVerifier()


def test_long_passage_sliding_window_chunking(verifier):
    """
    User Correction #14: Tests long passage (> 512 tokens) with the dispositive rule
    placed at the very end. Verifies sliding window chunking preserves the dispositive rule.
    """
    filler_sentence = "The Central Government may, by notification, appoint such persons as it thinks fit to be inspectors. "
    # Create ~600 tokens of preamble text
    preamble = filler_sentence * 25

    # Dispositive clause placed at the very end
    dispositive_clause = "Provided that every listed company shall have at least one woman director on its board."
    long_passage = preamble + dispositive_clause

    claim = "Every listed company is required to have at least one woman director."

    res = verifier.nli_engine.predict(
        premise_evidence=long_passage,
        hypothesis_claim=claim,
        claim_id="CLM_TRUNC_TEST",
        passage_id="PAS_LONG_001",
    )

    # Must have evaluated multiple chunks
    assert res.chunks_evaluated > 1
    # Must successfully recognize entailment despite length
    assert res.probabilities.entailment >= 0.70
    assert res.predicted_label == "entailment"


def test_chunking_preserves_contradiction_at_end(verifier):
    """Contradicting clause placed at the end of long passage is detected."""
    filler = "The Registrar may require any person to produce any document or book. "
    long_passage = (filler * 25) + "The maximum fine for this contravention shall not exceed ₹500 crore."
    claim = "The maximum fine for this contravention is ₹50 crore."

    verdict = verifier.verify_claim(
        claim_input={"claim_id": "CLM_TRUNC_CONTRA", "claim_text": claim},
        direct_evidence_text=long_passage,
        direct_passage_id="PAS_LONG_CONTRA",
    )

    assert verdict.status == EvidenceVerdictStatus.CONTRADICTED.value
