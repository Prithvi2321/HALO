"""
HALO Evidence Verifier: Batch CLI Tool
======================================
Protocol: v1.0-FROZEN
Batch execution tool for evidence verification across answers and claims.
Usage:
  python -m halo.evidence_verifier.verify \\
    --input experiments/runs/citation_verifier/dev_verified_citations.jsonl \\
    --output experiments/runs/evidence_verifier/dev_verified_evidence.jsonl
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import sys
import time

from halo.evidence_verifier.verifier import EvidenceVerifier
from halo.evidence_verifier.config import EvidenceVerifierConfig
from halo.evidence_verifier.schemas import (
    ClaimVerificationInput,
    CitationReferenceInput,
    EvidenceVerdictStatus,
)


def load_extracted_claims_lookup(repo_root: Path) -> Dict[str, Dict[str, Any]]:
    """Loads claims from claim_extractor runs to join claim text with citation verifier output."""
    claims_lookup: Dict[str, Dict[str, Any]] = {}
    candidate_files = [
        repo_root / "experiments" / "runs" / "claim_extractor" / "dev_extracted_claims.jsonl",
        repo_root / "experiments" / "runs" / "claim_extractor" / "train_extracted_claims.jsonl",
    ]
    for cf in candidate_files:
        if cf.exists():
            try:
                with open(cf, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        rec = json.loads(line)
                        for c in rec.get("claims", []):
                            cid = c.get("claim_id")
                            if cid:
                                claims_lookup[cid] = c
            except Exception:
                pass
    return claims_lookup


def build_claim_inputs_from_record(
    record: Dict[str, Any],
    claims_lookup: Dict[str, Dict[str, Any]],
) -> List[ClaimVerificationInput]:
    """Adapts citation verifier output records or raw claims into ClaimVerificationInput objects."""
    ans_id = record.get("answer_id") or record.get("id") or "ANS_UNKNOWN"

    # Case 1: Record already has a 'claims' array with claim text
    if "claims" in record and record["claims"]:
        claim_inputs = []
        for c in record["claims"]:
            cid = c.get("claim_id") or f"{ans_id}_C{len(claim_inputs)+1:03d}"
            ctext = c.get("claim_text") or c.get("text") or ""
            refs = []
            for r in c.get("citation_refs", []):
                refs.append(CitationReferenceInput(
                    citation_id=r.get("citation_id", ""),
                    passage_id=r.get("passage_id"),
                    verification_status=r.get("verification_status", "EXISTS"),
                ))
            claim_inputs.append(ClaimVerificationInput(
                answer_id=ans_id,
                claim_id=cid,
                claim_text=ctext,
                claim_atomicity=c.get("claim_atomicity", "ATOMIC"),
                citation_refs=refs,
                subclaims=c.get("subclaims", []),
            ))
        return claim_inputs

    # Case 2: Record is Citation Verifier output with 'citation_results'
    if "citation_results" in record:
        cit_results = record["citation_results"]
        # Group passages and verification status by claim_id
        claim_to_refs: Dict[str, List[CitationReferenceInput]] = {}
        for cr in cit_results:
            cit_id = cr.get("citation_id", "")
            existence = cr.get("existence", {})
            v_status = existence.get("status", "UNRESOLVED")
            pids = existence.get("matched_passage_ids", [])

            target_claim_ids = cr.get("claim_ids", [])
            for cid in target_claim_ids:
                if cid not in claim_to_refs:
                    claim_to_refs[cid] = []
                for pid in pids:
                    claim_to_refs[cid].append(CitationReferenceInput(
                        citation_id=cit_id,
                        passage_id=pid,
                        verification_status=v_status,
                    ))

        claim_inputs = []
        for cid, refs in claim_to_refs.items():
            looked_up = claims_lookup.get(cid, {})
            ctext = looked_up.get("claim_text") or looked_up.get("source_span", {}).get("source_text") or f"Legal proposition for {cid}"
            claim_inputs.append(ClaimVerificationInput(
                answer_id=ans_id,
                claim_id=cid,
                claim_text=ctext,
                claim_atomicity=looked_up.get("claim_atomicity", "ATOMIC"),
                citation_refs=refs,
                subclaims=looked_up.get("subclaims", []),
            ))
        return claim_inputs

    # Case 3: Single claim / benchmark record
    cid = record.get("claim_id") or record.get("id") or f"{ans_id}_C001"
    ctext = record.get("claim_text") or record.get("generated_claim") or ""
    return [ClaimVerificationInput(
        answer_id=ans_id,
        claim_id=cid,
        claim_text=ctext,
        claim_atomicity="ATOMIC",
        citation_refs=[],
    )]


def main():
    parser = argparse.ArgumentParser(description="HALO Evidence Verifier CLI")
    parser.add_argument("--input", "-i", required=True, help="Path to input JSON or JSONL file")
    parser.add_argument("--output", "-o", required=True, help="Path to output JSONL file")
    parser.add_argument("--config", "-c", default=None, help="Path to optional JSON configuration file")
    parser.add_argument("--batch-size", "-b", type=int, default=16, help="Batch size for inference")

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"[!] Error: Input file not found: {input_path}")
        sys.exit(1)

    config = EvidenceVerifierConfig()
    default_cal = config.repo_root / "experiments" / "verification" / "evidence_verifier" / "threshold_calibration.json"
    cal_file = Path(args.config) if args.config else default_cal
    if cal_file.exists():
        try:
            with open(cal_file, "r", encoding="utf-8") as cf:
                cfg_dict = json.load(cf)
                thresholds = cfg_dict.get("selected_thresholds") or cfg_dict.get("thresholds") or {}
                for k, v in thresholds.items():
                    if hasattr(config, k):
                        setattr(config, k, v)
                for k, v in cfg_dict.items():
                    if hasattr(config, k) and k not in ("selected_thresholds", "thresholds"):
                        setattr(config, k, v)
        except Exception as e:
            print(f"[*] Note: Using default config ({e})")

    config.batch_size = args.batch_size
    verifier = EvidenceVerifier(config=config)
    claims_lookup = load_extracted_claims_lookup(config.repo_root)

    start_time = time.perf_counter()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    records_processed = 0
    total_claims = 0
    verdict_counts: Dict[str, int] = {s.value: 0 for s in EvidenceVerdictStatus}
    written_verdicts = []

    with open(input_path, "r", encoding="utf-8") as in_f, open(output_path, "w", encoding="utf-8") as out_f:
        for line in in_f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception as e:
                print(f"[!] Warning: Failed to parse line as JSON: {e}")
                continue

            claim_inputs = build_claim_inputs_from_record(rec, claims_lookup)
            ans_id = rec.get("answer_id") or rec.get("id") or "ANS_UNKNOWN"

            ans_verdicts = []
            for c_in in claim_inputs:
                v = verifier.verify_claim(c_in)
                ans_verdicts.append(v)
                verdict_counts[v.status] = verdict_counts.get(v.status, 0) + 1
                total_claims += 1

            # Write answer-level container
            ans_result = {
                "schema_version": config.schema_version,
                "answer_id": ans_id,
                "total_claims": len(ans_verdicts),
                "verdicts": [v.to_dict() for v in ans_verdicts],
                "config_hash": config.compute_config_hash(),
            }
            canonical_out = json.dumps(ans_result, sort_keys=True, ensure_ascii=False)
            out_hash = hashlib.sha256(canonical_out.encode("utf-8")).hexdigest()
            ans_result["output_hash"] = out_hash

            out_f.write(json.dumps(ans_result, ensure_ascii=False) + "\n")
            written_verdicts.append(out_hash)
            records_processed += 1

    elapsed = round(time.perf_counter() - start_time, 2)

    # Compute master output hash and write run manifest
    master_out_hash = hashlib.sha256("".join(written_verdicts).encode("utf-8")).hexdigest()
    manifest = {
        "subsystem": "evidence_verifier",
        "verifier_version": config.verifier_version,
        "schema_version": config.schema_version,
        "input_file": str(input_path),
        "output_file": str(output_path),
        "config_hash": config.compute_config_hash(),
        "master_output_hash": master_out_hash,
        "records_processed": records_processed,
        "total_claims": total_claims,
        "verdict_distribution": verdict_counts,
        "elapsed_seconds": elapsed,
        "throughput_claims_per_sec": round(total_claims / max(elapsed, 0.001), 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_provenance": verifier.nli_engine.model_provenance.to_dict() if verifier.nli_engine.model_provenance else {},
    }

    manifest_path = output_path.parent / "run_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2, ensure_ascii=False)

    print(f"[+] Successfully verified {total_claims} claims across {records_processed} answers in {elapsed}s -> {output_path}")
    print(f"[+] Verdict breakdown: {verdict_counts}")
    print(f"[+] Run manifest saved -> {manifest_path}")


if __name__ == "__main__":
    main()
