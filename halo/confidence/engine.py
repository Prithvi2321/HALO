"""
Confidence Engine Subsystem
===========================
Protocol: v1.0-FROZEN
Computes mathematical, evidence-grounded confidence scores with zero LLM self-reflection.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional


@dataclass
class ClaimConfidenceScore:
    claim_id: str
    citation_score: float
    evidence_score: float
    temporal_score: float
    aggregate_confidence: float
    decision: str  # ACCEPT | QUALIFY | REJECT

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AnswerConfidenceScore:
    mean_claim_confidence: float
    min_claim_confidence: float
    supported_claim_ratio: float
    overall_confidence: float
    is_authoritative: bool
    quarantine_recommended: bool
    per_claim_scores: List[ClaimConfidenceScore] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ConfidenceEngine:
    """Computes deterministic verification confidence scores across pipeline subsystems."""

    CITATION_WEIGHTS = {
        "SUPPORTED": 1.0,
        "PARTIALLY_SUPPORTED": 0.7,
        "FLAGGED": 0.4,
        "METADATA_MISMATCH": 0.4,
        "CONTRADICTED": 0.0,
        "FABRICATED_CITATION": 0.0,
        "UNSUPPORTED": 0.0,
    }

    EVIDENCE_WEIGHTS = {
        "SUPPORTED": 1.0,
        "PARTIALLY_SUPPORTED": 0.5,
        "UNSUPPORTED": 0.0,
        "CONTRADICTED": 0.0,
    }

    TEMPORAL_WEIGHTS = {
        "CURRENT": 1.0,
        "IN_FORCE": 1.0,
        "AMENDED": 0.5,
        "HISTORICAL": 0.0,
        "REPEALED": 0.0,
        "SUPERSEDED": 0.0,
    }

    def compute_claim_confidence(
        self,
        claim_id: str,
        citation_status: str,
        evidence_status: str,
        temporal_status: str = "CURRENT",
        raw_entailment_score: Optional[float] = None,
    ) -> ClaimConfidenceScore:
        """
        Calculates multiplicative weakest-link confidence for an atomic proposition.
        Formula: Conf = CitScore * EvScore * TempScore
        """
        c_cit = self.CITATION_WEIGHTS.get(citation_status, 0.0)

        # Base evidence weight modified by entailment score if supported
        base_ev = self.EVIDENCE_WEIGHTS.get(evidence_status, 0.0)
        if evidence_status == "SUPPORTED" and raw_entailment_score is not None:
            c_ev = max(0.5, min(1.0, float(raw_entailment_score)))
        else:
            c_ev = base_ev

        c_temp = self.TEMPORAL_WEIGHTS.get(temporal_status, 1.0)

        # Multiplicative integration: Any zero collapses confidence to zero
        agg_conf = float(round(c_cit * c_ev * c_temp, 4))

        # Decision thresholding
        if agg_conf >= 0.75:
            decision = "ACCEPT"
        elif agg_conf >= 0.30:
            decision = "QUALIFY"
        else:
            decision = "REJECT"

        return ClaimConfidenceScore(
            claim_id=claim_id,
            citation_score=float(round(c_cit, 3)),
            evidence_score=float(round(c_ev, 3)),
            temporal_score=float(round(c_temp, 3)),
            aggregate_confidence=agg_conf,
            decision=decision,
        )

    def compute_answer_confidence(
        self,
        claim_scores: List[ClaimConfidenceScore],
    ) -> AnswerConfidenceScore:
        """Aggregates claim confidence scores into an answer-level confidence assessment."""
        if not claim_scores:
            return AnswerConfidenceScore(
                mean_claim_confidence=0.0,
                min_claim_confidence=0.0,
                supported_claim_ratio=0.0,
                overall_confidence=0.0,
                is_authoritative=False,
                quarantine_recommended=True,
                per_claim_scores=[],
            )

        confs = [c.aggregate_confidence for c in claim_scores]
        mean_conf = sum(confs) / len(confs)
        min_conf = min(confs)
        accepted_count = sum(1 for c in claim_scores if c.decision == "ACCEPT")
        supported_ratio = accepted_count / len(claim_scores)

        # Answer confidence formula: penalizes answers containing unverified/rejected claims
        has_rejected = any(c.decision == "REJECT" for c in claim_scores)
        quarantine = has_rejected or (supported_ratio < 0.7)

        # Weighted combination: 60% mean confidence, 40% min confidence
        overall = float(round(0.6 * mean_conf + 0.4 * min_conf, 4))
        if has_rejected:
            overall = min(overall, 0.45)

        is_auth = (overall >= 0.80) and (not has_rejected) and (supported_ratio == 1.0)

        return AnswerConfidenceScore(
            mean_claim_confidence=float(round(mean_conf, 4)),
            min_claim_confidence=float(round(min_conf, 4)),
            supported_claim_ratio=float(round(supported_ratio, 4)),
            overall_confidence=overall,
            is_authoritative=is_auth,
            quarantine_recommended=quarantine,
            per_claim_scores=claim_scores,
        )
