"""
HALO Dataset 3: Automated Quality Assurance & Integrity Audit
============================================================
Evaluates all 10 core QA gates on the frozen Dataset 3 benchmark suite:
  Gate 1: Schema Integrity & Pydantic Validation
  Gate 2: Evidence ID Existence in Frozen Corpus (D1 & D2)
  Gate 3: Dataset 1 Statutory Linkage Accuracy
  Gate 4: Dataset 2 Judicial Linkage & Citation Accuracy
  Gate 5: Synthetic Perturbation & Adversarial Status Validity
  Gate 6: Global Deduplication & Identifier Uniqueness
  Gate 7: Strict Split Isolation & Zero Leakage Audit (Train/Dev/Test)
  Gate 8: Ground Truth Non-Triviality & Atomic Sufficiency
  Gate 9: Fail-Closed & Robustness Soundness
  Gate 10: Human Annotation Audit & Difficulty Distribution
"""

import os
import sys
import json
import hashlib
from typing import Dict, Any, List

from scripts.dataset3.models import (
    RetrievalRecord,
    GroundingRecord,
    CitationVerificationRecord,
    PassageVerificationRecord,
    RobustnessRecord,
    Dataset3UnifiedRecord
)
from scripts.dataset3.validator import Dataset3Validator

MANIFEST_PATH = "data/dataset3/manifests/dataset3_manifest.json"
RECEIPT_PATH = "data/dataset3/manifests/freeze_receipt.json"
REPORT_OUTPUT_PATH = "data/dataset3/qa/automated_qa_report.json"


def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def load_jsonl(filepath: str) -> List[Dict[str, Any]]:
    records = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                records.append(json.loads(line_str))
    return records


