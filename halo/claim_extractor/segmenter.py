"""
HALO Claim Extractor: Legal Sentence Segmenter
==============================================
Protocol: v1.0-FROZEN
Segments legal text into sentences while protecting domain abbreviations,
initials, reporter citations, and preserving 100% exact character spans.
"""

import re
from dataclasses import dataclass
from typing import List


@dataclass
class SentenceSegment:
    """A segmented sentence preserving exact character offsets from the raw input text."""
    sentence_index: int
    text: str
    start_char: int
    end_char: int


class LegalSentenceSegmenter:
    """Segments legal text into sentences with strict abbreviation protection and span tracking."""

    # Set of known lowercase abbreviations (without the trailing dot)
    PROTECTED_ABBREVIATIONS = {
        "sec", "secs", "u/s", "w.e.f", "v", "vs", "no", "nos", "hon'ble",
        "art", "arts", "ors", "anr", "co", "ltd", "pvt", "e.g", "i.e",
        "al", "vol", "mr", "mrs", "ms", "dr", "prof", "sr", "jr",
        "para", "paras", "cl", "cls", "reg", "regs", "inc", "corp", "dept",
        "govt", "judg", "ed", "op", "cit", "ibid"
    }

    # Regex matching known multi-dot abbreviations (e.g. w.e.f., S.C.R., e.g., i.e.)
    MULTI_DOT_ABBREV_PAT = re.compile(
        r"\b(?:[A-Za-z]\.){2,}", re.IGNORECASE
    )

    def segment(self, text: str) -> List[SentenceSegment]:
        """
        Segments raw text into sentences while tracking exact character offsets.
        Guarantees text[segment.start_char:segment.end_char] == segment.text.
        """
        if not text or not text.strip():
            return []

        boundaries = [0]
        length = len(text)
        i = 0

        while i < length:
            char = text[i]

            # Check for sentence terminal candidates: '.', '!', '?', or '\n\n+'
            if char in {'.', '!', '?'}:
                # Lookahead: is this terminal followed by whitespace and a new sentence start?
                # or is it at the end of the text?
                j = i + 1
                while j < length and text[j] in {'.', '!', '?', '"', "'", ')'}:
                    j += 1  # include multi-punctuation like '...' or '."' or '.)'

                is_end_of_text = (j >= length)
                is_newline_break = (j < length and text[j] == '\n')
                has_space_and_capital = False

                k = j
                while k < length and text[k] in {' ', '\t'}:
                    k += 1

                if k < length and (text[k].isupper() or text[k] in {'"', "'", '₹', '[', '(', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9'}):
                    has_space_and_capital = True

                if is_end_of_text or is_newline_break or has_space_and_capital:
                    # Verify whether the period is an abbreviation
                    if char == '.':
                        if self._is_abbreviation_or_decimal(text, i):
                            i = j
                            continue

                    boundaries.append(j)
                    i = j
                    continue

            # Also treat multiple newlines (paragraphs) as hard sentence breaks
            elif char == '\n':
                if i + 1 < length and text[i + 1] == '\n':
                    j = i + 2
                    while j < length and text[j] == '\n':
                        j += 1
                    boundaries.append(j)
                    i = j
                    continue

            i += 1

        if boundaries[-1] != length:
            boundaries.append(length)

        # Deduplicate and sort boundaries
        boundaries = sorted(list(dict.fromkeys(boundaries)))

        segments: List[SentenceSegment] = []
        sent_idx = 0

        for b_idx in range(len(boundaries) - 1):
            st = boundaries[b_idx]
            en = boundaries[b_idx + 1]

            # Trim whitespace without losing exact character span tracking
            while st < en and text[st].isspace():
                st += 1
            while en > st and text[en - 1].isspace():
                en -= 1

            if st < en:
                seg_text = text[st:en]
                # Filter out pure punctuation artifacts (like stray bullet points)
                if any(c.isalnum() for c in seg_text):
                    segments.append(SentenceSegment(
                        sentence_index=sent_idx,
                        text=seg_text,
                        start_char=st,
                        end_char=en
                    ))
                    sent_idx += 1

        return segments

    def _is_abbreviation_or_decimal(self, text: str, dot_pos: int) -> bool:
        """Determines if the dot at dot_pos is part of a protected abbreviation or decimal."""
        # 1. Check if surrounded by digits: e.g. 12.01, 3.5, Section 135.1
        if dot_pos > 0 and dot_pos + 1 < len(text):
            if text[dot_pos - 1].isdigit() and text[dot_pos + 1].isdigit():
                return True

        # 2. Extract preceding word token (characters before dot_pos)
        start = dot_pos - 1
        while start >= 0 and (text[start].isalnum() or text[start] in {'.', "'", '/'}):
            start -= 1
        token = text[start + 1:dot_pos]

        token_lower = token.lower()

        # Check known dictionary of abbreviations
        if token_lower in self.PROTECTED_ABBREVIATIONS:
            return True

        # Single uppercase capital letter followed by dot: e.g. "S.", "L.", "C.", "R."
        if len(token) == 1 and token.isupper():
            return True

        # Check if preceding sequence is a multi-dot sequence like "S.C.R" or "w.e.f"
        check_window = text[max(0, dot_pos - 10):dot_pos + 1]
        if self.MULTI_DOT_ABBREV_PAT.search(check_window):
            return True

        # Check for Section/Sec or u/s abbreviations with subsection parens
        if token_lower in {"sec", "secs", "section"} and dot_pos + 1 < len(text) and text[dot_pos + 1].isspace():
            # e.g. "Sec. 135" -> dot is abbreviation
            return True

        return False
