"""
HALO Citation Verifier: Citation-to-Claim Association Tests (Gate CV6)
=====================================================================
Protocol: v1.0-FROZEN
Tests mapping between citations and extracted claims.
Verifies multi-claim associations and preservation of matched_passage_ids.
"""

from halo.citation_verifier.verifier import verify_citations


def test_one_citation_associated_with_multiple_claims():
    """Verify that a single citation referenced across multiple claims captures all claim_ids."""
    claims_payload = {
        "answer_id": "ANS_MULTI_ASSOC",
        "claims": [
            {
                "claim_id": "ANS_MULTI_ASSOC_C001",
                "claim_text": "Section 135(1) mandates a CSR Committee.",
                "source_span": {"start_char": 0, "end_char": 42},
                "citation_refs": [{"citation_text": "Section 135(1)", "start_char": 0, "end_char": 14}]
            },
            {
                "claim_id": "ANS_MULTI_ASSOC_C002",
                "claim_text": "Section 135(1) applies to firms with net worth of ₹500 crore.",
                "source_span": {"start_char": 43, "end_char": 105},
                "citation_refs": [{"citation_text": "Section 135(1)", "start_char": 43, "end_char": 57}]
            }
        ],
        "citations": [
            {"citation_text": "Section 135(1)", "start_char": 0, "end_char": 14}
        ]
    }

    res = verify_citations(claims_payload)
    assert res.total_citations >= 1
    c = res.citation_results[0]
    assert "ANS_MULTI_ASSOC_C001" in c.claim_ids
    assert len(c.existence.matched_passage_ids) >= 1


def test_matched_passage_ids_preserved_for_downstream():
    """Verify that matched passage IDs are preserved for the downstream Evidence Verifier."""
    res = verify_citations("Section 188(1) of the Companies Act, 2013 governs related party transactions.")
    c = res.citation_results[0]
    assert len(c.existence.matched_passage_ids) >= 1
    assert any("188" in pid for pid in c.existence.matched_passage_ids)
