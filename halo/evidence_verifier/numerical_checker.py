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
        "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20,
        "thirty": 30, "fifty": 50, "hundred": 100, "one hundred": 100,
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

    def _extract_quantities(self, text: str) -> List[Dict[str, Any]]:
        """Extracts substantive numerical entities: amounts, percentages, counts, durations."""
        cleaned = self._strip_citations(text)
        quantities: List[Dict[str, Any]] = []

        # A. Currency Amounts (e.g. ₹500 crore, ₹50 crore, ₹10 lakh, Rs. 5,000, rupees five crore)
        curr_pats = [
            # Symbols with scale: ₹500 crore, Rs. 50 crore, ₹ 10 lakh
            r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)\s*(crore|lakh|thousand|million|billion)?",
            # Words: rupees five hundred crore, rupees fifty crore, rupees five crore, ten lakh rupees
            r"(?:rupees\s+)(five hundred|five|fifty|one thousand|ten|two|three|one|twenty|hundred)?\s*(crore|lakh|thousand)?",
            # Numeric with scale: 500 crore, 50 crore, 10 lakh, 1,000 crore
            r"\b([\d,]+(?:\.\d+)?)\s+(crore|lakh|thousand|million|billion)\b",
            # Plain currency without scale: ₹5,000, Rs. 1,00,000
            r"(?:₹|rs\.?)\s*([\d,]+(?:\.\d+)?)",
        ]

        for pat in curr_pats:
            for m in re.finditer(pat, cleaned, re.IGNORECASE):
                raw = m.group(0).strip()
                val_str = m.group(1) if len(m.groups()) >= 1 else ""
                scale_str = m.group(2) if len(m.groups()) >= 2 else ""

                val = None
                if val_str:
                    clean_num = val_str.replace(",", "").strip().lower()
                    if clean_num in self.WORD_NUMBER_MAP:
                        val = float(self.WORD_NUMBER_MAP[clean_num])
                    else:
                        try:
                            val = float(clean_num)
                        except ValueError:
                            pass

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

        # B. Percentages (e.g. 25%, 2%, two per cent, at least two per cent)
        pct_pats = [
            r"\b([\d,]+(?:\.\d+)?)\s*(?:%|per\s+cent\.?|percent)\b",
            r"\b(two|three|five|ten|twenty|twenty-five)\s+per\s+cent\b",
        ]
        for pat in pct_pats:
            for m in re.finditer(pat, cleaned, re.IGNORECASE):
                raw = m.group(0).strip()
                val_str = m.group(1).strip().lower()
                if val_str in self.WORD_NUMBER_MAP:
                    val = float(self.WORD_NUMBER_MAP[val_str])
                else:
                    try:
                        val = float(val_str.replace(",", ""))
                    except ValueError:
                        continue
                quantities.append({
                    "type": NumericalMismatchType.PERCENTAGE_CHANGE.value,
                    "raw": raw,
                    "canonical_value": val,
                })

        # C. Fractions / Ratios (e.g. one-tenth, 1/10th, not less than one-tenth)
        frac_pats = [
            (r"\b(?:one-tenth|1/10th?)\b", 0.1),
            (r"\b(?:one-fifth|1/5th?)\b", 0.2),
            (r"\b(?:one-fourth|1/4th?|quarter)\b", 0.25),
            (r"\b(?:one-third|1/3rd?)\b", 0.333),
            (r"\b(?:one-half|1/2)\b", 0.5),
        ]
        for pat, frac_val in frac_pats:
            for m in re.finditer(pat, cleaned, re.IGNORECASE):
                quantities.append({
                    "type": NumericalMismatchType.THRESHOLD_CHANGE.value,
                    "raw": m.group(0).strip(),
                    "canonical_value": frac_val,
                })

        # D. Durations (e.g. 30 days, 15 days, 3 years, 6 months, 3 financial years)
        dur_pats = [
            r"\b([\d,]+)\s*(days?|weeks?|months?|years?|financial\s+years?)\b",
            r"\b(three|six|twelve|two)\s+(days?|weeks?|months?|years?|financial\s+years?)\b",
        ]
        for pat in dur_pats:
            for m in re.finditer(pat, cleaned, re.IGNORECASE):
                raw = m.group(0).strip()
                num_part = m.group(1).strip().lower()
                unit = m.group(2).lower().strip()
                val = self.WORD_NUMBER_MAP.get(num_part)
                if val is None:
                    try:
                        val = float(num_part)
                    except ValueError:
                        continue
                quantities.append({
                    "type": NumericalMismatchType.DURATION_CHANGE.value,
                    "raw": raw,
                    "canonical_value": f"{val}_{unit}",
                })

        # E. Counts (e.g. minimum three directors, two directors, five directors, 15 directors, 100 members)
        num_word_pat = "one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty|fifty|hundred|one\\s+hundred"
        count_pats = [
            r"\b(minimum|maximum|at\s+least)?\s*([\d,]+)\s+(directors?|members?|shareholders?|companies|persons?)\b",
            rf"\b(minimum|maximum|at\s+least)?\s*({num_word_pat})\s+(directors?|members?|shareholders?|companies|persons?)\b",
            rf"\b(?:minimum\s+)?number\s+of\s+(directors?|members?|shareholders?)\s+(?:[^.]{{0,50}}?\s+)?(?:is|shall\s+be)\s+([\d,]+|{num_word_pat})\b",
        ]
        for pat in count_pats:
            for m in re.finditer(pat, cleaned, re.IGNORECASE):
                raw = m.group(0).strip()
                groups = m.groups()
                if len(groups) == 2:
                    # e.g. number of directors ... is three
                    entity = groups[0].lower().strip()
                    num_part = groups[1].lower().strip()
                else:
                    num_part = groups[1].lower().strip()
                    entity = groups[2].lower().strip()

                val = self.WORD_NUMBER_MAP.get(num_part)
                if val is None:
                    try:
                        val = float(num_part.replace(",", ""))
                    except ValueError:
                        continue
                quantities.append({
                    "type": NumericalMismatchType.COUNT_CHANGE.value,
                    "raw": raw,
                    "canonical_value": f"{val}_{entity}",
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
            # Evidence contains no numbers to contradict; not a confirmed numerical mismatch
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
                    # Check exact value match
                    if c_val == e_val:
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
