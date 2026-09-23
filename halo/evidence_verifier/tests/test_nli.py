"""
Unit Tests for Gate EV3: NLI Model Integrity & Probabilities
============================================================
Protocol: v1.0-FROZEN
Tests model loading, evaluation mode, gradient freezing, runtime id2label mapping,
and probability normalization.
"""

import pytest
from halo.evidence_verifier.nli_engine import NLIEngine
from halo.evidence_verifier.config import EvidenceVerifierConfig


@pytest.fixture(scope="module")
def engine():
    cfg = EvidenceVerifierConfig()
    return NLIEngine.get_instance(cfg)


def test_model_label_mapping_integrity(engine):
    """Gate EV3: Runtime verification of id2label mapping."""
    raw_id2label = getattr(engine.model.config, "id2label", {})
    normalized = {int(k): str(v).lower() for k, v in raw_id2label.items()}
    assert normalized[0] == "contradiction"
    assert normalized[1] == "entailment"
    assert normalized[2] == "neutral"


def test_model_evaluation_mode(engine):
    """Gate EV3: Model must be in eval mode with gradients disabled."""
    assert not engine.model.training
    for param in engine.model.parameters():
        assert not param.requires_grad


def test_probability_normalization_and_ranges(engine):
    """Gate EV3: Softmax output probabilities must sum to 1.0 and be within [0, 1]."""
    premise = "Every company shall have a minimum number of three directors in the case of a public company."
    hypothesis = "Public companies must have at least three directors."

    result = engine.predict(premise, hypothesis)
    probs = result.probabilities

    assert 0.0 <= probs.contradiction <= 1.0
    assert 0.0 <= probs.entailment <= 1.0
    assert 0.0 <= probs.neutral <= 1.0

    total = probs.contradiction + probs.entailment + probs.neutral
    assert pytest.approx(total, abs=1e-4) == 1.0


def test_model_provenance_recorded(engine):
    """Gate EV15: Provenance must record model name, revision, torch, and transformers."""
    prov = engine.model_provenance
    assert prov is not None
    assert prov.name == "cross-encoder/nli-deberta-v3-base"
    assert prov.model_hash is not None
    assert len(prov.model_hash) == 64
    assert prov.torch_version is not None
    assert prov.transformers_version is not None
