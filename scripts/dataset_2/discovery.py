"""
HALO Dataset 2: Metadata Discovery Engine
========================================
Discovers company law candidates across registered legal sources,
applies multi-layer deduplication, and records candidate_judgments.jsonl.
"""

import os
import json
import logging
from typing import List, Dict, Any

from .models import CandidateJudgment, LifecycleState
from .adapters.sc_adapter import SupremeCourtAdapter
from .adapters.hc_adapter import HighCourtAdapter
from .adapters.nclat_adapter import NCLATAdapter
from .adapters.local_adapter import LocalReservoirAdapter
from .deduplicator import JudgmentDeduplicator

logger = logging.getLogger("halo.dataset_2.discovery")

REGISTRY_PATH = "Data/dataset2/discovery/source_registry.json"
CANDIDATES_OUTPUT_PATH = "Data/dataset2/discovery/candidate_judgments.jsonl"
DEDUP_LOG_PATH = "Data/dataset2/discovery/deduplication_log.json"

CORPORATE_LAW_TERMS = [
    # Statutory terms (2013 & 1956 continuity)
    "companies act",
    "company",
    "corporate",
    "section 241",
    "section 242",
    "section 244",
    "section 135",
    "section 188",
    "section 164",
    "section 166",
    "section 230",
    "section 232",
    "section 248",
    "section 447",
    "section 397",
    "section 398",
    # Substantive corporate doctrines
    "oppression",
    "mismanagement",
    "related party transaction",
    "corporate social responsibility",
    "disqualification of director",
    "fiduciary duty",
    "corporate veil",
    "merger",
    "amalgamation",
    "strike off",
    "national company law",
    "nclat",
    "nclt"
]


def load_adapters(registry_path: str = REGISTRY_PATH) -> List[Any]:
    if not os.path.exists(registry_path):
        raise FileNotFoundError(f"Source registry missing at {registry_path}")

    with open(registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)

    adapters = []
    for src in registry.get("sources", []):
        if not src.get("enabled", True):
            continue
        sid = src.get("source_id", "")
        if sid == "SRC_SC_REGISTRY":
            adapters.append(SupremeCourtAdapter(src))
        elif sid == "SRC_HC_REGISTRY":
            adapters.append(HighCourtAdapter(src))
        elif sid == "SRC_NCLAT_REGISTRY":
            adapters.append(NCLATAdapter(src))
        elif sid == "SRC_LOCAL_RESERVOIR":
            adapters.append(LocalReservoirAdapter(src))

    return adapters


def run_discovery(
    query_terms: List[str] = CORPORATE_LAW_TERMS,
    target_count: int = 60
) -> List[CandidateJudgment]:
    """Runs metadata discovery across all active adapters with forum quotas."""
    logger.info("=" * 65)
    logger.info("   HALO DATASET 2: METADATA DISCOVERY & CANDIDATE REGISTRY   ")
    logger.info("=" * 65)

    adapters = load_adapters()
    all_candidates: List[CandidateJudgment] = []

    for adapter in adapters:
        logger.info(f"\n[*] Querying {adapter.name} ({adapter.source_authority})...")
        try:
            if "SUPREME" in adapter.court:
                quota = 30
            elif "HIGH" in adapter.court:
                quota = 15
            elif "NCLAT" in adapter.court:
                quota = 12
            else:
                quota = 10

            cands = adapter.discover_candidates(query_terms, max_results=quota)
            logger.info(f"    [+] Discovered {len(cands)} raw candidates from {adapter.source_id}")
            all_candidates.extend(cands)
        except Exception as e:
            logger.error(f"    [-] Adapter {adapter.source_id} failed: {e}")

    logger.info(f"\n[+] Total raw candidates discovered across all sources: {len(all_candidates)}")

    # Run Deduplication
    logger.info("\n[*] Applying Multi-Layer Deduplication...")
    deduplicator = JudgmentDeduplicator(log_path=DEDUP_LOG_PATH)
    unique_candidates, duplicates = deduplicator.deduplicate(all_candidates)

    logger.info(f"    [+] Unique candidates:      {len(unique_candidates)}")
    logger.info(f"    [-] Duplicate candidates:   {len(duplicates)}")
    logger.info(f"    [+] Deduplication audit saved to: {DEDUP_LOG_PATH}")

    # Write candidate_judgments.jsonl
    os.makedirs(os.path.dirname(CANDIDATES_OUTPUT_PATH), exist_ok=True)
    with open(CANDIDATES_OUTPUT_PATH, "w", encoding="utf-8") as f:
        for cand in unique_candidates:
            f.write(cand.model_dump_json() + "\n")

    logger.info(f"[+] Candidate Registry written to: {CANDIDATES_OUTPUT_PATH}")
    return unique_candidates


if __name__ == "__main__":
    run_discovery()
