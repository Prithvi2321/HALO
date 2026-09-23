"""
Fail-Closed Governor Subsystem
==============================
Protocol: v1.0-FROZEN
Deterministic policy governor enforcing zero tolerance for unsupported legal claims.
"""

import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional


@dataclass
class GovernorVerdict:
    is_accepted: bool = False
    fail_closed: bool = False
    final_answer: str = ""
    verified_claims: List[Dict[str, Any]] = field(default_factory=list)
    qualified_claims: List[Dict[str, Any]] = field(default_factory=list)
    rejected_claims: List[Dict[str, Any]] = field(default_factory=list)
    overall_confidence: float = 0.0
    quarantine_report: Dict[str, Any] = field(default_factory=dict)
    audit_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FailClosedGovernor:
    """Enforces fail-closed quarantine and reconstructs trustworthy legal answers."""

    FAIL_CLOSED_NOTICE = (
        "### [FAIL-CLOSED ADVISORY: UNVERIFIED LEGAL ASSERTION]\n"
        "**Status**: QUARANTINED / REFUSED (Zero Authoritative Evidence)\n"
        "The HALO Verification System evaluated the query against the authoritative legal corpora "
        "(Companies Act, 2013 and Supreme Court Judgments) and determined that the asserted proposition "
        "is unsupported, contradicted, or outside the corpus coverage.\n\n"
        "To ensure zero ungrounded legal hallucination, this system refuses to endorse uncorroborated conclusions."
    )

    def __init__(self):
        pass

    def _compute_audit_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def govern(
        self,
        query: str,
        raw_answer: str,
        claims: List[Dict[str, Any]],
        verification_results: List[Dict[str, Any]],
        answer_confidence: Optional[Dict[str, Any]] = None,
    ) -> GovernorVerdict:
        """
        Filters claims, isolates discrepancies, triggers fail-closed when evidence is missing,
        and reconstructs an audited authoritative answer.
        """
        verified_claims = []
        qualified_claims = []
        rejected_claims = []

        # Map results by claim_id or index
        for idx, clm in enumerate(claims):
            vr = verification_results[idx] if idx < len(verification_results) else {}
            status = vr.get("status", "UNSUPPORTED")
            explanation = vr.get("explanation", "")
            pid = vr.get("authoritative_passage_id")

            item = {
                "claim_id": clm.get("claim_id", f"CLM_{idx+1:03d}"),
                "claim_text": clm.get("claim_text", ""),
                "citation_ids": clm.get("citation_ids", []),
                "status": status,
                "authoritative_passage_id": pid,
                "explanation": explanation,
                "tier_failed": vr.get("tier_failed"),
                "metadata_diff": vr.get("metadata_diff", {}),
            }

            if status == "SUPPORTED":
                verified_claims.append(item)
            elif status in {"PARTIALLY_SUPPORTED", "FLAGGED"}:
                qualified_claims.append(item)
            else:  # CONTRADICTED, FABRICATED_CITATION, UNSUPPORTED
                rejected_claims.append(item)

        total_claims = len(claims)
        conf = answer_confidence.get("overall_confidence", 0.0) if answer_confidence else 0.0

        # Fail-closed trigger condition:
        # If no verified claims exist, or if all claims are rejected, fail closed immediately.
        if not verified_claims:
            quarantine_rep = {
                "total_claims": total_claims,
                "rejected_count": len(rejected_claims),
                "qualified_count": len(qualified_claims),
                "verified_count": 0,
                "rejection_reasons": [r["explanation"] for r in rejected_claims],
            }
            audit_hash = self._compute_audit_hash(query + self.FAIL_CLOSED_NOTICE)
            return GovernorVerdict(
                is_accepted=False,
                fail_closed=True,
                final_answer=self.FAIL_CLOSED_NOTICE,
                verified_claims=[],
                qualified_claims=qualified_claims,
                rejected_claims=rejected_claims,
                overall_confidence=0.0,
                quarantine_report=quarantine_rep,
                audit_hash=audit_hash,
            )

        # Reconstruct verified answer
        answer_parts = ["### Verified Legal Findings\n"]
        for vc in verified_claims:
            txt = vc["claim_text"]
            pid = vc.get("authoritative_passage_id")
            if pid and pid != "NONE":
                answer_parts.append(f"- {txt} `[Source: {pid}]`")
            else:
                answer_parts.append(f"- {txt}")

        if qualified_claims:
            answer_parts.append("\n### Qualified Observations & Discrepancy Warnings")
            for qc in qualified_claims:
                answer_parts.append(f"- ⚠️ **Notice**: {qc['claim_text']}")
                answer_parts.append(f"  *Discrepancy*: {qc['explanation']}")

        if rejected_claims:
            answer_parts.append("\n### Quarantined / Suppressed Claims")
            for rc in rejected_claims:
                answer_parts.append(f"- ❌ **Purged**: {rc['claim_text']}")
                answer_parts.append(f"  *Reason*: {rc['explanation']}")

        final_ans = "\n".join(answer_parts)
        audit_hash = self._compute_audit_hash(query + final_ans)

        quarantine_rep = {
            "total_claims": total_claims,
            "verified_count": len(verified_claims),
            "qualified_count": len(qualified_claims),
            "rejected_count": len(rejected_claims),
            "quarantine_active": len(rejected_claims) > 0,
        }

        return GovernorVerdict(
            is_accepted=True,
            fail_closed=False,
            final_answer=final_ans,
            verified_claims=verified_claims,
            qualified_claims=qualified_claims,
            rejected_claims=rejected_claims,
            overall_confidence=conf if conf > 0.0 else 0.85,
            quarantine_report=quarantine_rep,
            audit_hash=audit_hash,
        )
