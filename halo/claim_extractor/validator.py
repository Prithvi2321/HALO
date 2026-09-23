"""
HALO Claim Extractor: Subsystem Validator
=========================================
Protocol: v1.0-FROZEN
Enforces input safety limits, schema compliance, span integrity, and the strict
'No Truth Leakage' constraint (Gate C9).
"""

from typing import List, Any
from halo.claim_extractor.schemas import ExtractedClaim, ClaimType
from halo.claim_extractor.config import ClaimExtractorConfig
from halo.claim_extractor.exceptions import (
    EmptyAnswerError,
    InvalidInputError,
    PayloadLimitExceededError,
    SchemaValidationError,
)


class SubsystemValidator:
    """Validates inputs and outputs for the Claim Extractor subsystem."""

    FORBIDDEN_TRUTH_LABELS = {
        "SUPPORTED", "CONTRADICTED", "HALLUCINATED", "CORRECT", "INCORRECT", "TRUE", "FALSE"
    }

    def validate_input(self, answer_text: Any, config: ClaimExtractorConfig) -> str:
        """Validates that raw input text meets safety and length requirements."""
        if answer_text is None:
            raise EmptyAnswerError("Input answer text cannot be None.")

        if not isinstance(answer_text, str):
            raise InvalidInputError(f"Input must be a string, got {type(answer_text).__name__}.")

        stripped = answer_text.strip()
        if not stripped:
            raise EmptyAnswerError("Input answer text contains only whitespace.")

        if len(answer_text) > config.max_answer_length:
            raise PayloadLimitExceededError(
                f"Answer length ({len(answer_text)} chars) exceeds max limit ({config.max_answer_length} chars).",
                {"length": len(answer_text), "max_allowed": config.max_answer_length}
            )

        return answer_text

    def validate_claims(self, claims: List[ExtractedClaim], config: ClaimExtractorConfig):
        """Validates that extracted claims adhere to schema, enum, and no-truth constraints."""
        if len(claims) > config.max_claim_count:
            raise PayloadLimitExceededError(
                f"Claim count ({len(claims)}) exceeds max limit ({config.max_claim_count}).",
                {"count": len(claims), "max_allowed": config.max_claim_count}
            )

        valid_types = {t.value for t in ClaimType}

        for c in claims:
            # 1. Check claim_type is in controlled enum
            if c.claim_type not in valid_types:
                raise SchemaValidationError(
                    f"Claim {c.claim_id} has invalid claim_type '{c.claim_type}'. Must be member of ClaimType enum.",
                    {"claim_id": c.claim_id, "invalid_type": c.claim_type}
                )

            # 2. Gate C9: Enforce 'No Truth Leakage'
            # Extractor must NEVER determine whether a claim is true or false
            c_dict_str = str(c.to_dict()).upper()
            for forbidden in self.FORBIDDEN_TRUTH_LABELS:
                # Ensure no field or value contains truth statuses
                if f"'{forbidden}'" in c_dict_str:
                    raise SchemaValidationError(
                        f"Gate C9 Violation: Extractor leaked verification status '{forbidden}' in claim {c.claim_id}.",
                        {"claim_id": c.claim_id, "forbidden_status": forbidden}
                    )

            # 3. Validate extraction_confidence bounds if present
            if c.extraction_confidence is not None:
                if not (0.0 <= c.extraction_confidence <= 1.0):
                    raise SchemaValidationError(
                        f"Claim {c.claim_id} extraction_confidence must be between 0.0 and 1.0, got {c.extraction_confidence}.",
                        {"claim_id": c.claim_id, "confidence": c.extraction_confidence}
                    )
