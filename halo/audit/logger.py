"""
Audit Logger Subsystem
======================
Protocol: v1.0-FROZEN
Provides cryptographic audit trail logging, persistence, and retrieval for HALO.
"""

import datetime
import hashlib
import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional


@dataclass
class AuditRecord:
    audit_id: str
    timestamp: str
    query: str
    raw_answer: str
    claims: List[Dict[str, Any]]
    verifications: List[Dict[str, Any]]
    confidence: Dict[str, Any]
    verdict: Dict[str, Any]
    content_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AuditLogger:
    """Logs and indexes all verification decisions with SHA-256 cryptographic integrity."""

    def __init__(self, log_path: str = "experiments/runs/halo/audit_store.jsonl"):
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        self._cache: Dict[str, AuditRecord] = {}
        self._load_cache()

    def _load_cache(self):
        if os.path.exists(self.log_path):
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            aid = data.get("audit_id")
                            if aid:
                                self._cache[aid] = AuditRecord(**data)
                        except Exception:
                            continue

    def _compute_hash(self, payload: Dict[str, Any]) -> str:
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def log_verification(
        self,
        query: str,
        raw_answer: str,
        claims: List[Any],
        verifications: List[Any],
        confidence: Any,
        verdict: Any,
    ) -> AuditRecord:
        """Constructs, seals, persists, and caches a query audit record."""
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        rand_id = uuid.uuid4().hex[:8]
        audit_id = f"AUD-{datetime.date.today().strftime('%Y%m%d')}-{rand_id}"

        claims_dict = [c.to_dict() if hasattr(c, "to_dict") else c for c in claims]
        verif_dict = [v.to_dict() if hasattr(v, "to_dict") else v for v in verifications]
        conf_dict = confidence.to_dict() if hasattr(confidence, "to_dict") else (confidence or {})
        verdict_dict = verdict.to_dict() if hasattr(verdict, "to_dict") else (verdict or {})

        payload = {
            "audit_id": audit_id,
            "timestamp": ts,
            "query": query,
            "raw_answer": raw_answer,
            "claims": claims_dict,
            "verifications": verif_dict,
            "confidence": conf_dict,
            "verdict": verdict_dict,
        }
        content_hash = self._compute_hash(payload)
        payload["content_hash"] = content_hash

        record = AuditRecord(**payload)
        self._cache[audit_id] = record

        # Append to audit store
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

        return record

    def get_audit_record(self, audit_id: str) -> Optional[AuditRecord]:
        """Retrieves an audit record by ID."""
        if audit_id in self._cache:
            return self._cache[audit_id]
        # Re-check file if missing from cache
        self._load_cache()
        return self._cache.get(audit_id)
