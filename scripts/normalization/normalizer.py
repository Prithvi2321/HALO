"""
Page-Aware Normalization, Footnote Extraction, and Boilerplate Removal.
Complies with Sections 11, 32, 44, 45, 48, 49 of prompt.md.
"""

import os
import sys
import json
import re
import unicodedata
import hashlib
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from scripts.models import NormalizedPage, Footnote


RUNNING_HEADER_PATTERNS = [
    re.compile(r"^\d+\s+THE\s+GAZETTE\s+OF\s+INDIA\s+EXTRAORDINARY.*$", re.IGNORECASE),
    re.compile(r"^SEC\.\s*\d+\]\s+THE\s+GAZETTE\s+OF\s+INDIA\s+EXTRAORDINARY\s+\d+.*$", re.IGNORECASE),
    re.compile(r"^THE\s+COMPANIES\s+ACT,\s*2013\s*$", re.IGNORECASE),
    re.compile(r"^_+\s*$", re.IGNORECASE),
]

RUNNING_FOOTER_PATTERNS = [
    re.compile(r"^IndiaCode\s*$", re.IGNORECASE),
    re.compile(r"^Page\s+\d+\s+of\s+\d+\s*$", re.IGNORECASE),
]

FOOTNOTE_PATTERN = re.compile(
    r"^\s*(\d+)\.\s+((?:Ins\.|Subs\.|The\s+|Sub-section|Clause|Section\s+\d+\s+omitted|Omitted)[\s\S]*?)$",
    re.MULTILINE
)
WEF_PATTERN = re.compile(r"\(w\.e\.f\.\s*(\d{1,2}[\-\/]\d{1,2}[\-\/]\d{4})\)", re.IGNORECASE)
ACT_PATTERN = re.compile(r"(Act\s+\d+\s+of\s+\d{4})", re.IGNORECASE)
SEC_PATTERN = re.compile(r"\b(?:s\.|sec\.|section)\s*([0-9]+[A-Z]*)", re.IGNORECASE)


def clean_line_breaks_and_hyphens(text: str) -> str:
    text = text.replace("\x02", "-")
    text = text.replace("\xad", "-")
    text = re.sub(r"([A-Za-z])-[\r\n]+([a-z])", r"\1\2", text)
    return text


def extract_page_footnotes(raw_text: str, page_num: int) -> tuple[str, list[Footnote]]:
    """
    Extracts official bottom footnotes on enacted pages (>= 16).
    Returns (body_text_without_footnotes, list_of_footnotes).
    """
    if page_num < 16:
        return raw_text, []

    lines = raw_text.splitlines()
    body_lines = []
    footnote_lines = []
    in_footnotes = False

    for line in lines:
        stripped = line.strip()
        # Footnotes appear near the bottom, matching digit dot keyword
        if not in_footnotes and re.match(r"^\s*\d+\.\s+(?:Ins\.|Subs\.|The\s+|Sub-section|Clause|Section\s+\d+\s+omitted|Omitted)", stripped):
            in_footnotes = True

        if in_footnotes:
            footnote_lines.append(line)
        else:
            body_lines.append(line)

    footnotes = []
    if footnote_lines:
        fn_block = "\n".join(footnote_lines)
        # Parse individual footnotes
        fn_matches = list(FOOTNOTE_PATTERN.finditer(fn_block))
        for m in fn_matches:
            marker = m.group(1)
            fn_text = m.group(2).strip()

            wef = WEF_PATTERN.search(fn_text)
            act = ACT_PATTERN.search(fn_text)
            sec = SEC_PATTERN.search(fn_text)

            commencement_date = None
            if wef:
                # Format to YYYY-MM-DD
                parts = wef.group(1).replace("/", "-").split("-")
                if len(parts) == 3:
                    d, m_val, y = parts[0].zfill(2), parts[1].zfill(2), parts[2]
                    commencement_date = f"{y}-{m_val}-{d}"

            footnotes.append(Footnote(
                footnote_id=f"FN_P{page_num}_{marker}",
                marker=marker,
                text=fn_text,
                source_page=page_num,
                amending_act=act.group(1) if act else None,
                amending_section=sec.group(1) if sec else None,
                commencement_date=commencement_date
            ))

    return "\n".join(body_lines), footnotes


