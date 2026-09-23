"""
HALO Claim Extractor: Atomicity & Decomposition Tests (Gate C2)
==============================================================
Protocol: v1.0-FROZEN
Tests decomposition of compound legal sentences, semicolons, provisos,
and coordinate conjunctions into independent atomic propositions.
"""

from halo.claim_extractor.claim_decomposer import ClaimDecomposer


def test_semicolon_split():
    """Verify that semicolons separating independent propositions are decomposed."""
    decomposer = ClaimDecomposer()
    sentence = "A public company must have at least three directors; a private company must have at least two directors."
    st = 0
    en = len(sentence)

    propositions = decomposer.decompose(sentence, st, en, parent_id_prefix="TEST_S01")
    assert len(propositions) == 2, f"Expected 2 propositions, got {len(propositions)}"

    p1, p2 = propositions
    assert "public company must have at least three directors" in p1.text
    assert "private company must have at least two directors" in p2.text
    assert p1.atomicity.is_atomic is True
    assert p1.atomicity.decomposition_type == "SEMICOLON_SPLIT"

    # Span verification
    assert sentence[p1.source_span.start_char:p1.source_span.end_char] == p1.source_span.source_text
    assert sentence[p2.source_span.start_char:p2.source_span.end_char] == p2.source_span.source_text


def test_proviso_split():
    """Verify that provisos ('Provided that...') are decomposed into separate claims."""
    decomposer = ClaimDecomposer()
    sentence = (
        "Every listed company shall appoint at least one woman director. "
        "Provided that a company covered under this section shall comply within six months."
    )
    st = 0
    en = len(sentence)

    propositions = decomposer.decompose(sentence, st, en, parent_id_prefix="TEST_S02")
    assert len(propositions) == 2

    p1, p2 = propositions
    assert "woman director" in p1.text
    assert "Provided that" in p2.text
    assert sentence[p1.source_span.start_char:p1.source_span.end_char] == p1.source_span.source_text
    assert sentence[p2.source_span.start_char:p2.source_span.end_char] == p2.source_span.source_text


def test_coordinate_clause_conjunction_split():
    """Verify decomposition of coordinate clauses linking distinct legal obligations."""
    decomposer = ClaimDecomposer()
    sentence = (
        "The company must maintain a registered office, "
        "and all statutory books must be open for inspection during business hours."
    )
    st = 0
    en = len(sentence)

    propositions = decomposer.decompose(sentence, st, en, parent_id_prefix="TEST_S03")
    assert len(propositions) == 2

    p1, p2 = propositions
    assert "maintain a registered office" in p1.text
    assert "statutory books must be open" in p2.text
    assert sentence[p1.source_span.start_char:p1.source_span.end_char] == p1.source_span.source_text
    assert sentence[p2.source_span.start_char:p2.source_span.end_char] == p2.source_span.source_text


def test_atomic_sentence_not_split():
    """Verify that a single atomic assertion is not artificially decomposed."""
    decomposer = ClaimDecomposer()
    sentence = "Every company shall hold its annual general meeting within six months of financial year end."
    st = 0
    en = len(sentence)

    propositions = decomposer.decompose(sentence, st, en, parent_id_prefix="TEST_S04")
    assert len(propositions) == 1
    assert propositions[0].text == sentence
    assert propositions[0].atomicity.is_atomic is True
    assert propositions[0].atomicity.parent_claim_id is None
