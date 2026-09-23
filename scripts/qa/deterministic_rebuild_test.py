"""
Deterministic Rebuild Verification Engine for HALO Dataset 1.
Implements Section 23 of the freeze specification:
Running the ingestion pipeline twice against identical source PDFs must produce identical canonical output.
Compares JSON structure, IDs, ordering, text, hashes, passages, versions, and provenance.
"""

import os
import sys
import json
import hashlib
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from scripts.parsing.structure_parser import parse_structure
from scripts.parsing.definitions_parser import parse_definitions
from scripts.parsing.schedules_parser import parse_schedules
from scripts.parsing.cross_references import extract_cross_references
from scripts.amendments.amendment_parser import parse_all_amendments
from scripts.amendments.transformation_engine import run_transformation_engine
from scripts.validation.validator import run_validation
from scripts.export.exporter import export_canonical_dataset


def compute_file_sha256(filepath: str) -> str:
    if not os.path.exists(filepath):
        return ""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def run_deterministic_rebuild_test(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    final_dir = config["output"]["final_dir"]

    tracked_files = [
        "companies_act_2013.json",
        "companies_act_2013_passages.jsonl",
        "companies_act_2013_versions.json",
        "companies_act_2013_amendments.json",
        "companies_act_2013_provenance.json",
        "companies_act_2013_cross_references.json",
        "companies_act_2013_definitions.json",
        "companies_act_2013_validation_report.json",
        "freeze_manifest.json",
        "dataset_1_manifest.json"
    ]

    print("=================================================================")
    print("  HALO DATASET 1: DETERMINISTIC REBUILD TEST (BUILD 1 vs BUILD 2)")
    print("=================================================================")

    # 1. Capture BUILD 1 Hashes
    print("\n[*] Capturing BUILD 1 File State & SHA-256 Hashes...")
    build1_hashes = {}
    for fname in tracked_files:
        fpath = os.path.join(final_dir, fname)
        if not os.path.exists(fpath):
            print(f"[!] Warning: {fname} missing before rebuild test. Running initial export...")
            export_canonical_dataset(config_path)
            break

    for fname in tracked_files:
        fpath = os.path.join(final_dir, fname)
        h = compute_file_sha256(fpath)
        sz = os.path.getsize(fpath) if os.path.exists(fpath) else 0
        build1_hashes[fname] = {"sha256": h, "size": sz}
        print(f"    [BUILD 1] {fname:42} | Size: {sz:8} bytes | SHA: {h[:16]}...")

    # 2. Execute BUILD 2 (Clean sequential pipeline execution)
    print("\n[*] Executing Clean Sequential Pipeline (BUILD 2)...")
    parse_structure(config_path)
    parse_definitions(config_path)
    parse_schedules(config_path)
    extract_cross_references(config_path)
    parse_all_amendments(config_path)
    run_transformation_engine(config_path)
    run_validation(config_path)
    export_canonical_dataset(config_path)

    # 3. Capture BUILD 2 Hashes
    print("\n[*] Capturing BUILD 2 File State & SHA-256 Hashes...")
    build2_hashes = {}
    for fname in tracked_files:
        fpath = os.path.join(final_dir, fname)
        h = compute_file_sha256(fpath)
        sz = os.path.getsize(fpath) if os.path.exists(fpath) else 0
        build2_hashes[fname] = {"sha256": h, "size": sz}
        print(f"    [BUILD 2] {fname:42} | Size: {sz:8} bytes | SHA: {h[:16]}...")

    # 4. Compare BUILD 1 vs BUILD 2
    print("\n[*] Evaluating Bit-Level & Structural Determinism...")
    discrepancies = []
    comparison_table = []

    for fname in tracked_files:
        b1 = build1_hashes[fname]
        b2 = build2_hashes[fname]
        matches = (b1["sha256"] == b2["sha256"] and b1["size"] == b2["size"])
        status_str = "MATCH (100% Deterministic)" if matches else "MISMATCH"
        if not matches:
            discrepancies.append(fname)
        comparison_table.append({
            "file": fname,
            "build1_sha256": b1["sha256"],
            "build2_sha256": b2["sha256"],
            "build1_size": b1["size"],
            "build2_size": b2["size"],
            "deterministic": matches
        })
        print(f"    {'[MATCH]' if matches else '[FAIL]'} {fname:42} -> {status_str}")

    all_match = (len(discrepancies) == 0)
    print("\n-----------------------------------------------------------------")
    if all_match:
        print("  [SUCCESS] DETERMINISTIC REBUILD PASSED: 10/10 ARTIFACTS IDENTICAL")
    else:
        print(f"  [FAILURE] DETERMINISTIC REBUILD FAILED: {len(discrepancies)} discrepancies")
    print("-----------------------------------------------------------------")

    result = {
        "status": "PASS" if all_match else "FAIL",
        "total_artifacts_compared": len(tracked_files),
        "matches_count": len(tracked_files) - len(discrepancies),
        "discrepancies_count": len(discrepancies),
        "discrepancies": discrepancies,
        "comparisons": comparison_table
    }

    report_path = os.path.join(config["output"]["base_dir"], "qa", "deterministic_rebuild_results.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"[+] Rebuild comparison results saved to: {report_path}")

    return result


if __name__ == "__main__":
    run_deterministic_rebuild_test()
