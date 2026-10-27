"""
HALO Supreme Court Judgments Ingestion Pipeline — Phase 2: Extract & Structure
=============================================================================
Processes bulk AWS Open Data Indian Supreme Court Judgments for a given year:
1. Loads rich metadata from metadata/parquet/year=YYYY/metadata.parquet.
2. Streams and parses all judgment PDFs from data/tar/year=YYYY/english/english.tar.
3. Cleans SCR running headers, pagination, and margin guidelines (A-H).
4. Splits judgments into structured, numbered paragraph passages with full legal provenance.
5. Emits canonical JSONL passages compatible with HALO Dataset 2 judicial corpus.
"""

import os
import sys
import json
import time
import re
import tarfile
import pymupdf
import pandas as pd
from typing import Dict, List, Any, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SC_DOWNLOAD_DIR = r"C:\Users\Prithviraj\Downloads\sc"
DEFAULT_YEAR = "2023"

def clean_scr_page(txt: str) -> str:
    """Removes SCR layout artifacts: margin line-markers (A-H), running headers, and page numbers."""
    txt = re.sub(r"^[A-H]\s*[\r\n]+", "", txt, flags=re.MULTILINE)
    txt = re.sub(r"SUPREME\s+COURT\s+REPORTS[^\n]*\n?", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"\[\d{4}\]\s*\d+\s*S\.C\.R\.[^\n]*\n?", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"\b\d{4}\s*INSC\s*\d+\b[^\n]*\n?", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"^\s*\d{1,4}\s*$", "", txt, flags=re.MULTILINE)
    return txt

def extract_paragraphs_from_doc(doc: pymupdf.Document) -> List[Tuple[int, str, str]]:
    """
    Extracts text and segments into structured paragraphs.
    Returns: List of (paragraph_number, paragraph_text, extraction_type)
    """
    full_text = "\n".join(clean_scr_page(p.get_text()) for p in doc)
    
    # Normalize inline start: e.g. "Leave granted. 1. The present..." -> insert newline
    full_text = re.sub(r"(\.\s+)(\d{1,3}\.\s+[A-Z])", r"\1\n\2", full_text)
    
    # Match numbered paragraphs: newline, digits, period, whitespace, uppercase/quote
    para_pattern = re.compile(r"\n\s*(\d{1,3})\.\s+(?=[A-Z“\"'\[\(\d])")
    matches = list(para_pattern.finditer(full_text))
    
    chain = []
    expected = 1
    for m in matches:
        num = int(m.group(1))
        if num == expected or (expected == 1 and num == 1):
            chain.append((num, m.start(), m.end()))
            expected = num + 1
        elif num > expected and num <= expected + 2:
            chain.append((num, m.start(), m.end()))
            expected = num + 1

    paras = []
    if len(chain) >= 2:
        for i in range(len(chain)):
            num, start, content_start = chain[i]
            end = chain[i+1][1] if i + 1 < len(chain) else len(full_text)
            p_txt = full_text[content_start:end].strip()
            if len(p_txt) >= 20: # filter spurious empty paragraphs
                paras.append((num, p_txt, "NUMBERED"))
    else:
        # Fallback for unnumbered narrative orders
        start_pos = 0
        for marker in ["JUDGMENT / ORDER OF THE SUPREME COURT", "JUDGMENT", "ORDER"]:
            pos = full_text.find(marker)
            if pos != -1:
                start_pos = pos + len(marker)
                break
        
        body = full_text[start_pos:].strip()
        raw_paras = [p.strip() for p in re.split(r"\n\s*\n+", body) if len(p.strip()) > 50]
        for idx, p_txt in enumerate(raw_paras, 1):
            paras.append((idx, p_txt, "NARRATIVE_FALLBACK"))

    return paras

