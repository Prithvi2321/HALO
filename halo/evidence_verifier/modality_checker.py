"""
HALO Evidence Verifier: Clause-Aware Deontic Modality Checker
=============================================================
Protocol: v1.0-FROZEN
Audits legal deontic modality (MANDATORY, PROHIBITED, PERMITTED, OPTIONAL, etc.)
using contextual multi-word pattern matching (User Correction #4).
Prevents single-word 'may' false positives and detects high-risk modal mutations.
"""

from typing import Optional, List, Tuple
import re

from halo.evidence_verifier.schemas import (
    CheckStatus,
    ModalityType,
    ModalityCheckResult,
)


class ModalityChecker:
    """Audits clause-aware deontic modality consistency between evidence and claim."""

    # Administrative boilerplate patterns to ignore when analyzing evidence
    ADMIN_BOILERPLATE_PATTERNS = [
        r"\bas\s+may\s+be\s+(?:prescribed|notified|specified|addressed|determined|ordered|required|applicable)\b",
        r"\bconditions\s+as\s+may\s+be\b",
        r"\brules\s+as\s+may\s+be\b",
        r"\bif\s+any\s*,\s*as\s+may\s+be\b",
        r"\bin\s+such\s+manner\s+as\s+may\s+be\b",
        r"\bterms\s+and\s+conditions\s+as\s+may\s+be\b",
    ]

    # Prioritized pattern sets: multi-word phrases evaluated before single words
    MODAL_PATTERNS: List[Tuple[ModalityType, List[str]]] = [
        # 1. Prohibitions (evaluate first to catch 'shall not', 'must not', 'may not')
        (
            ModalityType.PROHIBITED,
            [
                r"\bshall\s+not\b",
                r"\bmust\s+not\b",
                r"\bmay\s+not\b",
                r"\bcannot\b",
                r"\bcan\s+not\b",
                r"\bis\s+prohibited\s+from\b",
                r"\bis\s+forbidden\s+to\b",
                r"\bin\s+no\s+case\s+shall\b",
                r"\bno\s+\w+\s+shall\b",
                r"\bno\s+company\s+shall\b",
                r"\bno\s+director\s+shall\b",
                r"\bprohibited\b",
            ],
        ),
        # 2. Discretionary / Optional (evaluate before general permitted to catch voluntary choice)
        (
            ModalityType.OPTIONAL,
            [
                r"\bvoluntarily\s+choose\b",
                r"\boptionally\s+choose\b",
                r"\boptionally\b",
                r"\bpurely\s+discretionary\b",
                r"\bat\s+(?:its|the|their)\s+discretion\b",
                r"\bhave\s+discretion\b",
                r"\bhas\s+discretion\b",
                r"\bdiscretion\s+to\b",
                r"\bdiscretionary\b",
                r"\boptional\b",
                r"\bvoluntary\b",
                r"\bat\s+liberty\s+to\b",
                r"\bmay\s+be\s+omitted\b",
                r"\bmay\s+be\s+issued\s+publicly\s+unsigned\b",
                r"\bunsigned\b",
            ],
        ),
        # 3. Mandatory / Obligatory
        (
            ModalityType.MANDATORY,
            [
                r"\bshall\s+constitute\b",
                r"\bshall\s+ensure\b",
                r"\bshall\s+call\b",
                r"\bshall\s+be\s+liable\b",
                r"\bshall\s+have\b",
                r"\bshall\s+report\b",
                r"\bshall\s+be\s+signed\b",
                r"\bshall\s+be\s+filed\b",
                r"\bshall\s+be\s+punishable\b",
                r"\bshall\b(?!\s+(?:not|be\s+entitled|have\s+the\s+right)\b)",
                r"\bmust\b(?!\s+not\b)",
                r"\bis\s+required\s+to\b",
                r"\bduty\s+of\b",
                r"\bis\s+obligated\s+to\b",
                r"\bmandatory\b",
                r"\bmandatorily\b",
                r"\bobligatory\b",
                r"\bstrictly\s+requires\b",
            ],
        ),
        # 4. Permitted / Discretionary Powers & Rights
        (
            ModalityType.PERMITTED,
            [
                r"\bshall\s+be\s+entitled\s+to\b",
                r"\bshall\s+have\s+the\s+right\s+to\b",
                r"\bmay\b(?!\s+not\b)",
                r"\bis\s+permitted\s+to\b",
                r"\bis\s+entitled\s+to\b",
                r"\bhas\s+the\s+right\s+to\b",
                r"\bis\s+authorized\s+to\b",
                r"\bhas\s+the\s+power\s+to\b",
                r"\bcan\b(?!\s+not\b)",
            ],
        ),
        # 5. Conditional
        (
            ModalityType.CONDITIONAL,
            [
                r"\bsubject\s+to\b",
                r"\bprovided\s+that\b",
                r"\bon\s+condition\s+that\b",
                r"\bin\s+the\s+event\s+that\b",
            ],
        ),
    ]

    def __init__(self):
        self._compiled: List[Tuple[ModalityType, List[re.Pattern]]] = []
        for m_type, pats in self.MODAL_PATTERNS:
            compiled_pats = [re.compile(p, re.IGNORECASE) for p in pats]
            self._compiled.append((m_type, compiled_pats))

    def _strip_admin_boilerplate(self, text: str) -> str:
        """Removes administrative delegating phrases like 'as may be prescribed'."""
        cleaned = text
        for pat in self.ADMIN_BOILERPLATE_PATTERNS:
            cleaned = re.sub(pat, " ", cleaned, flags=re.IGNORECASE)
        return cleaned

    def detect_modality(self, text: str) -> ModalityType:
        """Extracts the dominant legal deontic modality from text using prioritized patterns."""
        if not text:
            return ModalityType.NONE

        for m_type, pats in self._compiled:
            for p in pats:
                if p.search(text):
                    return m_type

        return ModalityType.NONE

    def detect_modalities(self, text: str, is_evidence: bool = False) -> List[ModalityType]:
        """Detects all distinct legal deontic modalities present in text."""
        if not text:
            return []
        target_text = self._strip_admin_boilerplate(text) if is_evidence else text
        found: List[ModalityType] = []
        for m_type, pats in self._compiled:
            for p in pats:
                if p.search(target_text):
                    if m_type not in found:
                        found.append(m_type)
                    break
        return found

    def check(self, claim_text: str, evidence_text: str) -> ModalityCheckResult:
        """Audits deontic modality consistency between evidence premise and claim hypothesis."""
        claim_mod = self.detect_modality(claim_text)
        ev_modalities = self.detect_modalities(evidence_text, is_evidence=True)
        ev_mod = ev_modalities[0] if ev_modalities else ModalityType.NONE

        if claim_mod == ModalityType.NONE or not ev_modalities:
            return ModalityCheckResult(
                status=CheckStatus.NOT_APPLICABLE.value,
                claim_modality=claim_mod.value,
                evidence_modality=ev_mod.value,
                details="Explicit deontic modality not identified in both claim and evidence.",
            )

        # 1. High-risk conflicting pairs (take precedence over broad presence):
        # 1a. Evidence contains strictly MANDATORY obligation, but Claim asserts OPTIONAL or DISCRETIONARY
        if ModalityType.MANDATORY in ev_modalities and claim_mod in (ModalityType.OPTIONAL, ModalityType.DISCRETIONARY):
            return ModalityCheckResult(
                status=CheckStatus.MISMATCH.value,
                claim_modality=claim_mod.value,
                evidence_modality=ModalityType.MANDATORY.value,
                details="Modal mismatch: Statute imposes mandatory obligation ('shall'/'must'), but claim asserts it is discretionary or optional ('voluntarily'/'optionally').",
            )

        # 1b. Evidence contains strictly PROHIBITED, but Claim asserts PERMITTED or OPTIONAL
        if ModalityType.PROHIBITED in ev_modalities and claim_mod in (ModalityType.PERMITTED, ModalityType.OPTIONAL, ModalityType.MANDATORY):
            return ModalityCheckResult(
                status=CheckStatus.MISMATCH.value,
                claim_modality=claim_mod.value,
                evidence_modality=ModalityType.PROHIBITED.value,
                details="Modal mismatch: Statute prohibits action ('shall not'/'must not'/'without consent'), but claim asserts permission or discretion.",
            )

        # 1c. Evidence contains strictly MANDATORY obligation and NOT permitted, but Claim asserts PERMITTED ('may'/'can')
        if ModalityType.MANDATORY in ev_modalities and ModalityType.PERMITTED not in ev_modalities and claim_mod == ModalityType.PERMITTED:
            return ModalityCheckResult(
                status=CheckStatus.MISMATCH.value,
                claim_modality=claim_mod.value,
                evidence_modality=ModalityType.MANDATORY.value,
                details="Modal mismatch: Statute mandates action ('shall'/'must'), but claim asserts it is merely discretionary or permitted ('may'/'can').",
            )

        # 1d. Evidence is strictly PERMITTED or OPTIONAL, but Claim asserts MANDATORY
        if any(m in ev_modalities for m in (ModalityType.PERMITTED, ModalityType.OPTIONAL)) and ModalityType.MANDATORY not in ev_modalities and claim_mod == ModalityType.MANDATORY:
            return ModalityCheckResult(
                status=CheckStatus.MISMATCH.value,
                claim_modality=claim_mod.value,
                evidence_modality=ModalityType.PERMITTED.value,
                details="Modal mismatch: Statute specifies discretionary permission ('may'), but claim asserts mandatory obligation ('must'/'shall').",
            )

        # 1e. Entity-level duty clash: Statute binds the entity with 'shall', but claim asserts entity 'may'
        entity_mand_ev = bool(re.search(r"\b(?:every|a|the)?\s*(?:company|director|member|board)\s+shall\b", evidence_text, re.IGNORECASE))
        entity_perm_claim = bool(re.search(r"\b(?:every|a|the)?\s*(?:company|director|member|board)\s+may\b", claim_text, re.IGNORECASE))
        if entity_mand_ev and entity_perm_claim:
            return ModalityCheckResult(
                status=CheckStatus.MISMATCH.value,
                claim_modality=claim_mod.value,
                evidence_modality=ModalityType.MANDATORY.value,
                details="Modal mismatch: Statute binds the entity with mandatory command ('shall'), but claim asserts discretionary permission ('may').",
            )

        # 2. Compatible match: claim's modality is directly authorized in the evidence
        if claim_mod in ev_modalities:
            return ModalityCheckResult(
                status=CheckStatus.MATCH.value,
                claim_modality=claim_mod.value,
                evidence_modality=claim_mod.value,
                details=f"Deontic modality matches passage authority: {claim_mod.value}.",
            )

        return ModalityCheckResult(
            status=CheckStatus.NOT_APPLICABLE.value,
            claim_modality=claim_mod.value,
            evidence_modality=ev_mod.value,
            details=f"Non-conflicting modalities: Claim={claim_mod.value}, Evidence={[m.value for m in ev_modalities]}.",
        )


