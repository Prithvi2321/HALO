"""
HALO Citation Verifier: Original Text & Span Preservation Tests (Gate CV7)
=========================================================================
Protocol: v1.0-FROZEN
Tests that original citation strings and character offsets are preserved verbatim,
including punctuation, abbreviations, and Unicode characters.
"""

from halo.citation_verifier.verifier import verify_citations


def test_original_citation_text_preserved_verbatim():
    """Verify that original raw citation text is preserved exactly as extracted."""
    raw_cit = "Section 135(1)(a) of the Companies Act, 2013"
    res = verify_citations(raw_cit)
    assert res.total_citations == 1
    c = res.citation_results[0]
    assert c.citation_text == raw_cit


def test_unicode_citation_handling():
    """Verify handling of Unicode characters and non-standard spacing."""
    raw_cit = "Section 135(1) — Companies Act, 2013 [₹500 crore rule]"
    res = verify_citations(raw_cit)
    assert res.total_citations >= 1
    c = res.citation_results[0]
    assert "₹500 crore" in c.citation_text
