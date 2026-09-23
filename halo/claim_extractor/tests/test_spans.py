"""
HALO Claim Extractor: Span Integrity & Offset Tests (Gate C7)
============================================================
Protocol: v1.0-FROZEN
Tests 100% byte-for-byte character offset integrity across single and compound claims.
Guarantees answer[start_char:end_char] == source_text across diverse inputs.
"""

import pytest
from halo.claim_extractor.extractor import ClaimExtractor
from halo.claim_extractor.span_aligner import SpanAligner
from halo.claim_extractor.schemas import SourceSpan
from halo.claim_extractor.exceptions import SpanAlignmentError


def test_span_integrity_on_complex_text():
    """Verify that every extracted claim matches the exact slice of the input text."""
    extractor = ClaimExtractor()
    text = (
        "According to Section 188(1) of the Companies Act, 2013, related party transactions "
        "require prior consent of the Board of Directors given by a resolution at a meeting of the Board; "
        "furthermore, transactions exceeding ₹100 crore or 10% of turnover require prior approval by ordinary resolution. "
        "However, this requirement does not apply to transactions entered into by the company in its ordinary course of business."
    )
    res = extractor.extract(text, answer_id="ANS_SPAN_01")

    assert len(res.claims) >= 3
    aligner = SpanAligner()

    for claim in res.claims:
        # Direct verification
        st = claim.source_span.start_char
        en = claim.source_span.end_char
        actual = text[st:en]
        assert actual == claim.source_span.source_text, f"Span mismatch: '{actual}' != '{claim.source_span.source_text}'"

        # Verification via aligner
        assert aligner.verify_span(text, claim.source_span) is True


def test_span_aligner_raises_on_corrupted_offset():
    """Verify that SpanAligner immediately detects and raises on offset corruption."""
    aligner = SpanAligner()
    text = "Section 135 mandates CSR."

    # Corrupted start offset
    corrupted_span = SourceSpan(start_char=5, end_char=25, source_text="Section 135 mandates CSR.")
    with pytest.raises(SpanAlignmentError):
        aligner.verify_span(text, corrupted_span)

    # Out of bounds offset
    oob_span = SourceSpan(start_char=0, end_char=100, source_text="Section 135 mandates CSR.")
    with pytest.raises(SpanAlignmentError):
        aligner.verify_span(text, oob_span)
