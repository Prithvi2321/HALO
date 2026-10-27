"""
Phase 1 — SC Judgment Dataset Profiler
=======================================
Source : Indian Supreme Court Judgments (AWS Open Data)
         https://registry.opendata.aws/indian-supreme-court-judgments/
Year   : 2023 (english subset)

What this script does
---------------------
1. Parses the index JSON → builds a metadata DataFrame from filenames.
2. Extracts structured citation fields from each filename:
     YEAR_VOLUME_START_END_EN.pdf  →  year, volume, start_page, end_page
3. Checks usability of each record (citation parseable, unique, non-zero page range).
4. Extracts the TAR in a temp location and peeks at 5 PDFs with PyMuPDF to assess:
     - whether text is selectable (native PDF) or blank (scanned)
     - approximate page count and word count per page
5. Prints a full profile report and writes:
     sc_2023_profile.json        — structured per-record metadata
     sc_2023_profile_report.txt  — human-readable summary
     sc_2023_scanned_list.txt    — filenames likely to need OCR

Usage
-----
  cd c:\\HALO
  python scripts\\sc_ingest\\phase1_profile.py
"""

import io
import json
import os
import re
import sys
import tarfile
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime

# Force UTF-8 output on Windows so unicode box-drawing chars don't crash
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Output directory (inside HALO project) ────────────────────────────────────
PROJECT_ROOT  = Path(__file__).resolve().parent.parent.parent
SC_WORK_DIR   = PROJECT_ROOT / "Data" / "sc_judgments" / "2023"
SC_WORK_DIR.mkdir(parents=True, exist_ok=True)

INDEX_JSON = Path(r"C:\Users\Prithviraj\Downloads\sc\data\tar\year=2023\english\english.index.json")
TAR_PATH   = Path(r"C:\Users\Prithviraj\Downloads\sc\data\tar\year=2023\english\english.tar")

OUT_PROFILE     = SC_WORK_DIR / "sc_2023_profile.json"
OUT_REPORT      = SC_WORK_DIR / "sc_2023_profile_report.txt"
OUT_SCANNED     = SC_WORK_DIR / "sc_2023_scanned_list.txt"

# Number of PDFs to open for text-quality sampling
SAMPLE_SIZE = 10

# Minimum word count per page to consider it "native" (not scanned)
NATIVE_WORDS_PER_PAGE_THRESHOLD = 30

# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Parse index JSON
# ─────────────────────────────────────────────────────────────────────────────

def load_index(index_path: Path) -> dict:
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)

# Filename pattern: YEAR_VOLUME_STARTPAGE_ENDPAGE_EN.pdf
_FNAME_RE = re.compile(
    r"^(?P<year>\d{4})_(?P<volume>\d+)_(?P<start_page>\d+)_(?P<end_page>\d+)_EN\.pdf$",
    re.IGNORECASE
)

def parse_filename(fname: str) -> dict:
    m = _FNAME_RE.match(fname)
    if not m:
        return {"filename": fname, "parseable": False}
    year      = int(m.group("year"))
    volume    = int(m.group("volume"))
    start_pg  = int(m.group("start_page"))
    end_pg    = int(m.group("end_page"))
    page_span = end_pg - start_pg + 1
    # Citation format: (YEAR) VOLUME SCC START
    citation  = f"({year}) {volume} SCC {start_pg}"
    case_id   = f"SC_{year}_V{volume:02d}_P{start_pg:04d}"
    return {
        "filename"   : fname,
        "parseable"  : True,
        "year"       : year,
        "volume"     : volume,
        "start_page" : start_pg,
        "end_page"   : end_pg,
        "page_span"  : page_span,
        "citation"   : citation,
        "case_id"    : case_id,
        "usable"     : page_span > 0,
    }

# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Profile the metadata
# ─────────────────────────────────────────────────────────────────────────────

