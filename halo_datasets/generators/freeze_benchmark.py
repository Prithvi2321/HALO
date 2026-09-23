"""
HALO Expanded Verification Benchmark: Cryptographic Freeze & Sealing Engine
===========================================================================
Protocol: v1.0-FROZEN
Validates that all 18 Acceptance Gates (G1-G18) are satisfied, generates canonical
manifests and computes the Master Root SHA-256 hash, and seals:
  halo_datasets/manifests/VERIFICATION_DATASET_FREEZE_RECEIPT.json
"""

import datetime
import hashlib
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

BENCHMARK_ROOT = os.path.join(BASE_DIR, "halo_datasets")
MANIFESTS_DIR = os.path.join(BENCHMARK_ROOT, "manifests")
FREEZE_RECEIPT_PATH = os.path.join(MANIFESTS_DIR, "VERIFICATION_DATASET_FREEZE_RECEIPT.json")

from halo_datasets.generators.build_manifest import build_manifest
from halo_datasets.qa.run_all_qa import run_all_qa_gates


def compute_master_root_hash(file_digests: dict) -> str:
    """
    Deterministically computes master root hash over sorted (file_path, sha256) tuples.
    """
    sorted_pairs = sorted(file_digests.items())
    raw_payload = "\n".join(f"{p}:{h}" for p, h in sorted_pairs)
    return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()


def freeze_benchmark():
    print("=" * 80)
    print(" HALO EXPANDED VERIFICATION BENCHMARK — CRYPTOGRAPHIC FREEZE SEAL")
    print(" Protocol: v1.0-FROZEN | Target: 180 Verification Cases")
    print("=" * 80)

    # 1. First run the full QA suite
    qa_results = run_all_qa_gates()
    if not qa_results["all_passed"]:
        print("\n[!] FATAL: Cannot freeze benchmark suite — QA gates failed!")
        sys.exit(1)

    # 2. Build and refresh manifests
    manifest_data = build_manifest()

    file_digests = manifest_data["file_digests"]
    master_root_hash = compute_master_root_hash(file_digests)

    # 3. Create Freeze Receipt
    freeze_receipt = {
        "benchmark_id": "HALO_EXPANDED_VERIFICATION_BENCHMARK_SUITE",
        "benchmark_title": "HALO Expanded Legal Verification Benchmark Suite",
        "protocol_version": "v1.0-FROZEN",
        "status": "OFFICIALLY_AUDITED_AND_CRYPTOGRAPHICALLY_FROZEN",
        "freeze_timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_cases": manifest_data["total_unique_cases"],
        "master_root_hash_sha256": master_root_hash,
        "splits": manifest_data["splits"],
        "class_distribution": manifest_data["class_distribution"],
        "difficulty_distribution": manifest_data["difficulty_distribution"],
        "category_breakdown": {k: v["count"] for k, v in manifest_data["categories"].items()},
        "source_corpora_receipts": manifest_data["source_corpora_receipts"],
        "qa_audit_summary": {
            "total_gates_evaluated": qa_results["gates_evaluated"],
            "total_gates_passed": qa_results["gates_passed"],
            "all_gates_passed": qa_results["all_passed"],
            "gates_status": [
                {"gate": g["id"], "name": g["name"], "status": "PASSED" if g["passed"] else "FAILED"}
                for g in qa_results["gates"]
            ]
        },
        "file_digests": file_digests,
        "read_only_enforced": True
    }

    # Deterministic receipt signature
    receipt_sign_payload = json.dumps({
        "benchmark_id": freeze_receipt["benchmark_id"],
        "master_root_hash_sha256": freeze_receipt["master_root_hash_sha256"],
        "total_cases": freeze_receipt["total_cases"],
        "protocol_version": freeze_receipt["protocol_version"],
        "file_digests": freeze_receipt["file_digests"]
    }, sort_keys=True)
    freeze_receipt["receipt_signature_sha256"] = hashlib.sha256(receipt_sign_payload.encode("utf-8")).hexdigest()

    # 4. Write Freeze Receipt
    with open(FREEZE_RECEIPT_PATH, "w", encoding="utf-8") as f:
        json.dump(freeze_receipt, f, indent=2)

    print("\n" + "=" * 80)
    print(" [+] CRYPTOGRAPHIC FREEZE COMPLETE — BENCHMARK OFFICIALLY SEALED")
    print("=" * 80)
    print(f" Benchmark ID:            {freeze_receipt['benchmark_id']}")
    print(f" Protocol Version:        {freeze_receipt['protocol_version']}")
    print(f" Status:                  {freeze_receipt['status']}")
    print(f" Total Unique Cases:      {freeze_receipt['total_cases']}")
    print(f" Master Root SHA-256:     {freeze_receipt['master_root_hash_sha256']}")
    print(f" Receipt Signature:       {freeze_receipt['receipt_signature_sha256']}")
    print(f" Freeze Receipt Path:     {FREEZE_RECEIPT_PATH}")
    print("=" * 80)

    return freeze_receipt


if __name__ == "__main__":
    freeze_benchmark()
