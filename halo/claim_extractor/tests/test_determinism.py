"""
HALO Claim Extractor: Determinism & Hash Tests (Gate C8)
=======================================================
Protocol: v1.0-FROZEN
Tests deterministic execution: identical inputs produce bit-for-bit identical outputs,
identical claim IDs, and matching SHA-256 output hashes across independent executions.
"""

from halo.claim_extractor.extractor import ClaimExtractor


def test_repeated_execution_determinism():
    """Verify that multiple extraction runs on identical input yield identical hashes and claims."""
    extractor = ClaimExtractor()
    text = (
        "Section 135(1) of the Companies Act, 2013 mandates that every qualifying company "
        "shall constitute a Corporate Social Responsibility Committee; "
        "such committee shall consist of three or more directors, with at least one independent director."
    )

    results = [extractor.extract(text, answer_id="ANS_DET_01") for _ in range(5)]

    first = results[0]
    for other in results[1:]:
        assert other.input_hash == first.input_hash
        assert other.output_hash == first.output_hash
        assert len(other.claims) == len(first.claims)


        for c1, c2 in zip(first.claims, other.claims):
            assert c1.claim_id == c2.claim_id
            assert c1.claim_text == c2.claim_text
            assert c1.claim_type == c2.claim_type
            assert c1.source_span == c2.source_span
            assert c1.normalized_claim_key == c2.normalized_claim_key