def profile_metadata(records: list) -> dict:
    total         = len(records)
    parseable     = [r for r in records if r["parseable"]]
    unparseable   = [r for r in records if not r["parseable"]]
    usable        = [r for r in parseable if r["usable"]]
    zero_span     = [r for r in parseable if not r["usable"]]

    # Duplicate case_id check
    cid_counts = Counter(r["case_id"] for r in parseable)
    duplicates = {k: v for k, v in cid_counts.items() if v > 1}

    # Duplicate citation check
    cit_counts  = Counter(r["citation"] for r in parseable)
    dup_cits    = {k: v for k, v in cit_counts.items() if v > 1}

    # Volume distribution
    vol_dist = dict(sorted(Counter(r["volume"] for r in parseable).items()))

    # Page span distribution
    spans = [r["page_span"] for r in usable]
    avg_span = sum(spans) / len(spans) if spans else 0
    max_span = max(spans) if spans else 0
    min_span = min(spans) if spans else 0

    usable_pct = len(usable) / total * 100 if total > 0 else 0

    return {
        "total_files"          : total,
        "parseable"            : len(parseable),
        "unparseable"          : len(unparseable),
        "usable_citations"     : len(usable),
        "usable_pct"           : round(usable_pct, 2),
        "zero_span_files"      : len(zero_span),
        "duplicate_case_ids"   : len(duplicates),
        "duplicate_citations"  : len(dup_cits),
        "volumes_present"      : sorted(vol_dist.keys()),
        "volume_distribution"  : vol_dist,
        "page_span_avg"        : round(avg_span, 1),
        "page_span_min"        : min_span,
        "page_span_max"        : max_span,
        "unparseable_files"    : unparseable,
        "duplicate_case_id_details": duplicates,
    }

# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Sample PDFs from TAR for text quality
# ─────────────────────────────────────────────────────────────────────────────

