"""
HALO Dataset 2: Supreme Court Adapter (Optimized Concurrent)
============================================================
Queries the verified public Supreme Court Reports (SCR) repository
for metadata discovery and selective document acquisition using concurrent workers.
"""

import os
import re
import json
import time
import hashlib
import logging
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict, Any, Optional
import bs4

from .base import LegalSourceAdapter
from ..models import CandidateJudgment, SourceSnapshot, SourceAuthority, CourtType, LifecycleState

logger = logging.getLogger("halo.dataset_2.sc_adapter")


class SupremeCourtAdapter(LegalSourceAdapter):
    """Adapter for official Supreme Court of India SCR digital records."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.court_enum = CourtType.SUPREME_COURT_OF_INDIA
        self.metadata_prefix = config.get("metadata_prefix", "metadata/json/year={year}/")
        self.document_prefix = config.get("document_prefix", "data/pdf/year={year}/english/")
        self.document_suffix = config.get("document_suffix", "_EN.pdf")

    def _parse_html_metadata(self, raw_html: str, key: str, year: int) -> Dict[str, Any]:
        """Parses the embedded HTML metadata block from SCR records."""
        soup = bs4.BeautifulSoup(raw_html, "html.parser")
        meta = {
            "case_title": "Unknown Title",
            "case_number": "",
            "decision_date": None,
            "citations": [],
            "coram": [],
            "bench": "",
            "subject": "",
            "raw_text": soup.get_text(separator=" ", strip=True)
        }

        btn = soup.find("button", id=lambda x: x and x.startswith("link_"))
        if btn:
            strong = btn.find("strong")
            if strong:
                meta["case_title"] = strong.get_text(strip=True).replace("versus", " v. ")

        escr = soup.find("span", class_="escrText")
        if escr:
            meta["citations"].append(escr.get_text(strip=True))

        nc = soup.find("span", class_="ncDisplay")
        if nc:
            meta["citations"].append(nc.get_text(strip=True))

        text = soup.get_text(separator=" | ", strip=True)
        coram_match = re.search(r"Coram\s*:\s*([^|]+)", text, re.IGNORECASE)
        if coram_match:
            judges = [j.strip().rstrip("*") for j in coram_match.group(1).split(",") if j.strip()]
            meta["coram"] = judges

        date_match = re.search(r"Decision Date\s*:\s*([0-9]{2}-[0-9]{2}-[0-9]{4})", text, re.IGNORECASE)
        if date_match:
            raw_d = date_match.group(1)
            try:
                dt = datetime.strptime(raw_d, "%d-%m-%Y")
                meta["decision_date"] = dt.strftime("%Y-%m-%d")
            except Exception:
                meta["decision_date"] = raw_d

        case_no_match = re.search(r"Case No\s*:\s*([^|]+)", text, re.IGNORECASE)
        if case_no_match:
            meta["case_number"] = case_no_match.group(1).strip()

        bench_match = re.search(r"Bench\s*:\s*([^|]+)", text, re.IGNORECASE)
        if bench_match:
            meta["bench"] = bench_match.group(1).strip()

        return meta

    def _fetch_single_meta(self, k: str, yr: int, lowered_terms: List[str]) -> Optional[CandidateJudgment]:
        meta_url = f"{self.base_url}/{k}"
        req = urllib.request.Request(meta_url, headers={"User-Agent": "HALO-Curation-Agent/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=8) as mresp:
                mdata = json.loads(mresp.read().decode("utf-8"))
                raw_html = mdata.get("raw_html", "")
                raw_lower = raw_html.lower()

                matched = [t for t in lowered_terms if t in raw_lower]
                if matched:
                    parsed = self._parse_html_metadata(raw_html, k, yr)
                    item_path = mdata.get("path", "")
                    if not item_path:
                        item_path = k.split("/")[-1].replace(".json", "")

                    doc_url = f"{self.base_url}/{self.document_prefix.format(year=yr)}{item_path}{self.document_suffix}"
                    cand_id = f"CAND-SC-{yr}-{item_path}"

                    return CandidateJudgment(
                        candidate_id=cand_id,
                        source_id=self.source_id,
                        court=self.court_enum,
                        bench=parsed.get("bench"),
                        case_title=parsed.get("case_title", "Unknown Title"),
                        case_number=parsed.get("case_number"),
                        decision_date=parsed.get("decision_date"),
                        citations=parsed.get("citations", []),
                        coram=parsed.get("coram", []),
                        discovery_terms=matched,
                        topic_tags=[],
                        source_url=doc_url,
                        source_authority=self.source_authority,
                        lifecycle_state=LifecycleState.DISCOVERED,
                        relevance_score=None,
                        selection_status="PENDING"
                    )
        except Exception:
            pass
        return None

    def discover_candidates(
        self,
        query_terms: List[str],
        year_range: Optional[List[int]] = None,
        max_results: int = 50
    ) -> List[CandidateJudgment]:
        if not self.enabled:
            return []

        years = year_range or [2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015, 2014, 2013]
        candidates = []
        lowered_terms = [t.lower() for t in query_terms]

        for yr in years:
            if len(candidates) >= max_results:
                break
            prefix = self.metadata_prefix.format(year=yr)
            list_url = f"{self.base_url}/?prefix={prefix}&max-keys=60"
            req = urllib.request.Request(list_url, headers={"User-Agent": "HALO-Curation-Agent/1.0"})

            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    tree = ET.fromstring(resp.read().decode("utf-8"))
                    ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
                    keys = [elem.text for elem in tree.findall("s3:Contents/s3:Key", ns) if elem.text.endswith(".json")]

                # Sample up to 30 keys per year concurrently
                keys_to_scan = keys[:30]
                with ThreadPoolExecutor(max_workers=8) as executor:
                    futures = [executor.submit(self._fetch_single_meta, k, yr, lowered_terms) for k in keys_to_scan]
                    for fut in as_completed(futures):
                        res = fut.result()
                        if res:
                            candidates.append(res)
                            logger.info(f"    [+] Discovered SC candidate: {res.candidate_id} | {res.case_title[:45]}")
                            if len(candidates) >= max_results:
                                break
            except Exception as e:
                logger.warning(f"Error querying year {yr}: {e}")

        return candidates

    def fetch_metadata(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        parts = candidate_id.split("-")
        if len(parts) >= 4:
            yr = parts[2]
            item_path = "-".join(parts[3:])
            meta_url = f"{self.base_url}/{self.metadata_prefix.format(year=yr)}{item_path}.json"
            req = urllib.request.Request(meta_url, headers={"User-Agent": "HALO-Curation-Agent/1.0"})
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                logger.error(f"Error fetching metadata for {candidate_id}: {e}")
        return None

    def download_document(
        self,
        candidate: CandidateJudgment,
        target_dir: str
    ) -> Optional[SourceSnapshot]:
        os.makedirs(target_dir, exist_ok=True)
        filename = f"{candidate.candidate_id}.pdf"
        target_path = os.path.join(target_dir, filename)

        req = urllib.request.Request(candidate.source_url, headers={"User-Agent": "HALO-Curation-Agent/1.0"})
        try:
            start_time = datetime.utcnow().isoformat() + "Z"
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                headers = dict(resp.headers)

            with open(target_path, "wb") as f:
                f.write(data)

            sha256 = hashlib.sha256(data).hexdigest()
            file_size = len(data)

            return SourceSnapshot(
                source_id=self.source_id,
                source_authority=self.source_authority,
                source_url=candidate.source_url,
                retrieval_timestamp=start_time,
                http_metadata={
                    "status_code": 200,
                    "etag": headers.get("ETag", ""),
                    "content_length": int(headers.get("Content-Length", file_size)),
                    "content_type": headers.get("Content-Type", "application/pdf")
                },
                file_size=file_size,
                sha256=sha256,
                license=self.config.get("licensing", "CC-BY-4.0")
            )
        except Exception as e:
            logger.error(f"Failed to download document for {candidate.candidate_id}: {e}")
            return None
