"""
HALO Evidence Verifier: Input Validator & Gate EV12/EV13 Auditor
================================================================
Protocol: v1.0-FROZEN
Enforces input safety limits, untrusted string sanitization, probability validation,
and strict truth-label leakage prevention.
"""

from typing import Dict, Any, Union
import math

from halo.evidence_verifier.config import EvidenceVerifierConfig
from halo.evidence_verifier.schemas import NLIProbabilities
from halo.evidence_verifier.exceptions import (
    InvalidInputError,
    MalformedEvidenceError,
    TruthLabelLeakageError,
)


class SubsystemValidator:
    """Validates inputs and audits data structures for the Evidence Verifier subsystem."""

    FORBIDDEN_TRUTH_KEYS = {
        "ground_truth_status",
        "expected_status",
        "expected_label",
        "gold_support",
        "gold_contradiction",
        "expected_behavior",
        "test_case_label",
        "gold_label",
    }

    def validate_claim_input(self, claim_text: Any, config: EvidenceVerifierConfig) -> str:
        """Validates raw claim text against length and injection limits."""
        if claim_text is None:
            raise InvalidInputError("Claim text cannot be None.")

        if not isinstance(claim_text, str):
            claim_text = str(claim_text)

        cleaned = claim_text.strip()
        if not cleaned:
            raise InvalidInputError("Claim text cannot be empty or whitespace only.")

        if len(cleaned) > config.max_claim_text_length:
            raise InvalidInputError(
                f"Claim text length ({len(cleaned)}) exceeds max limit ({config.max_claim_text_length}).",
                {"length": len(cleaned), "max_limit": config.max_claim_text_length},
            )

        # Check for control characters (excluding standard whitespace)
        if any(ord(char) < 32 and char not in "\t\n\r" for char in cleaned):
            raise InvalidInputError("Claim text contains forbidden control characters.")

        return cleaned

    def validate_evidence_input(self, evidence_text: Any, config: EvidenceVerifierConfig) -> str:
        """Validates raw evidence text against length and injection limits."""
        if evidence_text is None:
            raise MalformedEvidenceError("Evidence text cannot be None.")

        if not isinstance(evidence_text, str):
            evidence_text = str(evidence_text)

        cleaned = evidence_text.strip()
        if not cleaned:
            raise MalformedEvidenceError("Evidence text cannot be empty or whitespace only.")

        if len(cleaned) > config.max_evidence_text_length:
            raise MalformedEvidenceError(
                f"Evidence text length ({len(cleaned)}) exceeds max limit ({config.max_evidence_text_length}).",
                {"length": len(cleaned), "max_limit": config.max_evidence_text_length},
            )

        return cleaned

    def audit_no_truth_leakage(self, data: Dict[str, Any]):
        """
        Gate EV12 / Leakage Prevention:
        Strictly enforces that Evidence Verifier NEVER consumes ground-truth labels,
        expected outcomes, or benchmark annotations during inference.
        """
        if not isinstance(data, dict):
            return

        for key in data.keys():
            k_lower = key.lower()
            if k_lower in self.FORBIDDEN_TRUTH_KEYS:
                raise TruthLabelLeakageError(
                    f"Forbidden truth-bearing field '{key}' detected in inference input. "
                    "Evidence Verifier cannot consume benchmark truth labels.",
                    {"forbidden_key": key, "value": data[key]},
                )

        # Check nested structures
        for val in data.values():
            if isinstance(val, dict):
                self.audit_no_truth_leakage(val)
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        self.audit_no_truth_leakage(item)

    def validate_probabilities(self, probs: Union[NLIProbabilities, Dict[str, float]]) -> bool:
        """Validates probability ranges: 0 <= p <= 1 and sum(p) approx 1."""
        if isinstance(probs, NLIProbabilities):
            c = probs.contradiction
            e = probs.entailment
            n = probs.neutral
        elif isinstance(probs, dict):
            c = float(probs.get("contradiction", 0.0))
            e = float(probs.get("entailment", 0.0))
            n = float(probs.get("neutral", 0.0))
        else:
            return False

        for p in (c, e, n):
            if math.isnan(p) or math.isinf(p) or p < 0.0 or p > 1.0:
                return False

        total = c + e + n
        if abs(total - 1.0) > 0.01:
            return False

        return True