def run_qa():
    print("=" * 70)
    print("  HALO DATASET 3: COMPREHENSIVE AUTOMATED QA & INTEGRITY AUDIT  ")
    print("=" * 70)

    if not os.path.exists(MANIFEST_PATH):
        print(f"[-] FAILED: Manifest missing at {MANIFEST_PATH}")
        sys.exit(1)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # 1. Verify Manifest Integrity & File Checksums
    print("\n[Audit Phase 1] Verifying SHA-256 Checksums and File Geometry...")
    manifest_errors = []
    for rel_path, meta in manifest.get("files", {}).items():
        full_path = os.path.join("data", "dataset3", rel_path)
        if not os.path.exists(full_path):
            manifest_errors.append(f"Missing file: {rel_path}")
            continue
        actual_hash = compute_sha256(full_path)
        if actual_hash != meta["sha256"]:
            manifest_errors.append(f"Checksum mismatch on {rel_path}: expected {meta['sha256']}, got {actual_hash}")
        actual_size = os.path.getsize(full_path)
        if actual_size != meta["size_bytes"]:
            manifest_errors.append(f"Size mismatch on {rel_path}: expected {meta['size_bytes']}, got {actual_size}")

    if manifest_errors:
        print(f"[-] Checksum validation FAILED ({len(manifest_errors)} errors):")
        for err in manifest_errors[:5]:
            print(f"    - {err}")
        sys.exit(1)
    else:
        print(f"    [+] All {len(manifest.get('files', {}))} files verified against SHA-256 manifest.")

    # 2. Load disk artifacts into typed models
    print("\n[Audit Phase 2] Loading Benchmark JSONL Partitions from Disk...")
    data: Dict[str, List[Any]] = {}

    d3_dir = os.path.join("data", "dataset3")
    ret_a = [RetrievalRecord.model_validate(d) for d in load_jsonl(os.path.join(d3_dir, "retrieval", "d3_a_direct.jsonl"))]
    ret_b = [RetrievalRecord.model_validate(d) for d in load_jsonl(os.path.join(d3_dir, "retrieval", "d3_b_semantic.jsonl"))]
    ret_c = [RetrievalRecord.model_validate(d) for d in load_jsonl(os.path.join(d3_dir, "retrieval", "d3_c_hard_negatives.jsonl"))]
    ground_d = [GroundingRecord.model_validate(d) for d in load_jsonl(os.path.join(d3_dir, "grounding", "d3_d_grounded_answers.jsonl"))]
    ver_e = [CitationVerificationRecord.model_validate(d) for d in load_jsonl(os.path.join(d3_dir, "citation_verification", "d3_e_citation_existence.jsonl"))]
    ver_f = [CitationVerificationRecord.model_validate(d) for d in load_jsonl(os.path.join(d3_dir, "citation_verification", "d3_f_metadata_mismatch.jsonl"))]
    ver_g = [PassageVerificationRecord.model_validate(d) for d in load_jsonl(os.path.join(d3_dir, "citation_verification", "d3_g_passage_fabrication.jsonl"))]
    rob_h = [RobustnessRecord.model_validate(d) for d in load_jsonl(os.path.join(d3_dir, "robustness", "d3_h_fail_closed.jsonl"))]
    rob_i = [RobustnessRecord.model_validate(d) for d in load_jsonl(os.path.join(d3_dir, "robustness", "d3_i_ambiguous.jsonl"))]
    rob_j = [RobustnessRecord.model_validate(d) for d in load_jsonl(os.path.join(d3_dir, "robustness", "d3_j_temporal.jsonl"))]
    rob_k = [RobustnessRecord.model_validate(d) for d in load_jsonl(os.path.join(d3_dir, "robustness", "d3_k_conflict.jsonl"))]
    rob_l = [RobustnessRecord.model_validate(d) for d in load_jsonl(os.path.join(d3_dir, "robustness", "d3_l_out_of_domain.jsonl"))]
    rob_m = [RobustnessRecord.model_validate(d) for d in load_jsonl(os.path.join(d3_dir, "robustness", "d3_m_injections.jsonl"))]

    data["d3_a"] = ret_a
    data["d3_b"] = ret_b
    data["d3_c"] = ret_c
    data["d3_d"] = ground_d
    data["d3_e"] = ver_e
    data["d3_f"] = ver_f
    data["d3_g"] = ver_g
    data["d3_h"] = rob_h
    data["d3_i"] = rob_i
    data["d3_j"] = rob_j
    data["d3_k"] = rob_k
    data["d3_l"] = rob_l
    data["d3_m"] = rob_m

    # Also verify canonical unified master file
    canonical_items = [Dataset3UnifiedRecord.model_validate(d) for d in load_jsonl(os.path.join(d3_dir, "canonical", "dataset3_all.jsonl"))]
    total_loaded = sum(len(v) for v in data.values())
    if len(canonical_items) != total_loaded:
        print(f"[-] FATAL: Canonical count ({len(canonical_items)}) does not match partition sum ({total_loaded})")
        sys.exit(1)

    print(f"    [+] Loaded {total_loaded} records across 13 partitions. Canonical master match verified.")

    # 3. Execute 10 QA Gates
    print("\n[Audit Phase 3] Executing 10-Gate Evaluation Engine...")
    validator = Dataset3Validator()
    report = validator.validate_all(data)

    print("\n" + "=" * 70)
    print(f"{'QA GATE':<45} | {'STATUS':<10} | {'DETAILS'}")
    print("-" * 70)
    for g_id, g_info in report["gates"].items():
        status = g_info["status"]
        status_str = f"[PASS]" if status == "PASS" else f"[FAIL]"
        desc = g_info.get("description", "")[:25]
        print(f"{g_id:<45} | {status_str:<10} | {desc}")
    print("=" * 70)

    # Save automated report
    if os.path.exists(REPORT_OUTPUT_PATH):
        try:
            import stat
            os.chmod(REPORT_OUTPUT_PATH, stat.S_IWRITE)
        except Exception:
            pass
    with open(REPORT_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n[+] Detailed automated QA report saved to {REPORT_OUTPUT_PATH}")

    if report["overall_status"] == "ALL_GATES_PASSED":
        print("\n>>> All defined structural, linkage, leakage, synthetic perturbation, robustness, and annotation QA gates passed for Dataset 3 v1.0.0. <<<")
        sys.exit(0)
    else:
        print("\n[-] FATAL: Dataset 3 QA verification FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    run_qa()
