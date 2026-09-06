# HALO Dataset 2: Curated Judicial Corpus Policy

**Corpus Scope**: Indian Corporate & Company Law  
**Relationship to Dataset 1**: Interprets, elaborates, and applies the provisions of the Companies Act, 2013 (and predecessor 1956 provisions with statutory continuity).  
**Target Size**: ~40–60 Curated Judgments  
**Governance Standard**: Fail-Closed Ingestion & Auditability

---

## 1. Cardinal Inclusion Criteria
A judgment is admitted into HALO Dataset 2 **only if** it satisfies all 10 inclusion criteria:

1. **Approved Source Authority**: Originates from an established, verifiable official repository (Supreme Court Reports/SCR, eCourts official portal) or a verified secondary open repository.
2. **Definite Court Identity**: Court level and bench are deterministically established (Supreme Court of India, National Company Law Appellate Tribunal, or High Court commercial division).
3. **Established Judgment Date**: The exact date of judgment/order is present and formatted in ISO-8601 (`YYYY-MM-DD`).
4. **Authoritative Case Number & Citation**: Contains an official case number (e.g. Civil Appeal, Company Appeal) and/or an official citation (INSC, SCR, SCC, Comp Cas).
5. **Corporate Law Subject Matter**: Directly concerns, interprets, or applies Indian corporate law, company law doctrines, statutory provisions of the Companies Act (2013 or 1956), or corporate insolvency interaction.
6. **Substantive Judicial Reasoning**: Contains substantive ratio decidendi or legal reasoning (not a routine administrative adjournment or summary dismissal without reasoning).
7. **Complete Textual Integrity**: Contains the full text of the judgment with readable typography, intact paragraphs, and verifiable page progression.
8. **Deterministic Lineage (Source Snapshot)**: URL, HTTP metadata, file size, retrieval timestamp, and SHA-256 hash must be recorded.
9. **Unique Identification**: Receives a persistent canonical identifier (`JUD-{COURT}-{ID}`) and does not duplicate an existing corpus record.
10. **Dataset 1 Cross-Referencing**: Contains at least one identifiable statutory cross-reference to an Indian statutory provision (with priority for Companies Act sections).

---

## 2. Cardinal Exclusion Criteria (Fail-Closed)
A candidate document is **strictly excluded** if any of the following apply:

1. **Unknown Court or Bench**: The issuing judicial forum cannot be verified with certainty.
2. **Unknown or Contradictory Date**: Judgment date is absent, malformed, or contradictory.
3. **Broken or Incomplete PDF**: Truncated pages, missing end pages, unreadable font encoding, or corrupt byte streams.
4. **Duplicate Record**: Matches an existing judgment by normalized case number, parties, date, or text fingerprint.
5. **Routine / Procedural Order**: Daily order sheets, notice issues, cause lists, or administrative directions lacking legal ratio.
6. **Unrelated Legal Domain**: Criminal, family, personal status, or tenancy disputes with no nexus to corporate law.
7. **Unverified Metadata**: Core metadata fields cannot be corroborated from authoritative source records.
8. **Unrecoverable OCR Quality**: Scanned document where OCR confidence falls below 0.80 or dictionary word ratio is below 70%.
9. **Commercial / Proprietary Annotations**: Headnotes or copyrighted summaries from proprietary commercial publishers.
10. **Synthetic / Artificial Content**: Any document generated, rewritten, or summarized by an LLM.

---

## 3. Fail-Closed Enforcement
If any inclusion test fails or an exclusion flag is raised, the ingestion pipeline terminates processing for that record with a descriptive rejection status (`REJECTED_METADATA`, `REJECTED_DUPLICATE`, `REJECTED_LOW_QUALITY`, `REJECTED_OUT_OF_DOMAIN`). Ambiguity is never resolved by guessing.
