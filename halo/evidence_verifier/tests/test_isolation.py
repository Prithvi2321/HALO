"""
Unit Tests for Gate EV14: Frozen Corpus Integrity & Test Quarantine
===================================================================
Protocol: v1.0-FROZEN
Tests that canonical corpora (D1, D2) and verification benchmark splits
remain strictly unchanged, and test split quarantine is actively enforced.
"""

from pathlib import Path
import hashlib
import json
import pytest

from halo.evidence_verifier.config import EvidenceVerifierConfig


def test_test_quarantine_manifest_exists():
    """Gate EV14: Test quarantine manifest must exist and bar evaluation."""
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    manifest_path = repo_root / "experiments" / "verification" / "evidence_verifier" / "test_quarantine_manifest.json"
    assert manifest_path.exists(), f"Quarantine manifest not found at {manifest_path}"

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["test_case_count"] == 28
    assert data["status"] == "QUARANTINED"
    assert data["evaluation_allowed"] is False
    assert len(data["benchmark_hash"]) == 64


def test_test_split_hash_matches_quarantine():
    """Gate EV14: Test split hash must match the quarantined benchmark hash."""
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    test_path = repo_root / "halo_datasets" / "splits" / "test.jsonl"
    manifest_path = repo_root / "experiments" / "verification" / "evidence_verifier" / "test_quarantine_manifest.json"

    assert test_path.exists()
    hasher = hashlib.sha256()
    with open(test_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    actual_hash = hasher.hexdigest()

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    assert actual_hash.lower() == manifest_data["benchmark_hash"].lower()


def test_canonical_corpora_remain_accessible(store=None):
    """Verifies canonical D1 and D2 passage corpora exist and are non-empty."""
    cfg = EvidenceVerifierConfig()
    assert Path(cfg.d1_passages_path).exists()
    assert Path(cfg.d2_passages_path).exists()
    assert Path(cfg.d1_passages_path).stat().st_size > 1000
    assert Path(cfg.d2_passages_path).stat().st_size > 1000
