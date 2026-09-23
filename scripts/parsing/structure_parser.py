"""
Legislative Structure Parser for the Companies Act, 2013.
Complies with Sections 12-18, 30-33, 40, 43, 46 of prompt.md.
Upgraded with Footnote indexing, Editorial Markers, Clean Canonical Text,
Explicit Temporal Lifecycle, and 4-tier Cryptographic Lineage.
"""

import os
import sys
import json
import re
import hashlib
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from scripts.models import (
    SectionNode, SubsectionNode, ClauseNode, ProvisoNode, ExplanationNode,
    ChapterNode, EditorialMarker, Footnote, EnforcementStatus
)


def compute_text_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def clean_to_canonical(text: str) -> str:
    """
    Produces clean statutory text suitable for BM25 and dense retrieval
    by unwrapping editorial amendment markers and stripping omission asterisks.
    """
    # 1. Remove editorial omission asterisks e.g. '4***', ' 1* * *'
    cleaned = re.sub(r"\s*\d+\s*\*[\*\s]*", "", text)
    # 2. Recursively unwrap bracketed amendments e.g. 3[...] -> ...
    pat = re.compile(r"\d+\s*\[([\s\S]*?)\]")
    while True:
        subbed, n = pat.subn(r"\1", cleaned)
        if n == 0:
            break
        cleaned = subbed
    # 3. Clean any orphaned bracket artifacts if any
    cleaned = re.sub(r"\[\s*", "", cleaned)
    cleaned = re.sub(r"\s*\]", "", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n[ \t]+", "\n", cleaned)
    return cleaned.strip()


def extract_editorial_markers_from_text(
    text: str,
    page_start: int,
    page_end: int,
    all_footnotes: list[dict],
    location: str = "section_text"
) -> tuple[list[EditorialMarker], list[Footnote]]:
    """
    Extracts editorial markers (like 3[...] or 4***) and links them to
    authoritative footnotes published at the bottom of the page.
    """
    markers = []
    associated_footnotes = []

    candidate_fns = [
        f for f in all_footnotes
        if (page_start - 1) <= f["source_page"] <= (page_end + 1)
    ]

    # 1. Bracketed markers \d+\[...\]
    for m in re.finditer(r"(\d+)\s*\[([\s\S]*?)\]", text):
        m_num = m.group(1)
        raw_snip = m.group(0)[:80].replace("\n", " ").strip()
        matched_fn = next((f for f in candidate_fns if f["marker"] == m_num), None)
        target_id = matched_fn["footnote_id"] if matched_fn else f"FN_P{page_start}_{m_num}"

        markers.append(EditorialMarker(
            marker=m_num,
            location=location,
            target=target_id,
            target_footnote_id=target_id,
            raw_snippet=raw_snip
        ))
        if matched_fn and matched_fn["footnote_id"] not in [f.footnote_id for f in associated_footnotes]:
            associated_footnotes.append(Footnote(**matched_fn))

    # 2. Asterisk omission markers \d+\*\*\*
    for m in re.finditer(r"(\d+)\s*\*[\*\s]*", text):
        m_num = m.group(1)
        raw_snip = m.group(0).strip()
        matched_fn = next((f for f in candidate_fns if f["marker"] == m_num), None)
        target_id = matched_fn["footnote_id"] if matched_fn else f"FN_P{page_start}_{m_num}"

        markers.append(EditorialMarker(
            marker=m_num,
            location="omission",
            target=target_id,
            target_footnote_id=target_id,
            raw_snippet=raw_snip
        ))
        if matched_fn and matched_fn["footnote_id"] not in [f.footnote_id for f in associated_footnotes]:
            associated_footnotes.append(Footnote(**matched_fn))

    return markers, associated_footnotes


def parse_provisos_and_explanations(text: str, page_start: int, page_end: int, parent_id: str, all_footnotes: list[dict]):
    provisos = []
    explanations = []

    # Detect provisos: Provided that, Provided further that, Provided also that
    proviso_pat = re.compile(
        r"(Provided\s+(?:further\s+|also\s+)?that\s+[\s\S]*?)(?=(?:Provided\s+(?:further\s+|also\s+)?that|Explanation|\([0-9a-z]+\)|$))",
        re.IGNORECASE
    )
    p_idx = 1
    for m in proviso_pat.finditer(text):
        p_text = m.group(1).strip()
        p_type = "proviso"
        if "further" in p_text[:20].lower():
            p_type = "further_proviso"
        elif "also" in p_text[:20].lower():
            p_type = "also_proviso"

        p_canonical = clean_to_canonical(p_text)
        provisos.append(ProvisoNode(
            proviso_id=f"{parent_id}_PROV_{p_idx}",
            proviso_type=p_type,
            text=p_text,
            canonical_text=p_canonical,
            source_page_start=page_start,
            source_page_end=page_end
        ))
        p_idx += 1

    # Detect explanations: Explanation.— or Explanation:
    exp_pat = re.compile(
        r"(Explanation(?:\s*\d+)?\s*[\.\:―—\-]\s*[\s\S]*?)(?=(?:Explanation|Provided|\([0-9a-z]+\)|$))",
        re.IGNORECASE
    )
    e_idx = 1
    for m in exp_pat.finditer(text):
        e_text = m.group(1).strip()
        e_canonical = clean_to_canonical(e_text)
        explanations.append(ExplanationNode(
            explanation_id=f"{parent_id}_EXP_{e_idx}",
            explanation_number=str(e_idx),
            text=e_text,
            canonical_text=e_canonical,
            source_page_start=page_start,
            source_page_end=page_end
        ))
        e_idx += 1

    return provisos, explanations


ROMAN_NUMS = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii", "xiii", "xiv", "xv"]
ROMAN_SET = set(ROMAN_NUMS)


def is_roman(s: str) -> bool:
    return s.lower() in ROMAN_SET


def parse_clauses_from_text(text: str, parent_id: str, page_start: int, page_end: int, all_footnotes: list[dict]) -> list[ClauseNode]:
    """
    Parses clauses: (a), (b), (c) etc. and nests Roman numeral sub-clauses (i), (ii) under their parent clause.
    Correctly excludes provisos and explanations from bleeding duplicate clauses into the parent.
    Eliminates false positives from internal citations like 'under clause (a)' or 'sub-clause (i)'.
    """
    # 1. Split body from provisos, explanations, or part headers
    m_supp = re.search(r"(?:^|[\r\n]+)\s*(?:(?:\d+\s*\[\s*)?(?:Provided\b|Explanation\b)|(?:PART\s+[IVXLCDM]+))", text)
    body_text = text[:m_supp.start()].strip() if m_supp else text.strip()

    # 2. Find all candidates of form (x)
    pat = re.compile(r"(?:^|[\r\n]+|\;\s*)\(([a-zA-Z0-9]+)\)\s+")
    matches = list(pat.finditer(body_text))

    candidates = []
    for m in matches:
        ident = m.group(1).lower()
        start = m.start()
        prefix = body_text[max(0, start - 30):start].lower()
        # Filter out statutory citations
        if re.search(r"\b(?:sub-section|sub-sections|sub-clause|sub-clauses|section|sections|clause|clauses|under|to|in|of|and|or)\s*$", prefix):
            continue
        candidates.append((ident, m.start(), m.end()))

    if not candidates:
        return []

    alpha_candidates = [c for c in candidates if re.match(r"^[a-z]{1,2}$", c[0]) and not is_roman(c[0])]

    clauses = []
    if alpha_candidates or any(c[0] in ["a", "b", "c"] for c in candidates):
        top_clauses = []
        for c in candidates:
            ident = c[0]
            if is_roman(ident):
                if ident == "i":
                    last_alpha = [tc[0] for tc in top_clauses if not is_roman(tc[0])]
                    if last_alpha and last_alpha[-1] == "h":
                        top_clauses.append(c)
                        continue
                continue
            if re.match(r"^[a-z]{1,2}$", ident):
                if not any(tc[0] == ident for tc in top_clauses):
                    top_clauses.append(c)

        for idx, (ident, c_start, content_start) in enumerate(top_clauses):
            end_pos = top_clauses[idx + 1][1] if idx + 1 < len(top_clauses) else len(body_text)
            cl_content = body_text[content_start:end_pos].strip()
            cl_id = f"{parent_id}_CLAUSE_{ident.upper()}"
            cl_text = f"({ident}) {cl_content}"
            cl_canonical = clean_to_canonical(cl_text)
            cl_markers, _ = extract_editorial_markers_from_text(cl_text, page_start, page_end, all_footnotes, location="clause_text")

            # Parse sub-clauses (i), (ii), etc. nested inside this clause
            sub_matches = list(pat.finditer(cl_content))
            sub_candidates = []
            for sm in sub_matches:
                s_ident = sm.group(1).lower()
                s_start = sm.start()
                s_prefix = cl_content[max(0, s_start - 30):s_start].lower()
                if re.search(r"\b(?:sub-section|sub-sections|sub-clause|sub-clauses|section|sections|clause|clauses|under|to|in|of|and|or)\s*$", s_prefix):
                    continue
                if is_roman(s_ident):
                    if not any(sc[0] == s_ident for sc in sub_candidates):
                        sub_candidates.append((s_ident, sm.start(), sm.end()))

            sub_clauses = []
            for s_idx, (s_ident, s_c_start, s_content_start) in enumerate(sub_candidates):
                s_end_pos = sub_candidates[s_idx + 1][1] if s_idx + 1 < len(sub_candidates) else len(cl_content)
                s_text = f"({s_ident}) {cl_content[s_content_start:s_end_pos].strip()}"
                s_canonical = clean_to_canonical(s_text)
                s_markers, _ = extract_editorial_markers_from_text(s_text, page_start, page_end, all_footnotes, location="subclause_text")
                sub_clauses.append(ClauseNode(
                    clause_id=f"{cl_id}_SUBCLAUSE_{s_ident.upper()}",
                    clause_identifier=f"({s_ident})",
                    text=s_text,
                    canonical_text=s_canonical,
                    editorial_markers=s_markers,
                    sub_clauses=[],
                    source_page_start=page_start,
                    source_page_end=page_end,
                    content_hash=compute_text_hash(s_canonical)
                ))

            clauses.append(ClauseNode(
                clause_id=cl_id,
                clause_identifier=f"({ident})",
                text=cl_text,
                canonical_text=cl_canonical,
                editorial_markers=cl_markers,
                sub_clauses=sub_clauses,
                source_page_start=page_start,
                source_page_end=page_end,
                content_hash=compute_text_hash(cl_canonical)
            ))
    else:
        roman_candidates = []
        for c in candidates:
            if is_roman(c[0]) and not any(rc[0] == c[0] for rc in roman_candidates):
                roman_candidates.append(c)

        for idx, (ident, c_start, content_start) in enumerate(roman_candidates):
            end_pos = roman_candidates[idx + 1][1] if idx + 1 < len(roman_candidates) else len(body_text)
            cl_content = body_text[content_start:end_pos].strip()
            cl_id = f"{parent_id}_CLAUSE_{ident.upper()}"
            cl_text = f"({ident}) {cl_content}"
            cl_canonical = clean_to_canonical(cl_text)
            cl_markers, _ = extract_editorial_markers_from_text(cl_text, page_start, page_end, all_footnotes, location="clause_text")

            clauses.append(ClauseNode(
                clause_id=cl_id,
                clause_identifier=f"({ident})",
                text=cl_text,
                canonical_text=cl_canonical,
                editorial_markers=cl_markers,
                sub_clauses=[],
                source_page_start=page_start,
                source_page_end=page_end,
                content_hash=compute_text_hash(cl_canonical)
            ))

    return clauses


def parse_subsections_from_text(text: str, section_id: str, page_start: int, page_end: int, all_footnotes: list[dict]) -> list[SubsectionNode]:
    """
    Parses numbered subsections: (1), (2), (3) etc. using sequential offset slicing.
    Correctly ignores internal citations such as 'under sub-section (4)' or 'clause (1)'.
    Captures nested clauses, provisos, and explanations within each subsection.
    """
    pat = re.compile(r"(?:^|[\r\n]+|(?<=[.—–—]))\s*(?:\d+\[)?\((\d+[A-Z]?)\)\s+")
    candidates = []
    for m in pat.finditer(text):
        num = m.group(1)
        start_idx = m.start()
        prefix = text[max(0, start_idx - 30):start_idx].lower()
        if re.search(r"\b(?:sub-section|sub-sections|sub-clause|sub-clauses|section|sections|clause|clauses|under|and|or|in|to)\s*$", prefix):
            continue
        candidates.append((num, m.start(), m.end()))

    if not candidates:
        return []

    # Enforce sequential progression: must begin with 1 (or 1A), and never duplicate an existing subsection number
    sub_starts = []
    for num, s_start, s_end in candidates:
        if not sub_starts:
            if num in ["1", "1A"]:
                sub_starts.append((num, s_start, s_end))
        else:
            existing_nums = [v[0] for v in sub_starts]
            if num not in existing_nums:
                sub_starts.append((num, s_start, s_end))

    if not sub_starts:
        return []

    subsections = []
    for idx, (sub_num, start_pos, content_start) in enumerate(sub_starts):
        end_pos = sub_starts[idx + 1][1] if idx + 1 < len(sub_starts) else len(text)
        sub_content = text[content_start:end_pos].strip()
        sub_id = f"{section_id}_SUB_{sub_num}"
        sub_text = f"({sub_num}) {sub_content}"
        sub_canonical = clean_to_canonical(sub_text)
        sub_markers, _ = extract_editorial_markers_from_text(sub_text, page_start, page_end, all_footnotes, location="subsection_text")

        # Parse nested clauses, provisos, explanations inside this subsection
        nested_clauses = parse_clauses_from_text(sub_content, sub_id, page_start, page_end, all_footnotes)
        provs, exps = parse_provisos_and_explanations(sub_content, page_start, page_end, sub_id, all_footnotes)

        subsections.append(SubsectionNode(
            subsection_id=sub_id,
            subsection_number=sub_num,
            text=sub_text,
            canonical_text=sub_canonical,
            editorial_markers=sub_markers,
            clauses=nested_clauses,
            provisos=provs,
            explanations=exps,
            source_page_start=page_start,
            source_page_end=page_end,
            content_hash=compute_text_hash(sub_canonical)
        ))

    return subsections


def parse_structure(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    norm_path = os.path.join(config["output"]["normalized_dir"], "pages_normalized.json")
    struct_dir = config["output"]["structured_dir"]
    fn_path = os.path.join(config["output"]["normalized_dir"], "statutory_footnotes.json")
    os.makedirs(struct_dir, exist_ok=True)

    with open(norm_path, "r", encoding="utf-8") as f:
        all_norm_pages = json.load(f)

    all_footnotes = []
    if os.path.exists(fn_path):
        with open(fn_path, "r", encoding="utf-8") as f:
            all_footnotes = json.load(f)

    # Source PDF sha256
    manifest_path = os.path.join(config["output"]["base_dir"], "companies_act_2013", "metadata", "source_manifest.json")
    source_pdf_sha256 = ""
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
            for doc in manifest_data:
                if doc["source_document_id"] == "ACT_COMPANIES_2013":
                    source_pdf_sha256 = doc["sha256"]

    act_pages = all_norm_pages["ACT_COMPANIES_2013"]

    print("[*] Parsing Chapter and Section Structure for ACT_COMPANIES_2013...")

    # 1. Parse TOC from pages 1-15
    toc_text = ""
    for p in act_pages:
        if 1 <= p["page_number"] <= 15:
            toc_text += p["clean_text"] + "\n"

    toc_pat = re.compile(r"^\s*(\d+[A-Z]?(?:-[A-Z]+)?)\.\s+([^\n\r]+)", re.MULTILINE)
    toc_sections = []
    for m in toc_pat.finditer(toc_text):
        s_num = m.group(1)
        s_head = m.group(2).strip().rstrip(".")
        if not s_head.startswith("CHAPTER") and not s_head.startswith("SCHEDULE"):
            if not toc_sections or toc_sections[-1][0] != s_num:
                toc_sections.append((s_num, s_head))

    # Parse Chapters from TOC or text
    chap_pat = re.compile(r"(?:^|\n)(CHAPTER\s+([IVXLCDM]+[A-Z]?))\s*\n+([A-Z\s,–—\-]+)", re.MULTILINE)
    enacted_pages = [p for p in act_pages if 16 <= p["page_number"] <= 252]

    # Map page numbers to Chapters
    chapter_map = []  # (start_page, chap_id, chap_num, chap_title)
    for p in enacted_pages:
        for m in chap_pat.finditer(p["clean_text"]):
            chap_num = m.group(2)
            chap_title = m.group(3).strip().splitlines()[0]
            chapter_map.append({
                "page": p["page_number"],
                "offset": m.start(),
                "chapter_id": f"ACT_COMPANIES_2013_CH_{chap_num}",
                "chapter_number": chap_num,
                "title": chap_title
            })

    # 2. Build full concatenated enacted text while tracking page offsets
    full_enacted_text = ""
    page_offsets = []  # (page_num, start_char, end_char)
    for p in enacted_pages:
        start_char = len(full_enacted_text)
        full_enacted_text += p["clean_text"] + "\n"
        end_char = len(full_enacted_text)
        page_offsets.append((p["page_number"], start_char, end_char))

    def get_page_for_char(char_pos: int) -> int:
        for p_num, s_char, e_char in page_offsets:
            if s_char <= char_pos <= e_char:
                return p_num
        return enacted_pages[-1]["page_number"]

    # Locate each section's start position in full_enacted_text
    section_locs = []  # (s_num, s_head, start_pos, header_end)
    search_from = 0

    for s_num, s_head in toc_sections:
        escaped_sec = re.escape(s_num)
        pat = re.compile(r"(?:^|\n)(?:\d+\s*)?\[?\s*" + escaped_sec + r"\.\s*\[?", re.MULTILINE)
        m = pat.search(full_enacted_text, search_from)
        if m:
            start_pos = m.start()
            section_locs.append((s_num, s_head, start_pos, m.end()))
            search_from = start_pos + 1
        else:
            # Fallback search from 0 if not found sequentially
            m_alt = pat.search(full_enacted_text)
            if m_alt:
                section_locs.append((s_num, s_head, m_alt.start(), m_alt.end()))
            else:
                print(f"    [!] Warning: Section {s_num} not found in enacted body.")

    # Sort section_locs by start_pos
    section_locs.sort(key=lambda x: x[2])

    # Extract text between consecutive sections
    sections_by_chapter = {}  # chapter_id -> list[SectionNode]
    all_section_nodes = []

    for idx, (s_num, s_head, start_pos, header_end) in enumerate(section_locs):
        end_pos = section_locs[idx + 1][2] if idx + 1 < len(section_locs) else len(full_enacted_text)
        sec_raw = full_enacted_text[start_pos:end_pos].strip()

        start_page = get_page_for_char(start_pos)
        end_page = get_page_for_char(end_pos)

        # Clean canonical text & extract editorial markers
        sec_canonical = clean_to_canonical(sec_raw)
        sec_markers, sec_footnotes = extract_editorial_markers_from_text(
            sec_raw, start_page, end_page, all_footnotes, location="section_text"
        )

        # Determine which Chapter this section belongs to
        active_chap = chapter_map[0]
        for ch in chapter_map:
            if ch["page"] < start_page or (ch["page"] == start_page and ch["offset"] <= (start_pos - [po[1] for po in page_offsets if po[0] == start_page][0])):
                active_chap = ch
            else:
                break

        sec_id = f"ACT_COMPANIES_2013_SEC_{s_num}"

        # Temporal lifecycle and status determination
        is_omitted = "[omitted" in s_head.lower() or "omitted by" in sec_raw[:140].lower() or "omitted by" in sec_canonical[:140].lower()
        is_repealed = "repealed by" in sec_raw[:140].lower() or "repealed by" in sec_canonical[:140].lower()

        commencement_date = None
        amendment_date = None
        amendment_history = []

        for fn in sec_footnotes:
            amendment_history.append(fn.text)
            if fn.commencement_date and not commencement_date:
                commencement_date = fn.commencement_date
            if fn.amending_act and not amendment_date:
                if "2015" in fn.amending_act:
                    amendment_date = "2015-05-29"
                elif "2020" in fn.amending_act:
                    amendment_date = "2020-09-28"
                elif "2018" in fn.amending_act:
                    amendment_date = "2018-01-03"
                elif "2019" in fn.amending_act:
                    amendment_date = "2019-07-31"

        if is_omitted:
            status = "omitted"
            enforcement_status = EnforcementStatus.OMITTED
            effective_from = "2013-09-12"
            effective_to = commencement_date or amendment_date or "2015-05-29"
        elif is_repealed:
            status = "repealed"
            enforcement_status = EnforcementStatus.REPEALED
            effective_from = "2013-09-12"
            effective_to = commencement_date or amendment_date or "2015-05-29"
        elif sec_footnotes:
            status = "active"
            if commencement_date:
                enforcement_status = EnforcementStatus.IN_FORCE
                effective_from = commencement_date
            else:
                enforcement_status = EnforcementStatus.AMENDED
                effective_from = None
            effective_to = None
        else:
            status = "active"
            enforcement_status = EnforcementStatus.IN_FORCE
            commencement_date = "2013-09-12"
            effective_from = "2013-09-12"
            effective_to = None

        # Parse subsections, provisos, explanations
        subsections = parse_subsections_from_text(sec_raw, sec_id, start_page, end_page, all_footnotes)
        clauses = []
        if not subsections:
            clauses = parse_clauses_from_text(sec_raw, sec_id, start_page, end_page, all_footnotes)
        provisos, explanations = parse_provisos_and_explanations(sec_raw, start_page, end_page, sec_id, all_footnotes)

        sec_node = SectionNode(
            section_id=sec_id,
            section_number=s_num,
            heading=s_head,
            text=sec_raw,
            canonical_text=sec_canonical,
            chapter_id=active_chap["chapter_id"],
            editorial_markers=sec_markers,
            footnotes=sec_footnotes,
            subsections=subsections,
            clauses=clauses,
            provisos=provisos,
            explanations=explanations,
            source_document_id="ACT_COMPANIES_2013",
            source_page_start=start_page,
            source_page_end=end_page,
            enactment_date="2013-08-29",
            publication_date="2013-08-30",
            amendment_date=amendment_date,
            commencement_date=commencement_date,
            enforcement_status=enforcement_status,
            effective_from=effective_from,
            effective_to=effective_to,
            status=status,
            version_id=f"COMPANIES_2013_SEC_{s_num}_V1",
            amendment_history=amendment_history,
            source_pdf_sha256=source_pdf_sha256,
            raw_extracted_text_sha256=compute_text_hash(sec_raw),
            canonical_text_sha256=compute_text_hash(sec_canonical),
            content_hash=compute_text_hash(sec_canonical),
            review_required=False
        )

        all_section_nodes.append(sec_node)
        chap_id = active_chap["chapter_id"]
        if chap_id not in sections_by_chapter:
            sections_by_chapter[chap_id] = []
        sections_by_chapter[chap_id].append(sec_node)

    # Build ChapterNodes
    chapters = []
    for ch in chapter_map:
        cid = ch["chapter_id"]
        c_sections = sections_by_chapter.get(cid, [])
        chapters.append(ChapterNode(
            chapter_id=cid,
            chapter_number=ch["chapter_number"],
            title=ch["title"],
            sections=c_sections
        ))

    output_data = {
        "document_id": "ACT_COMPANIES_2013",
        "act_title": "The Companies Act, 2013",
        "total_sections": len(all_section_nodes),
        "chapters": [c.model_dump() for c in chapters],
        "sections": [s.model_dump() for s in all_section_nodes]
    }

    out_file = os.path.join(struct_dir, "structured_act.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"    [+] Successfully structured {len(all_section_nodes)} sections across {len(chapters)} chapters.")
    print(f"    [+] Structured Act saved to: {out_file}")

    return output_data


if __name__ == "__main__":
    parse_structure()
