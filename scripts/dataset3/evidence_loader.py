"""
Evidence Harvester & Read-Only Indexer for HALO Dataset 3
=========================================================
Loads frozen Dataset 1 and frozen Dataset 2 artifacts without modifying either corpus.
Provides fast in-memory indexing for benchmark generation and validation.
"""

import os
import json
from typing import Dict, List, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

D1_FINAL = os.path.join(BASE_DIR, "data", "dataset_1", "final")
D2_CANONICAL = os.path.join(BASE_DIR, "data", "dataset2", "canonical")


class EvidenceCorpus:
    def __init__(self):
        # Dataset 1 in-memory stores
        self.d1_act: Dict[str, Any] = {}
        self.d1_sections: Dict[str, Dict[str, Any]] = {}
        self.d1_passages: Dict[str, Dict[str, Any]] = {}
        self.d1_section_passages: Dict[str, List[Dict[str, Any]]] = {}
        self.d1_definitions: List[Dict[str, Any]] = []
        self.d1_cross_refs: List[Dict[str, Any]] = []
        self.d1_amendments: List[Dict[str, Any]] = []

        # Dataset 2 in-memory stores
        self.d2_judgments: Dict[str, Dict[str, Any]] = {}
        self.d2_paragraphs: Dict[str, Dict[str, Any]] = {}
        self.d2_passages: Dict[str, Dict[str, Any]] = {}
        self.d2_judgment_passages: Dict[str, List[Dict[str, Any]]] = {}
        self.d2_citations: Dict[str, Dict[str, Any]] = {}
        self.d2_judgment_citations: Dict[str, List[Dict[str, Any]]] = {}
        self.d2_cross_refs: List[Dict[str, Any]] = []

        self._loaded = False

    def load(self):
        if self._loaded:
            return

        print("[*] [EvidenceLoader] Loading Frozen Dataset 1 (Statutory Corpus)...")
        # 1. companies_act_2013.json
        act_path = os.path.join(D1_FINAL, "companies_act_2013.json")
        with open(act_path, "r", encoding="utf-8") as f:
            self.d1_act = json.load(f)

        for ch in self.d1_act.get("chapters", []):
            ch_num = ch.get("chapter_number")
            for sec in ch.get("sections", []):
                sec_id = sec["section_id"]
                sec["chapter_number"] = ch_num
                self.d1_sections[sec_id] = sec

        # 2. companies_act_2013_passages.jsonl
        d1_pas_path = os.path.join(D1_FINAL, "companies_act_2013_passages.jsonl")
        with open(d1_pas_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                p = json.loads(line)
                pid = p["passage_id"]
                self.d1_passages[pid] = p
                sec_id = p.get("section_id")
                if sec_id:
                    self.d1_section_passages.setdefault(sec_id, []).append(p)

        # 3. definitions, cross_references, amendments
        with open(os.path.join(D1_FINAL, "companies_act_2013_definitions.json"), "r", encoding="utf-8") as f:
            self.d1_definitions = json.load(f)
        with open(os.path.join(D1_FINAL, "companies_act_2013_cross_references.json"), "r", encoding="utf-8") as f:
            self.d1_cross_refs = json.load(f)
        with open(os.path.join(D1_FINAL, "companies_act_2013_amendments.json"), "r", encoding="utf-8") as f:
            self.d1_amendments = json.load(f)

        print(f"    [+] Loaded {len(self.d1_sections)} sections, {len(self.d1_passages)} passages from Dataset 1.")

        print("[*] [EvidenceLoader] Loading Frozen Dataset 2 (Judicial Corpus)...")
        # 4. judgments.jsonl
        with open(os.path.join(D2_CANONICAL, "judgments.jsonl"), "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                j = json.loads(line)
                self.d2_judgments[j["judgment_id"]] = j

        # 5. paragraphs.jsonl
        with open(os.path.join(D2_CANONICAL, "paragraphs.jsonl"), "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                para = json.loads(line)
                self.d2_paragraphs[para["paragraph_id"]] = para

        # 6. passages.jsonl
        with open(os.path.join(D2_CANONICAL, "passages.jsonl"), "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                pas = json.loads(line)
                pid = pas["passage_id"]
                self.d2_passages[pid] = pas
                jid = pas.get("document_id")
                if jid:
                    self.d2_judgment_passages.setdefault(jid, []).append(pas)

        # 7. citations.jsonl
        with open(os.path.join(D2_CANONICAL, "citations.jsonl"), "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                cit = json.loads(line)
                cid = cit["citation_id"]
                self.d2_citations[cid] = cit
                jid = cit.get("judgment_id")
                if jid:
                    self.d2_judgment_citations.setdefault(jid, []).append(cit)

        # 8. cross_references.jsonl
        with open(os.path.join(D2_CANONICAL, "cross_references.jsonl"), "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                self.d2_cross_refs.append(json.loads(line))

        print(f"    [+] Loaded {len(self.d2_judgments)} judgments, {len(self.d2_passages)} passages, {len(self.d2_citations)} citations from Dataset 2.")
        self._loaded = True

    # Helper accessors
    def get_d1_section(self, section_id: str) -> Optional[Dict[str, Any]]:
        return self.d1_sections.get(section_id)

    def get_d1_passage(self, passage_id: str) -> Optional[Dict[str, Any]]:
        return self.d1_passages.get(passage_id)

    def get_d2_judgment(self, judgment_id: str) -> Optional[Dict[str, Any]]:
        return self.d2_judgments.get(judgment_id)

    def get_d2_passage(self, passage_id: str) -> Optional[Dict[str, Any]]:
        return self.d2_passages.get(passage_id)

    def get_d2_citations_for_judgment(self, judgment_id: str) -> List[Dict[str, Any]]:
        return self.d2_judgment_citations.get(judgment_id, [])

    def get_d2_passages_for_judgment(self, judgment_id: str) -> List[Dict[str, Any]]:
        return self.d2_judgment_passages.get(judgment_id, [])


# Global singleton
corpus = EvidenceCorpus()


def get_corpus() -> EvidenceCorpus:
    if not corpus._loaded:
        corpus.load()
    return corpus
