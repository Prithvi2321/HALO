"""
HALO Citation Verifier: End-to-End Pipeline & Metric Tests (Gates CV12-CV14)
============================================================================
Protocol: v1.0-FROZEN
Tests integration between Claim Extractor output and Citation Verifier.
Validates False Existence Rate (FER == 0.0%) and measures lookup latency.
"""

from halo.citation_verifier.verifier import CitationVerifier
from halo.citation_verifier.schemas import ExistenceStatus


def test_end_to_end_from_claim_extractor_output():
    """Verify integration consuming structured payload from claim extractor."""
    verifier = CitationVerifier()
    extractor_payload = {
        "answer_id": "ANS_E2E_001",
        "claims": [
            {
                "claim_id": "ANS_E2E_001_C001",
                "claim_text": "Section 135(1) of the Companies Act, 2013 mandates a CSR Committee.",
                "source_span": {"start_char": 0, "end_char": 68},
                "citation_refs": [
                    {"citation_text": "Section 135(1) of the Companies Act, 2013", "start_char": 0, "end_char": 42}
                ]
            },
            {
                "claim_id": "ANS_E2E_001_C002",
                "claim_text": "The Board must ensure compliance under Section 134(8).",
                "source_span": {"start_char": 69, "end_char": 123},
                "citation_refs": [
                    {"citation_text": "Section 134(8)", "start_char": 109, "end_char": 122}
                ]
            }
        ]
    }

    result = verifier.verify_answer(extractor_payload)

    assert result.success is True
    assert result.total_citations == 2
    assert len(result.input_hash) == 64
    assert len(result.output_hash) == 64

    # Both citations exist in D1
    for rec in result.citation_results:
        assert rec.existence.status == ExistenceStatus.EXISTS.value
        assert len(rec.claim_ids) >= 1
        assert len(rec.existence.matched_passage_ids) >= 1

    # Measure latency
    assert result.metrics["processing_time_ms"] >= 0.0


def test_false_existence_rate_is_zero():
    """
    Primary Safety Metric: False Existence Rate (FER)
    Ensure that NO non-authoritative or fabricated citation is classified as EXISTS.
    FER = FP / (FP + TN) == 0.0%
    """
    verifier = CitationVerifier()
    fabricated_test_cases = [
        "Under Section 12 of the Indian Corporate Metaverse and Blockchain Act, 2024, token issuance requires board consent.",
        "Under Section 5 of the Artificial Intelligence Commercial Code, 2025, neural weights must be registered.",
        "Section 480 of the Companies Act, 2013 sets forth registration of decentralized entities.",
        "Section 500 of the Companies Act, 2013 governs foreign sovereign mergers.",
        "In Zenith Corporate Robotics v. UOI, 2025 INSC 888, the court ruled on autonomous board quorum."
    ]

    fp = 0
    tn = 0
    for text in fabricated_test_cases:
        res = verifier.verify_answer(text)
        for rec in res.citation_results:
            if rec.existence.status == ExistenceStatus.EXISTS.value:
                fp += 1
            else:
                tn += 1

    total_negatives = fp + tn
    fer = (fp / total_negatives) if total_negatives > 0 else 0.0

    assert fp == 0, f"Violation: Fabricated citations classified as EXISTS: {fp}"
    assert fer == 0.0, f"False Existence Rate must be 0.0%, got {fer:.2%}"
