"""
HALO Claim Extractor: Claim Candidate Detector
==============================================
Protocol: v1.0-FROZEN
Distinguishes substantive proposition-bearing sentences from conversational boilerplate,
disclaimers, headings, and non-committal refusal responses.
"""

import re
from typing import Tuple


class ClaimCandidateDetector:
    """Detects whether a sentence constitutes an actionable, proposition-bearing legal claim candidate."""

    # Explicit refusal and non-answer indicators
    REFUSAL_PATS = [
        re.compile(r"^\s*I\s+(?:do\s+not|don't)\s+know\b", re.IGNORECASE),
        re.compile(r"^\s*I\s+(?:do\s+not|don't)\s+have\s+(?:sufficient|enough|any)?\b", re.IGNORECASE),
        re.compile(r"^\s*I\s+cannot\s+answer\b", re.IGNORECASE),
        re.compile(r"^\s*I\s+am\s+unable\s+to\b", re.IGNORECASE),
        re.compile(r"^\s*No\s+relevant\s+information\s+(?:was\s+found|is\s+available)\b", re.IGNORECASE),
        re.compile(r"^\s*The\s+provided\s+context\s+does\s+not\s+(?:contain|mention|specify)\b", re.IGNORECASE),
        re.compile(r"^\s*There\s+is\s+no\s+(?:mention|record|evidence)\s+of\b", re.IGNORECASE),
        re.compile(r"^\s*I\s+apologize,\s+but\b", re.IGNORECASE),
        re.compile(r"^\s*Not\s+applicable\b", re.IGNORECASE),
        re.compile(r"^\s*Insufficient\s+(?:evidence|information)\b", re.IGNORECASE),
    ]

    # Conversational meta-commentary and structural headings
    BOILERPLATE_PATS = [
        re.compile(r"^(?:Based\s+on|According\s+to)\s+the\s+(?:provided|authoritative|retrieved)\s+(?:legal\s+)?evidence(?:\s+provided)?:?$", re.IGNORECASE),
        re.compile(r"^(?:In\s+summary|To\s+summarize|Conclusion|Key\s+Takeaways|Relevant\s+Provisions|Analysis):?$", re.IGNORECASE),
        re.compile(r"^(?:Here\s+is\s+(?:the\s+)?(?:summary|breakdown|answer)):?$", re.IGNORECASE),
        re.compile(r"^(?:Please\s+note\s+that):?$", re.IGNORECASE),
    ]

    def is_claim_candidate(self, sentence_text: str) -> Tuple[bool, str]:
        """
        Evaluates whether sentence contains an actionable proposition.
        Returns (is_candidate, reason).
        """
        cleaned = sentence_text.strip()
        if not cleaned:
            return False, "EMPTY_TEXT"

        # Minimum word count check for meaningful legal assertion
        words = cleaned.split()
        if len(words) < 3:
            return False, "TOO_FEW_WORDS"

        # Check refusal patterns
        for pat in self.REFUSAL_PATS:
            if pat.search(cleaned):
                return False, "NON_ANSWER_OR_REFUSAL"

        # Check pure boilerplate headings
        for pat in self.BOILERPLATE_PATS:
            if pat.search(cleaned):
                return False, "BOILERPLATE_OR_HEADING"

        return True, "SUBSTANTIVE_CANDIDATE"
