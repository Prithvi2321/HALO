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
                r"\bprohibited\b",
            ],
        ),
        # 2. Discretionary / Optional (evaluate before general permitted to catch voluntary choice)
        (
            ModalityType.OPTIONAL,
            [
                r"\bvoluntarily\s+choose\b",
                r"\bpurely\s+discretionary\b",
                r"\bat\s+(?:its|the|their)\s+discretion\b",
                r"\bdiscretionary\b",
                r"\boptional\b",
                r"\bvoluntary\b",
                r"\bat\s+liberty\s+to\b",
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
                r"\bshall\b(?!\s+not\b)",
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
        # 4. Permitted / Discretionary Powers
        (
            ModalityType.PERMITTED,
            [
                r"\bmay\b(?!\s+not\b)",
                r"\bis\s+permitted\s+to\b",
                r"\bis\s+entitled\s+to\b",
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

    def detect_modality(self, text: str) -> ModalityType:
        """Extracts the dominant legal deontic modality from text using prioritized patterns."""
        if not text:
            return ModalityType.NONE

        for m_type, pats in self._compiled:
            for p in pats:
                if p.search(text):
                    return m_type

        return ModalityType.NONE

    def detect_modalities(self, text: str) -> List[ModalityType]:
        """Detects all distinct legal deontic modalities present in text."""
        if not text:
            return []
        found: List[ModalityType] = []
        for m_type, pats in self._compiled:
            for p in pats:
                if p.search(text):
                    if m_type not in found:
                        found.append(m_type)
                    break
        return found

    def _extract_modal_actions(self, text: str) -> List[Tuple[str, str]]:
        """Extracts (modal_verb, action_verb) pairs from text."""
        if not text:
            return []
        text_clean = re.sub(r"[\n\r]+", " ", text)
        matches = re.findall(
            r"\b(shall\s+not|must\s+not|may\s+not|cannot|shall|must|may|can)\b(?:\s*,\s*[^,]+,\s*|\s+(?:not\s+)?(?:be\s+)?|\s+)(\b\w+\b)",
            text_clean,
            re.IGNORECASE,
        )
        return [(m[0].lower().strip(), m[1].lower().strip()) for m in matches if len(m[1]) > 2]

    def check(self, claim_text: str, evidence_text: str) -> ModalityCheckResult:
        """Audits deontic modality consistency between evidence premise and claim hypothesis."""
        claim_mod = self.detect_modality(claim_text)
        ev_modalities = self.detect_modalities(evidence_text)
        ev_mod = ev_modalities[0] if ev_modalities else ModalityType.NONE

        if claim_mod == ModalityType.NONE or not ev_modalities:
            return ModalityCheckResult(
                status=CheckStatus.NOT_APPLICABLE.value,
                claim_modality=claim_mod.value,
                evidence_modality=ev_mod.value,
                details="Explicit deontic modality not identified in both claim and evidence.",
            )

        # 1. Compatible match: claim's modality is directly authorized in the evidence
        if claim_mod in ev_modalities:
            return ModalityCheckResult(
                status=CheckStatus.MATCH.value,
                claim_modality=claim_mod.value,
                evidence_modality=claim_mod.value,
                details=f"Deontic modality matches passage authority: {claim_mod.value}.",
            )

        # High-risk conflicting pairs when claim_mod is NOT supported by ev_modalities:
        # 2a. Evidence is strictly MANDATORY, but Claim asserts OPTIONAL or DISCRETIONARY
        if ModalityType.MANDATORY in ev_modalities and claim_mod in (ModalityType.OPTIONAL, ModalityType.DISCRETIONARY):
            return ModalityCheckResult(
                status=CheckStatus.MISMATCH.value,
                claim_modality=claim_mod.value,
                evidence_modality=ModalityType.MANDATORY.value,
                details="Modal mismatch: Statute imposes mandatory obligation ('shall'/'must'), but claim asserts it is discretionary or optional ('voluntarily'/'optional').",
            )

        # 2b. Evidence is strictly MANDATORY and Claim asserts PERMITTED ('may'/'can') on the SAME action verb
        if ModalityType.MANDATORY in ev_modalities and claim_mod == ModalityType.PERMITTED:
            claim_actions = self._extract_modal_actions(claim_text)
            ev_actions = self._extract_modal_actions(evidence_text)
            shared_action_mutation = False
            for c_mod, c_act in claim_actions:
                if c_mod in ("may", "can"):
                    for e_mod, e_act in ev_actions:
                        if e_mod in ("shall", "must") and (c_act == e_act or c_act.startswith(e_act) or e_act.startswith(c_act)):
                            shared_action_mutation = True
                            break
            if shared_action_mutation:
                return ModalityCheckResult(
                    status=CheckStatus.MISMATCH.value,
                    claim_modality=claim_mod.value,
                    evidence_modality=ModalityType.MANDATORY.value,
                    details="Modal mismatch: Statute mandates action ('shall'/'must'), but claim asserts it is discretionary ('may'/'can').",
                )

        # 3. Evidence is MANDATORY, but Claim asserts PROHIBITED
        if ModalityType.MANDATORY in ev_modalities and claim_mod == ModalityType.PROHIBITED:
            return ModalityCheckResult(
                status=CheckStatus.MISMATCH.value,
                claim_modality=claim_mod.value,
                evidence_modality=ModalityType.MANDATORY.value,
                details="Modal mismatch: Statute mandates action, but claim asserts prohibition.",
            )

        # 4. Evidence is PROHIBITED, but Claim asserts PERMITTED or MANDATORY or OPTIONAL
        if ModalityType.PROHIBITED in ev_modalities and claim_mod in (ModalityType.PERMITTED, ModalityType.MANDATORY, ModalityType.OPTIONAL, ModalityType.DISCRETIONARY):
            return ModalityCheckResult(
                status=CheckStatus.MISMATCH.value,
                claim_modality=claim_mod.value,
                evidence_modality=ModalityType.PROHIBITED.value,
                details="Modal mismatch: Statute prohibits action ('shall not'/'must not'), but claim asserts permission or obligation.",
            )

        # 5. Evidence is PERMITTED/OPTIONAL, but Claim asserts MANDATORY
        if any(m in ev_modalities for m in (ModalityType.PERMITTED, ModalityType.OPTIONAL)) and claim_mod == ModalityType.MANDATORY:
            return ModalityCheckResult(
                status=CheckStatus.MISMATCH.value,
                claim_modality=claim_mod.value,
                evidence_modality=ModalityType.PERMITTED.value,
                details="Modal mismatch: Statute specifies discretionary permission ('may'), but claim asserts mandatory obligation ('must'/'shall').",
            )

        return ModalityCheckResult(
            status=CheckStatus.NOT_APPLICABLE.value,
            claim_modality=claim_mod.value,
            evidence_modality=ev_mod.value,
            details=f"Non-conflicting modalities: Claim={claim_mod.value}, Evidence={[m.value for m in ev_modalities]}.",
        )

