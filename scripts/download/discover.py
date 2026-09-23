"""
PDF Discovery, Hashing, Staging and Manifest Generation.
Strictly adheres to Section 6 of prompt.md.
"""

import os
import sys
import shutil
import hashlib
import json
from datetime import datetime, timezone
import yaml
import pypdfium2 as pdfium

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from scripts.models import SourceDocumentManifest, VersionType


def compute_sha256(filepath: str) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def run_discovery(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    input_cfg = config["input"]
    output_cfg = config["output"]
    data_dir = input_cfg["data_dir"]

    # Target staging directories
    staged_base = output_cfg["staged_dir"]
    orig_dir = os.path.join(staged_base, "original")
    amend_dir = os.path.join(staged_base, "amendments")
    consol_dir = os.path.join(staged_base, "consolidated")
    meta_dir = os.path.join(staged_base, "metadata")

    for d in [orig_dir, amend_dir, consol_dir, meta_dir]:
        os.makedirs(d, exist_ok=True)

    # Document definitions
    doc_specs = [
        {
            "key": "original_act",
            "file_name": input_cfg["files"]["original_act"],
            "doc_id": "ACT_COMPANIES_2013",
            "doc_type": "Central Act",
            "title": "The Companies Act, 2013",
            "act_title": "The Companies Act, 2013",
            "act_number": "18 of 2013",
            "publication_date": "2013-08-30",
            "enactment_date": "2013-08-29",
            "effective_date": "2013-09-12",
            "version_type": VersionType.ORIGINAL,
            "as_of_date": "2020-09-28",  # IndiaCode official publication consolidated up to 2020
            "source_name": "India Code / Ministry of Corporate Affairs",
            "source_url": "https://www.indiacode.nic.in/handle/123456789/2114",
            "staging_subfolder": "original",
            "staging_filename": "companies_act_2013_original.pdf"
        },
        {
            "key": "amendment_2015",
            "file_name": input_cfg["files"]["amendment_2015"],
            "doc_id": "ACT_COMPANIES_AMEND_2015",
            "doc_type": "Amending Act",
            "title": "The Companies (Amendment) Act, 2015",
            "act_title": "The Companies (Amendment) Act, 2015",
            "act_number": "21 of 2015",
            "publication_date": "2015-05-26",
            "enactment_date": "2015-05-25",
            "effective_date": "2015-05-29",
            "version_type": VersionType.AMENDMENT,
            "as_of_date": "2015-05-29",
            "source_name": "The Gazette of India Extraordinary",
            "source_url": "https://www.mca.gov.in",
            "staging_subfolder": "amendments",
            "staging_filename": "amendment_2015.pdf"
        },
        {
            "key": "amendment_2020",
            "file_name": input_cfg["files"]["amendment_2020"],
            "doc_id": "ACT_COMPANIES_AMEND_2020",
            "doc_type": "Amending Act",
            "title": "The Companies (Amendment) Act, 2020",
            "act_title": "The Companies (Amendment) Act, 2020",
            "act_number": "29 of 2020",
            "publication_date": "2020-09-28",
            "enactment_date": "2020-09-28",
            "effective_date": "2020-12-21",
            "version_type": VersionType.AMENDMENT,
            "as_of_date": "2020-12-21",
            "source_name": "The Gazette of India Extraordinary",
            "source_url": "https://www.mca.gov.in",
            "staging_subfolder": "amendments",
            "staging_filename": "amendment_2020.pdf"
        }
    ]

    manifest_records = []
    now_iso = datetime.now(timezone.utc).isoformat()

    print(f"[*] Discovering documents in {data_dir}...")
    for spec in doc_specs:
        src_path = os.path.join(data_dir, spec["file_name"])
        if not os.path.exists(src_path):
            raise FileNotFoundError(f"Required document not found: {src_path}")

        file_size = os.path.getsize(src_path)
        sha256 = compute_sha256(src_path)

        # Count pages using pdfium
        pdf = pdfium.PdfDocument(src_path)
        page_count = len(pdf)

        # Stage file without overwriting source
        dest_dir = os.path.join(staged_base, spec["staging_subfolder"])
        dest_path = os.path.join(dest_dir, spec["staging_filename"])
        shutil.copy2(src_path, dest_path)

        # If it's the base act, also stage a reference copy to consolidated/
        if spec["key"] == "original_act":
            shutil.copy2(src_path, os.path.join(consol_dir, "companies_act_2013_current.pdf"))

        record = SourceDocumentManifest(
            source_document_id=spec["doc_id"],
            document_type=spec["doc_type"],
            title=spec["title"],
            act_title=spec["act_title"],
            act_number=spec["act_number"],
            publication_date=spec["publication_date"],
            enactment_date=spec["enactment_date"],
            effective_date=spec["effective_date"],
            version_type=spec["version_type"],
            as_of_date=spec["as_of_date"],
            source_name=spec["source_name"],
            source_url=spec["source_url"],
            downloaded_at=now_iso,
            file_name=spec["staging_filename"],
            file_size_bytes=file_size,
            sha256=sha256,
            page_count=page_count,
            mime_type="application/pdf"
        )
        manifest_records.append(record.model_dump())
        print(f"    [+] Discovered: {spec['title']} ({page_count} pages, {file_size} bytes, SHA: {sha256[:12]}...)")

    manifest_path = os.path.join(meta_dir, "source_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_records, f, indent=2, ensure_ascii=False)

    print(f"[*] Generated Source Manifest at: {manifest_path}")
    return {"manifest_path": manifest_path, "documents": manifest_records}


if __name__ == "__main__":
    run_discovery()
