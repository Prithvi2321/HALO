"""
HALO Dataset 2: Local Reservoir Adapter
======================================
Provides deterministic offline fallback ingestion from local verified storage.
"""

import os
import json
import hashlib
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from .base import LegalSourceAdapter
from ..models import CandidateJudgment, SourceSnapshot, SourceAuthority, CourtType, LifecycleState

logger = logging.getLogger("halo.dataset_2.local_adapter")


class LocalReservoirAdapter(LegalSourceAdapter):
    """Adapter reading from local pre-cached judgment store."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_path = config.get("base_path", "Data/dataset2/raw/local_reservoir")

    def discover_candidates(
        self,
        query_terms: List[str],
        year_range: Optional[List[int]] = None,
        max_results: int = 50
    ) -> List[CandidateJudgment]:
        if not os.path.exists(self.base_path):
            return []

        candidates = []
        for fname in os.listdir(self.base_path):
            if fname.endswith(".json"):
                fpath = os.path.join(self.base_path, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    cand = CandidateJudgment(**data)
                    candidates.append(cand)
                except Exception as e:
                    logger.debug(f"Failed to read local reservoir item {fname}: {e}")
        return candidates

    def fetch_metadata(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        fpath = os.path.join(self.base_path, f"{candidate_id}.json")
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def download_document(
        self,
        candidate: CandidateJudgment,
        target_dir: str
    ) -> Optional[SourceSnapshot]:
        os.makedirs(target_dir, exist_ok=True)
        src_pdf = os.path.join(self.base_path, f"{candidate.candidate_id}.pdf")
        dst_pdf = os.path.join(target_dir, f"{candidate.candidate_id}.pdf")

        if not os.path.exists(src_pdf):
            return None

        with open(src_pdf, "rb") as f:
            data = f.read()

        with open(dst_pdf, "wb") as f:
            f.write(data)

        sha256 = hashlib.sha256(data).hexdigest()
        file_size = len(data)

        return SourceSnapshot(
            source_id=self.source_id,
            source_authority=self.source_authority,
            source_url=f"file:///{os.path.abspath(src_pdf)}",
            retrieval_timestamp=datetime.utcnow().isoformat() + "Z",
            http_metadata={"status_code": 200, "content_length": file_size},
            file_size=file_size,
            sha256=sha256,
            license=self.config.get("licensing", "Local Curated")
        )