def normalize_pages(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    raw_path = os.path.join(config["output"]["raw_dir"], "pages_extracted.json")
    norm_dir = config["output"]["normalized_dir"]
    os.makedirs(norm_dir, exist_ok=True)

    with open(raw_path, "r", encoding="utf-8") as f:
        all_raw_pages = json.load(f)

    normalized_all = {}
    boilerplate_audit = []
    all_footnotes_catalog = []

    print("[*] Beginning Enhanced Page Normalization and Footnote Extraction...")

    for doc_id, pages in all_raw_pages.items():
        doc_normalized = []
        headers_count = 0
        footers_count = 0
        total_fn_count = 0

        for page_data in pages:
            page_num = page_data["page_number"]
            raw_text = page_data["raw_text"]

            # 1. Unicode NFC normalization
            text_nfc = unicodedata.normalize("NFC", raw_text)

            # 2. Extract official footnotes on Act pages
            body_text, footnotes = extract_page_footnotes(text_nfc, page_num)
            total_fn_count += len(footnotes)
            all_footnotes_catalog.extend([f.model_dump() for f in footnotes])

            # 3. Strip running headers and footers
            lines = body_text.splitlines()
            headers_removed = []
            footers_removed = []
            filtered_lines = []
            start_idx = 0

            if lines and lines[0].strip() == str(page_num):
                headers_removed.append(lines[0].strip())
                start_idx = 1

            for idx in range(start_idx, len(lines)):
                line_str = lines[idx].strip()

                if idx < 4:
                    is_header = False
                    for pat in RUNNING_HEADER_PATTERNS:
                        if pat.match(line_str):
                            headers_removed.append(line_str)
                            is_header = True
                            break
                    if is_header:
                        continue

                if idx >= len(lines) - 3:
                    is_footer = False
                    for pat in RUNNING_FOOTER_PATTERNS:
                        if pat.match(line_str):
                            footers_removed.append(line_str)
                            is_footer = True
                            break
                    if is_footer:
                        continue

                filtered_lines.append(lines[idx])

            clean_body = "\n".join(filtered_lines)
            clean_body = clean_line_breaks_and_hyphens(clean_body)

            # Compute canonical text sha256 for the statutory body
            body_hash = hashlib.sha256(clean_body.encode("utf-8")).hexdigest()

            if headers_removed or footers_removed:
                boilerplate_audit.append({
                    "document_id": doc_id,
                    "page_number": page_num,
                    "headers_removed": headers_removed,
                    "footers_removed": footers_removed
                })
                headers_count += len(headers_removed)
                footers_count += len(footers_removed)

            norm_page = NormalizedPage(
                source_document_id=doc_id,
                page_number=page_num,
                clean_text=clean_body,
                body_text=clean_body,
                footnotes=footnotes,
                headers_removed=headers_removed,
                footers_removed=footers_removed,
                canonical_text_sha256=body_hash
            )
            doc_normalized.append(norm_page.model_dump())

        normalized_all[doc_id] = doc_normalized
        print(f"    [+] {doc_id}: Normalized {len(pages)} pages | Footnotes cataloged: {total_fn_count} | Headers/Footers stripped: {headers_count}/{footers_count}")

    # Save master normalized pages
    master_norm_file = os.path.join(norm_dir, "pages_normalized.json")
    with open(master_norm_file, "w", encoding="utf-8") as f:
        json.dump(normalized_all, f, indent=2, ensure_ascii=False)

    # Save boilerplate audit
    audit_file = os.path.join(norm_dir, "boilerplate_audit.json")
    with open(audit_file, "w", encoding="utf-8") as f:
        json.dump(boilerplate_audit, f, indent=2, ensure_ascii=False)

    # Save official footnotes index
    fn_file = os.path.join(norm_dir, "statutory_footnotes.json")
    with open(fn_file, "w", encoding="utf-8") as f:
        json.dump(all_footnotes_catalog, f, indent=2, ensure_ascii=False)

    print(f"[*] Normalized pages written to: {master_norm_file}")
    print(f"[*] Statutory Footnotes index written to: {fn_file} ({len(all_footnotes_catalog)} footnotes)")

    return {
        "master_file": master_norm_file,
        "audit_file": audit_file,
        "footnotes_file": fn_file
    }


if __name__ == "__main__":
    normalize_pages()
