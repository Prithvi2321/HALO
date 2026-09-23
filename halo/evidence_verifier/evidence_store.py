"""
HALO Evidence Verifier: Canonical Evidence Store
================================================
Protocol: v1.0-FROZEN
Loads and serves authoritative D1 (statutory) and D2 (judicial) passages strictly read-only.
Enforces that Evidence Verifier consumes only resolved, canonical passage IDs.
Never modifies corpora and never performs citation-existence heuristics.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Any
import hashlib
import json
import os
import threading

from halo.evidence_verifier.config import EvidenceVerifierConfig
from halo.evidence_verifier.exceptions import CorpusAccessError, MalformedEvidenceError


@dataclass
class CanonicalPassageRecord:
    """Immutable authoritative passage representation."""
    passage_id: str
    text: str
    dataset: str
    source: str
    authority_id: Optional[str] = None
    section_id: Optional[str] = None
    text_hash: str = ""
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passage_id": self.passage_id,
            "text": self.text,
            "dataset": self.dataset,
            "source": self.source,
            "authority_id": self.authority_id,
            "section_id": self.section_id,
            "text_hash": self.text_hash,
            "metadata": self.metadata or {},
        }


class EvidenceStore:
    """Thread-safe, read-only canonical passage index for D1 and D2."""

    _instance: Optional["EvidenceStore"] = None
    _lock = threading.Lock()

    def __init__(self, config: Optional[EvidenceVerifierConfig] = None):
        self.config = config or EvidenceVerifierConfig()
        self._passages: Dict[str, CanonicalPassageRecord] = {}
        self._loaded = False
        self._load_lock = threading.Lock()
        self._load_canonical_passages()

    @classmethod
    def get_instance(cls, config: Optional[EvidenceVerifierConfig] = None) -> "EvidenceStore":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(config)
            return cls._instance

    @classmethod
    def reset_instance(cls):
        with cls._lock:
            cls._instance = None

    def _load_canonical_passages(self):
        with self._load_lock:
            if self._loaded:
                return

            # 1. Load D1 (Companies Act 2013 Statutory Passages)
            d1_path = Path(self.config.d1_passages_path)
            if not d1_path.exists():
                # Fallback check relative to repo root
                alt_d1 = self.config.repo_root / "data" / "dataset_1" / "final" / "companies_act_2013_passages.jsonl"
                if alt_d1.exists():
                    d1_path = alt_d1

            if d1_path.exists():
                self._load_d1(d1_path)

            # 2. Load D2 (Supreme Court & NCLAT Judicial Passages)
            d2_path = Path(self.config.d2_passages_path)
            if not d2_path.exists():
                alt_d2 = self.config.repo_root / "data" / "dataset2" / "canonical" / "passages.jsonl"
                if alt_d2.exists():
                    d2_path = alt_d2

            if d2_path.exists():
                self._load_d2(d2_path)

            self._loaded = True

    def _load_d1(self, path: Path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line_idx, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as e:
                        raise MalformedEvidenceError(f"Malformed JSON in D1 at line {line_idx}: {e}")

                    pid = record.get("passage_id")
                    if not pid or not isinstance(pid, str):
                        continue

                    # Prefer canonical_text, fallback to text
                    text = (record.get("canonical_text") or record.get("text") or "").strip()
                    if not text:
                        continue

                    sec_id = record.get("section_id")
                    authority_id = f"ACT_COMPANIES_2013_SEC_{sec_id}" if sec_id else "ACT_COMPANIES_2013"
                    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

                    self._passages[pid] = CanonicalPassageRecord(
                        passage_id=pid,
                        text=text,
                        dataset="D1",
                        source="Companies Act, 2013",
                        authority_id=authority_id,
                        section_id=str(sec_id) if sec_id else None,
                        text_hash=text_hash,
                        metadata={
                            "document_id": record.get("document_id"),
                            "subsection_id": record.get("subsection_id"),
                            "enactment_date": record.get("enactment_date"),
                            "status": record.get("status"),
                        },
                    )
        except Exception as e:
            if isinstance(e, MalformedEvidenceError):
                raise
            raise CorpusAccessError(f"Failed to load canonical D1 passages from {path}: {e}")

    def _load_d2(self, path: Path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line_idx, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as e:
                        raise MalformedEvidenceError(f"Malformed JSON in D2 at line {line_idx}: {e}")

                    pid = record.get("passage_id")
                    if not pid or not isinstance(pid, str):
                        continue

                    text = (record.get("text") or "").strip()
                    if not text:
                        continue

                    court = record.get("court") or "Supreme Court of India"
                    doc_id = record.get("document_id")
                    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

                    self._passages[pid] = CanonicalPassageRecord(
                        passage_id=pid,
                        text=text,
                        dataset="D2",
                        source=court,
                        authority_id=str(doc_id) if doc_id else None,
                        section_id=None,
                        text_hash=text_hash,
                        metadata={
                            "court": court,
                            "citation": record.get("citation"),
                            "topics": record.get("topics"),
                            "document_id": doc_id,
                        },
                    )
        except Exception as e:
            if isinstance(e, MalformedEvidenceError):
                raise
            raise CorpusAccessError(f"Failed to load canonical D2 passages from {path}: {e}")

    def get_passage(self, passage_id: str) -> Optional[CanonicalPassageRecord]:
        """Resolves authoritative passage by unique identifier. Returns None if not found."""
        if not passage_id or not isinstance(passage_id, str):
            return None
        return self._passages.get(passage_id.strip())

    def contains(self, passage_id: str) -> bool:
        """Checks if passage_id exists in canonical index."""
        if not passage_id or not isinstance(passage_id, str):
            return False
        return passage_id.strip() in self._passages

    @property
    def total_passages(self) -> int:
        return len(self._passages)

    @property
    def d1_passage_count(self) -> int:
        return sum(1 for p in self._passages.values() if p.dataset == "D1")

    @property
    def d2_passage_count(self) -> int:
        return sum(1 for p in self._passages.values() if p.dataset == "D2")
