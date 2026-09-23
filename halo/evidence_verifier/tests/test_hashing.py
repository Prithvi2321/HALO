"""
Unit Tests for Gate EV15: Cryptographic Provenance Hashing
==========================================================
Protocol: v1.0-FROZEN
Tests SHA-256 canonical hashing across input, config, and output structures.
Verifies resistance to dictionary key order perturbations.
"""

import pytest
import json
from halo.evidence_verifier.verifier import EvidenceVerifier
from halo.evidence_verifier.config import EvidenceVerifierConfig


@pytest.fixture(scope="module")
def verifier():
    return EvidenceVerifier()


def test_hash_lengths_and_determinism(verifier):
    """Gate EV15: Input, config, and output hashes must be valid 64-char hex strings."""
    verdict = verifier.verify_claim(
        claim_input={"claim_id": "CLM_HASH_01", "claim_text": "The company shall maintain ₹500 crore reserve."},
        direct_evidence_text="The company shall maintain ₹500 crore reserve.",
        direct_passage_id="PAS_HASH_01",
    )

    assert len(verdict.input_hash) == 64
    assert len(verdict.config_hash) == 64
    assert len(verdict.output_hash) == 64

    # Re-run identical input: hashes must be identical
    verdict2 = verifier.verify_claim(
        claim_input={"claim_id": "CLM_HASH_01", "claim_text": "The company shall maintain ₹500 crore reserve."},
        direct_evidence_text="The company shall maintain ₹500 crore reserve.",
        direct_passage_id="PAS_HASH_01",
    )

    assert verdict.input_hash == verdict2.input_hash
    assert verdict.config_hash == verdict2.config_hash
    assert verdict.output_hash == verdict2.output_hash


def test_canonical_json_order_invariance(verifier):
    """JSON key ordering must not change canonical output hash."""
    verdict = verifier.verify_claim(
        claim_input={"claim_id": "CLM_ORDER_01", "claim_text": "Public companies require three directors."},
        direct_evidence_text="Public companies require three directors.",
        direct_passage_id="PAS_ORDER_01",
    )

    d1 = verdict.to_dict()
    # Scramble dictionary ordering
    keys_reversed = list(reversed(list(d1.keys())))
    scrambled = {k: d1[k] for k in keys_reversed}

    h1 = verdict.compute_output_hash()
    scrambled["output_hash"] = ""
    canonical_scrambled = json.dumps(scrambled, sort_keys=True, ensure_ascii=False)
    import hashlib
    h2 = hashlib.sha256(canonical_scrambled.encode("utf-8")).hexdigest()

    assert h1 == h2
