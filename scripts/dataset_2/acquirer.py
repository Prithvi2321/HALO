"""
HALO Dataset 2: Selective Document Acquisition Engine
=====================================================
Downloads ONLY the shortlisted candidates marked 'SELECTED' by the selection gate.
Verifies SHA-256, stores source snapshots, and records raw metadata.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional

from .models import CandidateJudgment, SourceSnapshot, LifecycleState, CourtType
from .discovery import load_adapters

logger = logging.getLogger("halo.dataset_2.acquirer")

SHORTLIST_PATH = "Data/dataset2/discovery/shortlisted_candidates.jsonl"
SOURCE_BASE_DIR = "Data/dataset2/source"
RAW_META_DIR = "Data/dataset2/raw/metadata"


class DocumentAcquirer:
    """Acquires authoritative PDF documents for selected candidates."""

    def __init__(
        self,
        shortlist_path: str = SHORTLIST_PATH,
        source_base_dir: str = SOURCE_BASE_DIR,
        raw_meta_dir: str = RAW_META_DIR
    ):
        self.shortlist_path = shortlist_path
        self.source_base_dir = source_base_dir
        self.raw_meta_dir = raw_meta_dir
        self.adapters = {a.source_id: a for a in load_adapters()}

    def _get_court_subdir(self, court: CourtType) -> str:
        if court == CourtType.SUPREME_COURT_OF_INDIA:
            return "supreme_court"
        elif court == CourtType.NCLAT:
            return "nclat"
        elif court == CourtType.HIGH_COURT:
            return "high_court"
        return "other"

    def acquire_selected(self) -> List[Dict[str, Any]]:
        """Downloads only the selected candidates and returns acquisition ledger."""
        logger.info("\n" + "=" * 65)
        logger.info("       HALO DATASET 2: SELECTIVE DOCUMENT ACQUISITION          ")
        logger.info("=" * 65)

        if not os.path.exists(self.shortlist_path):
            raise FileNotFoundError(f"Shortlisted candidates missing at {self.shortlist_path}")

        selected_candidates: List[CandidateJudgment] = []
        with open(self.shortlist_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    cand = CandidateJudgment.model_validate_json(line)
                    if cand.selection_status == "SELECTED":
                        selected_candidates.append(cand)

        logger.info(f"[*] Total Candidates Approved for Acquisition: {len(selected_candidates)}")
        os.makedirs(self.raw_meta_dir, exist_ok=True)

        acquired_records = []
        for idx, cand in enumerate(selected_candidates, 1):
            logger.info(f"\n[{idx}/{len(selected_candidates)}] Acquiring: {cand.candidate_id} ({cand.court.value})")
            logger.info(f"    Case Title: {cand.case_title[:55]}")

            adapter = self.adapters.get(cand.source_id)
            if not adapter:
                logger.error(f"    [-] No adapter found for source {cand.source_id}")
                continue

            court_sub = self._get_court_subdir(cand.court)
            target_dir = os.path.join(self.source_base_dir, court_sub)

            # Download authoritative document
            snapshot = adapter.download_document(cand, target_dir)
            if snapshot:
                cand.lifecycle_state = LifecycleState.DOCUMENT_ACQUIRED
                logger.info(f"    [+] Acquired PDF: {snapshot.file_size:,} bytes | SHA-256: {snapshot.sha256[:20]}...")

                # Save raw metadata snapshot
                meta_path = os.path.join(self.raw_meta_dir, f"{cand.candidate_id}.json")
                with open(meta_path, "w", encoding="utf-8") as mf:
                    mf.write(cand.model_dump_json(indent=2))

                acquired_records.append({
                    "candidate": cand,
                    "snapshot": snapshot,
                    "pdf_path": os.path.join(target_dir, f"{cand.candidate_id}.pdf")
                })
            else:
                logger.error(f"    [-] Failed to acquire PDF for {cand.candidate_id}")
                cand.lifecycle_state = LifecycleState.REJECTED_UNVERIFIED_SOURCE

        logger.info(f"\n[+] Successfully Acquired {len(acquired_records)} / {len(selected_candidates)} Documents")
        return acquired_records
