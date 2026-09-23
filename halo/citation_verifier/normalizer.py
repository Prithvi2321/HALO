"""
HALO Citation Verifier: Citation Normalizer
===========================================
Protocol: v1.0-FROZEN
Provides transparent normalization of statutory and judicial citations,
generating canonical lookup keys while strictly preserving original raw citation text.
"""

import re
from typing import Dict, Any


class CitationNormalizer:
    """Normalizes statutory and judicial citations for deterministic corpus lookups."""

    @staticmethod
    def normalize_text(text: str) -> str:
        """Standardizes casing, punctuation, and whitespace."""
        if not text:
            return ""
        # Remove unicode non-breaking spaces and clean whitespace
        cleaned = text.replace("\u00a0", " ").strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned

    @staticmethod
    def canonical_act_key(act_name: str) -> str:
        """Normalizes Act titles into canonical lookup keys."""
        if not act_name:
            return ""
        cleaned = act_name.upper().strip()
        cleaned = re.sub(r"^THE\s+", "", cleaned)
        cleaned = re.sub(r"[,\.]+", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned

    @staticmethod
    def canonical_reporter_key(reporter_str: str) -> str:
        """
        Normalizes reporter strings for exact canonical indexing.
        E.g. '[2016] 11 S.C.R. 149' -> '2016_11_SCR_149'
        E.g. '(2018) 1 SCC 353' -> '2018_1_SCC_353'
        E.g. '2016 INSC 1150' -> '2016_INSC_1150'
        """
        if not reporter_str:
            return ""
        cleaned = reporter_str.upper().strip()
        # Remove brackets, parentheses, dots
        cleaned = re.sub(r"[\[\]\(\)\.]+", "", cleaned)
        cleaned = re.sub(r"\s+", "_", cleaned)
        return cleaned

    @staticmethod
    def canonical_case_title_key(title: str) -> str:
        """
        Normalizes case names for fuzzy and normalized title lookups.
        E.g. 'Bhushan Power & Steel Ltd. v. Mr. S.L. Seal' -> 'BHUSHAN POWER STEEL V MR SL SEAL'
        """
        if not title:
            return ""
        cleaned = title.upper().strip()
        cleaned = cleaned.replace("&", "AND")
        cleaned = re.sub(r"\bPVT\.?\b", "PRIVATE", cleaned)
        cleaned = re.sub(r"\bLTD\.?\b", "LIMITED", cleaned)
        cleaned = re.sub(r"\bVS\.?\b", "V", cleaned)
        cleaned = re.sub(r"\bVERSUS\b", "V", cleaned)
        cleaned = re.sub(r"[^A-Z0-9\s]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    @staticmethod
    def normalize_section_number(sec: str) -> str:
        """Normalizes section strings: '135', '135(1)', 'Sec. 135' -> '135'."""
        if not sec:
            return ""
        m = re.search(r"(\d+[A-Za-z]?)", sec)
        return m.group(1).upper() if m else sec.strip().upper()
