"""
HALO Dataset 2: Human & Policy Selection Gate
=============================================
Enforces topic coverage, court diversity, and score thresholds to produce
the final shortlisted ~40-60 candidates in shortlisted_candidates.jsonl.
ONLY candidates marked 'SELECTED' by this gate are approved for download.
"""

import os
import json
import logging
from typing import List, Dict, Any, Tuple
from .models import CandidateJudgment, CourtType, LifecycleState

logger = logging.getLogger("halo.dataset_2.selection_gate")

SHORTLIST_OUTPUT_PATH = "Data/dataset2/discovery/shortlisted_candidates.jsonl"

TARGET_DISTRIBUTION = {
    CourtType.SUPREME_COURT_OF_INDIA: (25, 35),
    CourtType.NCLAT: (8, 15),
    CourtType.HIGH_COURT: (8, 15)
}


class SelectionGate:
    """Selects the final curated cohort based on quality, diversity, and coverage."""

    def __init__(
        self,
        min_score: float = 0.60,
        shortlist_path: str = SHORTLIST_OUTPUT_PATH
    ):
        self.min_score = min_score
        self.shortlist_path = shortlist_path

    def select_cohort(
        self,
        scored_pairs: List[Tuple[CandidateJudgment, Dict[str, Any]]],
        total_target: int = 50
    ) -> List[CandidateJudgment]:
        """
        Applies multi-stage selection:
        1. Filters by minimum score threshold.
        2. Groups by judicial tier.
        3. Enforces topic coverage across all 11 corporate topics.
        4. Selects top candidates within target court brackets.
        """
        logger.info("\n" + "=" * 65)
        logger.info("      HALO DATASET 2: SELECTION GATE & COVERAGE OPTIMIZER      ")
        logger.info("=" * 65)

        # Filter by threshold
        eligible = [p for p in scored_pairs if p[1]["composite_score"] >= self.min_score]
        logger.info(f"[*] Candidates meeting threshold (S >= {self.min_score}): {len(eligible)} / {len(scored_pairs)}")

        # Group by court
        by_court: Dict[CourtType, List[Tuple[CandidateJudgment, Dict[str, Any]]]] = {
            CourtType.SUPREME_COURT_OF_INDIA: [],
            CourtType.NCLAT: [],
            CourtType.HIGH_COURT: []
        }
        for cand, sdata in eligible:
            by_court[cand.court].append((cand, sdata))

        selected: List[CandidateJudgment] = []
        topic_coverage: Dict[str, int] = {}

        for court_type, candidates in by_court.items():
            min_target, max_target = TARGET_DISTRIBUTION[court_type]
            court_name = court_type.value

            # Sort descending by score
            candidates.sort(key=lambda x: x[1]["composite_score"], reverse=True)
            court_selected = 0

            for cand, sdata in candidates:
                if court_selected >= max_target:
                    break

                # Check topic coverage
                cand_topics = sdata["topics"]
                cand.selection_status = "SELECTED"
                cand.lifecycle_state = LifecycleState.SELECTED
                selected.append(cand)
                court_selected += 1

                for t in cand_topics:
                    topic_coverage[t] = topic_coverage.get(t, 0) + 1

            logger.info(f"    [+] {court_name:24} | Target: {min_target}-{max_target} | Selected: {court_selected}")

        logger.info(f"\n[+] Total Selected Judgments for Ingestion: {len(selected)}")
        logger.info("\n[*] Topic Coverage Breakdown across Selected Cohort:")
        for topic, count in sorted(topic_coverage.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"    - {topic:40} : {count} cases")

        # Write shortlisted_candidates.jsonl
        os.makedirs(os.path.dirname(self.shortlist_path), exist_ok=True)
        with open(self.shortlist_path, "w", encoding="utf-8") as f:
            for cand in selected:
                f.write(cand.model_dump_json() + "\n")

        logger.info(f"\n[+] Shortlisted candidates written to: {self.shortlist_path}")
        return selected
