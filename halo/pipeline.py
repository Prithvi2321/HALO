"""
HALO End-to-End Pipeline
========================
Protocol: v1.0-FROZEN
Orchestrates the complete HALO Legal Verification and Fail-Closed Governance Architecture:
1. Candidate Legal Answer Input
2. Atomic Legal Claim Extraction (ClaimExtractor)
3. 3-Tier Citation Verification (CitationVerifier)
4. Substantive Evidence & NLI Entailment (EvidenceVerifier)
5. Amendment & Temporal Enforceability (TemporalVerifier)
6. Doctrinal & Forum Conflict Detection (ConflictDetector)
7. Evidence-Derived Confidence Calculation (ConfidenceEngine)
8. Fail-Closed Policy Enforcement & Reconstruction (FailClosedGovernor)
9. Cryptographic Audit Storage (AuditLogger)
"""

import os
import sys
from typing import Dict, List, Any, Optional

from halo.claim_extractor.extractor import ClaimExtractor, AtomicClaim
from halo.citation_verifier.verifier import CitationVerifier, CitationVerificationResult
from halo.evidence_verifier.verifier import EvidenceVerifier, EvidenceVerificationResult
from halo.temporal_verifier.verifier import TemporalVerifier, TemporalVerificationResult
from halo.conflict_detector.detector import ConflictDetector, ConflictDetectionResult
from halo.confidence.engine import ConfidenceEngine, ClaimConfidenceScore, AnswerConfidenceScore
from halo.governor.governor import FailClosedGovernor, GovernorVerdict
from halo.audit.logger import AuditLogger, AuditRecord


