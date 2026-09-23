"""
HALO Citation Verifier: Master Pipeline Verifier
================================================
Protocol: v1.0-FROZEN
Orchestrates Tier 1 (Existence), Tier 2 (Metadata), and Tier 3 (Claim Association)
verification across extracted citations from generated legal answers.
Preserves epistemic neutrality (Gate CV9) and cryptographic auditability (Gate CV13).
"""

import time
import json
import hashlib
import uuid
from typing import Dict, Any, List, Optional, Union

from halo.citation_verifier.config import CitationVerifierConfig
from halo.citation_verifier.corpus_index import CorpusIndex
from halo.citation_verifier.parser import CitationParser
from halo.citation_verifier.normalizer import CitationNormalizer
from halo.citation_verifier.statutory_matcher import StatutoryMatcher
from halo.citation_verifier.judicial_matcher import JudicialMatcher
from halo.citation_verifier.association import CitationClaimAssociator
from halo.citation_verifier.validator import SubsystemValidator
from halo.citation_verifier.schemas import (
    CitationVerificationRecord,
    CitationVerificationResult,
    ParsedCitation,
    AuthorityType,
    ExistenceStatus,
    MetadataStatus,
    ExistenceResult,
    MetadataResult,
    MatchConfidenceTier,
    AuthorityHierarchy
)
from halo.citation_verifier.exceptions import CitationVerifierError


