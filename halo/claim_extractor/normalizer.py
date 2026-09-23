"""
HALO Claim Extractor: Claim Normalizer & Key Generator
======================================================
Protocol: v1.0-FROZEN
Generates auxiliary canonical grouping keys (normalized_claim_key) for deduplication
and grouping audits WITHOUT altering the verbatim claim_text.
"""

import re
import hashlib


class ClaimNormalizer:
    """Generates auxiliary normalized representations without modifying the original claim text."""

    def compute_normalized_key(self, claim_text: str, claim_type: str) -> str:
        """
        Creates a deterministic normalized key representing the core semantic predicate.
        Formula: SHA-256 over lowercased, whitespace-collapsed, punctuation-stripped text.
        """
        # Lowercase
        normalized = claim_text.lower()

        # Remove punctuation except numerals and percentages
        normalized = re.sub(r"[^\w\s%₹]", " ", normalized)

        # Collapse whitespace
        tokens = normalized.split()

        # Remove common stop words for semantic grouping
        stop_words = {"the", "a", "an", "is", "are", "of", "in", "to", "for", "by", "that", "this", "under"}
        content_tokens = [t for t in tokens if t not in stop_words]

        joined = " ".join(content_tokens)
        payload = f"{claim_type}:{joined}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