class HaloPipeline:
    """Production-grade HALO Verification and Fail-Closed Governance Pipeline."""

    def __init__(self, log_path: str = "experiments/runs/halo/audit_store.jsonl"):
        self.claim_extractor = ClaimExtractor()
        self.citation_verifier = CitationVerifier()
        self.evidence_verifier = EvidenceVerifier()
        self.temporal_verifier = TemporalVerifier()
        self.conflict_detector = ConflictDetector()
        self.confidence_engine = ConfidenceEngine()
        self.governor = FailClosedGovernor()
        self.audit_logger = AuditLogger(log_path=log_path)

    def process(
        self,
        query: str,
        raw_answer: str,
        candidate_passages: Optional[List[Dict[str, Any]]] = None,
        explicit_citations: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Executes complete verification pipeline on query and candidate answer.
        """
        candidate_passages = candidate_passages or []
        explicit_citations = explicit_citations or []

        # 1. Atomic Claim Extraction
        extracted_claims = self.claim_extractor.extract_claims(raw_answer)
        if not extracted_claims and raw_answer.strip():
            extracted_claims = [
                AtomicClaim(
                    claim_id="CLM_001",
                    claim_text=raw_answer.strip(),
                    citation_ids=[],
                    claim_type="STATUTORY_RULE",
                    atomicity_status="ATOMIC",
                )
            ]

        # 2. Per-claim Verification Loop
        verification_records = []
        claim_confidences = []

        for idx, claim in enumerate(extracted_claims):
            cid = claim.claim_id
            ctext = claim.claim_text

            # Extract or assign citation
            cit = None
            if idx < len(explicit_citations):
                cit = explicit_citations[idx]
            elif explicit_citations:
                cit = explicit_citations[0]
            else:
                # Infer basic citation dictionary from text
                cit = {}
                if "section" in ctext.lower() or "act" in ctext.lower():
                    cit["type"] = "STATUTORY"
                    cit["act"] = "Companies Act, 2013"
                    import re
                    m = re.search(r"section\s+(\d+[A-Za-z]?)", ctext, re.IGNORECASE)
                    if m:
                        cit["section"] = m.group(1)
                else:
                    cit["type"] = "JUDICIAL"

            # Tier A: Citation Verification
            cit_res = self.citation_verifier.verify(
                citation=cit, claim_text=ctext, case_id=cid
            )

            # Tier B: Passage / Evidence Verification
            best_passage = ""
            best_pid = cit_res.authoritative_passage_id
            if candidate_passages:
                best_passage = candidate_passages[0].get("text", "")
                best_pid = candidate_passages[0].get("passage_id", best_pid)
            elif cit_res.evidence_passage:
                best_passage = cit_res.evidence_passage

            ev_res = self.evidence_verifier.verify(
                claim=ctext,
                evidence_passage=best_passage,
                case_id=cid,
                authoritative_passage_id=best_pid,
            )

            # Tier C: Temporal Verification
            temp_res = self.temporal_verifier.verify(
                citation=cit, claim_text=ctext, case_id=cid
            )

            # Synthesize overall status for the proposition
            if cit_res.status == "FABRICATED_CITATION":
                final_status = "FABRICATED_CITATION"
                explanation = cit_res.explanation
                tier_failed = "EXISTENCE"
            elif temp_res.status == "CONTRADICTED":
                final_status = "CONTRADICTED"
                explanation = temp_res.explanation
                tier_failed = "TEMPORAL"
            elif ev_res.status == "CONTRADICTED":
                final_status = "CONTRADICTED"
                explanation = ev_res.explanation
                tier_failed = "PASSAGE_SUPPORT"
            elif cit_res.status == "CONTRADICTED":
                final_status = "CONTRADICTED"
                explanation = cit_res.explanation
                tier_failed = "METADATA"
            elif cit_res.status in {"FLAGGED", "METADATA_MISMATCH"}:
                final_status = "FLAGGED"
                explanation = cit_res.explanation
                tier_failed = "METADATA"
            elif ev_res.status == "PARTIALLY_SUPPORTED" or cit_res.status == "PARTIALLY_SUPPORTED":
                final_status = "PARTIALLY_SUPPORTED"
                explanation = ev_res.explanation or cit_res.explanation
                tier_failed = "PASSAGE_SUPPORT"
            elif ev_res.status == "UNSUPPORTED":
                final_status = "UNSUPPORTED"
                explanation = ev_res.explanation
                tier_failed = "PASSAGE_SUPPORT"
            else:
                final_status = "SUPPORTED"
                explanation = ev_res.explanation or cit_res.explanation
                tier_failed = None

            verif_rec = {
                "claim_id": cid,
                "status": final_status,
                "tier_failed": tier_failed,
                "authoritative_passage_id": best_pid,
                "explanation": explanation,
                "citation_result": cit_res.to_dict(),
                "evidence_result": ev_res.to_dict(),
                "temporal_result": temp_res.to_dict(),
            }
            verification_records.append(verif_rec)

            # Compute claim-level confidence score
            c_score = self.confidence_engine.compute_claim_confidence(
                claim_id=cid,
                citation_status=cit_res.status,
                evidence_status=ev_res.status,
                temporal_status=temp_res.temporal_status,
                raw_entailment_score=ev_res.entailment_score,
            )
            claim_confidences.append(c_score)

        # 3. Conflict Detection
        conflict_res = self.conflict_detector.detect_conflicts(
            query=query,
            claims=[c.claim_text for c in extracted_claims],
            evidences=candidate_passages,
        )

        # 4. Aggregate Answer Confidence
        ans_conf = self.confidence_engine.compute_answer_confidence(claim_confidences)

        # 5. Fail-Closed Governor Policy Enforcement
        verdict = self.governor.govern(
            query=query,
            raw_answer=raw_answer,
            claims=[c.to_dict() for c in extracted_claims],
            verification_results=verification_records,
            answer_confidence=ans_conf.to_dict(),
        )

        # 6. Audit Trail Logging
        audit_rec = self.audit_logger.log_verification(
            query=query,
            raw_answer=raw_answer,
            claims=extracted_claims,
            verifications=verification_records,
            confidence=ans_conf,
            verdict=verdict,
        )

        return {
            "audit_id": audit_rec.audit_id,
            "query": query,
            "is_authoritative": verdict.is_accepted and not verdict.fail_closed,
            "fail_closed": verdict.fail_closed,
            "final_answer": verdict.final_answer,
            "overall_confidence": ans_conf.overall_confidence,
            "claims": [c.to_dict() for c in extracted_claims],
            "verification_records": verification_records,
            "quarantine_report": verdict.quarantine_report,
            "conflict_detection": conflict_res.to_dict(),
            "content_hash": audit_rec.content_hash,
            "timestamp": audit_rec.timestamp,
        }
