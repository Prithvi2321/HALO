"""
HALO Citation Verifier: Judicial Citation Matcher
=================================================
Protocol: v1.0-FROZEN
Resolves judicial citations against authoritative D2 index.
Strictly enforces: FUZZY_CANDIDATE must NEVER emit EXISTS (Gate CV5).
Verifies court, year, and paragraph boundaries.
"""

from typing import Tuple, Optional
from halo.citation_verifier.corpus_index import CorpusIndex
from halo.citation_verifier.schemas import (
    ParsedCitation,
    ExistenceResult,
    MetadataResult,
    ExistenceStatus,
    MetadataStatus,
    MatchConfidenceTier,
    AuthorityHierarchy
)
from halo.citation_verifier.metadata_matcher import MetadataMatcher


class JudicialMatcher:
    """Matches and verifies judicial citations against the D2 corpus."""

    def __init__(self, index: CorpusIndex):
        self.index = index

    def verify(self, parsed: ParsedCitation) -> Tuple[ExistenceResult, MetadataResult]:
        """
        Executes Tier 1 (Existence) and Tier 2 (Metadata) verification for a judicial citation.
        """
        judgment_id: Optional[str] = None
        confidence: str = MatchConfidenceTier.NO_MATCH.value

        # 1. Lookup by reporter citation first (exact)
        if parsed.reporter:
            jid = self.index.find_judgment_by_citation(parsed.reporter)
            if jid:
                judgment_id = jid
                confidence = MatchConfidenceTier.EXACT_MATCH.value

        # 2. Lookup by case title if not found by reporter
        if not judgment_id and parsed.case_title:
            jid, conf = self.index.find_judgment_by_title(parsed.case_title)
            if jid:
                judgment_id = jid
                confidence = conf

        # 3. Apply Strict Inviolable Safety Rule:
        # FUZZY_CANDIDATE must NEVER emit EXISTS
        if confidence == MatchConfidenceTier.FUZZY_CANDIDATE.value:
            exist_status = ExistenceStatus.AMBIGUOUS.value
            explanation = f"Fuzzy candidate identified for '{parsed.case_title or parsed.reporter}', but sub-threshold match cannot be verified as existing."
            matched_pids = []
            hierarchy = AuthorityHierarchy(authority_exists=False)
        elif judgment_id and confidence in {MatchConfidenceTier.EXACT_MATCH.value, MatchConfidenceTier.NORMALIZED_MATCH.value}:
            exist_status = ExistenceStatus.EXISTS.value
            explanation = f"Judgment {judgment_id} exists in authoritative judicial corpus."
            matched_pids = self.index.resolve_judicial_passages(judgment_id)
            hierarchy = AuthorityHierarchy(
                authority_exists=True,
                section_exists=True,
                subsection_exists=True if not parsed.paragraph else False,
                matched_passage_ids=matched_pids
            )
        else:
            exist_status = ExistenceStatus.NOT_FOUND.value
            confidence = MatchConfidenceTier.NO_MATCH.value
            explanation = f"Judicial authority '{parsed.citation_text}' not found in authoritative corpus."
            matched_pids = []
            hierarchy = AuthorityHierarchy(authority_exists=False)

        exist_res = ExistenceResult(
            status=exist_status,
            confidence_tier=confidence,
            canonical_authority_id=judgment_id,
            matched_passage_ids=matched_pids,
            hierarchy=hierarchy,
            explanation=explanation
        )

        # 4. Metadata Verification
        if judgment_id:
            judgment_meta = self.index.get_judgment(judgment_id)
            max_para = self.index.get_max_paragraph_in_judgment(judgment_id)
            meta_res = MetadataMatcher.compare_judicial_metadata(parsed, judgment_meta, max_para)
        else:
            meta_res = MetadataResult(
                status=MetadataStatus.UNRESOLVED.value,
                explanation="Cannot verify metadata for non-existent or unresolved judgment."
            )

        return exist_res, meta_res
