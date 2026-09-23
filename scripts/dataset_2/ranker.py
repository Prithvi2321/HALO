"""
HALO Dataset 2: Candidate Ranking & Selection Scoring Engine
============================================================
Evaluates candidates across the 7 weighted criteria and 11-topic rubric.
Outputs selection_scores.jsonl.
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Tuple
from .models import CandidateJudgment, SourceAuthority, CourtType

logger = logging.getLogger("halo.dataset_2.ranker")

SELECTION_SCORES_PATH = "Data/dataset2/discovery/selection_scores.jsonl"

TOPIC_KEYWORDS = {
    "Oppression & Mismanagement": ["241", "242", "244", "397", "398", "oppression", "mismanagement"],
    "Related-Party Transactions": ["188", "184", "189", "related party", "related-party", "arm's length"],
    "Director Liability & Disqualification": ["164", "166", "167", "149", "disqualification of director", "director's duty", "fiduciary"],
    "Corporate Governance & Board Powers": ["173", "177", "178", "179", "audit committee", "board of directors", "independent director"],
    "Corporate Social Responsibility": ["135", "csr", "schedule vii", "corporate social responsibility"],
    "Shareholder Rights & Class Actions": ["47", "100", "108", "245", "voting rights", "requisition", "class action"],
    "Incorporation & Corporate Veil": ["corporate veil", "alter ego", "separate legal entity", "incorporation", "shell company"],
    "Mergers, Amalgamations & Arrangements": ["230", "231", "232", "391", "394", "compromise", "amalgamation", "merger"],
    "Corporate Fraud & Severe Penalties": ["447", "448", "sfio", "fraud", "serious fraud investigation"],
    "Tribunal & Appellate Jurisdiction": ["408", "410", "420", "421", "430", "nclt", "nclat", "jurisdiction of civil court"],
    "General Statutory Interpretation": ["companies act", "statutory interpretation", "ultra vires", "company law"]
}


class CandidateRanker:
    """Computes multi-factor selection scores and topic assignments."""

    def __init__(self, scores_output_path: str = SELECTION_SCORES_PATH):
        self.scores_output_path = scores_output_path

    def classify_topics(self, cand: CandidateJudgment) -> List[str]:
        """Classifies a candidate into one or more of the 11 topics."""
        combined_text = f"{cand.case_title} {cand.case_number or ''} {' '.join(cand.discovery_terms)} {' '.join(cand.citations)}".lower()
        matched_topics = []
        for topic, terms in TOPIC_KEYWORDS.items():
            for t in terms:
                if t in combined_text:
                    matched_topics.append(topic)
                    break
        if not matched_topics:
            matched_topics = ["General Statutory Interpretation"]
        return matched_topics

    def score_candidate(self, cand: CandidateJudgment, topic_counts: Dict[str, int]) -> Dict[str, Any]:
        """Calculates granular component scores and final weighted score."""
        combined_text = f"{cand.case_title} {cand.case_number or ''} {' '.join(cand.discovery_terms)} {' '.join(cand.citations)}".lower()

        # 1. Statutory Relevance (w=0.25)
        statutory_hits = sum(1 for kw in ["section 241", "section 188", "section 135", "section 164", "section 230", "section 447", "companies act"] if kw in combined_text)
        statutory_score = min(1.0, 0.4 + (statutory_hits * 0.15))

        # 2. Legal Reasoning Depth (w=0.20)
        # Higher score if not an interlocutory/daily order
        is_substantive = not any(w in combined_text for w in ["adjournment", "notice issue", "daily order", "interim relief only"])
        reasoning_score = 0.85 if is_substantive else 0.40

        # 3. Precedential Significance (w=0.15)
        has_neutral = any("insc" in c.lower() for c in cand.citations)
        has_scr = any("s.c.r" in c.lower() or "scr" in c.lower() for c in cand.citations)
        has_compcas = any("comp cas" in c.lower() or "scl" in c.lower() for c in cand.citations)
        precedence_score = 0.50
        if has_neutral: precedence_score += 0.25
        if has_scr or has_compcas: precedence_score += 0.25
        precedence_score = min(1.0, precedence_score)

        # 4. Citation Network Value (w=0.10)
        cit_score = min(1.0, len(cand.citations) * 0.40)

        # 5. Factual & Topic Diversity (w=0.10)
        topics = self.classify_topics(cand)
        # Bonus for underrepresented topics
        least_pop = min(topic_counts.get(t, 0) for t in topics)
        diversity_score = max(0.4, 1.0 - (least_pop * 0.10))

        # 6. Statutory Section Coverage (w=0.10)
        # Bonus for core Dataset 1 sections: §135, §188, §241, §242, §447
        core_hits = sum(1 for s in ["135", "188", "241", "242", "447"] if s in combined_text)
        coverage_score = min(1.0, 0.5 + (core_hits * 0.25))

        # 7. Source Authority (w=0.10)
        if cand.source_authority == SourceAuthority.OFFICIAL:
            authority_score = 1.0
        elif cand.source_authority == SourceAuthority.SECONDARY:
            authority_score = 0.85
        else:
            authority_score = 0.50

        # Composite weighted score
        composite = (
            (statutory_score * 0.25) +
            (reasoning_score * 0.20) +
            (precedence_score * 0.15) +
            (cit_score * 0.10) +
            (diversity_score * 0.10) +
            (coverage_score * 0.10) +
            (authority_score * 0.10)
        )

        return {
            "candidate_id": cand.candidate_id,
            "case_title": cand.case_title,
            "court": cand.court.value,
            "decision_date": cand.decision_date,
            "topics": topics,
            "component_scores": {
                "statutory_relevance": round(statutory_score, 3),
                "reasoning_depth": round(reasoning_score, 3),
                "precedential_significance": round(precedence_score, 3),
                "citation_network": round(cit_score, 3),
                "topic_diversity": round(diversity_score, 3),
                "statutory_coverage": round(coverage_score, 3),
                "source_authority": round(authority_score, 3)
            },
            "composite_score": round(composite, 4)
        }

    def rank_candidates(self, candidates: List[CandidateJudgment]) -> List[Tuple[CandidateJudgment, Dict[str, Any]]]:
        """Ranks all candidates, updates candidate objects, and writes scores."""
        topic_counts: Dict[str, int] = {}
        # Pre-pass to estimate topic distribution
        for c in candidates:
            for t in self.classify_topics(c):
                topic_counts[t] = topic_counts.get(t, 0) + 1

        scored_pairs = []
        for c in candidates:
            score_data = self.score_candidate(c, topic_counts)
            c.relevance_score = score_data["composite_score"]
            c.topic_tags = score_data["topics"]
            scored_pairs.append((c, score_data))

        # Sort descending by composite score
        scored_pairs.sort(key=lambda x: x[1]["composite_score"], reverse=True)

        # Write selection_scores.jsonl
        os.makedirs(os.path.dirname(self.scores_output_path), exist_ok=True)
        with open(self.scores_output_path, "w", encoding="utf-8") as f:
            for _, sdata in scored_pairs:
                f.write(json.dumps(sdata) + "\n")

        logger.info(f"[+] Selection scores written to: {self.scores_output_path}")
        return scored_pairs
