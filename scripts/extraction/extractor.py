"""
Text Extraction Engine with Page-by-Page Mapping and OCR Fallback.
Complies with Section 8, 9, and 10 of prompt.md.
"""

import os
import sys
import json
import yaml
import hashlib
import pypdfium2 as pdfium

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from scripts.models import ExtractedPage
from scripts.extraction.ocr_fallback import ocr_page


def extract_pages(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    meta_path = os.path.join(config["output"]["staged_dir"], "metadata", "source_manifest.json")
    with open(meta_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    raw_dir = config["output"]["raw_dir"]
    staged_base = config["output"]["staged_dir"]
    os.makedirs(raw_dir, exist_ok=True)

    min_chars = config["extraction"].get("min_chars_per_page", 50)
    ocr_enabled = config["extraction"].get("ocr_fallback_enabled", True)

    all_extracted = {}
    total_pages_extracted = 0
    total_ocr_pages = 0

    print("[*] Beginning Text Extraction across all documents...")

    for doc_meta in manifest:
        doc_id = doc_meta["source_document_id"]
        file_name = doc_meta["file_name"]

        found_path = None
        for root, _, files in os.walk(staged_base):
            if file_name in files:
                found_path = os.path.join(root, file_name)
                break

        if not found_path:
            raise FileNotFoundError(f"File {file_name} not found in staged directory.")

        pdf = pdfium.PdfDocument(found_path)
        page_count = len(pdf)
        doc_pages = []

        print(f"    [*] Extracting {doc_id} ({page_count} pages)...")

        for p_idx in range(page_count):
            page_num = p_idx + 1
            page = pdf[p_idx]
            textpage = page.get_textpage()
            raw_text = textpage.get_text_bounded() or ""
            char_count = len(raw_text.strip())

            method = "native_pdf"
            ocr_conf = None
            warnings = []

            if char_count < min_chars and ocr_enabled:
                print(f"        [!] Page {page_num} has only {char_count} chars. Triggering OCR fallback...")
                ocr_text, avg_conf = ocr_page(found_path, p_idx)
                if len(ocr_text.strip()) > char_count:
                    raw_text = ocr_text
                    char_count = len(ocr_text.strip())
                    method = "ocr"
                    ocr_conf = avg_conf
                    total_ocr_pages += 1
                else:
                    warnings.append("OCR_YIELDED_FEWER_CHARS")

            raw_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
            page_obj = ExtractedPage(
                source_document_id=doc_id,
                page_number=page_num,
                char_count=char_count,
                raw_text=raw_text,
                raw_text_sha256=raw_hash,
                extraction_method=method,
                ocr_confidence=ocr_conf,
                warnings=warnings
            )
            doc_pages.append(page_obj.model_dump())
            total_pages_extracted += 1

        all_extracted[doc_id] = doc_pages

        # Save per-document raw pages
        doc_raw_file = os.path.join(raw_dir, f"{doc_id}_pages.json")
        with open(doc_raw_file, "w", encoding="utf-8") as f:
            json.dump(doc_pages, f, indent=2, ensure_ascii=False)
        print(f"        [+] Saved {page_count} pages to {doc_raw_file}")

    # Master raw dump
    master_file = os.path.join(raw_dir, "pages_extracted.json")
    with open(master_file, "w", encoding="utf-8") as f:
        json.dump(all_extracted, f, indent=2, ensure_ascii=False)

    print(f"[*] Total pages extracted: {total_pages_extracted}, OCR fallback pages: {total_ocr_pages}")
    print(f"[*] Master extracted file: {master_file}")

    return {
        "master_file": master_file,
        "total_pages": total_pages_extracted,
        "ocr_pages": total_ocr_pages
    }


if __name__ == "__main__":
    extract_pages()
