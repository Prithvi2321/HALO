"""
HALO Claim Extractor: Span Aligner & Integrity Auditor
======================================================
Protocol: v1.0-FROZEN
Verifies that extracted character spans match the source answer text 100% byte-for-byte.
Enforces Gate C7 (Span Integrity) across all extracted propositions.
"""

from typing import List
from halo.claim_extractor.schemas import ExtractedClaim, SourceSpan
from halo.claim_extractor.exceptions import SpanAlignmentError


class SpanAligner:
    """Enforces byte-for-byte character span integrity against the original answer text."""

    def verify_span(self, full_text: str, span: SourceSpan) -> bool:
        """
        Verifies that full_text[span.start_char:span.end_char] == span.source_text.
        Raises SpanAlignmentError if mismatched.
        """
        st = span.start_char
        en = span.end_char

        if st < 0 or en < 0 or st >= en or en > len(full_text):
            raise SpanAlignmentError(
                f"Span offsets [{st}:{en}] out of bounds for text of length {len(full_text)}.",
                {"start_char": st, "end_char": en, "text_length": len(full_text)}
            )

        actual_slice = full_text[st:en]
        if actual_slice != span.source_text:
            raise SpanAlignmentError(
                f"Span alignment mismatch: expected '{span.source_text[:30]}...', found '{actual_slice[:30]}...'.",
                {
                    "start_char": st,
                    "end_char": en,
                    "expected": span.source_text,
                    "actual": actual_slice
                }
            )

        return True

    def verify_all_claims(self, full_text: str, claims: List[ExtractedClaim]) -> bool:
        """Audits span integrity across all extracted claims."""
        for c in claims:
            self.verify_span(full_text, c.source_span)
        return True
