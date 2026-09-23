"""
HALO Evidence Verifier: Multi-Evidence Aggregator & Hard Safety Overrides
========================================================================
Protocol: v1.0-FROZEN
Aggregates evidence across candidate passages with strict governance:
1. Hard safety overrides: Symbolic mismatches strictly block SUPPORTED (User Correction #2)
2. Strict conflict definition: Requires distinct passages (passage_id_A != passage_id_B) (User Correction #7)
3. Strict PARTIALLY_SUPPORTED: Only for explicitly declared compound claims (User Correction #6)
4. Full evidence item preservation without averaging away conflicts
"""

from typing import List, Dict, Any, Tuple, Optional
import hashlib
import re

from halo.evidence_verifier.config import EvidenceVerifierConfig
from halo.evidence_verifier.schemas import (
    EvidenceVerdictStatus,
    CheckStatus,
    ClaimAtomicity,
    NLIPairResult,
    NumericalCheckResult,
    ModalityCheckResult,
    NegationCheckResult,
    EvidenceItem,
    AggregationSummary,
)


class EvidenceAggregator:
    """Aggregates independent evidence passage evaluations into a deterministic verdict."""

    def __init__(self, config: Optional[EvidenceVerifierConfig] = None):
        self.config = config or EvidenceVerifierConfig()

    def evaluate_single_item(
        self,
        claim_text: str,
        passage_id: str,
        source: str,
        dataset: str,
        authority_id: Optional[str],
        section_id: Optional[str],
        passage_text: str,
        nli_result: NLIPairResult,
        numerical_result: NumericalCheckResult,
        modality_result: ModalityCheckResult,
        negation_result: NegationCheckResult,
    ) -> EvidenceItem:
        """Evaluates a single evidence passage against the claim, applying hard safety overrides."""
        local_status = EvidenceVerdictStatus.NEUTRAL.value
        text_hash = hashlib.sha256(passage_text.strip().encode("utf-8")).hexdigest()

        # 1. User Correction #2: Hard Safety Overrides
        # Symbolic mismatches strictly block SUPPORTED.
        # If there is semantic engagement (NLI is not completely neutral/tangential), it triggers CONTRADICTED.
        # If NLI shows the passage is completely tangential (neutral >= 0.70), it remains NEUTRAL.
        has_symbolic_mismatch = (
            numerical_result.status == CheckStatus.MISMATCH.value
            or modality_result.status == CheckStatus.MISMATCH.value
            or negation_result.status == CheckStatus.MISMATCH.value
        )

        probs = nli_result.probabilities

        if self.config.enforce_symbolic_overrides and has_symbolic_mismatch:
            # If the passage is completely tangential to the claim (negligible lexical overlap and neutral >= 0.70),
            # disparate topic numbers remain NEUTRAL.
            claim_tokens = [w for w in re.findall(r"\b\w+\b", claim_text.lower()) if len(w) > 3 and w not in {"under", "section", "this", "that", "with", "from"}]
            ev_tokens = set(re.findall(r"\b\w+\b", passage_text.lower()))
            overlap = (sum(1 for t in claim_tokens if t in ev_tokens) / len(claim_tokens)) if claim_tokens else 0.0

            if overlap < 0.15 and probs.neutral >= 0.70 and probs.entailment < 0.15 and probs.contradiction < 0.15:
                local_status = EvidenceVerdictStatus.NEUTRAL.value
            else:
                local_status = EvidenceVerdictStatus.CONTRADICTED.value

            return EvidenceItem(
                passage_id=passage_id,
                source=source,
                dataset=dataset,
                authority_id=authority_id,
                section_id=section_id,
                text=passage_text,
                text_hash=text_hash,
                nli=nli_result.probabilities,
                numerical_check=numerical_result,
                modality_check=modality_result,
                negation_check=negation_result,
                local_status=local_status,
            )

        # 2. In the absence of symbolic mismatches, evaluate NLI thresholds
        probs = nli_result.probabilities
        if (
            probs.entailment >= self.config.entailment_min
            and probs.contradiction <= self.config.contradiction_max_for_entailment
        ):
            local_status = EvidenceVerdictStatus.SUPPORTED.value
        elif (
            probs.contradiction >= self.config.contradiction_min
            and probs.entailment <= self.config.entailment_max_for_contradiction
        ):
            local_status = EvidenceVerdictStatus.CONTRADICTED.value
        else:
            local_status = EvidenceVerdictStatus.NEUTRAL.value

        return EvidenceItem(
            passage_id=passage_id,
            source=source,
            dataset=dataset,
            authority_id=authority_id,
            section_id=section_id,
            text=passage_text,
            text_hash=text_hash,
            nli=nli_result.probabilities,
            numerical_check=numerical_result,
            modality_check=modality_result,
            negation_check=negation_result,
            local_status=local_status,
        )

    def aggregate(
        self,
        claim_id: str,
        claim_text: str,
        evidence_items: List[EvidenceItem],
        claim_atomicity: str = ClaimAtomicity.ATOMIC.value,
        subclaim_verdicts: Optional[List[str]] = None,
    ) -> Tuple[str, str, Optional[str], AggregationSummary]:
        """
        Deterministically aggregates multiple evidence items according to strict HALO priority:
        1. No usable evidence -> UNRESOLVED
        2. Strong support + Strong contradiction from DISTINCT passages -> CONFLICTED
        3. Validated contradiction signal -> CONTRADICTED
        4. Strong support with no contradiction -> SUPPORTED
        5. Compound claim with partial support -> PARTIALLY_SUPPORTED
        6. Insufficient / tangential -> NEUTRAL
        """
        if not evidence_items:
            summary = AggregationSummary(unresolved_count=1)
            return (
                EvidenceVerdictStatus.UNRESOLVED.value,
                "No usable or verified evidence passages available for claim.",
                None,
                summary,
            )

        support_items = [it for it in evidence_items if it.local_status == EvidenceVerdictStatus.SUPPORTED.value]
        contradiction_items = [it for it in evidence_items if it.local_status == EvidenceVerdictStatus.CONTRADICTED.value]
        neutral_items = [it for it in evidence_items if it.local_status == EvidenceVerdictStatus.NEUTRAL.value]
        unresolved_items = [it for it in evidence_items if it.local_status == EvidenceVerdictStatus.UNRESOLVED.value]

        support_count = len(support_items)
        contradiction_count = len(contradiction_items)
        neutral_count = len(neutral_items)
        unresolved_count = len(unresolved_items)

        # 1. User Correction #7: Strict CONFLICTED definition
        # Must have support AND contradiction from at least two DISTINCT passage IDs
        if support_count > 0 and contradiction_count > 0:
            support_pids = {it.passage_id for it in support_items}
            contra_pids = {it.passage_id for it in contradiction_items}

            # Conflict requires different passages (passage_id_A != passage_id_B)
            # A single passage can never conflict with itself
            distinct_passages = support_pids.symmetric_difference(contra_pids) or (support_pids != contra_pids)
            if distinct_passages or len(support_pids.union(contra_pids)) >= 2:
                summary = AggregationSummary(
                    support_count=support_count,
                    contradiction_count=contradiction_count,
                    neutral_count=neutral_count,
                    unresolved_count=unresolved_count,
                    conflict=True,
                )
                best_id = support_items[0].passage_id
                reason = (
                    f"Semantic evidence conflict: Distinct authoritative passages provide conflicting evidence. "
                    f"Passages supporting: {sorted(list(support_pids))}; "
                    f"Passages contradicting: {sorted(list(contra_pids))}."
                )
                return EvidenceVerdictStatus.CONFLICTED.value, reason, best_id, summary

        # 2. Validated Contradiction Priority
        if contradiction_count > 0:
            # Select clearest contradiction as best evidence
            best_contra = max(contradiction_items, key=lambda it: it.nli.contradiction)
            summary = AggregationSummary(
                support_count=support_count,
                contradiction_count=contradiction_count,
                neutral_count=neutral_count,
                unresolved_count=unresolved_count,
                conflict=False,
            )
            reasons = []
            if best_contra.numerical_check.status == CheckStatus.MISMATCH.value:
                reasons.append(best_contra.numerical_check.details)
            if best_contra.modality_check.status == CheckStatus.MISMATCH.value:
                reasons.append(best_contra.modality_check.details)
            if best_contra.negation_check.status == CheckStatus.MISMATCH.value:
                reasons.append(best_contra.negation_check.details)
            if not reasons:
                reasons.append(f"NLI semantic contradiction (score {best_contra.nli.contradiction:.3f}).")

            reason_str = f"Authoritative passage '{best_contra.passage_id}' contradicts claim: " + " ".join(reasons)
            return EvidenceVerdictStatus.CONTRADICTED.value, reason_str, best_contra.passage_id, summary

        # 3. Strong Support Priority
        if support_count > 0:
            best_supp = max(support_items, key=lambda it: it.nli.entailment)
            summary = AggregationSummary(
                support_count=support_count,
                contradiction_count=0,
                neutral_count=neutral_count,
                unresolved_count=unresolved_count,
                conflict=False,
            )
            reason_str = (
                f"Authoritative passage '{best_supp.passage_id}' provides sufficient semantic evidence for claim "
                f"(NLI entailment score: {best_supp.nli.entailment:.3f}, contradiction: {best_supp.nli.contradiction:.3f})."
            )
            return EvidenceVerdictStatus.SUPPORTED.value, reason_str, best_supp.passage_id, summary

        # 4. User Correction #6: Strict PARTIALLY_SUPPORTED
        # Only emitted when upstream representation explicitly declared COMPOUND claim with subclaims
        if claim_atomicity == ClaimAtomicity.COMPOUND.value and subclaim_verdicts:
            sub_supp = sum(1 for v in subclaim_verdicts if v == EvidenceVerdictStatus.SUPPORTED.value)
            if sub_supp > 0 and sub_supp < len(subclaim_verdicts):
                summary = AggregationSummary(
                    support_count=support_count,
                    contradiction_count=contradiction_count,
                    neutral_count=neutral_count,
                    unresolved_count=unresolved_count,
                    conflict=False,
                )
                reason_str = (
                    f"Compound claim partial support: {sub_supp}/{len(subclaim_verdicts)} subclaims "
                    "supported by evidence passage."
                )
                best_id = evidence_items[0].passage_id
                return EvidenceVerdictStatus.PARTIALLY_SUPPORTED.value, reason_str, best_id, summary

        # 5. Tangential / Insufficient Evidence -> NEUTRAL
        summary = AggregationSummary(
            support_count=0,
            contradiction_count=0,
            neutral_count=neutral_count,
            unresolved_count=unresolved_count,
            conflict=False,
        )
        best_id = evidence_items[0].passage_id if evidence_items else None
        reason_str = (
            f"Evidence passages provide insufficient textual entailment to corroborate claim "
            f"(neutral score: {evidence_items[0].nli.neutral:.3f})."
        )
        return EvidenceVerdictStatus.NEUTRAL.value, reason_str, best_id, summary