def run_extraction(year: str = DEFAULT_YEAR):
    print("=" * 75)
    print(f"HALO SUPREME COURT EXTRACTION PIPELINE: YEAR = {year}")
    print("=" * 75)

    tar_path = os.path.join(SC_DOWNLOAD_DIR, "data", "tar", f"year={year}", "english", "english.tar")
    parquet_path = os.path.join(SC_DOWNLOAD_DIR, "metadata", "parquet", f"year={year}", "metadata.parquet")
    output_dir = os.path.join(BASE_DIR, "Data", "sc_judgments", year)
    os.makedirs(output_dir, exist_ok=True)
    passages_out_file = os.path.join(output_dir, f"sc_{year}_passages.jsonl")
    summary_out_file = os.path.join(output_dir, f"sc_{year}_summary.json")

    # 1. Load Parquet Metadata
    print(f"[*] Loading Parquet metadata from: {parquet_path}...")
    df = pd.read_parquet(parquet_path)
    print(f"    [+] Loaded {len(df)} metadata records.")

    # Index metadata by 'path' column (e.g. '2023_7_322_346' -> record)
    meta_by_path = {}
    for _, row in df.iterrows():
        p = str(row.get("path", "")).strip()
        if p:
            meta_by_path[p] = row.to_dict()

    # 2. Open TAR Archive and Process PDFs
    print(f"[*] Opening TAR archive: {tar_path}...")
    t_start = time.perf_counter()

    with tarfile.open(tar_path, "r") as tf:
        members = tf.getmembers()
        print(f"    [+] Found {len(members)} PDFs in archive.")

        total_pdfs = len(members)
        total_passages = 0
        numbered_count = 0
        narrative_count = 0
        failed_count = 0

        with open(passages_out_file, "w", encoding="utf-8") as out_f:
            for i, m in enumerate(members, 1):
                # Match path key: filename e.g. "2023_7_322_346_EN.pdf" -> "2023_7_322_346"
                base_name = m.name.replace("_EN.pdf", "").replace(".pdf", "")
                meta_item = meta_by_path.get(base_name, {})

                f = tf.extractfile(m)
                pdf_bytes = f.read()
                doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")

                paras = extract_paragraphs_from_doc(doc)
                if not paras:
                    failed_count += 1
                    continue

                p_type = paras[0][2]
                if p_type == "NUMBERED":
                    numbered_count += 1
                else:
                    narrative_count += 1

                doc_id = f"JUD-SC-{year}-{base_name}"
                case_title = meta_item.get("title") or base_name
                citation = meta_item.get("citation")
                neutral_cit = meta_item.get("nc_display") or meta_item.get("case_id")
                decision_date = meta_item.get("decision_date")
                judge = meta_item.get("judge")
                author_judge = meta_item.get("author_judge")
                disposal = meta_item.get("disposal_nature")
                court = meta_item.get("court") or "Supreme Court of India"
                cnr = meta_item.get("cnr")

                for p_num, p_text, _ in paras:
                    total_passages += 1
                    pid = f"PAS-{doc_id}-P{p_num:03d}"
                    rec = {
                        "passage_id": pid,
                        "document_id": doc_id,
                        "paragraph_number": p_num,
                        "text": p_text,
                        "case_title": case_title,
                        "citation": citation,
                        "neutral_citation": neutral_cit,
                        "cnr": cnr,
                        "decision_date": decision_date,
                        "judge": judge,
                        "author_judge": author_judge,
                        "disposal_nature": disposal,
                        "court": court,
                        "extraction_type": p_type,
                        "source_file": m.name,
                        "dataset": "dataset2"
                    }
                    out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")

                if i % 100 == 0 or i == total_pdfs:
                    elapsed = time.perf_counter() - t_start
                    print(f"    [{i:3d}/{total_pdfs}] Processed {i} PDFs | Passages generated: {total_passages:,} | Elapsed: {elapsed:.1f}s")

    elapsed_total = round(time.perf_counter() - t_start, 2)
    success_rate = round((total_pdfs - failed_count) / total_pdfs * 100.0, 2)

    summary = {
        "year": year,
        "total_pdfs": total_pdfs,
        "successfully_extracted": total_pdfs - failed_count,
        "failed_pdfs": failed_count,
        "extraction_success_rate": success_rate,
        "numbered_split_count": numbered_count,
        "narrative_fallback_count": narrative_count,
        "total_passages_generated": total_passages,
        "avg_passages_per_judgment": round(total_passages / (total_pdfs - failed_count), 1),
        "elapsed_seconds": elapsed_total,
        "output_passages_file": passages_out_file
    }

    with open(summary_out_file, "w", encoding="utf-8") as sf:
        json.dump(summary, sf, indent=2)

    print("\n" + "=" * 75)
    print("EXTRACTION COMPLETE SUMMARY:")
    print("=" * 75)
    print(f"Total PDFs Processed:       {total_pdfs}")
    print(f"Extraction Success Rate:    {success_rate}% ({total_pdfs - failed_count}/{total_pdfs})")
    print(f"  - Numbered Paragraphs:    {numbered_count} ({numbered_count/total_pdfs*100:.1f}%)")
    print(f"  - Narrative Fallback:     {narrative_count} ({narrative_count/total_pdfs*100:.1f}%)")
    print(f"  - Failed / Scanned:       {failed_count}")
    print(f"Total Passages Generated:   {total_passages:,}")
    print(f"Avg Passages per Judgment:  {round(total_passages / (total_pdfs - failed_count), 1)}")
    print(f"Total Processing Time:      {elapsed_total}s ({elapsed_total/total_pdfs*1000:.1f}ms per PDF)")
    print(f"Output File:                {passages_out_file}")
    print("=" * 75)

if __name__ == "__main__":
    y = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_YEAR
    run_extraction(y)
