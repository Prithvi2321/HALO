"""
HALO Citation Verifier: Subsystem Validator & Gate CV9 Auditor
==============================================================
Protocol: v1.0-FROZEN
Enforces input safety limits, untrusted string sanitization, and the strict
'No Evidence Support Decision Leakage' constraint (Gate CV9).
"""

from typing import List, Dict, Any
from halo.citation_verifier.schemas import CitationVerificationRecord
from halo.citation_verifier.config import CitationVerifierConfig
from halo.citation_verifier.exceptions import (
    InvalidInputError,
    MalformedCitationError,
    EvidenceLeakageViolationError
)


class SubsystemValidator:
    """Validates inputs and audits outputs for the Citation Verifier subsystem."""

    FORBIDDEN_TRUTH_LABELS = {
        "SUPPORTED",
        "CONTRADICTED",
        "HALLUCINATED",
        "CORRECT",
        "INCORRECT",
        "PARTIALLY_SUPPORTED"
    }

    def validate_citation_input(self, citation_text: Any, config: CitationVerifierConfig) -> str:
        """Validates raw citation text against length and injection limits."""
        if citation_text is None:
            raise InvalidInputError("Citation text cannot be None.")

        if not isinstance(citation_text, str):
            citation_text = str(citation_text)

        cleaned = citation_text.strip()
        if not cleaned:
            raise MalformedCitationError("Citation text cannot be empty or whitespace only.")

        if len(cleaned) > config.max_citation_text_length:
            raise MalformedCitationError(
                f"Citation text length ({len(cleaned)}) exceeds max limit ({config.max_citation_text_length}).",
                {"length": len(cleaned), "max_limit": config.max_citation_text_length}
            )

        # Check for control characters
        if any(ord(char) < 32 and char not in "\t\n\r" for char in cleaned):
            raise MalformedCitationError("Citation text contains forbidden control characters.")

        return cleaned

    def audit_no_evidence_leakage(self, records: List[CitationVerificationRecord]):
        """
        Gate CV9: Strictly enforces that Citation Verifier NEVER evaluates whether
        a citation supports or contradicts the claim proposition.
        """
        for rec in records:
            d_str = str(rec.to_dict()).upper()
            for forbidden in self.FORBIDDEN_TRUTH_LABELS:
                # Ensure no field or status contains forbidden truth evaluation strings
                if f"'{forbidden}'" in d_str or f'"{forbidden}"' in d_str:
                    raise EvidenceLeakageViolationError(
                        f"Gate CV9 Violation: Citation Verifier emitted evidence support status '{forbidden}' in citation {rec.citation_id}.",
                        {"citation_id": rec.citation_id, "forbidden_status": forbidden}
                    )
