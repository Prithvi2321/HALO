"""
HALO Claim Extractor: Controlled Claim Classifier
=================================================
Protocol: v1.0-FROZEN
Classifies atomic claims into the strictly controlled ClaimType enum.
Deterministic, multi-feature rule-based classification with controlled fallback to OTHER.
"""

import re
from halo.claim_extractor.schemas import ClaimType


class LegalClaimClassifier:
    """Classifies atomic legal claims into the strictly controlled ClaimType enum."""

    # 1. Case Holding patterns
    HOLDING_PATS = [
        re.compile(r"\b(?:held\s+that|ruled\s+that|observed\s+that|laid\s+down\s+that|decided\s+that|judgment\s+in)\b", re.IGNORECASE),
        re.compile(r"\b(?:in\s+(?:Mobilox|Bhushan|Tata|Old\s+Settlers|United\s+India|Apex))\b", re.IGNORECASE),
        re.compile(r"\b(?:Supreme\s+Court\s+(?:held|concluded|settled|affirmed|reversed))\b", re.IGNORECASE),
    ]

    # 2. Exception & Proviso patterns
    EXCEPTION_PATS = [
        re.compile(r"\b(?:provided\s+(?:that|further)|except\s+(?:where|as)|unless\s+otherwise|subject\s+to\s+sub-section|saving\s+clause)\b", re.IGNORECASE),
    ]

    # 3. Definition patterns
    DEFINITION_PATS = [
        re.compile(r"\b(?:means\s+and\s+includes|is\s+defined\s+as|shall\s+mean|shall\s+be\s+deemed\s+to\s+be)\b", re.IGNORECASE),
        re.compile(r"\b(?:term\s+['\"][^'\"]+['\"]\s+means)\b", re.IGNORECASE),
    ]

    # 4. Temporal claim patterns
    TEMPORAL_PATS = [
        re.compile(r"(?:\b(?:effective\s+from|prior\s+to\s+repeal|repealed\s+by|omitted\s+by|amended\s+by|as\s+of\s+\d+|under\s+prevailing\s+law|under\s+current\s+law|in\s+2026|under\s+(?:the\s+)?1956\s+Act|currently|came\s+into\s+force)\b|\bw\.e\.f\.)", re.IGNORECASE),
    ]

    # 5. Authority & Forum patterns
    AUTHORITY_PATS = [
        re.compile(r"\b(?:National\s+Company\s+Law\s+Tribunal|NCLAT|NCLT|Ministry\s+of\s+Corporate\s+Affairs|MCA|Registrar\s+of\s+Companies|ROC|Special\s+Courts?|Parliament\s+of\s+India|Adjudicating\s+Officers?|Tribunal|Company\s+Law\s+Board)\b", re.IGNORECASE),
    ]

    # 6. Legal Prohibition patterns
    PROHIBITION_PATS = [
        re.compile(r"\b(?:shall\s+not|cannot|may\s+not|is\s+prohibited\s+from|strictly\s+prohibited|shall\s+not\s+be\s+eligible|barred\s+from|is\s+barred|no\s+company\s+shall|no\s+person\s+shall|neither\s+director|prohibition\s+on)\b", re.IGNORECASE),
    ]

    # 7. Numerical Requirement patterns (specific thresholds, monetary amounts, days, ratios)
    NUMERICAL_PATS = [
        re.compile(r"\b(?:crore|lakh|percent|%|₹|rupees|clear\s+days|months|years|one-tenth|one-third|one-half|two\s+per\s+cent|minimum\s+(?:number\s+of\s+)?(?:\d+|two|three|five)\s+directors|maximum\s+of\s+(?:\d+|fifteen|twenty)\s+directors)\b", re.IGNORECASE),
    ]

    # 8. Legal Obligation patterns (mandatory force)
    OBLIGATION_PATS = [
        re.compile(r"\b(?:shall\s+(?:constitute|appoint|ensure|spend|file|annex|give|transfer|maintain)|must\s+(?:have|maintain|spend|constitute|be|file)|is\s+required\s+to|mandatory|mandates|obligatory|shall\s+be\s+liable|punishable\s+with)\b", re.IGNORECASE),
    ]

    # 9. Legal Permission patterns (discretionary force)
    PERMISSION_PATS = [
        re.compile(r"\b(?:may\s+(?!not\b)[a-z]+|is\s+permitted\s+to|can\s+choose|discretionary|has\s+discretion|at\s+its\s+option|purely\s+voluntary|entitled\s+to|liberty\s+to)\b", re.IGNORECASE),
    ]

    # 10. Procedural Requirement patterns
    PROCEDURAL_PATS = [
        re.compile(r"\b(?:ordinary\s+resolution|special\s+resolution|board\s+resolution|general\s+meeting|annual\s+general\s+meeting|AGM|EGM|notice\s+in\s+writing|board\s+consent|audit\s+committee\s+approval|requisition)\b", re.IGNORECASE),
    ]

    # 11. Scope of Applicability patterns
    SCOPE_PATS = [
        re.compile(r"\b(?:applies\s+to|applicable\s+to|exempt\s+from|listed\s+(?:public\s+)?company|private\s+company|foreign\s+company|charitable\s+company)\b", re.IGNORECASE),
    ]

    # 12. Statutory Provision patterns
    STATUTORY_PATS = [
        re.compile(r"\b(?:Section|Sec\.|Sections|Secs\.)\s+\d+[A-Za-z]?(?:\(\d+\))*\b", re.IGNORECASE),
        re.compile(r"\b(?:Companies\s+Act,\s*\d{4}|Insolvency\s+and\s+Bankruptcy\s+Code)\b", re.IGNORECASE),
    ]

    def classify(self, claim_text: str) -> str:
        """
        Classifies claim text into the controlled ClaimType enum string.
        Evaluates specialized legal categories before falling back to general ones.
        """
        cleaned = claim_text.strip()
        if not cleaned:
            return ClaimType.OTHER.value

        # Priority 1: Judicial Precedent / Case Holding
        for pat in self.HOLDING_PATS:
            if pat.search(cleaned):
                return ClaimType.CASE_HOLDING.value

        # Priority 2: Statutory Exception / Proviso
        for pat in self.EXCEPTION_PATS:
            if pat.search(cleaned):
                return ClaimType.EXCEPTION.value

        # Priority 3: Definitions
        for pat in self.DEFINITION_PATS:
            if pat.search(cleaned):
                return ClaimType.DEFINITION.value

        # Priority 4: Chronological / Temporal Claims
        for pat in self.TEMPORAL_PATS:
            if pat.search(cleaned):
                return ClaimType.TEMPORAL_CLAIM.value

        # Priority 5: Authority / Forum / Regulatory Jurisdiction
        for pat in self.AUTHORITY_PATS:
            if pat.search(cleaned):
                return ClaimType.AUTHORITY_CLAIM.value

        # Priority 6: Legal Prohibitions (Absolute negative bars)
        for pat in self.PROHIBITION_PATS:
            if pat.search(cleaned):
                return ClaimType.LEGAL_PROHIBITION.value

        # Priority 7: Quantitative / Numerical Thresholds
        for pat in self.NUMERICAL_PATS:
            if pat.search(cleaned):
                return ClaimType.NUMERICAL_REQUIREMENT.value

        # Priority 8: Legal Obligations (Affirmative statutory duties)
        for pat in self.OBLIGATION_PATS:
            if pat.search(cleaned):
                return ClaimType.LEGAL_OBLIGATION.value

        # Priority 9: Legal Permissions (Discretionary options)
        for pat in self.PERMISSION_PATS:
            if pat.search(cleaned):
                return ClaimType.LEGAL_PERMISSION.value

        # Priority 10: Procedural Formalities
        for pat in self.PROCEDURAL_PATS:
            if pat.search(cleaned):
                return ClaimType.PROCEDURAL_REQUIREMENT.value

        # Priority 11: Scope of Application
        for pat in self.SCOPE_PATS:
            if pat.search(cleaned):
                return ClaimType.SCOPE_CLAIM.value

        # Priority 12: Statutory Provision Citation / Statement
        for pat in self.STATUTORY_PATS:
            if pat.search(cleaned):
                return ClaimType.STATUTORY_PROVISION.value

        # Default legal requirement or factual assertion
        if any(w in cleaned.lower() for w in ["director", "company", "board", "share", "member", "audit"]):
            return ClaimType.LEGAL_REQUIREMENT.value

        return ClaimType.OTHER.value
