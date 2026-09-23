"""
Unit Tests for Gate EV1: Schema Validity & Data Contracts
=========================================================
Protocol: v1.0-FROZEN
Tests strict typing, controlled enums, serialization, and roundtrip deserialization.
"""

import pytest
import json
from halo.evidence_verifier.schemas import (
    EvidenceVerdictStatus,
    CheckStatus,
    NumericalMismatchType,
    ModalityType,
    ClaimAtomicity,
    NLILabel,
    NLIProbabilities,
    NLIPairResult,
    NumericalCheckResult,
    ModalityCheckResult,
    NegationCheckResult,
    EvidenceItem,
    AggregationSummary,
    ModelProvenance,
    EvidenceVerdict,
    EvidenceVerificationResult,
)


def test_verdict_status_enum_completeness():
    expected_statuses = {"SUPPORTED", "CONTRADICTED", "PARTIALLY_SUPPORTED", "NEUTRAL", "CONFLICTED", "UNRESOLVED"}
    actual_statuses = {s.value for s in EvidenceVerdictStatus}
    assert actual_statuses == expected_statuses
    assert EvidenceVerdictStatus.from_str("supported") == EvidenceVerdictStatus.SUPPORTED
    assert EvidenceVerdictStatus.from_str("invalid") == EvidenceVerdictStatus.UNRESOLVED


def test_check_status_enum():
    assert CheckStatus.MATCH.value == "MATCH"
    assert CheckStatus.MISMATCH.value == "MISMATCH"
    assert CheckStatus.NOT_APPLICABLE.value == "NOT_APPLICABLE"
    assert CheckStatus.UNRESOLVED.value == "UNRESOLVED"
    assert CheckStatus.from_str("mismatch") == CheckStatus.MISMATCH
    assert CheckStatus.from_str("unknown") == CheckStatus.NOT_APPLICABLE


def test_nli_probabilities_serialization():
    probs = NLIProbabilities(contradiction=0.02, entailment=0.94, neutral=0.04)
    d = probs.to_dict()
    assert d == {"contradiction": 0.02, "entailment": 0.94, "neutral": 0.04}
    assert probs.entailment_probability == 0.94
    assert probs.contradiction_probability == 0.02
    assert probs.neutral_probability == 0.04

    recovered = NLIProbabilities.from_dict(d)
    assert recovered.contradiction == 0.02
    assert recovered.entailment == 0.94
    assert recovered.neutral == 0.04


def test_evidence_item_roundtrip():
    item = EvidenceItem(
        passage_id="PAS_001",
        source="Companies Act, 2013",
        dataset="D1",
        authority_id="ACT_COMPANIES_2013_SEC_135",
        section_id="135",
        text="Sample statutory text.",
        text_hash="abc123hash",
        nli=NLIProbabilities(0.01, 0.98, 0.01),
        numerical_check=NumericalCheckResult(status=CheckStatus.MATCH.value),
        modality_check=ModalityCheckResult(status=CheckStatus.MATCH.value),
        negation_check=NegationCheckResult(status=CheckStatus.MATCH.value),
        local_status=EvidenceVerdictStatus.SUPPORTED.value,
    )
    d = item.to_dict()
    assert d["passage_id"] == "PAS_001"
    assert d["local_status"] == "SUPPORTED"
    assert d["nli"]["entailment"] == 0.98

    restored = EvidenceItem.from_dict(d)
    assert restored.passage_id == item.passage_id
    assert restored.nli.entailment == item.nli.entailment
    assert restored.numerical_check.status == CheckStatus.MATCH.value


def test_evidence_verdict_roundtrip_and_hashing():
    verdict = EvidenceVerdict(
        claim_id="CLM_TEST_001",
        claim_text="The company must file returns within 30 days.",
        status=EvidenceVerdictStatus.SUPPORTED.value,
        evidence_items=[],
        best_evidence_id="PAS_001",
        best_evidence={"passage_id": "PAS_001"},
        nli=NLIProbabilities(0.02, 0.92, 0.06),
        numerical_check=NumericalCheckResult(status=CheckStatus.MATCH.value),
        modality_check=ModalityCheckResult(status=CheckStatus.MATCH.value),
        negation_check=NegationCheckResult(status=CheckStatus.MATCH.value),
        aggregation=AggregationSummary(support_count=1, conflict=False),
        claim_atomicity=ClaimAtomicity.ATOMIC.value,
        decision_reason="Authoritative evidence establishes support.",
        model=ModelProvenance(name="cross-encoder/nli-deberta-v3-base"),
        config_hash="cfg_hash_123",
        input_hash="inp_hash_123",
        output_hash="",
    )
    h1 = verdict.compute_output_hash()
    assert len(h1) == 64
    verdict.output_hash = h1

    d = verdict.to_dict()
    restored = EvidenceVerdict.from_dict(d)
    assert restored.claim_id == "CLM_TEST_001"
    assert restored.status == EvidenceVerdictStatus.SUPPORTED.value
    assert restored.output_hash == h1
    assert restored.compute_output_hash() == h1
