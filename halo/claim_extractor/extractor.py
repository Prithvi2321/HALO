"""
HALO Claim Extractor: Master Pipeline Engine
============================================
Protocol: v1.0-FROZEN
Orchestrates:
  Preprocessor -> Sentence Segmentation -> Citation Detection ->
  Claim Candidate Detection -> Propositional Atomicity Decomposition ->
  Claim Type Classification -> Citation Proximity Association ->
  Span Integrity Verification -> Hashing & Observability
"""

import datetime
import hashlib
import time
import uuid
from typing import Optional, List, Dict, Any

from halo.claim_extractor.config import ClaimExtractorConfig
from halo.claim_extractor.schemas import (
    ClaimExtractionResult,
    ExtractedClaim,
    CitationRef,
    SourceSpan,
    AtomicityMeta,
)
from halo.claim_extractor.segmenter import LegalSentenceSegmenter
from halo.claim_extractor.citation_detector import LegalCitationDetector
from halo.claim_extractor.claim_detector import ClaimCandidateDetector
from halo.claim_extractor.claim_decomposer import ClaimDecomposer
from halo.claim_extractor.claim_classifier import LegalClaimClassifier
from halo.claim_extractor.span_aligner import SpanAligner
from halo.claim_extractor.normalizer import ClaimNormalizer
from halo.claim_extractor.validator import SubsystemValidator
from halo.claim_extractor.exceptions import (
    ClaimExtractorError,
    EmptyAnswerError,
)


