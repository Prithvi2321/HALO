"""
HALO Evidence Verifier: Token-Boundary Polarity & Negation Checker
==================================================================
Protocol: v1.0-FROZEN
Audits explicit polarity flips between evidence premise and claim hypothesis.
Uses token/word-boundary matching and legal antonym pairs (User Correction #5).
Specifically excludes false-negation tokens like 'notwithstanding' and 'notification'.
"""

from typing import List, Tuple, Set, Optional
import re

from halo.evidence_verifier.schemas import (
    CheckStatus,
    NegationCheckResult,
)


class NegationChecker:
    """Audits explicit polarity consistency using word-boundary matching and legal antonyms."""

    # Words that contain 'not' or 'no' but are NOT semantic negators in legal context
    FALSE_NEGATORS = {
        "notwithstanding",
        "notification",
        "notifications",
        "notice",
        "notices",
        "noted",
        "notable",
        "notably",
        "notary",
        "nominal",
        "norm",
        "normal",
    }

    # Core explicit negator tokens with strict word boundaries
    EXPLICIT_NEGATORS = [
        r"\bnot\b",
        r"\bno\b",
        r"\bneither\b",
        r"\bnor\b",
        r"\bnever\b",
        r"\bwithout\b",
        r"\bnone\b",
    ]

    # Legal affirmative vs negative antonym pairs
    ANTONYM_PAIRS: List[Tuple[str, str]] = [
        (r"\bliable\b", r"\b(?:not\s+liable|non-liable|no\s+liability)\b"),
        (r"\bexempt\b", r"\b(?:not\s+exempt|non-exempt|no\s+exemption)\b"),
        (r"\bpermitted\b", r"\b(?:prohibited|forbidden|barred|not\s+permitted)\b"),
        (r"\bvalid\b", r"\b(?:void|invalid|unenforceable|not\s+valid)\b"),
        (r"\bapplicable\b", r"\b(?:inapplicable|not\s+applicable)\b"),
        (r"\brequired\b", r"\b(?:not\s+required|exempt\s+from\s+requirement)\b"),
        (r"\bguilty\b", r"\b(?:not\s+guilty|innocent)\b"),
        (r"\bshall\s+disclose\b", r"\bshall\s+not\s+disclose\b"),
        (r"\bshall\s+apply\b", r"\bshall\s+not\s+apply\b"),
        (r"\bmay\s+apply\b", r"\bmay\s+not\s+apply\b"),
        (r"\bnothing\s+(?:in\s+this\s+[^,\s]+\s+)?shall\s+apply\b", r"\b(?:attract|penal\s+fines|penalty)\b"),
        (r"\bexempt\b", r"\b(?:attract|penal\s+fines|penalty|punishable)\b"),
    ]

    def __init__(self):
        self._neg_regexes = [re.compile(p, re.IGNORECASE) for p in self.EXPLICIT_NEGATORS]
        self._compiled_antonyms = [
            (re.compile(aff, re.IGNORECASE), re.compile(neg, re.IGNORECASE))
            for aff, neg in self.ANTONYM_PAIRS
        ]

    def _has_explicit_negation(self, text: str) -> bool:
        """Detects presence of true grammatical negators while filtering false positives."""
        tokens = set(re.findall(r"\b[a-zA-Z]+\b", text.lower()))
        filtered_tokens = tokens - self.FALSE_NEGATORS

        for reg in self._neg_regexes:
            m = reg.search(text)
            if m:
                # Ensure the matched word is not one of the false negators
                matched_word = m.group(0).lower()
                if matched_word in filtered_tokens:
                    return True
        return False

    def check(self, claim_text: str, evidence_text: str) -> NegationCheckResult:
        """Audits polarity consistency between evidence premise and claim hypothesis."""
        claim_clean = claim_text.strip()
        ev_clean = evidence_text.strip()

        # 1. Check legal antonym pairs
        for aff_pat, neg_pat in self._compiled_antonyms:
            # Case A: Evidence has affirmative, Claim has negative
            if aff_pat.search(ev_clean) and neg_pat.search(claim_clean):
                return NegationCheckResult(
                    status=CheckStatus.MISMATCH.value,
                    claim_polarity="NEGATIVE",
                    evidence_polarity="AFFIRMATIVE",
                    details=f"Polarity mismatch: Evidence asserts affirmative proposition ({aff_pat.pattern}), but claim asserts negative proposition ({neg_pat.pattern}).",
                )
            # Case B: Evidence has negative, Claim has affirmative
            if neg_pat.search(ev_clean) and aff_pat.search(claim_clean):
                return NegationCheckResult(
                    status=CheckStatus.MISMATCH.value,
                    claim_polarity="AFFIRMATIVE",
                    evidence_polarity="NEGATIVE",
                    details=f"Polarity mismatch: Evidence asserts negative proposition ({neg_pat.pattern}), but claim asserts affirmative proposition ({aff_pat.pattern}).",
                )

        # 2. Check explicit grammatical negators in predicate context
        claim_neg = self._has_explicit_negation(claim_clean)
        ev_neg = self._has_explicit_negation(ev_clean)

        # Specifically look for explicit polarity flip on common legal verbs
        # e.g. "shall disclose" vs "shall not disclose"
        # Exclude threshold bounds ("shall not be less than", "shall not exceed")
        is_threshold_bound = bool(
            re.search(r"shall\s+not\s+(?:be\s+less\s+than|exceed|be\s+more\s+than)", ev_clean, re.IGNORECASE)
            or re.search(r"\bnot\s+less\s+than\b", claim_clean, re.IGNORECASE)
        )
        if not is_threshold_bound:
            if ("shall not" in ev_clean.lower() and "shall" in claim_clean.lower() and "shall not" not in claim_clean.lower()):
                return NegationCheckResult(
                    status=CheckStatus.MISMATCH.value,
                    claim_polarity="AFFIRMATIVE",
                    evidence_polarity="NEGATIVE",
                    details="Polarity flip: Evidence specifies 'shall not' prohibition, but claim asserts affirmative obligation 'shall'.",
                )

            if ("shall not" in claim_clean.lower() and "shall" in ev_clean.lower() and "shall not" not in ev_clean.lower()):
                return NegationCheckResult(
                    status=CheckStatus.MISMATCH.value,
                    claim_polarity="NEGATIVE",
                    evidence_polarity="AFFIRMATIVE",
                    details="Polarity flip: Claim asserts 'shall not' prohibition, but evidence specifies affirmative obligation 'shall'.",
                )

        if claim_neg == ev_neg:
            return NegationCheckResult(
                status=CheckStatus.MATCH.value,
                claim_polarity="NEGATIVE" if claim_neg else "AFFIRMATIVE",
                evidence_polarity="NEGATIVE" if ev_neg else "AFFIRMATIVE",
                details="Polarity alignment: Both evidence and claim share consistent polarity.",
            )

        return NegationCheckResult(
            status=CheckStatus.NOT_APPLICABLE.value,
            claim_polarity="NEGATIVE" if claim_neg else "AFFIRMATIVE",
            evidence_polarity="NEGATIVE" if ev_neg else "AFFIRMATIVE",
            details="No high-risk direct polarity contradiction detected.",
        )
