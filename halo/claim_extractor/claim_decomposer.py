"""
HALO Claim Extractor: Propositional Atomicity & Decomposer
==========================================================
Protocol: v1.0-FROZEN
Deconstructs compound legal sentences into atomic, independently verifiable propositions.
Preserves exact character spans, parent-child relationships, modality, and quantitative terms.
"""

import re
from dataclasses import dataclass
from typing import List, Optional
from halo.claim_extractor.schemas import AtomicityMeta, SourceSpan


@dataclass
class DecomposedProposition:
    """An atomic proposition extracted from a sentence."""
    text: str
    source_span: SourceSpan
    atomicity: AtomicityMeta


class ClaimDecomposer:
    """Decomposes compound sentences into atomic legal propositions while preserving exact spans."""

    # 1. Coordinate clause conjunctions linking independent legal assertions
    # E.g. "...must have at least three directors, and all directors must be foreign nationals"
    # E.g. "...mandates spending 2% on CSR, and failure by the board leads to criminal imprisonment"
    # E.g. "...requires board consent, and every transaction must receive prior approval from Supreme Court"
    COORDINATE_SPLIT_PATS = [
        re.compile(r",\s+(?:and\s+)(?=[a-z0-9\s]+(?:must|shall|may|can|cannot|is\s+required|is\s+prohibited|is\s+barred|is\s+automatically|leads\s+to|results\s+in))", re.IGNORECASE),
        re.compile(r",\s+(?:and\s+)(?=(?:every|all|both|neither|no|any|the|such)\s+[a-z0-9\s]+(?:must|shall|may|can|cannot|is|are|will))", re.IGNORECASE),
        re.compile(r";\s+(?:and\s+)?", re.IGNORECASE),
        re.compile(r",\s+(?:failing\s+which|in\s+default\s+of\s+which)\s+", re.IGNORECASE),
    ]

    # 2. Proviso patterns
    PROVISO_PAT = re.compile(
        r"(?<=[a-zA-Z0-9\)])\s*:\s*(?=Provided\s+(?:that|further))|(?<=[a-zA-Z0-9\)])\.\s+(?=Provided\s+(?:that|further))",
        re.IGNORECASE
    )

    def decompose(self, sentence_text: str, sentence_start: int, sentence_end: int, parent_id_prefix: str) -> List[DecomposedProposition]:
        """
        Decomposes a single sentence into one or more atomic propositions.
        Guarantees:
          sentence_text[sub_span.start_char - sentence_start : sub_span.end_char - sentence_start] == sub_span.source_text
        """
        clean_sentence = sentence_text.strip()
        if not clean_sentence:
            return []

        # 1. Check for Semicolon splits
        if ";" in clean_sentence:
            propositions = self._split_by_delimiters(clean_sentence, sentence_start, r";\s*", "SEMICOLON_SPLIT", parent_id_prefix)
            if len(propositions) > 1:
                return propositions

        # 2. Check for Proviso splits
        proviso_match = self.PROVISO_PAT.search(clean_sentence)
        if proviso_match:
            idx = proviso_match.start()
            part1 = clean_sentence[:idx].strip()
            part2 = clean_sentence[proviso_match.end():].strip()
            if len(part1.split()) >= 3 and len(part2.split()) >= 3:
                p1_start = sentence_start
                p1_end = sentence_start + len(part1)
                p2_start = sentence_start + proviso_match.end()
                p2_end = sentence_start + len(clean_sentence)

                return [
                    DecomposedProposition(
                        text=part1,
                        source_span=SourceSpan(p1_start, p1_end, part1),
                        atomicity=AtomicityMeta(is_atomic=True, parent_claim_id=f"{parent_id_prefix}_P", decomposition_type="PROVISO_MAIN_SPLIT")
                    ),
                    DecomposedProposition(
                        text=part2,
                        source_span=SourceSpan(p2_start, p2_end, part2),
                        atomicity=AtomicityMeta(is_atomic=True, parent_claim_id=f"{parent_id_prefix}_P", decomposition_type="PROVISO_SUB_SPLIT")
                    )
                ]

        # 3. Check for Coordinate Clause Conjunctions
        for pat in self.COORDINATE_SPLIT_PATS:
            match = pat.search(clean_sentence)
            if match:
                cut_start = match.start()
                cut_end = match.end()

                part1 = clean_sentence[:cut_start].strip()
                part2 = clean_sentence[cut_end:].strip()

                if len(part1.split()) >= 3 and len(part2.split()) >= 3:
                    # Calculate exact character offsets within the original text
                    p1_st = sentence_start
                    p1_en = sentence_start + len(part1)

                    p2_st = sentence_start + cut_end
                    p2_en = sentence_start + len(clean_sentence)

                    return [
                        DecomposedProposition(
                            text=part1,
                            source_span=SourceSpan(p1_st, p1_en, part1),
                            atomicity=AtomicityMeta(is_atomic=True, parent_claim_id=f"{parent_id_prefix}_P", decomposition_type="COORDINATE_CLAUSE_SPLIT")
                        ),
                        DecomposedProposition(
                            text=part2,
                            source_span=SourceSpan(p2_st, p2_en, part2),
                            atomicity=AtomicityMeta(is_atomic=True, parent_claim_id=f"{parent_id_prefix}_P", decomposition_type="COORDINATE_CLAUSE_SPLIT")
                        )
                    ]

        # Single atomic proposition (no decomposition required)
        return [
            DecomposedProposition(
                text=clean_sentence,
                source_span=SourceSpan(sentence_start, sentence_end, clean_sentence),
                atomicity=AtomicityMeta(is_atomic=True, parent_claim_id=None, decomposition_type=None)
            )
        ]

    def _split_by_delimiters(self, text: str, base_offset: int, delimiter_regex: str, decomp_type: str, parent_prefix: str) -> List[DecomposedProposition]:
        """Splits text by regex pattern while preserving exact character offsets."""
        parts = []
        last_end = 0

        for match in re.finditer(delimiter_regex, text):
            sub_text = text[last_end:match.start()].strip()
            if len(sub_text.split()) >= 3:
                # Find exact start and end of stripped sub_text in raw text slice
                rel_st = text.find(sub_text, last_end)
                rel_en = rel_st + len(sub_text)
                parts.append(DecomposedProposition(
                    text=sub_text,
                    source_span=SourceSpan(base_offset + rel_st, base_offset + rel_en, sub_text),
                    atomicity=AtomicityMeta(is_atomic=True, parent_claim_id=f"{parent_prefix}_P", decomposition_type=decomp_type)
                ))
            last_end = match.end()

        # Tail
        tail = text[last_end:].strip()
        if len(tail.split()) >= 3:
            rel_st = text.find(tail, last_end)
            rel_en = rel_st + len(tail)
            parts.append(DecomposedProposition(
                text=tail,
                source_span=SourceSpan(base_offset + rel_st, base_offset + rel_en, tail),
                atomicity=AtomicityMeta(is_atomic=True, parent_claim_id=f"{parent_prefix}_P", decomposition_type=decomp_type)
            ))

        return parts