class ClaimExtractor:
    """Production-grade legal claim extraction engine for HALO."""

    def __init__(self, config: Optional[ClaimExtractorConfig] = None):
        self.config = config or ClaimExtractorConfig()
        self.segmenter = LegalSentenceSegmenter()
        self.citation_detector = LegalCitationDetector()
        self.candidate_detector = ClaimCandidateDetector()
        self.decomposer = ClaimDecomposer()
        self.classifier = LegalClaimClassifier()
        self.span_aligner = SpanAligner()
        self.normalizer = ClaimNormalizer()
        self.validator = SubsystemValidator()

    def extract(
        self,
        answer_text: str,
        answer_id: Optional[str] = None,
        run_id: Optional[str] = None
    ) -> ClaimExtractionResult:
        """
        Extracts atomic legal claims from a generated answer string.
        Guarantees:
          - 100% span integrity: answer_text[c.source_span.start_char:c.source_span.end_char] == c.source_span.source_text
          - Zero truth evaluation (no SUPPORTED, CONTRADICTED, etc.)
          - Modality, numerical, and temporal preservation
          - Deterministic input and output hashing
        """
        start_time = time.perf_counter()
        effective_run_id = run_id or f"RUN_{uuid.uuid4().hex[:12].upper()}"
        effective_answer_id = answer_id or f"ANS_{uuid.uuid4().hex[:8].upper()}"

        # 1. Handle empty / None input safely
        if answer_text is None or not isinstance(answer_text, str) or not answer_text.strip():
            if self.config.allow_empty_claims_on_non_legal and answer_text is not None and isinstance(answer_text, str) and not answer_text.strip():
                return self._create_empty_result(
                    answer_text="",
                    answer_id=effective_answer_id,
                    run_id=effective_run_id,
                    start_time=start_time,
                    reason="EMPTY_WHITESPACE"
                )
            try:
                self.validator.validate_input(answer_text, self.config)
            except ClaimExtractorError as e:
                return self._create_error_result(
                    answer_text=str(answer_text or ""),
                    answer_id=effective_answer_id,
                    run_id=effective_run_id,
                    error=e,
                    start_time=start_time
                )

        # Compute deterministic input hash
        input_hash = hashlib.sha256(answer_text.encode("utf-8")).hexdigest()

        # 2. Validate input constraints
        try:
            self.validator.validate_input(answer_text, self.config)
        except ClaimExtractorError as e:
            return self._create_error_result(
                answer_text=answer_text,
                answer_id=effective_answer_id,
                run_id=effective_run_id,
                error=e,
                start_time=start_time
            )

        # 3. Detect all citations in the whole answer
        all_citations = self.citation_detector.detect_citations(answer_text)

        # 4. Segment text into sentences preserving character offsets
        sentence_segments = self.segmenter.segment(answer_text)

        claims: List[ExtractedClaim] = []
        claim_counter = 1

        for s_idx, segment in enumerate(sentence_segments):
            # Check candidate status (filter refusals like "I don't know" or boilerplate headings)
            is_candidate, reason = self.candidate_detector.is_claim_candidate(segment.text)
            if not is_candidate:
                continue

            # Decompose compound sentence into atomic propositions
            parent_prefix = f"{effective_answer_id}_S{s_idx + 1:02d}"
            if self.config.decompose_compound_claims:
                atomic_propositions = self.decomposer.decompose(
                    segment.text, segment.start_char, segment.end_char, parent_prefix
                )
            else:
                from halo.claim_extractor.claim_decomposer import DecomposedProposition
                atomic_propositions = [
                    DecomposedProposition(
                        text=segment.text,
                        source_span=SourceSpan(segment.start_char, segment.end_char, segment.text),
                        atomicity=AtomicityMeta(is_atomic=True, parent_claim_id=None, decomposition_type=None)
                    )
                ]

            # Find citations belonging to this sentence segment
            sentence_citations = [
                c for c in all_citations
                if segment.start_char <= c.start_char and c.end_char <= segment.end_char
            ]

            # Associate citations with proximity fallback if needed
            associated_citations = sentence_citations
            if not associated_citations and self.config.citation_proximity_strategy == "same_sentence_then_adjacent":
                # Check preceding sentence
                if s_idx > 0:
                    prev_seg = sentence_segments[s_idx - 1]
                    prev_cits = [
                        c for c in all_citations
                        if prev_seg.start_char <= c.start_char and c.end_char <= prev_seg.end_char
                    ]
                    if prev_cits:
                        associated_citations = prev_cits

                # Check following sentence
                if not associated_citations and s_idx + 1 < len(sentence_segments):
                    next_seg = sentence_segments[s_idx + 1]
                    next_cits = [
                        c for c in all_citations
                        if next_seg.start_char <= c.start_char and c.end_char <= next_seg.end_char
                    ]
                    if next_cits:
                        associated_citations = next_cits

            for prop in atomic_propositions:
                claim_id = f"{effective_answer_id}_C{claim_counter:03d}"
                claim_type = self.classifier.classify(prop.text)
                norm_key = self.normalizer.compute_normalized_key(prop.text, claim_type)

                claim = ExtractedClaim(
                    claim_id=claim_id,
                    claim_text=prop.text,
                    claim_type=claim_type,
                    source_span=prop.source_span,
                    sentence_index=segment.sentence_index,
                    citation_refs=associated_citations,
                    atomicity=prop.atomicity,
                    extraction_confidence=None,  # Do not fabricate confidence
                    normalized_claim_key=norm_key
                )
                claims.append(claim)
                claim_counter += 1

        # 5. Audit Span Integrity
        if self.config.strict_span_integrity:
            try:
                self.span_aligner.verify_all_claims(answer_text, claims)
            except ClaimExtractorError as e:
                return self._create_error_result(
                    answer_text=answer_text,
                    answer_id=effective_answer_id,
                    run_id=effective_run_id,
                    error=e,
                    start_time=start_time
                )

        # 6. Validate Claims and Enforce No Truth Leakage
        try:
            self.validator.validate_claims(claims, self.config)
        except ClaimExtractorError as e:
            return self._create_error_result(
                answer_text=answer_text,
                answer_id=effective_answer_id,
                run_id=effective_run_id,
                error=e,
                start_time=start_time
            )

        # 7. Compute deterministic output hash
        import json
        claims_payload = json.dumps([c.to_dict() for c in claims], sort_keys=True, ensure_ascii=False)
        output_hash = hashlib.sha256(claims_payload.encode("utf-8")).hexdigest()

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        metadata = {
            "run_id": effective_run_id,
            "answer_id": effective_answer_id,
            "extractor_version": self.config.extractor_version,
            "schema_version": self.config.schema_version,
            "model": "HALO_DETERMINISTIC_HYBRID_EXTRACTOR_v1",
            "prompt_version": "claim_extraction_v1",
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "input_char_length": len(answer_text),
            "sentence_count": len(sentence_segments),
            "claim_count": len(claims),
            "citation_count": len(all_citations),
            "processing_time_ms": latency_ms,
            "status": "SUCCESS"
        }

        return ClaimExtractionResult(
            success=True,
            answer_id=effective_answer_id,
            input_hash=input_hash,
            output_hash=output_hash,
            claims=claims,
            citations=all_citations,
            metadata=metadata,
            errors=[]
        )

    def _create_empty_result(
        self,
        answer_text: str,
        answer_id: str,
        run_id: str,
        start_time: float,
        reason: str
    ) -> ClaimExtractionResult:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        input_hash = hashlib.sha256(answer_text.encode("utf-8")).hexdigest()
        output_hash = hashlib.sha256("[]".encode("utf-8")).hexdigest()

        return ClaimExtractionResult(
            success=True,
            answer_id=answer_id,
            input_hash=input_hash,
            output_hash=output_hash,
            claims=[],
            citations=[],
            metadata={
                "run_id": run_id,
                "answer_id": answer_id,
                "extractor_version": self.config.extractor_version,
                "schema_version": self.config.schema_version,
                "model": "HALO_DETERMINISTIC_HYBRID_EXTRACTOR_v1",
                "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "claim_count": 0,
                "citation_count": 0,
                "processing_time_ms": latency_ms,
                "status": "EMPTY_OR_NON_LEGAL_ANSWER",
                "reason": reason
            },
            errors=[]
        )

    def _create_error_result(
        self,
        answer_text: str,
        answer_id: str,
        run_id: str,
        error: ClaimExtractorError,
        start_time: float
    ) -> ClaimExtractionResult:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        input_hash = hashlib.sha256(answer_text.encode("utf-8")).hexdigest()

        return ClaimExtractionResult(
            success=False,
            answer_id=answer_id,
            input_hash=input_hash,
            output_hash="",
            claims=[],
            citations=[],
            metadata={
                "run_id": run_id,
                "answer_id": answer_id,
                "extractor_version": self.config.extractor_version,
                "schema_version": self.config.schema_version,
                "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "processing_time_ms": latency_ms,
                "status": "FAILED"
            },
            errors=[error.to_dict()]
        )


def extract_claims(text: str, answer_id: Optional[str] = None) -> ClaimExtractionResult:
    """Convenience functional interface."""
    extractor = ClaimExtractor()
    return extractor.extract(text, answer_id=answer_id)
