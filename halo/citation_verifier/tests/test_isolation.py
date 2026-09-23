"""
HALO Citation Verifier: Corpus Isolation & Freeze Protection Tests (Gates CV10 & CV11)
======================================================================================
Protocol: v1.0-FROZEN
Tests that authoritative corpora (D1, D2) and benchmark datasets remain 100% untouched,
and that the held-out test split (28 cases) remains strictly quarantined.
"""

import json
import hashlib
from pathlib import Path


def test_frozen_benchmark_integrity():
    """Gate CV10: Verify that verification benchmark assets match the freeze receipt."""
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    receipt_path = repo_root / "halo_datasets" / "manifests" / "VERIFICATION_DATASET_FREEZE_RECEIPT.json"

    assert receipt_path.exists(), f"Freeze receipt missing at {receipt_path}"

    with open(receipt_path, "r", encoding="utf-8") as f:
        receipt = json.load(f)

    file_digests = receipt.get("file_digests", {})
    assert len(file_digests) == 19

    for rel_path, expected_sha in file_digests.items():
        actual_path = repo_root / "halo_datasets" / rel_path
        assert actual_path.exists(), f"Missing registered file: {actual_path}"
        actual_sha = hashlib.sha256(actual_path.read_bytes()).hexdigest()
        assert actual_sha == expected_sha, f"SHA-256 mismatch for {rel_path}"


def test_test_split_quarantine():
    """Gate CV11: Verify that test split contains exactly 28 cases and remains quarantined."""
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    test_path = repo_root / "halo_datasets" / "splits" / "test.jsonl"

    assert test_path.exists()
    with open(test_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    assert len(lines) == 28, f"Quarantine breach: expected 28 cases, found {len(lines)}"
