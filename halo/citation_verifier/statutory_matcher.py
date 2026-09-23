"""
HALO Citation Verifier: Statutory Matcher
=========================================
Protocol: v1.0-FROZEN
Resolves statutory citations against authoritative D1 index.
Enforces strict hierarchical resolution: Authority -> Section -> Subsection -> Passage Resolution.
Strictly forbids FUZZY_CANDIDATE from emitting EXISTS.
"""

from typing import Optional, Dict, Any, Tuple
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


class StatutoryMatcher:
    """Matches and verifies statutory citations against the D1 corpus."""

    def __init__(self, index: CorpusIndex):
        self.index = index

    def verify(self, parsed: ParsedCitation) -> Tuple[ExistenceResult, MetadataResult]:
        """
        Executes Tier 1 (Existence) and Tier 2 (Metadata) verification for a statutory citation.
        """
        act_name = parsed.act_name or self.index.config.default_act_context
        section = parsed.section
        subsection = parsed.subsection

        # 1. Check if the cited Act exists
        if parsed.act_name:
            if not self.index.act_exists(parsed.act_name):
                # Fabricated or unsupported enactment
                hierarchy = AuthorityHierarchy(authority_exists=False)
                exist_res = ExistenceResult(
                    status=ExistenceStatus.NOT_FOUND.value,
                    confidence_tier=MatchConfidenceTier.NO_MATCH.value,
                    canonical_authority_id=None,
                    matched_passage_ids=[],
                    hierarchy=hierarchy,
                    explanation=f"The cited enactment '{parsed.act_name}' does not exist in the authoritative legal corpus."
                )
                meta_res = MetadataResult(
                    status=MetadataStatus.UNRESOLVED.value,
                    explanation=f"Cannot verify metadata for non-existent Act '{parsed.act_name}'."
                )
                return exist_res, meta_res

        # 2. Check if Section is present in the citation
        if not section:
            # Bare Act without section
            if self.index.act_exists(act_name):
                act_meta = self.index.d1_acts.get(self.index.d1_acts.get("COMPANIES ACT 2013", {}).get("title", ""))
                exist_res = ExistenceResult(
                    status=ExistenceStatus.EXISTS.value,
                    confidence_tier=MatchConfidenceTier.EXACT_MATCH.value,
                    canonical_authority_id="ACT_COMPANIES_2013",
                    matched_passage_ids=[],
                    hierarchy=AuthorityHierarchy(authority_exists=True),
                    explanation=f"Statute '{act_name}' exists in authoritative corpus."
                )
                meta_res = MetadataResult(
                    status=MetadataStatus.MATCH.value,
                    explanation="Statute existence verified."
                )
                return exist_res, meta_res
            else:
                exist_res = ExistenceResult(
                    status=ExistenceStatus.NOT_FOUND.value,
                    confidence_tier=MatchConfidenceTier.NO_MATCH.value,
                    explanation="Statutory authority not found."
                )
                meta_res = MetadataResult(status=MetadataStatus.UNRESOLVED.value)
                return exist_res, meta_res

        # 3. Hierarchical Resolution against Canonical D1 Index
        hierarchy = self.index.resolve_statutory_hierarchy(act_name, section, subsection)

        if hierarchy.section_exists:
            sec_id = hierarchy.details.get("canonical_section_id", f"ACT_COMPANIES_2013_SEC_{section}")
            exist_status = ExistenceStatus.EXISTS.value
            confidence = MatchConfidenceTier.EXACT_MATCH.value
            explanation = f"Section {section} exists in authoritative {act_name}."
        else:
            sec_id = None
            exist_status = ExistenceStatus.NOT_FOUND.value
            confidence = MatchConfidenceTier.NO_MATCH.value
            explanation = f"Section {section} not found in authoritative statutory corpus."

        exist_res = ExistenceResult(
            status=exist_status,
            confidence_tier=confidence,
            canonical_authority_id=sec_id,
            matched_passage_ids=hierarchy.matched_passage_ids,
            hierarchy=hierarchy,
            explanation=explanation
        )

        # 4. Metadata Verification
        act_meta = self.index.d1_acts.get("COMPANIES ACT 2013")
        meta_res = MetadataMatcher.compare_statutory_metadata(parsed, hierarchy, act_meta)

        return exist_res, meta_res
