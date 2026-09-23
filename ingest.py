"""
HALO Dataset 1 - Companies Act, 2013 Statutory Ingestion CLI.
Production-grade orchestration adhering strictly to prompt.md specifications.
"""

import sys
import os
import argparse
import json

from scripts.download.discover import run_discovery
from scripts.extraction.pdf_verifier import verify_pdfs
from scripts.extraction.extractor import extract_pages
from scripts.normalization.normalizer import normalize_pages
from scripts.parsing.structure_parser import parse_structure
from scripts.parsing.definitions_parser import parse_definitions
from scripts.parsing.schedules_parser import parse_schedules
from scripts.parsing.cross_references import extract_cross_references
from scripts.amendments.amendment_parser import parse_all_amendments
from scripts.amendments.transformation_engine import run_transformation_engine
from scripts.validation.validator import run_validation
from scripts.export.exporter import export_canonical_dataset


def cmd_discover(args):
    print("\n=== STEP 1: PDF DISCOVERY & MANIFEST GENERATION ===")
    run_discovery(args.config)


def cmd_verify(args):
    print("\n=== STEP 2: PDF INTEGRITY VERIFICATION ===")
    verify_pdfs(args.config)


def cmd_extract(args):
    print("\n=== STEP 3: TEXT EXTRACTION & OCR FALLBACK ===")
    extract_pages(args.config)
    print("\n=== STEP 4: PAGE NORMALIZATION & BOILERPLATE AUDITING ===")
    normalize_pages(args.config)


def cmd_parse(args):
    print("\n=== STEP 5: LEGISLATIVE STRUCTURE PARSING ===")
    parse_structure(args.config)
    parse_definitions(args.config)
    parse_schedules(args.config)
    extract_cross_references(args.config)


def cmd_amendments(args):
    print("\n=== STEP 6: AMENDMENT PARSING & DETERMINISTIC TRANSFORMATION ===")
    parse_all_amendments(args.config)
    run_transformation_engine(args.config)


def cmd_validate(args):
    print("\n=== STEP 7: MULTI-STAGE VALIDATION & CONSOLIDATION CHECK ===")
    run_validation(args.config)


def cmd_export(args):
    print("\n=== STEP 8: CANONICAL EXPORT & REPORT GENERATION ===")
    export_canonical_dataset(args.config)


def cmd_all(args):
    print("================================================================")
    print("  HALO DATASET 1: STATUTORY INGESTION PIPELINE (ALL STEPS)")
    print("================================================================")
    cmd_discover(args)
    cmd_verify(args)
    cmd_extract(args)
    cmd_parse(args)
    cmd_amendments(args)
    cmd_validate(args)
    cmd_export(args)
    print("\n[SUCCESS] PIPELINE EXECUTION COMPLETE. All artifacts validated.")


