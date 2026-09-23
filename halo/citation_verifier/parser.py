"""
HALO Citation Verifier: Structured Citation Parser
==================================================
Protocol: v1.0-FROZEN
Deterministic, rule-grounded parser for statutory and judicial citations.
Extracts structured components (Act, Section, Subsection, Case Name, Court, Year, Reporter, Para)
from both raw strings and pre-structured citation metadata objects.
"""

import re
from typing import Union, Dict, Any, Optional
from halo.citation_verifier.schemas import ParsedCitation, AuthorityType


class CitationParser:
    """Parses raw citation text or metadata dicts into structured ParsedCitation objects."""

    # Statutory Regex Patterns
    STATUTORY_SECTION_PAT = re.compile(
        r"(?:Section|Sec\.|Sections|Secs\.)\s+"
        r"(?P<section>\d+[A-Za-z]?)"
        r"(?:\s*\((?P<subsection>\d+)\))?"
        r"(?:\s*\((?P<clause>[a-z]+)\))?",
        re.IGNORECASE
    )

    ACT_NAME_PAT = re.compile(
        r"(?:of\s+(?:the\s+)?)?"
        r"(?P<act>(?:[A-Za-z\s,]+(?:Act|Code),\s*\d{4}|\bIBC\b|\bInsolvency\s+and\s+Bankruptcy\s+Code\b))",
        re.IGNORECASE
    )

    # Judicial Regex Patterns
    REPORTER_PAT = re.compile(
        r"(?P<reporter>\[\d{4}\]\s+\d+\s+S\.C\.R\.\s+\d+|\(\d{4}\)\s+\d+\s+SCC\s+\d+|\d{4}\s+INSC\s+\d+|\bAIR\s+\d{4}\s+SC\s+\d+)",
        re.IGNORECASE
    )

    PARAGRAPH_PAT = re.compile(
        r"\b(?:paragraph|para\.?|p\.)\s*(?P<para>\d+)\b",
        re.IGNORECASE
    )

    COURT_PAT = re.compile(
        r"\b(?P<court>Supreme\s+Court(?:\s+of\s+India)?|NCLAT|NCLT|High\s+Court(?:\s+of\s+[A-Za-z]+)?|Special\s+Court)\b",
        re.IGNORECASE
    )

    YEAR_PAT = re.compile(
        r"\b(?P<year>19\d{2}|20\d{2})\b"
    )

    CASE_VS_PAT = re.compile(
        r"(?P<title>[A-Z][A-Za-z0-9\s&.,'()-]+?\s+(?:v\.|vs\.|versus)\s+[A-Z][A-Za-z0-9\s&.,'()-]+?)(?=(?:,\s*\[|,\s*\(|,\s*\d{4}|,\s*AIR|\s+held|\s+decided|;|\.|\n|$))",
        re.IGNORECASE
    )

    HEADING_ASSERTION_PAT = re.compile(
        r"\b(?:titled|entitled|named|is called|with heading)\s+['\"](?P<heading>[^'\"]+)['\"]",
        re.IGNORECASE
    )

    def parse(self, citation_input: Union[str, Dict[str, Any]]) -> ParsedCitation:
        """
        Parses citation string or dictionary into a normalized ParsedCitation.
        """
        if isinstance(citation_input, dict):
            return self._parse_from_dict(citation_input)
        elif isinstance(citation_input, str):
            return self._parse_from_string(citation_input)
        else:
            return ParsedCitation(citation_text=str(citation_input), authority_type=AuthorityType.UNKNOWN.value)

    def _parse_from_dict(self, d: Dict[str, Any]) -> ParsedCitation:
        """Constructs ParsedCitation from pre-structured dictionary (e.g. benchmark case)."""
        cit_text = d.get("citation_text")
        parsed_from_text = None
        if cit_text and isinstance(cit_text, str) and cit_text.strip():
            parsed_from_text = self._parse_from_string(cit_text)

        asserted_heading = d.get("asserted_heading") or (parsed_from_text.asserted_heading if parsed_from_text else None)

        # Determine if statute or judicial
        if "act" in d or "section" in d:
            act = d.get("act") or (parsed_from_text.act_name if parsed_from_text else None)
            sec = d.get("section") if d.get("section") is not None else (parsed_from_text.section if parsed_from_text else None)
            sub = d.get("subsection") if d.get("subsection") is not None else (parsed_from_text.subsection if parsed_from_text else None)
            cl = d.get("clause") if d.get("clause") is not None else (parsed_from_text.clause if parsed_from_text else None)

            # Form text representation if not provided
            if not cit_text:
                parts = []
                if sec:
                    parts.append(f"Section {sec}")
                    if sub:
                        parts.append(f"({sub})")
                    if cl:
                        parts.append(f"({cl})")
                if act:
                    parts.append(f"of {act}")
                cit_text = " ".join(parts) if parts else str(d)

            return ParsedCitation(
                citation_text=cit_text,
                authority_type=AuthorityType.STATUTE.value,
                act_name=act,
                section=str(sec) if sec is not None else None,
                subsection=str(sub) if sub is not None else None,
                clause=str(cl) if cl is not None else None,
                asserted_heading=asserted_heading
            )

        elif "case_name" in d or "citation_number" in d or "court" in d:
            case_title = d.get("case_name") or (parsed_from_text.case_title if parsed_from_text else None)
            reporter = d.get("citation_number") or (parsed_from_text.reporter if parsed_from_text else None)
            court = d.get("court") or (parsed_from_text.court if parsed_from_text else None)
            year = str(d.get("year")) if d.get("year") is not None else (parsed_from_text.year if parsed_from_text else None)
            para = str(d.get("paragraph")) if d.get("paragraph") is not None else (parsed_from_text.paragraph if parsed_from_text else None)

            if not cit_text:
                parts = [p for p in [case_title, reporter, court, year] if p]
                cit_text = ", ".join(parts) if parts else str(d)

            return ParsedCitation(
                citation_text=cit_text,
                authority_type=AuthorityType.JUDGMENT.value,
                case_title=case_title,
                reporter=reporter,
                court=court,
                year=year,
                paragraph=para
            )

        elif parsed_from_text is not None and parsed_from_text.authority_type != AuthorityType.UNKNOWN.value:
            return parsed_from_text

        return ParsedCitation(
            citation_text=str(cit_text or d),
            authority_type=AuthorityType.UNKNOWN.value
        )

    def _parse_from_string(self, text: str) -> ParsedCitation:
        """Extracts structured fields from raw unstructured citation text."""
        cleaned = text.strip()
        if not cleaned:
            return ParsedCitation(citation_text="", authority_type=AuthorityType.UNKNOWN.value)

        # 1. Check for Judicial Citation First (e.g. S.C.R., SCC, case names with v.)
        reporter_m = self.REPORTER_PAT.search(cleaned)
        case_vs_m = self.CASE_VS_PAT.search(cleaned)
        para_m = self.PARAGRAPH_PAT.search(cleaned)
        court_m = self.COURT_PAT.search(cleaned)

        if reporter_m or case_vs_m:
            reporter = reporter_m.group("reporter").strip() if reporter_m else None
            case_title = case_vs_m.group("title").strip() if case_vs_m else None
            if case_title:
                case_title = re.sub(r"^(?:in\s+|re:\s*)", "", case_title, flags=re.IGNORECASE).strip()
            paragraph = para_m.group("para").strip() if para_m else None
            court = court_m.group("court").strip() if court_m else None

            # Extract year from reporter e.g. [2016] or (2018) or standalone year
            year = None
            if reporter:
                ym = re.search(r"(\d{4})", reporter)
                if ym:
                    year = ym.group(1)
            if not year:
                ym = self.YEAR_PAT.search(cleaned)
                if ym:
                    year = ym.group("year")

            return ParsedCitation(
                citation_text=cleaned,
                authority_type=AuthorityType.JUDGMENT.value,
                case_title=case_title,
                court=court,
                year=year,
                reporter=reporter,
                paragraph=paragraph
            )

        # 2. Check for Statutory Citation
        sec_m = self.STATUTORY_SECTION_PAT.search(cleaned)
        act_m = self.ACT_NAME_PAT.search(cleaned)

        if sec_m or act_m:
            section = sec_m.group("section") if sec_m else None
            subsection = sec_m.group("subsection") if sec_m else None
            clause = sec_m.group("clause") if sec_m else None
            act_name = act_m.group("act").strip() if act_m else None

            # Clean leading prepositions and trailing punctuation from act name
            if act_name:
                act_name = re.sub(r"^(?:of\s+(?:the\s+)?|under\s+(?:the\s+)?)", "", act_name, flags=re.IGNORECASE)
                act_name = re.sub(r"^[,\s]+|[,\s]+$", "", act_name)

            heading_m = self.HEADING_ASSERTION_PAT.search(cleaned)
            asserted_heading = heading_m.group("heading").strip() if heading_m else None

            return ParsedCitation(
                citation_text=cleaned,
                authority_type=AuthorityType.STATUTE.value,
                act_name=act_name,
                section=section,
                subsection=subsection,
                clause=clause,
                asserted_heading=asserted_heading
            )

        # Fallback
        return ParsedCitation(
            citation_text=cleaned,
            authority_type=AuthorityType.UNKNOWN.value
        )
