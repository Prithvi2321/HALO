"""
HALO Claim Extractor: Citation Detector
=======================================
Protocol: v1.0-FROZEN
Detects statutory and judicial citation references within generated legal text,
recording exact character spans and citation types without verifying truth or validity.
"""

import re
from typing import List
from halo.claim_extractor.schemas import CitationRef


class LegalCitationDetector:
    """Detects statutory, judicial, and constitutional citations preserving character offsets."""

    # Statutory citation patterns (e.g. Section 135(1)(a) of the Companies Act, 2013)
    STATUTORY_PATS = [
        # Full Section with optional enactment
        re.compile(
            r"\b(?:Section|Sec\.|Sections|Secs\.)\s+"
            r"(\d+[A-Za-z]?(?:\s*\(\d+\))*(?:\s*\([a-z]\))*(?:\s*\([ivx]+\))*)"
            r"(?:\s+of\s+(?:the\s+)?([A-Za-z\s,]+(?:Act|Code),\s*\d{4}))?",
            re.IGNORECASE
        ),
        # Standalone Act references (e.g. Companies Act, 2013, Companies Act, 1956)
        re.compile(
            r"\b((?:The\s+)?(?:Companies|Insolvency\s+and\s+Bankruptcy|Limitation|Competition|Partnership|Arbitration\s+and\s+Conciliation)\s+Act,\s*\d{4})\b",
            re.IGNORECASE
        ),
        # IBC shorthand
        re.compile(
            r"\b(Insolvency\s+and\s+Bankruptcy\s+Code(?:,\s*2016)?|\bIBC\b)\b",
            re.IGNORECASE
        ),
        # Constitutional Articles
        re.compile(
            r"\b(Article\s+\d+[A-Za-z]?(?:\(\d+\))?)\b",
            re.IGNORECASE
        ),
    ]

    # Judicial reporter citation patterns (e.g. [2016] 11 S.C.R. 149, (2017) 10 SCC 1006, 2021 INSC 999)
    JUDICIAL_PATS = [
        # Supreme Court Reports (S.C.R.)
        re.compile(r"(\[\d{4}\]\s+\d+\s+S\.C\.R\.\s+\d+)", re.IGNORECASE),
        # Supreme Court Cases (SCC)
        re.compile(r"(\(\d{4}\)\s+\d+\s+SCC\s+\d+)", re.IGNORECASE),
        # Indian Supreme Court Neutral Citation (INSC)
        re.compile(r"(\d{4}\s+INSC\s+\d+)", re.IGNORECASE),
        # All India Reporter (AIR)
        re.compile(r"(\bAIR\s+\d{4}\s+SC\s+\d+)\b", re.IGNORECASE),
        # Case Titles with v. / vs.
        re.compile(
            r"\b([A-Z][A-Za-z0-9\s&.,'()-]+\s+(?:v\.|vs\.)\s+[A-Z][A-Za-z0-9\s&.,'()-]+?)(?=(?:,\s*\[\d{4}\]|,\s*\(\d{4}\)|,\s*\d{4}\s+INSC|,\s*AIR|\s+held|\s+ruled|\s+decided|;|\.|\n))",
            re.IGNORECASE
        ),
    ]

    def detect_citations(self, text: str) -> List[CitationRef]:
        """
        Scans text and returns all detected citations with exact character offsets.
        Guarantees text[cit.start_char:cit.end_char] == cit.citation_text.
        """
        if not text or not text.strip():
            return []

        citations: List[CitationRef] = []
        seen_spans = set()

        # 1. Statutory scans
        for pat in self.STATUTORY_PATS:
            for match in pat.finditer(text):
                full_text = match.group(0).strip()
                st = match.start(0)
                en = st + len(full_text)

                span_key = (st, en)
                if span_key in seen_spans:
                    continue
                seen_spans.add(span_key)

                norm_id = self._normalize_statutory_id(full_text)
                cit_type = "CONSTITUTIONAL" if "article" in full_text.lower() else "STATUTORY"

                citations.append(CitationRef(
                    citation_text=full_text,
                    start_char=st,
                    end_char=en,
                    citation_type=cit_type,
                    normalized_id=norm_id
                ))

        # 2. Judicial scans
        for pat in self.JUDICIAL_PATS:
            for match in pat.finditer(text):
                full_text = match.group(0).strip()
                st = match.start(0)
                en = st + len(full_text)

                span_key = (st, en)
                if span_key in seen_spans:
                    continue
                seen_spans.add(span_key)

                norm_id = self._normalize_judicial_id(full_text)

                citations.append(CitationRef(
                    citation_text=full_text,
                    start_char=st,
                    end_char=en,
                    citation_type="JUDICIAL",
                    normalized_id=norm_id
                ))

        # Sort by start_char
        citations.sort(key=lambda c: c.start_char)
        return citations

    def _normalize_statutory_id(self, cit_text: str) -> str:
        """Constructs a standardized identifier for the statutory reference."""
        # Find section number
        sec_m = re.search(r"(?:Section|Sec\.)\s+(\d+[A-Za-z]?(?:\(\d+\))*)", cit_text, re.IGNORECASE)
        if sec_m:
            raw_sec = sec_m.group(1).upper().replace("(", "_SUB_").replace(")", "")
            return f"ACT_COMPANIES_2013_SEC_{raw_sec}"
        return re.sub(r"[^A-Za-z0-9_]+", "_", cit_text.strip().upper())

    def _normalize_judicial_id(self, cit_text: str) -> str:
        """Constructs a standardized identifier for judicial references."""
        return re.sub(r"[^A-Za-z0-9_]+", "_", cit_text.strip().upper())
