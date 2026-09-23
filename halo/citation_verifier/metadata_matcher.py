"""
HALO Citation Verifier: Metadata Matcher
========================================
Protocol: v1.0-FROZEN
Compares parsed citation metadata fields against canonical authoritative records.
Evaluates Court, Year, Section, Subsection, Paragraph bounds, and Act Title consistency.
"""

import re
from typing import Dict, Any, List, Optional
from halo.citation_verifier.schemas import (
    ParsedCitation,
    MetadataResult,
    MetadataStatus,
    MetadataFieldDiff,
    AuthorityHierarchy
)


class MetadataMatcher:
    """Performs field-by-field metadata verification against canonical legal records."""

    @staticmethod
    def compare_statutory_metadata(
        parsed: ParsedCitation,
        hierarchy: AuthorityHierarchy,
        canonical_act_meta: Optional[Dict[str, Any]] = None
    ) -> MetadataResult:
        """
        Audits statutory citation metadata:
        - Act year / title alignment (e.g. Companies Act, 2018 -> MISMATCH with 2013)
        - Section and Subsection availability
        - Topic / Heading alignment
        """
        diffs: Dict[str, MetadataFieldDiff] = {}
        mismatches: List[str] = []

        # 1. Act Title / Year check
        if parsed.act_name and canonical_act_meta:
            canonical_title = canonical_act_meta.get("short_title", "Companies Act, 2013")
            canonical_year = str(canonical_act_meta.get("enactment_date", "2013"))[:4]
            # Check for year discrepancy (e.g. Companies Act, 2018)
            year_m = re.search(r"\b(19\d{2}|20\d{2})\b", parsed.act_name)
            if year_m and year_m.group(1) != canonical_year:
                diffs["act_year"] = MetadataFieldDiff(
                    field_name="act_year",
                    cited_value=year_m.group(1),
                    canonical_value=canonical_year,
                    matches=False,
                    notes=f"Act year mismatch: enacted in {canonical_year}, cited as {year_m.group(1)}."
                )
                mismatches.append("act_year_mismatch")
            else:
                diffs["act_title"] = MetadataFieldDiff(
                    field_name="act_title",
                    cited_value=parsed.act_name,
                    canonical_value=canonical_title,
                    matches=True
                )

        # 2. Section check
        if parsed.section:
            diffs["section"] = MetadataFieldDiff(
                field_name="section",
                cited_value=parsed.section,
                canonical_value=parsed.section if hierarchy.section_exists else None,
                matches=hierarchy.section_exists,
                notes=None if hierarchy.section_exists else f"Section {parsed.section} not found in authoritative Act."
            )
            if not hierarchy.section_exists:
                mismatches.append("section_not_found")

        # 3. Subsection check
        if parsed.subsection:
            available_subs = hierarchy.details.get("available_subsections", [])
            sub_matches = hierarchy.subsection_exists
            diffs["subsection"] = MetadataFieldDiff(
                field_name="subsection",
                cited_value=parsed.subsection,
                canonical_value=parsed.subsection if sub_matches else (available_subs[0] if available_subs else None),
                matches=sub_matches,
                notes=None if sub_matches else f"Subsection ({parsed.subsection}) not found. Available: {available_subs[:5]}."
            )
        # 4. Heading / Title check
        if parsed.asserted_heading and hierarchy.section_exists:
            canonical_heading = hierarchy.details.get("section_heading", "")
            norm_asserted = re.sub(r"[^A-Za-z0-9]+", " ", parsed.asserted_heading).lower().strip()
            norm_canonical = re.sub(r"[^A-Za-z0-9]+", " ", canonical_heading).lower().strip()
            heading_matches = (norm_asserted == norm_canonical or norm_asserted in norm_canonical or norm_canonical in norm_asserted)
            diffs["heading"] = MetadataFieldDiff(
                field_name="heading",
                cited_value=parsed.asserted_heading,
                canonical_value=canonical_heading,
                matches=heading_matches,
                notes=None if heading_matches else f"Heading mismatch: cited '{parsed.asserted_heading}', canonical is '{canonical_heading}'."
            )
            if not heading_matches:
                mismatches.append("heading_mismatch")

        # Determine overall metadata status
        if not hierarchy.section_exists:
            status = MetadataStatus.UNRESOLVED.value
            explanation = f"Section {parsed.section} not found in authoritative statute."
        elif mismatches:
            # If only subsection or minor year differed -> PARTIAL_MATCH or MISMATCH
            if len(mismatches) == 1 and mismatches[0] == "subsection_mismatch":
                status = MetadataStatus.PARTIAL_MATCH.value
                explanation = f"Section {parsed.section} exists, but subsection ({parsed.subsection}) differs from authoritative text."
            else:
                status = MetadataStatus.MISMATCH.value
                explanation = f"Metadata conflicts detected: {', '.join(mismatches)}."
        else:
            status = MetadataStatus.MATCH.value
            explanation = "All statutory metadata fields match authoritative canonical record."

        return MetadataResult(
            status=status,
            fields=diffs,
            mismatches=mismatches,
            explanation=explanation
        )

    @staticmethod
    def compare_judicial_metadata(
        parsed: ParsedCitation,
        canonical_judgment: Optional[Dict[str, Any]],
        max_para_num: int
    ) -> MetadataResult:
        """
        Audits judicial citation metadata:
        - Court verification (Supreme Court vs NCLAT vs High Court)
        - Decision year verification (Volume/enactment year)
        - Paragraph bounds verification (e.g. Para 999 requested in a 24-para judgment)
        """
        if not canonical_judgment:
            return MetadataResult(
                status=MetadataStatus.UNRESOLVED.value,
                fields={},
                mismatches=["judgment_not_found"],
                explanation="No authoritative judgment record available for comparison."
            )

        diffs: Dict[str, MetadataFieldDiff] = {}
        mismatches: List[str] = []

        canonical_court = canonical_judgment.get("court", "SUPREME_COURT_OF_INDIA")
        canonical_title = canonical_judgment.get("case_title", "")
        canonical_citations = canonical_judgment.get("citations", [])

        # 1. Court Verification
        if parsed.court:
            cited_court_upper = parsed.court.upper()
            court_matches = False

            if "SUPREME" in cited_court_upper and "SUPREME" in canonical_court:
                court_matches = True
            elif "NCLAT" in cited_court_upper and "NCLAT" in canonical_court:
                court_matches = True
            elif "HIGH" in cited_court_upper and "HIGH" in canonical_court:
                court_matches = True

            diffs["court"] = MetadataFieldDiff(
                field_name="court",
                cited_value=parsed.court,
                canonical_value=canonical_court,
                matches=court_matches,
                notes=None if court_matches else f"Court mismatch: decided by {canonical_court}, not {parsed.court}."
            )
            if not court_matches:
                mismatches.append("court_mismatch")

        # 2. Decision Year / Volume Verification
        if parsed.year:
            # Check year in canonical citations or date_of_judgment
            c_years = []
            for c in canonical_citations:
                for ym in [c[1:5] if c.startswith("[") else None, c[:4]]:
                    if ym and ym.isdigit():
                        c_years.append(ym)

            year_matches = parsed.year in c_years if c_years else True
            diffs["year"] = MetadataFieldDiff(
                field_name="year",
                cited_value=parsed.year,
                canonical_value=c_years[0] if c_years else None,
                matches=year_matches,
                notes=None if year_matches else f"Year mismatch: volume/decision year is {c_years}, not {parsed.year}."
            )
            if not year_matches:
                mismatches.append("year_mismatch")

        # 3. Paragraph Bounds Verification
        if parsed.paragraph:
            try:
                cited_para = int(parsed.paragraph)
                para_valid = (max_para_num > 0 and cited_para <= max_para_num)
                diffs["paragraph"] = MetadataFieldDiff(
                    field_name="paragraph",
                    cited_value=str(cited_para),
                    canonical_value=f"<= {max_para_num}",
                    matches=para_valid,
                    notes=None if para_valid else f"Paragraph {cited_para} out of bounds (judgment has {max_para_num} paragraphs)."
                )
                if not para_valid:
                    mismatches.append("paragraph_out_of_bounds")
            except ValueError:
                pass

        # Overall judicial metadata status
        if mismatches:
            status = MetadataStatus.MISMATCH.value
            explanation = f"Metadata conflicts detected: {', '.join(mismatches)}."
        else:
            status = MetadataStatus.MATCH.value
            explanation = "All judicial metadata fields match authoritative judgment record."

        return MetadataResult(
            status=status,
            fields=diffs,
            mismatches=mismatches,
            explanation=explanation
        )
