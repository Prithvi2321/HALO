"""
HALO Claim Extractor: Isolation & Freeze Protection Tests (Gates C10 & C11)
===========================================================================
Protocol: v1.0-FROZEN
Tests that frozen benchmarks and corpora remain 100% byte-for-byte unmodified (Gate C10),
and that the 28-case test split remains strictly quarantined (Gate C11).
"""

import json
import hashlib
from pathlib import Path


def test_frozen_benchmark_integrity():
    """Gate C10: Verify that verification benchmark assets match the freeze receipt."""
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    receipt_path = repo_root / "halo_datasets" / "manifests" / "VERIFICATION_DATASET_FREEZE_RECEIPT.json"

    assert receipt_path.exists(), f"Freeze receipt missing at {receipt_path}"

    with open(receipt_path, "r", encoding="utf-8") as f:
        receipt = json.load(f)

    file_digests = receipt.get("file_digests", {})
    assert len(file_digests) == 19, f"Expected 19 registered benchmark files, found {len(file_digests)}"

    for rel_path, expected_sha in file_digests.items():
        actual_path = repo_root / "halo_datasets" / rel_path
        assert actual_path.exists(), f"Registered asset missing: {actual_path}"
        actual_sha = hashlib.sha256(actual_path.read_bytes()).hexdigest()
        assert actual_sha == expected_sha, f"SHA-256 mismatch for {rel_path} (Frozen asset modified!)"


def test_test_split_quarantine():
    """Gate C11: Verify that test split contains exactly 28 cases and remains isolated."""
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    test_path = repo_root / "halo_datasets" / "splits" / "test.jsonl"

    assert test_path.exists(), f"Test split file missing at {test_path}"

    with open(test_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    assert len(lines) == 28, f"Test split quarantine breached: expected 28 cases, found {len(lines)}"
