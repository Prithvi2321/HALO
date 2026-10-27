"""
HALO Evidence Verifier: Deterministic Numerical Consistency Checker
===================================================================
Protocol: v1.0-FROZEN
Audits substantive legal numbers (amounts, currencies, percentages, durations,
counts, thresholds) while strictly ignoring citation identifiers (Section 135, Rule 12).
Emits structured consistency signals.
Critical invariant: Matching numbers do NOT imply entailment.
"""

from typing import List, Dict, Any, Tuple, Optional, Set
import re

from halo.evidence_verifier.schemas import (
    CheckStatus,
    NumericalMismatchType,
    NumericalCheckResult,
)


class NumericalChecker:
    """Audits numerical consistency between evidence premise and claim hypothesis."""

    # 1. Statutory / Citation Identifiers to IGNORE (User Correction #3)
    CITATION_PATTERNS = [
        r"\bsections?\s+\d+[a-z]?(?:\s*\([a-z0-9]+\))*",
        r"\brules?\s+\d+[a-z]?(?:\s*\([a-z0-9]+\))*",
        r"\bclauses?\s+\([a-z0-9]+\)",
        r"\bclauses?\s+\d+[a-z]?",
        r"\barticles?\s+\d+[a-z]?",
        r"\bschedules?\s+[ivx0-9]+",
        r"\bact\s+(?:no\.\s*)?\d+\s+of\s+\d{4}",
        r"\bno\.\s*\d+\s+of\s+\d{4}",
        r"\border\s+[ivx0-9]+",
        r"\bparagraphs?\s+\d+",
        r"\bpara\s+\d+",
        r"\bproviso\s+(?:to\s+section\s+\d+)?",
    ]

    # Comprehensive word-to-number mapping
    WORD_NUMBER_MAP = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
        "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
        "nineteen": 19, "twenty": 20, "twenty-one": 21, "twenty-four": 24,
        "twenty-five": 25, "thirty": 30, "forty": 40, "fifty": 50,
        "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
        "hundred": 100, "one hundred": 100,
        "one hundred and twenty": 120, "hundred and twenty": 120,
        "five hundred": 500, "one thousand": 1000, "thousand": 1000,
    }

    # Scale multipliers
    SCALES = {
        "crore": 10_000_000,
        "lakh": 100_000,
        "thousand": 1_000,
        "million": 1_000_000,
        "billion": 1_000_000_000,
    }

    def __init__(self):
        self._cit_regex = re.compile("|".join(self.CITATION_PATTERNS), re.IGNORECASE)

    def _strip_citations(self, text: str) -> str:
        """Removes citation identifiers like 'Section 135(1)' so they are not treated as quantities."""
        return self._cit_regex.sub(" ", text)

    def _parse_num_val(self, raw_str: str) -> Optional[float]:
        """Parses digits or word numbers into a float."""
        clean = raw_str.replace(",", "").strip().lower()
        if clean in self.WORD_NUMBER_MAP:
            return float(self.WORD_NUMBER_MAP[clean])
        try:
            return float(clean)
        except ValueError:
            return None

    def _extract_quantities(self, text: str) -> List[Dict[str, Any]]:
        """Extracts substantive numerical entities: amounts, percentages, counts, durations, multipliers."""
        cleaned = self._strip_citations(text)
        quantities: List[Dict[str, Any]] = []

        # A. Currency Amounts (e.g. ₹500 crore, ₹50 crore, ₹10 lakh, Rs. 5,000, rupees five crore)
        curr_pats = [
            r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)\s*(crore|lakh|thousand|million|billion)?",
            r"(?:rupees\s+)(five hundred|five|fifty|one thousand|ten|two|three|one|twenty|hundred)?\s*(crore|lakh|thousand)?",
            r"\b([\d,]+(?:\.\d+)?)\s+(crore|lakh|thousand|million|billion)\b",
            r"(?:₹|rs\.?)\s*([\d,]+(?:\.\d+)?)",
        ]

        for pat in curr_pats:
            for m in re.finditer(pat, cleaned, re.IGNORECASE):
                raw = m.group(0).strip()
                val_str = m.group(1) if len(m.groups()) >= 1 else ""
                scale_str = m.group(2) if len(m.groups()) >= 2 else ""

                val = self._parse_num_val(val_str) if val_str else None
                scale = 1.0
                if scale_str and scale_str.lower() in self.SCALES:
                    scale = float(self.SCALES[scale_str.lower()])

                if val is not None:
                    canonical_val = val * scale
                    quantities.append({
                        "type": NumericalMismatchType.AMOUNT_CHANGE.value,
                        "raw": raw,
                        "canonical_value": canonical_val,
                    })

        # B. Percentages & Fractions (Unified under PERCENTAGE_CHANGE, canonicalized to percentage value e.g. 10.0, 25.0)
        # 1. Explicit Percentages (Note: no trailing \b after % because % is non-word)
        pct_pats = [
            r"(\b[\d,]+(?:\.\d+)?)\s*(?:%|(?:\bper\s+cent\.?\b)|(?:\bpercent\b))",
            r"\b([a-z-]+)\s+(?:per\s+cent\.?|percent)\b",
        ]
        for pat in pct_pats:
            for m in re.finditer(pat, cleaned, re.IGNORECASE):
                raw = m.group(0).strip()
                val_str = m.group(1).strip().lower()
                val = self._parse_num_val(val_str)
                if val is not None:
                    quantities.append({
                        "type": NumericalMismatchType.PERCENTAGE_CHANGE.value,
                        "raw": raw,
                        "canonical_value": round(val, 2),
                    })

        # 2. Statutory Fractions mapped to percentage equivalents
        frac_pats = [
            (r"\b(?:one-tenth|1/10th?)\b", 10.0),
            (r"\b(?:one-fifth|1/5th?)\b", 20.0),
            (r"\b(?:one-fourth|1/4th?|quarter)\b", 25.0),
            (r"\b(?:one-third|1/3rd?)\b", 33.33),
            (r"\b(?:one-half|1/2)\b", 50.0),
        ]
        for pat, pct_equiv in frac_pats:
            for m in re.finditer(pat, cleaned, re.IGNORECASE):
                quantities.append({
                    "type": NumericalMismatchType.PERCENTAGE_CHANGE.value,
                    "raw": m.group(0).strip(),
                    "canonical_value": pct_equiv,
                })

        # C. Multipliers (e.g. three times, 5 times, twice, thrice)
        mult_pats = [
            r"\b([\d,]+|[a-z-]+)\s+times\b",
        ]
        for pat in mult_pats:
            for m in re.finditer(pat, cleaned, re.IGNORECASE):
                raw = m.group(0).strip()
                val = self._parse_num_val(m.group(1))
                if val is not None:
                    quantities.append({
                        "type": NumericalMismatchType.THRESHOLD_CHANGE.value,
                        "raw": raw,
                        "canonical_value": val,
                    })

        # D. Durations (Normalized to approximate days: 1 day=1, 1 week=7, 1 month=30, 1 year=365)
        num_words = "|".join(re.escape(k) for k in sorted(self.WORD_NUMBER_MAP.keys(), key=len, reverse=True))
        dur_pats = [
            r"\b([\d,]+)\s*(days?|weeks?|months?|years?|financial\s+years?)\b",
            rf"\b({num_words})\s+(days?|weeks?|months?|years?|financial\s+years?)\b",
        ]
        unit_days = {
            "day": 1.0, "days": 1.0,
            "week": 7.0, "weeks": 7.0,
            "month": 30.0, "months": 30.0,
            "year": 365.0, "years": 365.0,
            "financial year": 365.0, "financial years": 365.0,
        }
        for pat in dur_pats:
            for m in re.finditer(pat, cleaned, re.IGNORECASE):
                raw = m.group(0).strip()
                val = self._parse_num_val(m.group(1))
                unit = m.group(2).lower().strip()
                if val is not None and unit in unit_days:
                    canonical_days = val * unit_days[unit]
                    quantities.append({
                        "type": NumericalMismatchType.DURATION_CHANGE.value,
                        "raw": raw,
                        "canonical_value": canonical_days,
                    })

        # E. Counts (e.g. minimum three directors, two directors, five directors, 15 directors, 100 members)
        count_pats = [
            r"\b(minimum|maximum|at\s+least)?\s*([\d,]+)\s+(directors?|members?|shareholders?|companies|persons?)\b",
            rf"\b(minimum|maximum|at\s+least)?\s*({num_words})\s+(directors?|members?|shareholders?|companies|persons?)\b",
            rf"\b(?:minimum\s+)?number\s+of\s+(directors?|members?|shareholders?)\s+(?:[^.]{{0,50}}?\s+)?(?:is|shall\s+be)\s+([\d,]+|{num_words})\b",
        ]
        for pat in count_pats:
            for m in re.finditer(pat, cleaned, re.IGNORECASE):
                raw = m.group(0).strip()
                groups = m.groups()
                if len(groups) == 2:
                    entity = groups[0].lower().strip()
                    num_part = groups[1].lower().strip()
                else:
                    num_part = groups[1].lower().strip()
                    entity = groups[2].lower().strip()

                val = self._parse_num_val(num_part)
                if val is not None:
                    quantities.append({
                        "type": NumericalMismatchType.COUNT_CHANGE.value,
                        "raw": raw,
                        "canonical_value": f"{val}_{entity.rstrip('s')}",
                    })

        return quantities

    def check(self, claim_text: str, evidence_text: str) -> NumericalCheckResult:
        """Audits numerical consistency between evidence and claim."""
        claim_quants = self._extract_quantities(claim_text)
        evidence_quants = self._extract_quantities(evidence_text)

        if not claim_quants:
            return NumericalCheckResult(
                status=CheckStatus.NOT_APPLICABLE.value,
                mismatch_type=NumericalMismatchType.NONE.value,
                claim_values=[],
                evidence_values=[q["raw"] for q in evidence_quants],
                details="No substantive numerical quantities in claim.",
            )

        claim_raws = [q["raw"] for q in claim_quants]
        ev_raws = [q["raw"] for q in evidence_quants]

        if not evidence_quants:
            return NumericalCheckResult(
                status=CheckStatus.NOT_APPLICABLE.value,
                mismatch_type=NumericalMismatchType.NONE.value,
                claim_values=claim_raws,
                evidence_values=[],
                details=f"Claim asserts numerical quantities {claim_raws}, but evidence passage contains no corresponding quantities to compare.",
            )

        # Compare matching categories
        mismatches: List[Tuple[str, str, str]] = []
        matches: List[Tuple[str, str]] = []

        for cq in claim_quants:
            c_type = cq["type"]
            c_val = cq["canonical_value"]
            found_match = False
            conflicting_ev = []

            for eq in evidence_quants:
                e_type = eq["type"]
                e_val = eq["canonical_value"]

                if c_type == e_type:
                    # Compare numerical value with category-specific tolerance
                    is_equal = False
                    if isinstance(c_val, (int, float)) and isinstance(e_val, (int, float)):
                        if c_type == NumericalMismatchType.DURATION_CHANGE.value:
                            # Allow 5% tolerance for rounding (e.g. 360 vs 365 days)
                            ratio = c_val / max(e_val, 1e-6)
                            is_equal = 0.90 <= ratio <= 1.10
                        elif c_type == NumericalMismatchType.PERCENTAGE_CHANGE.value:
                            is_equal = abs(c_val - e_val) < 0.5
                        else:
                            is_equal = abs(c_val - e_val) < 1e-4
                    else:
                        is_equal = (c_val == e_val)

                    if is_equal:
                        found_match = True
                        matches.append((cq["raw"], eq["raw"]))
                        break
                    else:
                        conflicting_ev.append(eq)

            if not found_match and conflicting_ev:
                mismatches.append((cq["raw"], conflicting_ev[0]["raw"], c_type))

        if mismatches:
            c_raw, e_raw, m_type = mismatches[0]
            return NumericalCheckResult(
                status=CheckStatus.MISMATCH.value,
                mismatch_type=m_type,
                claim_values=claim_raws,
                evidence_values=ev_raws,
                details=f"Numerical mismatch detected ({m_type}): Claim asserts '{c_raw}', but evidence establishes '{e_raw}'.",
            )

        if matches:
            return NumericalCheckResult(
                status=CheckStatus.MATCH.value,
                mismatch_type=NumericalMismatchType.NONE.value,
                claim_values=claim_raws,
                evidence_values=ev_raws,
                details=f"Substantive numerical quantities match between claim and evidence: {matches}.",
            )

        return NumericalCheckResult(
            status=CheckStatus.NOT_APPLICABLE.value,
            mismatch_type=NumericalMismatchType.NONE.value,
            claim_values=claim_raws,
            evidence_values=ev_raws,
            details="No conflicting numerical quantities detected.",
        )

