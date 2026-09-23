"""
HALO Dataset 2: Abstract Legal Source Adapter
=============================================
Provides a unified contract for querying metadata reservoirs and selectively
acquiring judicial documents from official and secondary legal sources.
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..models import CandidateJudgment, SourceSnapshot, SourceAuthority, CourtType

logger = logging.getLogger("halo.dataset_2.adapters")


class LegalSourceAdapter(ABC):
    """Abstract interface for legal document and metadata sources."""

    def __init__(self, config: Dict[str, Any]):
        self.source_id = config.get("source_id", "UNKNOWN_SOURCE")
        self.name = config.get("name", "Unknown Source")
        self.court = config.get("court", "UNKNOWN_COURT")
        self.source_authority = SourceAuthority(config.get("source_authority", "SECONDARY"))
        self.base_url = config.get("base_url", "")
        self.enabled = config.get("enabled", True)
        self.config = config

    @abstractmethod
    def discover_candidates(
        self,
        query_terms: List[str],
        year_range: Optional[List[int]] = None,
        max_results: int = 100
    ) -> List[CandidateJudgment]:
        """Query the source repository metadata and return matching candidate judgments."""
        pass

    @abstractmethod
    def fetch_metadata(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        """Fetch granular metadata JSON for a single candidate."""
        pass

    @abstractmethod
    def download_document(
        self,
        candidate: CandidateJudgment,
        target_dir: str
    ) -> Optional[SourceSnapshot]:
        """
        Download the authoritative judgment document (PDF), compute SHA-256,
        record HTTP metadata, and return an immutable SourceSnapshot.
        """
        pass
