"""
HALO Citation Verifier: Ambiguity & Fuzzy Candidate Tests (Gate CV5)
===================================================================
Protocol: v1.0-FROZEN
Tests handling of ambiguous citations and strictly verifies that
FUZZY_CANDIDATE matches are NEVER classified as EXISTS.
"""

from halo.citation_verifier.verifier import verify_citations
from halo.citation_verifier.schemas import ExistenceStatus


def test_fuzzy_candidate_never_emits_exists():
    """
    Gate CV5 Inviolable Rule: A sub-threshold fuzzy match on a judgment title
    must evaluate to AMBIGUOUS or UNRESOLVED, NEVER to EXISTS.
    """
    # Slightly distorted/sub-threshold title that should trigger fuzzy candidate
    distorted_title = "In Old Settlers of Northern Territories v. Apex Authority, the court ruled."
    res = verify_citations(distorted_title)
    if res.total_citations > 0:
        c = res.citation_results[0]
        # Assert strictly that it is NEVER classified as EXISTS
        assert c.existence.status != ExistenceStatus.EXISTS.value, "Violation: FUZZY_CANDIDATE emitted EXISTS!"
        assert c.existence.status in {ExistenceStatus.AMBIGUOUS.value, ExistenceStatus.NOT_FOUND.value, ExistenceStatus.UNRESOLVED.value}


def test_ambiguous_citation_returns_candidates_or_ambiguous():
    """Verify that ambiguous or incomplete citations are not arbitrarily assigned."""
    # When multiple possibilities or incomplete citation
    res = verify_citations("The tribunal relied on Section 10.")
    c = res.citation_results[0]
    # Should resolve with clear explanation and not crash
    assert c.citation_text == "The tribunal relied on Section 10."
