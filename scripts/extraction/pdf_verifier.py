"""
PDF Integrity Verification.
Complies with Section 7 of prompt.md.
"""

import os
import sys
import json
import yaml
import pypdfium2 as pdfium

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from scripts.download.discover import compute_sha256


def verify_pdfs(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    meta_path = os.path.join(config["output"]["staged_dir"], "metadata", "source_manifest.json")
    with open(meta_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    staged_base = config["output"]["staged_dir"]
    val_dir = config["output"]["validation_dir"]
    os.makedirs(val_dir, exist_ok=True)

    report_items = []
    all_passed = True

    print("[*] Running PDF Integrity Verification...")

    for doc_meta in manifest:
        doc_id = doc_meta["source_document_id"]
        # Find file path in staged dir
        found_path = None
        for root, _, files in os.walk(staged_base):
            if doc_meta["file_name"] in files:
                found_path = os.path.join(root, doc_meta["file_name"])
                break

        if not found_path or not os.path.exists(found_path):
            report_items.append({
                "document_id": doc_id,
                "pdf_valid": False,
                "error": f"File not found: {doc_meta['file_name']}",
                "warnings": ["FILE_MISSING"]
            })
            all_passed = False
            continue

        curr_hash = compute_sha256(found_path)
        hash_match = (curr_hash == doc_meta["sha256"])

        warnings = []
        if not hash_match:
            warnings.append("SHA256_MISMATCH")
            all_passed = False

        try:
            doc = pdfium.PdfDocument(found_path)
            page_count = len(doc)
            is_encrypted = False  # If opened successfully without password, not locked
            empty_pages = []
            corrupted_pages = []
            pages_with_text = 0

            for i in range(page_count):
                try:
                    page = doc[i]
                    textpage = page.get_textpage()
                    txt = textpage.get_text_range().strip()
                    if len(txt) == 0:
                        empty_pages.append(i + 1)
                    else:
                        pages_with_text += 1
                except Exception as pe:
                    corrupted_pages.append(i + 1)

            if empty_pages:
                warnings.append(f"EMPTY_PAGES: {empty_pages}")
            if corrupted_pages:
                warnings.append(f"CORRUPTED_PAGES: {corrupted_pages}")
                all_passed = False

            has_embedded_text = (pages_with_text > 0)
            requires_ocr = (pages_with_text < page_count)

            item = {
                "document_id": doc_id,
                "file_name": doc_meta["file_name"],
                "pdf_valid": len(corrupted_pages) == 0 and hash_match,
                "page_count": page_count,
                "expected_page_count": doc_meta["page_count"],
                "has_embedded_text": has_embedded_text,
                "requires_ocr": requires_ocr,
                "sha256": curr_hash,
                "warnings": warnings
            }
            report_items.append(item)
            print(f"    [+] {doc_id}: Valid={item['pdf_valid']}, Pages={page_count}, EmbeddedText={has_embedded_text}, Warnings={warnings}")

        except Exception as e:
            report_items.append({
                "document_id": doc_id,
                "pdf_valid": False,
                "error": str(e),
                "warnings": ["PDF_OPEN_FAILED"]
            })
            all_passed = False

    result = {
        "status": "PASS" if all_passed else "FAIL",
        "documents": report_items
    }

    report_path = os.path.join(val_dir, "pdf_integrity_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"[*] PDF Integrity Report written to {report_path}")
    return result


if __name__ == "__main__":
    verify_pdfs()
