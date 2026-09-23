"""
HALO Claim Extractor: End-to-End Pipeline & Auditability Tests (Gate C12)
========================================================================
Protocol: v1.0-FROZEN
Tests end-to-end claim extraction pipeline, refusal text filtering,
round-trip JSONL export, and SHA-256 auditability.
"""

from halo.claim_extractor.extractor import ClaimExtractor
from halo.claim_extractor.schemas import ClaimExtractionResult


def test_refusal_text_handling():
    """Verify that refusal and disclaimer statements are filtered out cleanly."""
    extractor = ClaimExtractor()
    refusal_text = "I do not have sufficient legal evidence to answer this question."
    res = extractor.extract(refusal_text, answer_id="ANS_REFUSAL_01")

    assert res.success is True
    assert len(res.claims) == 0


def test_end_to_end_b5_answer_extraction():
    """Verify end-to-end extraction on a representative B5-generated answer."""
    extractor = ClaimExtractor()
    b5_answer = (
        "Based on the authoritative legal evidence provided, Section 135(1) of the Companies Act, 2013 "
        "mandates that every company having net worth of ₹500 crore or more shall constitute a Corporate Social Responsibility Committee. "
        "Furthermore, Section 135(5) requires the Board to ensure that the company spends at least two per cent of the average net profits. "
        "Failure to comply with these provisions attracts penalty proceedings under Section 134(8)."
    )

    res = extractor.extract(b5_answer, answer_id="EXP_B5_DEV_SAMPLE")

    assert res.success is True
    assert len(res.claims) >= 3
    assert len(res.input_hash) == 64
    assert len(res.output_hash) == 64

    # Verify 100% byte-for-byte span alignment across all claims
    for claim in res.claims:
        st = claim.source_span.start_char
        en = claim.source_span.end_char
        assert b5_answer[st:en] == claim.source_span.source_text
        assert len(claim.citation_refs) >= 1

    # Round-trip dictionary test
    result_dict = res.to_dict()
    reconstructed = ClaimExtractionResult.from_dict(result_dict)
    assert reconstructed.output_hash == res.output_hash
    assert len(reconstructed.claims) == len(res.claims)