def cmd_audit(args):
    sec_num = args.section.strip()
    print(f"\n=== PROVENANCE & GROUND-TRUTH AUDIT FOR SECTION {sec_num} ===")
    prov_file = "data/dataset_1/final/companies_act_2013_provenance.json"
    act_file = "data/dataset_1/final/companies_act_2013.json"
    passages_file = "data/dataset_1/final/companies_act_2013_passages.jsonl"
    versions_file = "data/dataset_1/final/companies_act_2013_versions.json"
    struct_file = "data/dataset_1/structured/structured_act.json"

    if not os.path.exists(prov_file) or not os.path.exists(act_file):
        print("[!] Error: Canonical final files not found. Run 'python ingest.py all' first.")
        return

    with open(prov_file, "r", encoding="utf-8") as f:
        provenance = json.load(f)

    target_prov = next((p for p in provenance if p["section_number"] == sec_num), None)
    if not target_prov:
        print(f"[!] Section {sec_num} not found in provenance index.")
        return

    # Find section node in structured act
    sec_node = None
    if os.path.exists(struct_file):
        with open(struct_file, "r", encoding="utf-8") as f:
            structured_act = json.load(f)
            sec_node = next((s for s in structured_act["sections"] if s["section_number"] == sec_num), None)

    print(f"Section ID:              {target_prov['section_id']}")
    print(f"Heading:                 {sec_node['heading'] if sec_node else 'N/A'}")
    print(f"Source Document:         {target_prov['source_document_id']} ({target_prov['source_file']})")
    print(f"Source Pages:            Page {target_prov['source_page_start']} to {target_prov['source_page_end']}")
    print("\n--- 4-TIER CRYPTOGRAPHIC LINEAGE ---")
    print(f"  1. source_pdf_sha256:        {target_prov.get('source_pdf_sha256', target_prov.get('sha256'))}")
    print(f"  2. raw_extracted_text_sha256:{target_prov.get('raw_extracted_text_sha256', 'N/A')}")
    print(f"  3. canonical_text_sha256:    {target_prov.get('canonical_text_sha256', 'N/A')}")
    print(f"  4. content_hash:             {target_prov['content_hash']}")

    if sec_node:
        print("\n--- TEMPORAL LIFECYCLE ---")
        print(f"  Enacted:               {sec_node.get('enactment_date', '2013-08-29')}")
        print(f"  Published:             {sec_node.get('publication_date', '2013-08-30')}")
        print(f"  Amended:               {sec_node.get('amendment_date') or 'None'}")
        print(f"  Commenced:             {sec_node.get('commencement_date') or '2013-09-12'}")
        print(f"  Enforcement Status:    {sec_node.get('enforcement_status')}")
        print(f"  Effective From:        {sec_node.get('effective_from')}")
        print(f"  Effective To:          {sec_node.get('effective_to') or 'In Force (Current)'}")

        print("\n--- EDITORIAL MARKERS & FOOTNOTES ---")
        markers = sec_node.get("editorial_markers", [])
        footnotes = sec_node.get("footnotes", [])
        print(f"  Editorial Markers Found: {len(markers)}")
        for m in markers:
            print(f"    - Marker '{m['marker']}' [{m.get('location', 'text')}]: {m.get('raw_snippet', '')} -> Target: {m.get('target')}")
        print(f"  Authoritative Footnotes: {len(footnotes)}")
        for fn in footnotes:
            comm = f" | w.e.f. {fn['commencement_date']}" if fn.get('commencement_date') else ""
            print(f"    - [{fn['footnote_id']}] (Marker {fn['marker']}): {fn['text'][:100]}...{comm}")

        print("\n--- DUAL-TEXT COMPARISON (RAW vs CANONICAL) ---")
        raw_preview = sec_node['text'][:180].replace('\n', ' ')
        can_preview = sec_node['canonical_text'][:180].replace('\n', ' ')
        print(f"  [RAW]:       {raw_preview}...")
        print(f"  [CANONICAL]: {can_preview}...")

    # Find passages
    matching_passages = []
    with open(passages_file, "r", encoding="utf-8") as f:
        for line in f:
            pas = json.loads(line)
            if pas["section_id"] == target_prov["section_id"]:
                matching_passages.append(pas)

    print(f"\n--- RETRIEVAL PASSAGES ({len(matching_passages)} passages) ---")
    for idx, p in enumerate(matching_passages[:2]):
        print(f"  [{idx+1}] ID: {p['passage_id']} (Type: {p['passage_type']})")
        print(f"      Canonical Text: {p['canonical_text'][:120]}...")

    # Find temporal versions
    if os.path.exists(versions_file):
        with open(versions_file, "r", encoding="utf-8") as f:
            v_data = json.load(f)
        print("\n--- STATUTORY CONSOLIDATION VERSIONS ---")
        for v in v_data["versions"]:
            v_sec = next((s for s in v["sections"] if s["section_number"] == sec_num), None)
            if v_sec:
                print(f"  - Version: {v['version_tag']} ({v['effective_from']} to {v['effective_to'] or 'current'})")
                print(f"    Hash: {v_sec['content_hash'][:16]}... | Amendments: {v_sec.get('amendment_history', [])}")


def main():
    parser = argparse.ArgumentParser(description="HALO Dataset 1 Ingestion Engine")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")

    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")
    subparsers.add_parser("discover", help="Discover PDFs, hash, stage and generate manifest")
    subparsers.add_parser("verify", help="Verify PDF integrity")
    subparsers.add_parser("extract", help="Extract text and normalize pages")
    subparsers.add_parser("parse", help="Parse chapters, sections, definitions, schedules, cross-references")
    subparsers.add_parser("amendments", help="Parse amendments and run transformation engine")
    subparsers.add_parser("validate", help="Run multi-stage validation checks")
    subparsers.add_parser("export", help="Export canonical JSON and JSONL artifacts")
    subparsers.add_parser("all", help="Execute complete ingestion pipeline end-to-end")

    audit_parser = subparsers.add_parser("audit", help="Audit provenance and history of a specific section")
    audit_parser.add_argument("--section", required=True, help="Section number (e.g. 135, 12, 2)")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmd_map = {
        "discover": cmd_discover,
        "verify": cmd_verify,
        "extract": cmd_extract,
        "parse": cmd_parse,
        "amendments": cmd_amendments,
        "validate": cmd_validate,
        "export": cmd_export,
        "all": cmd_all,
        "audit": cmd_audit
    }
    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
