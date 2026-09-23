"""
HALO Citation Verifier: Determinism & Hash Reproducibility Tests (Gate CV8)
==========================================================================
Protocol: v1.0-FROZEN
Tests deterministic execution: identical citation inputs produce bit-for-bit
identical output structures, identical citation IDs, and matching SHA-256 hashes.
"""

from halo.citation_verifier.verifier import verify_citations


def test_repeated_verification_determinism():
    """Verify that multiple runs on identical input produce identical hashes and records."""
    text = "Under Section 135(1) of the Companies Act, 2013 and Section 188, companies have compliance duties."

    results = [verify_citations(text, answer_id="ANS_DET_VERIF") for _ in range(5)]

    first = results[0]
    for other in results[1:]:
        assert other.input_hash == first.input_hash
        assert other.output_hash == first.output_hash
        assert other.total_citations == first.total_citations

        for c1, c2 in zip(first.citation_results, other.citation_results):
            assert c1.citation_id == c2.citation_id
            assert c1.citation_text == c2.citation_text
            assert c1.existence.status == c2.existence.status
            assert c1.metadata.status == c2.metadata.status
            assert c1.output_hash == c2.output_hash
