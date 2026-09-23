"""
HALO Citation Verifier: Citation-to-Claim Association (Tier 3)
==============================================================
Protocol: v1.0-FROZEN
Associates verified citations with their referencing atomic claims.
Preserves claim_ids, character spans, and matched passage IDs for downstream Evidence Verifier.
Strictly avoids truth/evidence support evaluation (Gate CV9).
"""

from typing import List, Dict, Any
from halo.citation_verifier.schemas import CitationVerificationRecord


class CitationClaimAssociator:
    """Associates citation records with referencing claim IDs."""

    @staticmethod
    def map_claims_to_citations(
        claims: List[Dict[str, Any]],
        citation_records: List[CitationVerificationRecord]
    ) -> List[CitationVerificationRecord]:
        """
        Maps extracted claims to citations based on explicit citation_refs or span containment.
        Updates claim_ids in CitationVerificationRecord in-place and returns the updated records.
        """
        for cit_rec in citation_records:
            associated_claims = set(cit_rec.claim_ids)

            for claim in claims:
                cid = claim.get("claim_id")
                if not cid:
                    continue

                # Check 1: Explicit citation_refs attached to claim
                cit_refs = claim.get("citation_refs", [])
                for cr in cit_refs:
                    cr_text = cr.get("citation_text", "")
                    if cr_text and (cr_text == cit_rec.citation_text or cr_text in cit_rec.citation_text or cit_rec.citation_text in cr_text):
                        associated_claims.add(cid)
                    elif cit_rec.start_char == cr.get("start_char") and cit_rec.end_char == cr.get("end_char"):
                        associated_claims.add(cid)

                # Check 2: Citation span contained within claim span
                c_span = claim.get("source_span", {})
                c_st = c_span.get("start_char", -1)
                c_en = c_span.get("end_char", -1)
                if c_st >= 0 and c_en > c_st:
                    if c_st <= cit_rec.start_char and cit_rec.end_char <= c_en:
                        associated_claims.add(cid)

                # Check 3: Text containment in claim_text
                claim_text = claim.get("claim_text", "")
                if cit_rec.citation_text and cit_rec.citation_text in claim_text:
                    associated_claims.add(cid)

            cit_rec.claim_ids = sorted(list(associated_claims))

        return citation_records