class CitationVerifier:
    """Master pipeline engine for citation existence and metadata verification."""

    def __init__(self, config: Optional[CitationVerifierConfig] = None):
        self.config = config or CitationVerifierConfig()
        self.corpus_index = CorpusIndex.get_instance(self.config)
        self.parser = CitationParser()
        self.normalizer = CitationNormalizer()
        self.statutory_matcher = StatutoryMatcher(self.corpus_index)
        self.judicial_matcher = JudicialMatcher(self.corpus_index)
        self.associator = CitationClaimAssociator()
        self.validator = SubsystemValidator()

    def verify_answer(
        self,
        extracted_data: Union[Dict[str, Any], str],
        answer_id: Optional[str] = None
    ) -> CitationVerificationResult:
        """
        Verifies all citations associated with an answer or claim extractor output payload.
        """
        start_time = time.perf_counter()
        errors: List[Dict[str, Any]] = []

        # 1. Normalize Input Structure
        if isinstance(extracted_data, str):
            effective_answer_id = answer_id or f"ANS_{uuid.uuid4().hex[:8].upper()}"
            claims_list = []
            raw_text = extracted_data
            input_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
            # Extract citations from raw text using parser
            parsed = self.parser.parse(raw_text)
            detected_citations = [{
                "citation_text": raw_text,
                "start_char": 0,
                "end_char": len(raw_text)
            }]
        elif isinstance(extracted_data, dict):
            effective_answer_id = (
                answer_id
                or extracted_data.get("answer_id")
                or extracted_data.get("id")
                or extracted_data.get("query_id")
                or f"ANS_{uuid.uuid4().hex[:8].upper()}"
            )
            claims_list = extracted_data.get("claims", [])
            input_canonical = json.dumps(extracted_data, sort_keys=True, ensure_ascii=False)
            input_hash = hashlib.sha256(input_canonical.encode("utf-8")).hexdigest()

            # Gather citations from claims and top-level citations
            detected_citations = self._gather_citations(extracted_data)
        else:
            raise CitationVerifierError(f"Unsupported input type: {type(extracted_data).__name__}")

        # 2. Process and Verify Citations
        records: List[CitationVerificationRecord] = []
        cit_counter = 1

        for cit_item in detected_citations:
            try:
                if isinstance(cit_item, dict):
                    raw_cit_text = cit_item.get("citation_text")
                    if not raw_cit_text:
                        parts = [str(cit_item.get(k)) for k in ["act", "section", "case_name", "citation_number"] if cit_item.get(k)]
                        raw_cit_text = ", ".join(parts) if parts else str(cit_item)
                    st_char = int(cit_item.get("start_char", 0))
                    en_char = int(cit_item.get("end_char", len(raw_cit_text)))
                    cleaned_cit = self.validator.validate_citation_input(raw_cit_text, self.config)
                    parsed = self.parser.parse(cit_item)
                else:
                    raw_cit_text = str(cit_item)
                    st_char = 0
                    en_char = len(raw_cit_text)
                    cleaned_cit = self.validator.validate_citation_input(raw_cit_text, self.config)
                    parsed = self.parser.parse(cleaned_cit)


                # Route to appropriate matcher
                if parsed.authority_type == AuthorityType.JUDGMENT.value:
                    exist_res, meta_res = self.judicial_matcher.verify(parsed)
                    auth_type = AuthorityType.JUDGMENT.value
                    source_corpus = "D2_JUDICIAL"
                elif parsed.authority_type == AuthorityType.STATUTE.value:
                    exist_res, meta_res = self.statutory_matcher.verify(parsed)
                    auth_type = AuthorityType.STATUTE.value
                    source_corpus = "D1_STATUTORY"
                else:
                    # Attempt statutory lookup first, then judicial
                    exist_res, meta_res = self.statutory_matcher.verify(parsed)
                    if exist_res.status == ExistenceStatus.EXISTS.value:
                        auth_type = AuthorityType.STATUTE.value
                        source_corpus = "D1_STATUTORY"
                    else:
                        j_exist, j_meta = self.judicial_matcher.verify(parsed)
                        if j_exist.status == ExistenceStatus.EXISTS.value:
                            exist_res, meta_res = j_exist, j_meta
                            auth_type = AuthorityType.JUDGMENT.value
                            source_corpus = "D2_JUDICIAL"
                        else:
                            auth_type = AuthorityType.UNKNOWN.value
                            source_corpus = "UNKNOWN"

                # Generate deterministic citation ID
                cit_id = f"{effective_answer_id}_CIT{cit_counter:03d}"
                cit_input_hash = hashlib.sha256(raw_cit_text.encode("utf-8")).hexdigest()

                # Determine primary verification tier
                v_tier = "METADATA" if exist_res.status == ExistenceStatus.EXISTS.value else "EXISTENCE"

                # Explanation synthesis
                explanation = f"Existence: {exist_res.explanation} Metadata: {meta_res.explanation}"

                # Assemble Record
                rec = CitationVerificationRecord(
                    citation_id=cit_id,
                    claim_ids=[],
                    citation_text=raw_cit_text,
                    start_char=st_char,
                    end_char=en_char,
                    existence=exist_res,
                    metadata=meta_res,
                    verification_tier=v_tier,
                    authority_type=auth_type,
                    canonical_authority_id=exist_res.canonical_authority_id,
                    source_corpus=source_corpus,
                    explanation=explanation,
                    input_hash=cit_input_hash,
                    output_hash=""
                )

                # Compute record output hash
                rec_canonical = json.dumps(rec.to_dict(), sort_keys=True, ensure_ascii=False)
                rec.output_hash = hashlib.sha256(rec_canonical.encode("utf-8")).hexdigest()

                records.append(rec)
                cit_counter += 1

            except Exception as e:
                errors.append({"citation_text": raw_cit_text, "error": str(e)})

        # 3. TIER 3: Associate Citations to Claims
        if claims_list:
            records = self.associator.map_claims_to_citations(claims_list, records)

        # 4. Gate CV9 Audit: Ensure Zero Evidence/Truth Decision Leakage
        self.validator.audit_no_evidence_leakage(records)

        # 5. Measure Latency and Compute Metrics
        total_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Summary Metrics
        exist_counts = {s.value: 0 for s in ExistenceStatus}
        meta_counts = {s.value: 0 for s in MetadataStatus}
        for r in records:
            exist_counts[r.existence.status] = exist_counts.get(r.existence.status, 0) + 1
            meta_counts[r.metadata.status] = meta_counts.get(r.metadata.status, 0) + 1

        metrics = {
            "processing_time_ms": total_time_ms,
            "total_citations": len(records),
            "existence_counts": exist_counts,
            "metadata_counts": meta_counts,
        }

        # 6. Compute Master Output Hash
        out_payload = [r.to_dict() for r in records]
        out_canonical = json.dumps(out_payload, sort_keys=True, ensure_ascii=False)
        output_hash = hashlib.sha256(out_canonical.encode("utf-8")).hexdigest()

        return CitationVerificationResult(
            success=len(errors) == 0,
            answer_id=effective_answer_id,
            input_hash=input_hash,
            output_hash=output_hash,
            total_citations=len(records),
            citation_results=records,
            metrics=metrics,
            errors=errors,
            metadata={
                "verifier_version": self.config.verifier_version,
                "schema_version": self.config.schema_version,
                "d1_sections_indexed": len(self.corpus_index.d1_sections),
                "d2_judgments_indexed": len(self.corpus_index.d2_judgments_by_id)
            }
        )

    def _gather_citations(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collects unique citations from top-level citations and claims."""
        citations = []
        seen = set()

        # Top-level direct citation object (e.g. benchmark case format)
        if "citation" in data and isinstance(data["citation"], dict):
            c = data["citation"]
            key = str(sorted(c.items()))
            seen.add(key)
            citations.append(c)

        # Top-level citations list
        for c in data.get("citations", []):
            if isinstance(c, dict):
                ct = c.get("citation_text", str(c))
                if ct not in seen:
                    seen.add(ct)
                    citations.append(c)

        # Claims citation_refs
        for claim in data.get("claims", []):
            for cr in claim.get("citation_refs", []):
                ct = cr.get("citation_text")
                if ct and ct not in seen:
                    seen.add(ct)
                    citations.append(cr)

        return citations


def verify_citations(
    extracted_data: Union[Dict[str, Any], str],
    answer_id: Optional[str] = None
) -> CitationVerificationResult:
    """Convenience functional API for CitationVerifier."""
    verifier = CitationVerifier()
    return verifier.verify_answer(extracted_data, answer_id=answer_id)