def sample_pdfs(tar_path: Path, filenames: list, sample_size: int = 10) -> list:
    """
    Opens `sample_size` PDFs from the TAR directly in-memory and checks
    whether text is selectable (native) or empty (likely scanned).
    Returns a list of per-file quality dicts.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("[WARN] PyMuPDF not installed. Skipping PDF text-quality sampling.")
        print("       Install: pip install pymupdf")
        return []

    # Pick evenly spaced samples across the file list
    step     = max(1, len(filenames) // sample_size)
    sampled  = filenames[::step][:sample_size]

    print(f"\n[PDF SAMPLE] Opening {len(sampled)} PDFs from TAR …")
    results  = []

    with tarfile.open(tar_path, "r") as tf:
        members_by_name = {m.name: m for m in tf.getmembers()}

        for fname in sampled:
            member = members_by_name.get(fname)
            if member is None:
                results.append({"filename": fname, "status": "NOT_IN_TAR"})
                continue
            try:
                f   = tf.extractfile(member)
                buf = f.read()
                doc = fitz.open(stream=buf, filetype="pdf")

                page_count  = doc.page_count
                total_words = 0
                for pg in doc:
                    words = pg.get_text("words")
                    total_words += len(words)
                avg_words_per_page = total_words / page_count if page_count > 0 else 0

                is_native = avg_words_per_page >= NATIVE_WORDS_PER_PAGE_THRESHOLD
                status    = "NATIVE" if is_native else "LIKELY_SCANNED"

                res = {
                    "filename"          : fname,
                    "status"            : status,
                    "page_count"        : page_count,
                    "total_words"       : total_words,
                    "avg_words_per_page": round(avg_words_per_page, 1),
                }
                print(f"  {fname:<40} | {page_count:>3} pages | {avg_words_per_page:>6.1f} wpp | {status}")
                results.append(res)
                doc.close()

            except Exception as e:
                results.append({"filename": fname, "status": "ERROR", "error": str(e)})
                print(f"  {fname:<40} | ERROR: {e}")

    return results

# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — TAR vs Index cross-check
# ─────────────────────────────────────────────────────────────────────────────

def crosscheck_tar(tar_path: Path, index_filenames: set) -> dict:
    """Check which index files are present in TAR and vice versa."""
    print("\n[TAR CHECK] Reading TAR member list …")
    tar_filenames = set()
    with tarfile.open(tar_path, "r") as tf:
        for m in tf.getmembers():
            if m.isfile():
                # Strip leading ./ or similar
                name = Path(m.name).name
                tar_filenames.add(name)

    in_index_not_tar = index_filenames - tar_filenames
    in_tar_not_index = tar_filenames - index_filenames
    matched          = index_filenames & tar_filenames

    print(f"  Index files   : {len(index_filenames)}")
    print(f"  TAR files     : {len(tar_filenames)}")
    print(f"  Matched       : {len(matched)}")
    print(f"  Orphan (index only): {len(in_index_not_tar)}")
    print(f"  Orphan (TAR only)  : {len(in_tar_not_index)}")

    return {
        "index_count"      : len(index_filenames),
        "tar_count"        : len(tar_filenames),
        "matched_count"    : len(matched),
        "orphan_index_only": sorted(in_index_not_tar),
        "orphan_tar_only"  : sorted(in_tar_not_index),
    }

# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Build report
# ─────────────────────────────────────────────────────────────────────────────

def build_report(index_meta: dict, meta_stats: dict, crosscheck: dict,
                 pdf_samples: list, records: list) -> str:
    scanned  = [s for s in pdf_samples if s.get("status") == "LIKELY_SCANNED"]
    native   = [s for s in pdf_samples if s.get("status") == "NATIVE"]

    lines = [
        "=" * 70,
        "  HALO — SC Judgment Dataset 2023 — Phase 1 Profile Report",
        f"  Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 70,
        "",
        "── 1. INDEX OVERVIEW ─────────────────────────────────────────────────",
        f"  Year                 : {index_meta.get('year')}",
        f"  Archive type         : {index_meta.get('archive_type')}",
        f"  Files in index       : {index_meta.get('file_count')}",
        f"  Archive size         : {index_meta.get('parts', [{}])[0].get('size_human', 'N/A') if index_meta.get('parts') else 'N/A'}",
        "",
        "── 2. METADATA PROFILE ───────────────────────────────────────────────",
        f"  Total index entries  : {meta_stats['total_files']}",
        f"  Parseable filenames  : {meta_stats['parseable']}",
        f"  Unparseable          : {meta_stats['unparseable']}  ← cannot extract citation",
        f"  Usable citations     : {meta_stats['usable_citations']}  ({meta_stats['usable_pct']}%)",
        f"  Zero-span files      : {meta_stats['zero_span_files']}  ← start_page == end_page",
        f"  Duplicate case_ids   : {meta_stats['duplicate_case_ids']}",
        f"  Duplicate citations  : {meta_stats['duplicate_citations']}",
        "",
        f"  Page span  avg={meta_stats['page_span_avg']}  min={meta_stats['page_span_min']}  max={meta_stats['page_span_max']}",
        "",
        f"  Volumes present      : {meta_stats['volumes_present']}",
        "  Volume distribution  :",
    ]
    for vol, cnt in meta_stats["volume_distribution"].items():
        lines.append(f"    Volume {vol:>2} : {cnt:>3} judgments")

    lines += [
        "",
        "── 3. TAR ↔ INDEX CROSS-CHECK ───────────────────────────────────────",
        f"  Files in index       : {crosscheck['index_count']}",
        f"  Files in TAR         : {crosscheck['tar_count']}",
        f"  Matched              : {crosscheck['matched_count']}",
        f"  Orphan (index only)  : {len(crosscheck['orphan_index_only'])}",
        f"  Orphan (TAR only)    : {len(crosscheck['orphan_tar_only'])}",
    ]
    if crosscheck["orphan_index_only"]:
        lines.append("  Missing from TAR (first 10):")
        for f in crosscheck["orphan_index_only"][:10]:
            lines.append(f"    {f}")
    if crosscheck["orphan_tar_only"]:
        lines.append("  In TAR but not in index (first 10):")
        for f in crosscheck["orphan_tar_only"][:10]:
            lines.append(f"    {f}")

    lines += [
        "",
        "── 4. PDF TEXT-QUALITY SAMPLE ────────────────────────────────────────",
    ]
    if pdf_samples:
        lines.append(f"  Sampled {len(pdf_samples)} PDFs:")
        lines.append(f"  Native (text-selectable) : {len(native)}")
        lines.append(f"  Likely scanned (no text) : {len(scanned)}")
        lines.append("")
        lines.append(f"  {'Filename':<42} {'Pages':>5} {'Avg wpp':>8}  Status")
        lines.append(f"  {'-'*42} {'-'*5} {'-'*8}  {'-'*14}")
        for s in pdf_samples:
            lines.append(
                f"  {s['filename']:<42} {s.get('page_count','?'):>5} "
                f"{s.get('avg_words_per_page','?'):>8}  {s.get('status','?')}"
            )
    else:
        lines.append("  [SKIPPED — PyMuPDF not installed]")

    lines += [
        "",
        "── 5. DECISIONS & NEXT STEPS ────────────────────────────────────────",
    ]

    usable_pct = meta_stats["usable_pct"]
    if usable_pct >= 90:
        lines.append(f"  Citation usability: {usable_pct}% — GOOD. No fallback needed for Tier-1.")
    elif usable_pct >= 70:
        lines.append(f"  Citation usability: {usable_pct}% — OK. Consider a filename-based fallback.")
    else:
        lines.append(f"  Citation usability: {usable_pct}% — LOW. Tier-1 needs a robust fallback strategy.")

    scanned_pct = len(scanned) / len(pdf_samples) * 100 if pdf_samples else 0
    if scanned_pct > 20:
        lines.append(f"  Scanned PDFs: {scanned_pct:.0f}% of sample — OCR pipeline required.")
    else:
        lines.append(f"  Scanned PDFs: {scanned_pct:.0f}% of sample — PyMuPDF text extraction sufficient.")

    if crosscheck["orphan_index_only"]:
        lines.append(f"  {len(crosscheck['orphan_index_only'])} files in index not found in TAR — filter these out before ingestion.")

    lines += [
        "",
        "  Recommended next step: Phase 2 — PDF-to-paragraphs extractor.",
        "=" * 70,
    ]
    return "\n".join(lines)

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  HALO — SC Judgment Dataset 2023 — Phase 1 Profiler")
    print("=" * 70)

    # 1. Load index
    print(f"\n[STEP 1] Loading index: {INDEX_JSON}")
    index_meta = load_index(INDEX_JSON)
    all_parts  = index_meta.get("parts", [])

    # Collect all filenames from index
    all_filenames: list = []
    for part in all_parts:
        files = part.get("files", [])
        all_filenames.extend(files)
    # Fallback: top-level files key
    if not all_filenames and "files" in index_meta:
        all_filenames = index_meta["files"]

    print(f"  Total filenames in index : {len(all_filenames)}")

    # 2. Parse filenames → metadata records
    print(f"\n[STEP 2] Parsing filenames …")
    records = [parse_filename(fn) for fn in all_filenames]

    # 3. Profile metadata
    print(f"\n[STEP 3] Profiling metadata …")
    meta_stats = profile_metadata(records)
    print(f"  Parseable  : {meta_stats['parseable']}/{meta_stats['total_files']}")
    print(f"  Usable     : {meta_stats['usable_citations']} ({meta_stats['usable_pct']}%)")
    print(f"  Duplicates : {meta_stats['duplicate_case_ids']} case_ids")

    # 4. Cross-check TAR vs index
    index_fname_set = set(all_filenames)
    crosscheck = crosscheck_tar(TAR_PATH, index_fname_set)

    # 5. Sample PDFs for text quality
    usable_fnames = [r["filename"] for r in records if r.get("usable")]
    pdf_samples   = sample_pdfs(TAR_PATH, usable_fnames, SAMPLE_SIZE)

    # 6. Build and print report
    print("\n")
    report = build_report(index_meta, meta_stats, crosscheck, pdf_samples, records)
    print(report)

    # 7. Save outputs
    # Full per-record profile
    profile_data = {
        "generated_at"   : datetime.now().isoformat(),
        "source_index"   : str(INDEX_JSON),
        "source_tar"     : str(TAR_PATH),
        "index_metadata" : {k: v for k, v in index_meta.items() if k != "parts"},
        "stats"          : meta_stats,
        "crosscheck"     : crosscheck,
        "pdf_samples"    : pdf_samples,
        "records"        : records,
    }
    with open(OUT_PROFILE, "w", encoding="utf-8") as f:
        json.dump(profile_data, f, indent=2, ensure_ascii=False)
    print(f"\n[SAVE] Profile JSON  → {OUT_PROFILE}")

    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"[SAVE] Report TXT   → {OUT_REPORT}")

    # Scanned list
    scanned_fnames = [s["filename"] for s in pdf_samples if s.get("status") == "LIKELY_SCANNED"]
    with open(OUT_SCANNED, "w", encoding="utf-8") as f:
        f.write("\n".join(scanned_fnames))
    if scanned_fnames:
        print(f"[SAVE] Scanned list → {OUT_SCANNED}  ({len(scanned_fnames)} files)")
    else:
        print(f"[SAVE] Scanned list → {OUT_SCANNED}  (0 files — all native)")

    print(f"\n[DONE] Phase 1 complete. Check {OUT_REPORT} for the full summary.")


if __name__ == "__main__":
    main()
