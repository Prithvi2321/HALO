"""
HALO Claim Extractor: Segmentation Tests
========================================
Protocol: v1.0-FROZEN
Tests legal sentence segmentation, abbreviation protection (Sec., w.e.f., Ltd., v., S.C.R.),
and character span offset accuracy.
"""

from halo.claim_extractor.segmenter import LegalSentenceSegmenter


def test_abbreviation_protection():
    """Verify that common legal abbreviations do not trigger false sentence breaks."""
    segmenter = LegalSentenceSegmenter()
    text = (
        "In Tata Consultancy Services Ltd. v. State of A.P., the Hon'ble Supreme Court interpreted Sec. 135. "
        "The notification was issued w.e.f. 01.04.2014 by the Govt. of India."
    )
    segments = segmenter.segment(text)

    # Should be exactly 2 sentences, not broken at Ltd., v., Hon'ble, Sec., w.e.f., Govt.
    assert len(segments) == 2, f"Expected 2 sentences, got {len(segments)}: {[s.text for s in segments]}"
    assert "Tata Consultancy Services Ltd. v. State of A.P." in segments[0].text
    assert "Sec. 135" in segments[0].text
    assert "w.e.f. 01.04.2014" in segments[1].text


def test_segment_span_integrity():
    """Verify that every segmented sentence precisely matches text[start_char:end_char]."""
    segmenter = LegalSentenceSegmenter()
    text = (
        "Section 135(1) mandates a CSR Committee. "
        "Every company meeting net worth of ₹500 crore shall comply. "
        "Failure to comply results in penalties under Section 134(8)."
    )
    segments = segmenter.segment(text)
    assert len(segments) == 3

    for seg in segments:
        extracted_slice = text[seg.start_char:seg.end_char]
        assert extracted_slice == seg.text, f"Span mismatch: '{extracted_slice}' != '{seg.text}'"


def test_empty_and_whitespace():
    """Verify that empty or whitespace strings yield zero segments."""
    segmenter = LegalSentenceSegmenter()
    assert segmenter.segment("") == []
    assert segmenter.segment("   \n\t   ") == []


def test_newlines_and_paragraph_boundaries():
    """Verify proper segmentation across paragraph breaks."""
    segmenter = LegalSentenceSegmenter()
    text = "First legal proposition under Section 102.\n\nSecond legal proposition under Section 134."
    segments = segmenter.segment(text)
    assert len(segments) == 2
    for seg in segments:
        assert text[seg.start_char:seg.end_char] == seg.text
