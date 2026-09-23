"""
HALO Citation Verifier: Authoritative Corpus Index (D1 & D2)
============================================================
Protocol: v1.0-FROZEN
Fast, in-memory read-only index over frozen D1 (Companies Act, 2013) and D2 (Judgments).
Strictly separates Authority Existence -> Section Existence -> Subsection Existence -> Passage Resolution.
No hard-coded numeric section bounds; queries canonical index directly.
"""

import json
import re
from typing import Dict, Any, Optional, List, Tuple, Set
from pathlib import Path

from halo.citation_verifier.config import CitationVerifierConfig
from halo.citation_verifier.normalizer import CitationNormalizer
from halo.citation_verifier.schemas import AuthorityHierarchy


class CorpusIndex:
    """Read-only in-memory index for fast canonical existence and metadata lookups."""

    _instance: Optional["CorpusIndex"] = None

    def __init__(self, config: Optional[CitationVerifierConfig] = None):
        self.config = config or CitationVerifierConfig()
        self._initialized = False

        # D1 Statutory Stores
        self.d1_acts: Dict[str, Dict[str, Any]] = {}
        self.d1_sections: Dict[str, Dict[str, Any]] = {}  # sec_num -> section data
        self.d1_subsections: Dict[Tuple[str, str], Dict[str, Any]] = {}  # (sec_num, sub_num) -> sub data
        self.d1_section_passages: Dict[str, List[str]] = {}  # sec_num -> [passage_ids]
        self.d1_subsection_passages: Dict[Tuple[str, str], List[str]] = {}  # (sec_num, sub_num) -> [passage_ids]

        # D2 Judicial Stores
        self.d2_judgments_by_id: Dict[str, Dict[str, Any]] = {}
        self.d2_judgments_by_citation: Dict[str, str] = {}  # normalized citation key -> judgment_id
        self.d2_judgments_by_title: Dict[str, str] = {}  # normalized case title -> judgment_id
        self.d2_judgment_paragraphs: Dict[str, Set[int]] = {}  # judgment_id -> set of para numbers
        self.d2_judgment_passages: Dict[str, List[str]] = {}  # judgment_id -> [passage_ids]
        self.d2_paragraph_passages: Dict[Tuple[str, int], List[str]] = {}  # (judgment_id, para_num) -> [passage_ids]

        self._load_corpora()

    @classmethod
    def get_instance(cls, config: Optional[CitationVerifierConfig] = None) -> "CorpusIndex":
        """Singleton accessor for efficient reuse across queries."""
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance

    def _load_corpora(self):
        """Loads and indexes frozen D1 and D2 assets."""
        if self._initialized:
            return

        # 1. Load D1 Statutory Corpus
        self._load_d1_statute()
        self._load_d1_passages()

        # 2. Load D2 Judicial Corpus
        self._load_d2_judgments()
        self._load_d2_passages()
        self._load_d2_paragraphs()

        self._initialized = True

    def _load_d1_statute(self):
        """Loads the statutory hierarchy from companies_act_2013.json."""
        act_path = self.config.d1_act_path
        if not act_path.exists():
            return

        with open(act_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        act_title = data.get("title", "The Companies Act, 2013")
        norm_act_key = CitationNormalizer.canonical_act_key(act_title)

        self.d1_acts[norm_act_key] = {
            "document_id": data.get("document_id", "ACT_COMPANIES_2013"),
            "title": act_title,
            "short_title": "Companies Act, 2013",
            "enactment_date": data.get("enactment_date", "2013-08-29"),
            "total_sections": data.get("total_sections", 470),
        }
        # Common aliases
        self.d1_acts["COMPANIES ACT 2013"] = self.d1_acts[norm_act_key]
        self.d1_acts["COMPANIES ACT"] = self.d1_acts[norm_act_key]

        # Index chapters, sections, subsections
        for ch in data.get("chapters", []):
            ch_num = ch.get("chapter_number")
            ch_title = ch.get("heading")
            for sec in ch.get("sections", []):
                sec_num = str(sec.get("section_number", "")).strip().upper()
                if not sec_num:
                    continue

                self.d1_sections[sec_num] = {
                    "section_id": sec.get("section_id", f"ACT_COMPANIES_2013_SEC_{sec_num}"),
                    "section_number": sec_num,
                    "heading": sec.get("heading", ""),
                    "chapter_number": ch_num,
                    "chapter_title": ch_title,
                    "subsections": [str(s.get("subsection_number")) for s in sec.get("subsections", []) if s.get("subsection_number")],
                }

                # Index subsections
                for sub in sec.get("subsections", []):
                    sub_num = str(sub.get("subsection_number", "")).strip()
                    if sub_num:
                        self.d1_subsections[(sec_num, sub_num)] = {
                            "subsection_id": sub.get("subsection_id"),
                            "subsection_number": sub_num,
                            "text": sub.get("text", "")
                        }

    def _load_d1_passages(self):
        """Indexes passage IDs from companies_act_2013_passages.jsonl."""
        passages_path = self.config.d1_passages_path
        if not passages_path.exists():
            return

        with open(passages_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                p = json.loads(line)
                pid = p.get("passage_id")
                sec_id = p.get("section_id", "")
                sub_id = p.get("subsection_id")

                # Extract section number from section_id (e.g. ACT_COMPANIES_2013_SEC_135)
                sec_m = re.search(r"SEC_(\d+[A-Za-z]?)", sec_id)
                if sec_m:
                    sec_num = sec_m.group(1).upper()
                    if sec_num not in self.d1_section_passages:
                        self.d1_section_passages[sec_num] = []
                    self.d1_section_passages[sec_num].append(pid)

                    # Subsection
                    if sub_id:
                        sub_m = re.search(r"SUB_(\d+)", sub_id)
                        if sub_m:
                            sub_num = sub_m.group(1)
                            key = (sec_num, sub_num)
                            if key not in self.d1_subsection_passages:
                                self.d1_subsection_passages[key] = []
                            self.d1_subsection_passages[key].append(pid)

    def _load_d2_judgments(self):
        """Indexes judgments from judgments.jsonl."""
        judgments_path = self.config.d2_judgments_path
        if not judgments_path.exists():
            return

        with open(judgments_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                j = json.loads(line)
                jid = j.get("judgment_id")
                self.d2_judgments_by_id[jid] = j

                # Index neutral citation and reporters
                citations = j.get("citations", [])
                neutral = j.get("neutral_citation")
                all_cits = list(citations)
                if neutral and neutral not in all_cits:
                    all_cits.append(neutral)

                for cit in all_cits:
                    norm_cit_key = CitationNormalizer.canonical_reporter_key(cit)
                    if norm_cit_key:
                        self.d2_judgments_by_citation[norm_cit_key] = jid

                # Index title
                title = j.get("case_title", "")
                if title:
                    norm_title = CitationNormalizer.canonical_case_title_key(title)
                    self.d2_judgments_by_title[norm_title] = jid

    def _load_d2_passages(self):
        """Indexes passage IDs from D2 passages.jsonl."""
        passages_path = self.config.d2_passages_path
        if not passages_path.exists():
            return

        with open(passages_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                p = json.loads(line)
                pid = p.get("passage_id")
                jid = p.get("document_id")
                if jid:
                    if jid not in self.d2_judgment_passages:
                        self.d2_judgment_passages[jid] = []
                    self.d2_judgment_passages[jid].append(pid)

    def _load_d2_paragraphs(self):
        """Indexes paragraph numbers and paragraph bounds from D2 paragraphs.jsonl."""
        paras_path = self.config.d2_paragraphs_path
        if not paras_path.exists():
            return

        with open(paras_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                para = json.loads(line)
                jid = para.get("judgment_id")
                pnum = para.get("paragraph_number")
                if jid and pnum is not None:
                    if jid not in self.d2_judgment_paragraphs:
                        self.d2_judgment_paragraphs[jid] = set()
                    self.d2_judgment_paragraphs[jid].add(int(pnum))

    # ==========================================
    # Statutory Lookup APIs (Separation of Hierarchy)
    # ==========================================

    def act_exists(self, act_name: str) -> bool:
        """Determines if the cited Act exists in authoritative statutory corpus."""
        if not act_name:
            return False
        norm = CitationNormalizer.canonical_act_key(act_name)
        # Direct match or substring match against known acts
        for known_act in self.d1_acts:
            if norm == known_act or known_act in norm or norm in known_act:
                return True
        return False

    def section_exists(self, act_name: Optional[str], section_number: str) -> bool:
        """
        Determines whether a section exists in the canonical corpus.
        No hard-coded numeric bounds; queries canonical index directly.
        """
        if not section_number:
            return False
        sec_clean = CitationNormalizer.normalize_section_number(section_number)
        return sec_clean in self.d1_sections

    def subsection_exists(self, section_number: str, subsection_number: str) -> bool:
        """Determines whether a specific subsection exists for a section."""
        sec_clean = CitationNormalizer.normalize_section_number(section_number)
        sub_clean = str(subsection_number).strip()
        return (sec_clean, sub_clean) in self.d1_subsections

    def resolve_statutory_hierarchy(
        self,
        act_name: Optional[str],
        section_number: Optional[str],
        subsection_number: Optional[str]
    ) -> AuthorityHierarchy:
        """
        Hierarchical resolution: Authority -> Section -> Subsection -> Passage IDs.
        """
        auth_ok = self.act_exists(act_name) if act_name else True
        sec_clean = CitationNormalizer.normalize_section_number(section_number) if section_number else ""
        sec_ok = sec_clean in self.d1_sections if sec_clean else False
        sub_ok = self.subsection_exists(sec_clean, subsection_number) if (sec_clean and subsection_number) else False

        # Resolve retrievable passage IDs if available
        matched_pids: List[str] = []
        if sec_clean and subsection_number and (sec_clean, str(subsection_number)) in self.d1_subsection_passages:
            matched_pids = self.d1_subsection_passages[(sec_clean, str(subsection_number))]
        elif sec_clean and sec_clean in self.d1_section_passages:
            matched_pids = self.d1_section_passages[sec_clean]

        sec_meta = self.d1_sections.get(sec_clean, {})
        return AuthorityHierarchy(
            authority_exists=auth_ok,
            section_exists=sec_ok,
            subsection_exists=sub_ok,
            matched_passage_ids=matched_pids,
            details={
                "section_heading": sec_meta.get("heading", ""),
                "canonical_section_id": sec_meta.get("section_id"),
                "available_subsections": sec_meta.get("subsections", [])
            }
        )

    # ==========================================
    # Judicial Lookup APIs
    # ==========================================

    def find_judgment_by_citation(self, citation_str: str) -> Optional[str]:
        """Finds judgment_id by reporter citation (e.g. [2016] 11 S.C.R. 149, 2016 INSC 1150)."""
        if not citation_str:
            return None
        key = CitationNormalizer.canonical_reporter_key(citation_str)
        if key in self.d2_judgments_by_citation:
            return self.d2_judgments_by_citation[key]

        # Partial matching on volume and page (e.g. 2016 11 SCR 149)
        for cand_key, jid in self.d2_judgments_by_citation.items():
            if key and (key in cand_key or cand_key in key):
                return jid
        return None

    def find_judgment_by_title(self, title_str: str) -> Tuple[Optional[str], str]:
        """
        Looks up judgment by case title.
        Returns (judgment_id, confidence_tier).
        """
        if not title_str:
            return None, "NO_MATCH"

        norm_title = CitationNormalizer.canonical_case_title_key(title_str)
        if norm_title in self.d2_judgments_by_title:
            return self.d2_judgments_by_title[norm_title], "EXACT_MATCH"

        # Normalized coverage matching on distinctive legal title words
        stop_words = {"LIMITED", "PRIVATE", "AND", "ORS", "THE", "OF", "V", "PVT", "LTD"}
        norm_words = set(norm_title.split()) - stop_words
        if not norm_words:
            return None, "NO_MATCH"

        best_jid = None
        best_tier = "NO_MATCH"
        best_cov = 0.0

        for cand_title, jid in self.d2_judgments_by_title.items():
            cand_words = set(cand_title.split()) - stop_words
            inter = norm_words & cand_words
            cov = len(inter) / len(norm_words)

            if cov >= 0.7 and len(inter) >= 2 and cov > best_cov:
                best_jid = jid
                best_tier = "NORMALIZED_MATCH"
                best_cov = cov
            elif cov >= 0.3 and len(inter) >= 2 and best_tier != "NORMALIZED_MATCH" and cov > best_cov:
                best_jid = jid
                best_tier = "FUZZY_CANDIDATE"
                best_cov = cov

        return best_jid, best_tier


    def get_judgment(self, judgment_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves authoritative judgment metadata."""
        return self.d2_judgments_by_id.get(judgment_id)

    def paragraph_exists_in_judgment(self, judgment_id: str, paragraph_num: int) -> bool:
        """Determines whether a paragraph exists within the judgment's paragraph bounds."""
        paras = self.d2_judgment_paragraphs.get(judgment_id, set())
        return paragraph_num in paras

    def get_max_paragraph_in_judgment(self, judgment_id: str) -> int:
        """Returns the maximum paragraph number in the judgment."""
        paras = self.d2_judgment_paragraphs.get(judgment_id, set())
        return max(paras) if paras else 0

    def resolve_judicial_passages(self, judgment_id: str, paragraph_num: Optional[int] = None) -> List[str]:
        """Resolves retrievable passage IDs for the judgment or paragraph."""
        pids = self.d2_judgment_passages.get(judgment_id, [])
        return pids
