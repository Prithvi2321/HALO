"""
Unit Tests for Gate EV4: Critical NLI Direction (Premise = Evidence, Hypothesis = Claim)
========================================================================================
Protocol: v1.0-FROZEN
Verifies by actual argument inspection that:
PREMISE    = authoritative legal evidence passage
HYPOTHESIS = generated atomic claim
"""

import pytest
from halo.evidence_verifier.nli_engine import NLIEngine
from halo.evidence_verifier.config import EvidenceVerifierConfig


def test_nli_direction_argument_inspection():
    """Gate EV4: Dedicated test inspecting actual arguments passed to tokenizer/model."""
    cfg = EvidenceVerifierConfig()
    engine = NLIEngine.get_instance(cfg)

    evidence_text = "The Board of Directors shall consist of individuals and shall have a minimum of three directors in a public company."
    claim_text = "Public companies must have at least three directors on their board."

    captured_args = []
    original_tokenizer = engine.tokenizer

    class TokenizerWrapper:
        def __init__(self, tok):
            self._tok = tok

        def __call__(self, *args, **kwargs):
            captured_args.append({"args": args, "kwargs": kwargs})
            return self._tok(*args, **kwargs)

        def __getattr__(self, name):
            return getattr(self._tok, name)

    try:
        engine.tokenizer = TokenizerWrapper(original_tokenizer)

        result = engine.predict(
            premise_evidence=evidence_text,
            hypothesis_claim=claim_text,
            claim_id="CLM_DIR_TEST",
            passage_id="PAS_DIR_TEST",
        )

        assert len(captured_args) > 0
        first_call = captured_args[0]
        args = first_call["args"]

        # Tokenizer is called with (premise, hypothesis)
        # Arg 0 must be the evidence premise (or chunk thereof)
        assert len(args) >= 2
        premise_arg = args[0]
        hypothesis_arg = args[1]

        assert evidence_text.startswith(premise_arg) or premise_arg in evidence_text, (
            f"Premise argument does not match evidence passage! Got: {premise_arg[:50]}"
        )
        assert hypothesis_arg == claim_text or hypothesis_arg in claim_text, (
            f"Hypothesis argument does not match claim text! Got: {hypothesis_arg}"
        )

        # Invert check: Ensure claim is NOT premise and evidence is NOT hypothesis
        assert hypothesis_arg != evidence_text
        assert premise_arg != claim_text

    finally:
        engine.tokenizer = original_tokenizer
