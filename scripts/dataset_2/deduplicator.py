"""
HALO Dataset 2: Multi-Layer Deduplication Engine
================================================
Deduplicates judicial candidates across normalized case numbers,
parties, decision dates, citations, and text fingerprints.
Logs all merge/rejection operations to deduplication_log.json.
"""

import re
import json
import logging
import hashlib
from typing import List, Dict, Any, Tuple
from .models import CandidateJudgment, LifecycleState

logger = logging.getLogger("halo.dataset_2.deduplicator")


class JudgmentDeduplicator:
    """Multi-fingerprint deduplicator for legal candidates."""

    def __init__(self, log_path: str = "Data/dataset2/discovery/deduplication_log.json"):
        self.log_path = log_path
        self.seen_case_numbers: Dict[str, str] = {}    # normalized_case_no -> candidate_id
        self.seen_date_parties: Dict[str, str] = {}    # (date, normalized_parties) -> candidate_id
        self.seen_citations: Dict[str, str] = {}       # normalized_citation -> candidate_id
        self.dedup_log: List[Dict[str, Any]] = []

    def _normalize_case_no(self, case_no: str) -> str:
        """Normalizes case number string (e.g. 'Civil Appeal No. 7157 of 2008' -> 'ca_7157_2008')."""
        if not case_no:
            return ""
        s = case_no.lower()
        s = re.sub(r"[^a-z0-9]", "_", s)
        s = re.sub(r"_+", "_", s).strip("_")
        return s

    def _normalize_parties(self, title: str) -> str:
        """Extracts and normalizes core corporate names from title."""
        if not title:
            return ""
        s = title.lower()
        s = re.sub(r"\b(m/s|ltd|limited|pvt|private|corp|corporation|inc|anr|ors|versus|v\.)\b", " ", s)
        s = re.sub(r"[^a-z0-9]", "", s)
        return s[:32]

    def _normalize_citation(self, cit: str) -> str:
        if not cit:
            return ""
        return re.sub(r"[^a-z0-9]", "", cit.lower())

    def deduplicate(self, candidates: List[CandidateJudgment]) -> Tuple[List[CandidateJudgment], List[CandidateJudgment]]:
        """
        Processes candidate list, returning (unique_candidates, duplicate_candidates).
        Updates candidate status and generates detailed audit log.
        """
        unique: List[CandidateJudgment] = []
        duplicates: List[CandidateJudgment] = []

        for cand in candidates:
            cand_id = cand.candidate_id
            case_no_norm = self._normalize_case_no(cand.case_number or "")
            parties_norm = self._normalize_parties(cand.case_title)
            date_str = cand.decision_date or "unknown_date"
            date_parties_key = f"{date_str}:{parties_norm}"

            is_dup = False
            dup_reason = ""
            existing_id = ""

            # Check 1: Normalized case number
            if case_no_norm and len(case_no_norm) > 4:
                if case_no_norm in self.seen_case_numbers:
                    is_dup = True
                    existing_id = self.seen_case_numbers[case_no_norm]
                    dup_reason = f"Exact normalized case number match: '{case_no_norm}' (Original: {existing_id})"
                else:
                    self.seen_case_numbers[case_no_norm] = cand_id

            # Check 2: Date + Parties fingerprint
            if not is_dup and parties_norm and len(parties_norm) > 6 and date_str != "unknown_date":
                if date_parties_key in self.seen_date_parties:
                    is_dup = True
                    existing_id = self.seen_date_parties[date_parties_key]
                    dup_reason = f"Exact date & party fingerprint match: '{date_parties_key}' (Original: {existing_id})"
                else:
                    self.seen_date_parties[date_parties_key] = cand_id

            # Check 3: Citation match
            if not is_dup:
                for cit in cand.citations:
                    norm_cit = self._normalize_citation(cit)
                    if norm_cit and len(norm_cit) > 5:
                        if norm_cit in self.seen_citations:
                            is_dup = True
                            existing_id = self.seen_citations[norm_cit]
                            dup_reason = f"Exact legal citation match: '{norm_cit}' (Original: {existing_id})"
                            break
                        else:
                            self.seen_citations[norm_cit] = cand_id

            if is_dup:
                cand.lifecycle_state = LifecycleState.REJECTED_DUPLICATE
                cand.selection_status = "REJECTED_DUPLICATE"
                duplicates.append(cand)
                self.dedup_log.append({
                    "action": "REJECT_DUPLICATE",
                    "duplicate_candidate_id": cand_id,
                    "existing_candidate_id": existing_id,
                    "reason": dup_reason,
                    "case_title": cand.case_title,
                    "case_number": cand.case_number
                })
                logger.info(f"Duplicate rejected: {cand_id} -> {existing_id} ({dup_reason})")
            else:
                unique.append(cand)

        # Write deduplication log to disk
        try:
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump({
                    "total_candidates_processed": len(candidates),
                    "unique_count": len(unique),
                    "duplicates_rejected": len(duplicates),
                    "log": self.dedup_log
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write deduplication log: {e}")

        return unique, duplicates
