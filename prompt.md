# HALO — DATASET 1

## Production-Grade Ingestion and Consolidation of the Companies Act, 2013

You are acting as a combined:

* Senior Legal Data Architect
* Indian Legislative Document Specialist
* Data Engineering Lead
* Information Retrieval Engineer
* Document Parsing Engineer
* AI/ML Dataset Engineer
* FAANG Staff Software Engineer
* Data Quality Engineer
* Cybersecurity Architect
* Legal-Tech System Architect

You are working on **HALO**, a trustworthy Indian legal research system.

Your task is NOT to build a chatbot.

Your task is to design and implement the **authoritative statutory ingestion pipeline for Dataset 1**, beginning with the **Companies Act, 2013**.

The resulting dataset will later be used for:

* hybrid BM25 + semantic retrieval
* legal question answering
* citation verification
* claim-evidence verification
* temporal legal reasoning
* amendment tracking
* source provenance
* hallucination detection
* fail-closed behavior
* evaluation benchmarks

The ingestion pipeline must therefore prioritize:

> **LEGAL CORRECTNESS > TRACEABILITY > DETERMINISM > DATA QUALITY > COMPLETENESS > CONVENIENCE**

Do not take shortcuts.

Do not invent legal text.

Do not silently repair ambiguous legal text.

Do not use an LLM to determine authoritative ground truth when deterministic extraction or official source evidence is available.

---

# 1. PRIMARY OBJECTIVE

Build a production-grade ingestion pipeline that transforms official Companies Act, 2013 source documents into a structured, version-aware, provenance-preserving JSON dataset.

The pipeline must support:

```text
Original Companies Act, 2013
        +
Amending Acts
        +
Official amendment notifications/orders where relevant
        +
Official consolidated/current version, if available
        ↓
Document discovery
        ↓
PDF integrity verification
        ↓
Text extraction
        ↓
OCR fallback where necessary
        ↓
Page-aware normalization
        ↓
Legislative structure detection
        ↓
Section/subsection/clause parsing
        ↓
Schedule parsing
        ↓
Cross-reference detection
        ↓
Amendment extraction
        ↓
Temporal/version reconstruction
        ↓
Current consolidated representation
        ↓
Validation
        ↓
Dataset 1 JSON
        ↓
Quality report
        ↓
Human review queue for uncertain records
```

The final system must allow a developer to answer:

> “Where exactly did this legal text come from?”

For every extracted legal provision, we must be able to trace:

```text
Current provision
    ↓
section/subsection/clause
    ↓
source page
    ↓
source PDF
    ↓
source document hash
    ↓
official source URL
    ↓
version/effective date
    ↓
amendment history
```

---

# 2. CRITICAL LEGAL REQUIREMENT

Do NOT assume that downloading only the original Companies Act PDF is sufficient.

An amendment Act may contain text such as:

* “for the words X, the words Y shall be substituted”
* “in section X...”
* “after sub-section (X), the following shall be inserted”
* “sub-section X shall be omitted”
* “section X shall be substituted”
* “in clause X...”
* “for clause X, the following clause shall be substituted”

The amendment document may therefore NOT contain the complete updated Companies Act.

The system must treat legislation as versioned source material.

Conceptually:

```text
Original Act
    ↓
Amendment 1
    ↓
Amendment 2
    ↓
Amendment 3
    ↓
...
    ↓
Current legally applicable text
```

The system must NEVER blindly concatenate amendment documents to the original Act.

---

# 3. SOURCE HIERARCHY

Design the ingestion system around source authority.

Preferred source hierarchy:

1. Official Government of India legislative source
2. India Code
3. Official Gazette
4. Ministry of Corporate Affairs
5. Legislative Department
6. Other official government publication
7. Secondary legal databases ONLY for cross-checking
8. Never treat random websites as authoritative ground truth

If multiple official sources disagree:

* do NOT silently choose one
* record the conflict
* preserve both source references
* create a human-review item
* identify which source has stronger authority
* explain the conflict

Never fabricate a resolution.

---

# 4. INPUT DOCUMENT TYPES

The pipeline must support these document types.

## A. Original Act

Example:

```text
Companies Act, 2013
Act No. 18 of 2013
```

Store:

```text
version_type = "original"
```

## B. Amending Act

Example:

```text
Companies (Amendment) Act, YYYY
```

Store:

```text
version_type = "amendment"
```

## C. Amendment Rules / Notifications

Where relevant, distinguish:

```text
amendment_act
amendment_rules
notification
order
circular
```

Do not mix these categories.

## D. Consolidated Act

If an official source provides a consolidated version incorporating amendments:

```text
version_type = "consolidated"
```

Record:

```text
consolidated_as_of
```

## E. Historical versions

If available, preserve them.

Example:

```text
2013 original
2015 version
2017 version
2020 version
2023 version
current version
```

---

# 5. REQUIRED DIRECTORY STRUCTURE

Design the project around this structure:

```text
halo/
│
├── data/
│   │
│   └── dataset_1/
│       │
│       ├── companies_act_2013/
│       │   │
│       │   ├── original/
│       │   │   └── companies_act_2013_original.pdf
│       │   │
│       │   ├── amendments/
│       │   │   ├── amendment_2015.pdf
│       │   │   ├── amendment_2017.pdf
│       │   │   └── ...
│       │   │
│       │   ├── notifications/
│       │   │
│       │   ├── consolidated/
│       │   │   └── companies_act_2013_current.pdf
│       │   │
│       │   └── metadata/
│       │
│       ├── raw/
│       ├── extracted/
│       ├── normalized/
│       ├── structured/
│       ├── versions/
│       ├── validation/
│       ├── review_queue/
│       └── final/
│
├── scripts/
│   ├── download/
│   ├── extraction/
│   ├── parsing/
│   ├── amendments/
│   ├── validation/
│   └── export/
│
└── reports/
```

Never overwrite original source PDFs.

---

# 6. SOURCE MANIFEST

Before processing any PDF, generate a source manifest.

Required fields:

```json
{
  "source_document_id": "",
  "document_type": "",
  "title": "",
  "act_title": "",
  "act_number": "",
  "publication_date": "",
  "enactment_date": "",
  "effective_date": "",
  "version_type": "",
  "as_of_date": "",
  "source_name": "",
  "source_url": "",
  "downloaded_at": "",
  "file_name": "",
  "file_size_bytes": 0,
  "sha256": "",
  "page_count": 0,
  "mime_type": "application/pdf"
}
```

If a value cannot be determined:

```json
null
```

Never invent it.

---

# 7. PDF INTEGRITY CHECK

Before extraction:

1. Confirm file exists.
2. Confirm PDF can be opened.
3. Calculate SHA-256.
4. Determine page count.
5. Determine whether PDF contains:

   * embedded text
   * scanned images
   * mixed text and images
6. Detect encrypted/password-protected PDFs.
7. Detect corrupted pages.
8. Detect empty pages.
9. Detect duplicated pages.
10. Detect suspicious page numbering.

Generate a report.

Example:

```json
{
  "document_id": "...",
  "pdf_valid": true,
  "page_count": 500,
  "has_embedded_text": true,
  "requires_ocr": false,
  "warnings": []
}
```

---

# 8. TEXT EXTRACTION STRATEGY

Use this priority:

```text
Native PDF text extraction
        ↓
Quality assessment
        ↓
If quality insufficient:
        OCR
        ↓
Compare native text and OCR
        ↓
Select best representation
```

Do not OCR every page unnecessarily.

Preserve:

```text
page_number
raw_text
extraction_method
```

Example:

```json
{
  "page_number": 17,
  "text": "...",
  "extraction_method": "native_pdf"
}
```

or:

```json
{
  "page_number": 17,
  "text": "...",
  "extraction_method": "ocr"
}
```

---

# 9. OCR EDGE CASES

Handle:

* `Section` recognized as `Sectlon`
* `1` recognized as `I`
* `0` recognized as `O`
* `(1)` recognized as `(l)`
* `(a)` recognized as `(a)`
* broken words
* missing punctuation
* duplicated text
* header/footer contamination
* page numbers inserted into paragraphs
* hyphenation across lines
* multi-column ordering problems
* tables
* footnotes
* marginal notes
* stamps
* signatures
* handwritten annotations
* government seals
* low-resolution scans

IMPORTANT:

Never silently alter legal wording because OCR appears incorrect.

Instead:

```json
{
  "raw_text": "...",
  "normalized_text": "...",
  "ocr_warning": true,
  "review_required": true
}
```

---

# 10. PAGE-AWARE EXTRACTION

Every extracted provision must retain page provenance.

At minimum:

```text
source_document_id
source_page_start
source_page_end
```

Prefer:

```text
source_page
source_text_offset_start
source_text_offset_end
```

where feasible.

This allows HALO to later show:

> “This claim came from Section 135(1), page 87 of the authoritative source.”

---

# 11. HEADER AND FOOTER REMOVAL

Detect repeated headers and footers.

Examples:

```text
THE COMPANIES ACT, 2013
MINISTRY OF CORPORATE AFFAIRS
Page 45
```

Do not allow these to contaminate legal passage embeddings.

However:

> NEVER delete text merely because it appears repetitive.

First determine whether it is:

* header
* footer
* legal text
* marginal note
* section heading

Store removed boilerplate separately for auditability.

---

# 12. LEGAL STRUCTURE PARSER

Identify the hierarchy:

```text
Act
 ├── Chapter
 │    ├── Section
 │    │    ├── subsection
 │    │    │    ├── clause
 │    │    │    │    └── sub-clause
 │    │    │
 │    │    └── explanation/proviso
 │    │
 │    └── ...
 │
 └── Schedule
```

The parser must NOT assume that every Act follows exactly the same formatting.

---

# 13. SECTION DETECTION

Detect patterns such as:

```text
1.
1. Short title...
2.
3.
```

Also support:

```text
Section 1
Section 2
```

and formatting where the number and heading appear on separate lines.

Each section must receive deterministic ID:

```text
ACT_COMPANIES_2013_SEC_1
ACT_COMPANIES_2013_SEC_2
...
```

Never generate random IDs.

---

# 14. SECTION METADATA

Each section should contain:

```json
{
  "section_id": "ACT_COMPANIES_2013_SEC_1",
  "section_number": "1",
  "heading": "",
  "text": "",
  "subsections": [],
  "provisos": [],
  "explanations": [],
  "illustrations": [],
  "clauses": [],
  "source_page_start": 1,
  "source_page_end": 2,
  "effective_from": null,
  "effective_to": null,
  "version_id": "",
  "amendment_history": []
}
```

---

# 15. SUBSECTION PARSING

Support:

```text
(1)
(2)
(3)
```

Do not flatten subsections irreversibly.

Example:

```json
{
  "subsection_id": "ACT_COMPANIES_2013_SEC_135_SUB_1",
  "subsection_number": "1",
  "text": "...",
  "clauses": []
}
```

---

# 16. CLAUSE PARSING

Support:

```text
(a)
(b)
(c)
```

and:

```text
(i)
(ii)
(iii)
```

and nested structures.

Example:

```text
(1)
  (a)
    (i)
    (ii)
  (b)
```

Represent hierarchy explicitly.

---

# 17. PROVISOS

Detect:

```text
Provided that...
Provided further that...
```

A proviso is legally significant.

Do NOT merge it into unrelated text without preserving its identity.

Example:

```json
{
  "type": "proviso",
  "text": "..."
}
```

---

# 18. EXPLANATIONS

Detect:

```text
Explanation.—
Explanation:
```

Preserve explanations separately.

They may materially affect interpretation.

---

# 19. DEFINITIONS

Identify definition sections and individual defined terms.

For example:

```text
"company" means ...
```

Preserve the defined term.

Recommended:

```json
{
  "term": "company",
  "definition": "...",
  "section_id": "..."
}
```

Do not treat definitions as ordinary prose only.

---

# 20. SCHEDULES

Do not ignore Schedules.

The Companies Act may contain legally relevant schedules.

Represent:

```json
{
  "schedule_id": "",
  "schedule_number": "",
  "title": "",
  "parts": [],
  "paragraphs": [],
  "source_pages": []
}
```

Handle:

* Parts
* paragraphs
* tables
* forms
* numbered items
* notes

---

# 21. TABLES

Tables may contain legally meaningful information.

Do not simply discard tables.

For each table:

```json
{
  "table_id": "",
  "caption": "",
  "headers": [],
  "rows": [],
  "source_page": 0
}
```

Preserve the original textual representation as well.

---

# 22. CROSS-REFERENCES

Detect references such as:

```text
section 135
section 135(1)
clause (a)
sub-section (3)
Schedule II
section 2(76)
```

Create explicit relationships.

Example:

```json
{
  "source_passage_id": "...",
  "target_reference": "Section 135",
  "reference_type": "cross_reference"
}
```

Do NOT resolve references using guesses.

---

# 23. INTERNAL REFERENCES

Detect:

```text
as provided in this Act
under this section
under sub-section (1)
subject to section X
notwithstanding anything contained in...
```

These relationships are important for multi-hop retrieval.

Store them.

---

# 24. AMENDMENT DOCUMENT PARSING

This is one of the most important requirements.

For every amendment document, extract:

```text
amending_act
amendment_date
effective_date
target_act
target_section
target_subsection
target_clause
operation
old_text
new_text
provenance
```

Possible operations:

```text
INSERT
DELETE
SUBSTITUTE
RENUMBER
OMIT
ADD
REPEAL
REPEAL_AND_REPLACE
MODIFY
PROVISO_INSERT
CLAUSE_INSERT
SCHEDULE_REPLACEMENT
```

Example:

```json
{
  "amendment_id": "...",
  "target_section": "135",
  "target_subsection": "1",
  "operation": "SUBSTITUTE",
  "old_text": "...",
  "new_text": "...",
  "effective_from": "...",
  "source_document_id": "...",
  "source_page": 5
}
```

---

# 25. AMENDMENT APPLICATION ENGINE

Do NOT ask an LLM to simply rewrite the entire Act after reading amendments.

Instead:

```text
Original structured Act
        ↓
Amendment operations
        ↓
Deterministic transformation engine
        ↓
New structured version
```

Each transformation must be logged.

Example:

```json
{
  "target": "ACT_COMPANIES_2013_SEC_135_SUB_1",
  "operation": "SUBSTITUTE",
  "previous_version": "...",
  "new_version": "...",
  "amendment_id": "...",
  "effective_date": "...",
  "applied_at": "..."
}
```

---

# 26. AMENDMENT EDGE CASES

Explicitly handle:

### Case 1 — Section replacement

```text
Section 5 shall be substituted by...
```

### Case 2 — Subsection replacement

```text
for sub-section (2), substitute...
```

### Case 3 — Clause insertion

```text
after clause (a), insert...
```

### Case 4 — Clause deletion

```text
clause (b) shall be omitted
```

### Case 5 — Word substitution

```text
for the words "X", substitute "Y"
```

### Case 6 — Phrase substitution

```text
for "X and Y", substitute "A and B"
```

### Case 7 — Multiple substitutions

One amendment may modify multiple locations.

### Case 8 — Renumbering

```text
sub-section (3) shall be renumbered as sub-section (4)
```

### Case 9 — Consequential amendment

One change may require related references to be updated.

### Case 10 — Schedule replacement

An entire Schedule may be replaced.

### Case 11 — Amendment with delayed commencement

The amendment Act may be enacted on one date but come into force later.

Do NOT use enactment date automatically as effective date.

### Case 12 — Different commencement dates

Different provisions may come into force on different dates.

### Case 13 — Retrospective amendment

Preserve retrospective effect.

### Case 14 — Partial commencement

Some provisions may be commenced while others remain uncommenced.

### Case 15 — Repeal

Record the repeal event.

### Case 16 — Savings clause

Preserve savings provisions.

### Case 17 — Ordinance / later Act interaction

Do not assume chronological order alone determines legal applicability.

### Case 18 — Amendment to an already amended provision

Apply amendments in correct legal order.

---

# 27. EFFECTIVE DATE LOGIC

Distinguish:

```text
enactment_date
publication_date
commencement_date
effective_from
effective_to
```

Never assume:

```text
enactment_date == effective_date
```

If commencement information is unavailable:

```json
"effective_from": null,
"review_required": true
```

---

# 28. TEMPORAL VERSIONING

Every legal provision should conceptually support:

```text
version_id
valid_from
valid_to
```

Example:

```json
{
  "version_id": "COMPANIES_2013_SEC_135_V3",
  "valid_from": "2020-04-01",
  "valid_to": null
}
```

Historical versions must remain available.

Do NOT destroy old text when applying amendments.

---

# 29. CURRENT CONSOLIDATED VERSION

If an official consolidated Companies Act is available:

Use it as:

```text
authoritative validation target
```

NOT as a replacement for amendment provenance.

Compare:

```text
deterministically reconstructed version
             VS
official consolidated version
```

If differences exist:

```text
FAIL VALIDATION
```

Do not automatically modify the dataset.

Generate:

```text
CONSOLIDATION_MISMATCH
```

and send it to review.

---

# 30. JSON DATA MODEL

Generate a final canonical structure similar to:

```json
[
  {
    "document_id": "ACT_COMPANIES_2013",
    "source": "India Code",
    "act_title": "The Companies Act, 2013",
    "act_number": "18 of 2013",
    "enactment_date": null,
    "jurisdiction": "India",
    "document_type": "Central Act",
    "source_url": "",
    "retrieved_at": "",
    "content_hash": "",
    "version_id": "",
    "version_type": "consolidated_current",
    "as_of_date": null,
    "chapters": []
  }
]
```

Use:

```text
snake_case
```

consistently.

---

# 31. DETERMINISTIC IDENTIFIERS

IDs must be generated by code.

Examples:

```text
ACT_COMPANIES_2013

ACT_COMPANIES_2013_CH_1

ACT_COMPANIES_2013_SEC_1

ACT_COMPANIES_2013_SEC_2

ACT_COMPANIES_2013_SEC_2_SUB_1

ACT_COMPANIES_2013_SEC_2_SUB_1_CLAUSE_A

ACT_COMPANIES_2013_SCH_1
```

Passage IDs:

```text
PAS_ACT_COMPANIES_2013_SEC_2
PAS_ACT_COMPANIES_2013_SEC_2_SUB_1
PAS_ACT_COMPANIES_2013_SEC_2_SUB_1_CLAUSE_A
```

Never let an LLM generate IDs.

---

# 32. CANONICAL TEXT

Define deterministic normalization rules.

Allowed:

* normalize Unicode
* normalize whitespace
* normalize line breaks
* remove extraction-only artifacts
* remove repeated headers/footers
* normalize obvious PDF encoding artifacts

NOT allowed without review:

* changing legal words
* correcting grammar
* changing punctuation that may have legal meaning
* changing numbers
* changing dates
* changing section references
* changing defined terms

Maintain both:

```text
raw_text
canonical_text
```

---

# 33. CONTENT HASHING

Calculate SHA-256 hashes for:

1. Original PDF
2. Extracted page text
3. Canonical section text
4. Complete structured document

Example:

```json
{
  "source_pdf_sha256": "...",
  "canonical_text_sha256": "...",
  "structured_content_sha256": "..."
}
```

This prevents silent data corruption.

---

# 34. LEGAL TEXT MUST NEVER BE GENERATED

The LLM must NEVER:

* invent missing sections
* reconstruct missing text from memory
* guess OCR output
* invent amendment dates
* invent page numbers
* invent source URLs
* invent Act numbers
* invent section headings
* fabricate citations
* fill missing legal text from general knowledge

If uncertain:

```text
UNKNOWN
```

or:

```json
"review_required": true
```

---

# 35. LLM ROLE

Use the LLM only for tasks where semantic interpretation is useful.

Examples:

* classify ambiguous document type
* identify probable amendment operation
* detect suspicious structural anomalies
* suggest section boundaries when deterministic parser is uncertain
* classify OCR anomalies
* identify possible cross-references
* explain validation mismatches

But:

> LLM output must NEVER overwrite authoritative extracted text automatically.

The LLM may produce:

```json
{
  "suggestion": "...",
  "confidence": 0.81,
  "requires_human_review": true
}
```

---

# 36. CONFIDENCE MODEL

Separate:

```text
extraction_confidence
parsing_confidence
amendment_confidence
validation_confidence
```

Do not create a single meaningless confidence number.

Example:

```json
{
  "extraction_confidence": 0.99,
  "structure_confidence": 0.96,
  "amendment_confidence": 0.91,
  "validation_status": "PASS"
}
```

---

# 37. FAILURE STATES

Define explicit failure states.

Examples:

```text
PDF_CORRUPTED
PDF_ENCRYPTED
OCR_REQUIRED
OCR_LOW_CONFIDENCE
TEXT_EXTRACTION_FAILED
SECTION_PARSE_FAILED
SUBSECTION_PARSE_FAILED
CLAUSE_PARSE_FAILED
DUPLICATE_SECTION
MISSING_SECTION
INVALID_SECTION_SEQUENCE
AMBIGUOUS_AMENDMENT
UNKNOWN_EFFECTIVE_DATE
CONSOLIDATION_MISMATCH
SOURCE_CONFLICT
PAGE_MAPPING_FAILED
HASH_MISMATCH
UNSUPPORTED_STRUCTURE
REVIEW_REQUIRED
```

Never hide failures.

---

# 38. DUPLICATE DETECTION

Detect:

* duplicate pages
* duplicate sections
* duplicate amendment records
* repeated paragraphs
* duplicate PDFs
* identical source hashes
* near-duplicate versions

Use:

```text
SHA-256
exact text comparison
normalized text comparison
similarity detection
```

Do not delete duplicates automatically.

Mark them.

---

# 39. MISSING DATA DETECTION

Check:

* missing section numbers
* unexpected jumps
* duplicate section numbers
* missing headings
* missing subsections
* missing schedules
* empty legal text
* suspiciously short sections
* pages with no extracted text
* pages containing images but no text

Example:

```text
Section 134
Section 135
Section 137
```

Potential missing:

```text
Section 136
```

Do NOT assume Section 136 is missing because numbering can be intentionally omitted/repealed.

Instead:

```text
possible_missing_or_omitted_section
```

and validate against official source.

---

# 40. REPEALED / OMITTED PROVISIONS

Do not simply delete repealed or omitted provisions.

Preserve historical existence.

Example:

```json
{
  "section_number": "X",
  "status": "omitted",
  "historical_text": "...",
  "effective_to": "...",
  "repealed_by": "..."
}
```

This is critical for temporal legal research.

---

# 41. FOOTNOTES AND EDITORIAL NOTES

Distinguish:

```text
legal text
editorial note
source annotation
footnote
marginal note
```

Do not accidentally merge editorial notes into statutory text.

---

# 42. MULTI-COLUMN PDF PROBLEM

Detect reading order.

If the PDF visually contains:

```text
Column 1       Column 2
A              B
C              D
```

do not extract:

```text
A B C D
```

if the actual reading order is:

```text
A C B D
```

Use layout-aware extraction where necessary.

---

# 43. PAGE BREAK PROBLEM

A section may span:

```text
Page 10
Page 11
Page 12
```

Do not treat page breaks as legal boundaries.

The section must remain one logical provision.

---

# 44. LINE BREAK PROBLEM

Input:

```text
The company
shall maintain
proper books
of account.
```

Output:

```text
The company shall maintain proper books of account.
```

But preserve raw extraction too.

---

# 45. HYPHENATION

Example:

```text
inter-
pretation
```

may become:

```text
interpretation
```

But only when deterministic rules strongly support it.

Never alter legally meaningful hyphens blindly.

---

# 46. NUMBERING EDGE CASES

Handle:

```text
2.
2A.
2A(1)
2A(1)(a)
```

and:

```text
section 2A
```

Do not assume all section numbers are integers.

---

# 47. LETTER CASE

Do not normalize legal text to lowercase.

Preserve:

```text
Companies
Company
Central Government
```

exactly.

---

# 48. PUNCTUATION

Preserve authoritative punctuation.

For example:

```text
“and”
```

versus:

```text
“or”
```

must never be normalized as stylistic variants.

---

# 49. SPECIAL CHARACTERS

Handle:

```text
₹
—
–
“
”
'
’
§
%
```

and Unicode safely.

Never corrupt rupee symbols, quotation marks, dashes, or legal symbols.

---

# 50. LEGAL DEFINITIONS

Create a definition index.

Example:

```json
{
  "term": "subsidiary company",
  "source_section": "2(87)",
  "definition_passage_id": "...",
  "valid_from": "...",
  "valid_to": null
}
```

This will later support retrieval.

---

# 51. PROVENANCE REQUIREMENT

Every passage must answer:

```text
What source created this?
Which document?
Which page?
Which section?
Which version?
Which amendment?
Which effective date?
Which hash?
```

No provenance-less legal text may enter the final corpus.

---

# 52. FINAL PASSAGE SCHEMA

Every retrievable passage should approximately contain:

```json
{
  "passage_id": "",
  "document_id": "ACT_COMPANIES_2013",
  "version_id": "",
  "section_id": "",
  "subsection_id": null,
  "clause_id": null,
  "passage_type": "subsection",
  "heading": "",
  "text": "",
  "canonical_text": "",
  "source_document_id": "",
  "source_page_start": 0,
  "source_page_end": 0,
  "source_url": "",
  "effective_from": null,
  "effective_to": null,
  "status": "active",
  "amendment_history": [],
  "content_hash": "",
  "review_required": false
}
```

---

# 53. VALIDATION TESTS

Create automated validation tests for:

### Structural validation

* valid JSON
* required fields
* deterministic IDs
* unique IDs
* correct hierarchy

### Legal structure validation

* section uniqueness
* subsection uniqueness
* clause uniqueness
* schedule presence
* no accidental section loss

### Provenance validation

* every passage has source document
* every passage has source page
* source PDF exists
* source hash matches

### Temporal validation

* valid date format
* valid date ordering
* amendment chronology
* effective date logic

### Amendment validation

* target exists
* operation is supported
* resulting structure remains valid

### Content validation

* empty sections
* suspiciously short sections
* OCR anomalies
* duplicate text
* missing pages

---

# 54. GOLDEN TEST CASES

Create a golden test suite.

It must contain examples of:

1. Simple section
2. Section with subsection
3. Section with clauses
4. Nested clauses
5. Proviso
6. Explanation
7. Definition
8. Schedule
9. Table
10. Cross-reference
11. Section amendment
12. Subsection amendment
13. Clause insertion
14. Clause deletion
15. Word substitution
16. Delayed commencement
17. Repeal
18. Omission
19. Historical version
20. Consolidated version mismatch
21. OCR corruption
22. Multi-column page
23. Section spanning pages
24. Duplicate page
25. Missing page
26. Invalid PDF

---

# 55. QUALITY GATES

A document must NOT enter:

```text
final/
```

unless:

```text
PDF_VALID = PASS
TEXT_EXTRACTION = PASS
STRUCTURE_VALIDATION = PASS
PROVENANCE_VALIDATION = PASS
HASH_VALIDATION = PASS
AMENDMENT_VALIDATION = PASS
CONSOLIDATION_VALIDATION = PASS
```

If any critical check fails:

```text
review_queue/
```

instead.

---

# 56. HUMAN REVIEW QUEUE

Create machine-readable review records.

Example:

```json
{
  "review_id": "",
  "document_id": "",
  "page": 87,
  "entity_id": "",
  "issue_type": "OCR_LOW_CONFIDENCE",
  "severity": "HIGH",
  "machine_output": "",
  "expected_action": "VERIFY_AGAINST_SOURCE_PDF",
  "status": "OPEN"
}
```

Human reviewers should be able to inspect the exact source page.

---

# 57. DATASET VERSIONING

Dataset itself must be versioned.

Example:

```text
dataset_version = 1.0.0
```

Use semantic versioning.

Example:

```text
1.0.0 = initial validated corpus
1.1.0 = new validated source/version
1.1.1 = correction to metadata
2.0.0 = schema-breaking change
```

---

# 58. IMMUTABILITY

Original source files must be immutable.

Never modify:

```text
original/*.pdf
amendments/*.pdf
```

Derived data may be regenerated.

---

# 59. REPRODUCIBILITY

A developer should be able to run:

```bash
python ingest.py
```

and reproduce the structured dataset from the same source files.

Given identical:

```text
source PDFs
parser version
configuration
```

the output should be deterministic.

Avoid random IDs.

---

# 60. AUDIT LOG

Record:

```text
document downloaded
hash generated
text extracted
OCR executed
section parsed
amendment detected
amendment applied
validation executed
validation failed
human review created
dataset exported
```

---

# 61. OUTPUT FILES

Produce at minimum:

```text
final/
├── companies_act_2013.json
├── companies_act_2013_passages.jsonl
├── companies_act_2013_versions.json
├── companies_act_2013_amendments.json
├── companies_act_2013_provenance.json
├── companies_act_2013_cross_references.json
└── companies_act_2013_validation_report.json
```

---

# 62. PASSAGE JSONL

Each line must represent one retrievable legal passage.

Example:

```json
{
  "passage_id": "...",
  "document_id": "...",
  "section_id": "...",
  "text": "...",
  "effective_from": "...",
  "effective_to": null,
  "source_page_start": 87,
  "source_page_end": 88
}
```

This file will later be consumed by:

```text
BM25
Elasticsearch/OpenSearch
vector database
hybrid retrieval
reranker
citation verifier
```

---

# 63. DO NOT MIX DATASET 1 WITH BENCHMARK DATA

Dataset 1 is authoritative corpus data.

Do NOT put synthetic questions into it.

Do NOT put Gemini-generated answers into it.

Do NOT put hallucinated claims into it.

Those belong in separate evaluation datasets.

Dataset 1 should contain:

```text
authoritative legal content
metadata
versions
provenance
amendment history
cross-references
passages
validation information
```

---

# 64. SECURITY

Treat downloaded PDFs as untrusted input.

Protect against:

* malicious PDFs
* zip bombs
* path traversal
* oversized files
* malformed PDFs
* decompression bombs
* malicious OCR payloads
* unexpected embedded files
* executable attachments

Never execute content extracted from PDFs.

Use sandboxed extraction where possible.

---

# 65. PERFORMANCE

Design for eventual ingestion of:

```text
100+
500+
1000+
```

Acts and thousands of amendment documents.

Do not build an architecture that only works for one Act.

Use:

* streaming where possible
* caching
* incremental processing
* document-level checkpoints
* parallel extraction where safe
* deterministic processing
* resumable jobs

---

# 66. INCREMENTAL INGESTION

If a new amendment arrives:

Do NOT reprocess every Act unnecessarily.

Determine:

```text
affected_act
affected_sections
affected_versions
```

and update only necessary derived structures.

However, provide a full rebuild option for verification.

---

# 67. OBSERVABILITY

Track:

```text
documents_processed
pages_processed
OCR_pages
sections_detected
subsections_detected
clauses_detected
amendments_detected
amendments_applied
validation_failures
review_items
processing_time
```

Generate a final ingestion report.

---

# 68. EXPECTED REPORT

Produce something like:

```text
COMPANIES ACT 2013 INGESTION REPORT

Source documents:  X
Pages processed:   X
OCR pages:         X
Sections detected: X
Schedules:         X
Subsections:       X
Clauses:           X
Amendments:        X
Amendments applied:X

Validation:
PDF integrity       PASS
Text extraction     PASS
Structure            PASS
Provenance           PASS
Temporal             PASS
Amendment            PASS
Consolidation        PASS

Human review:
HIGH                 X
MEDIUM               X
LOW                  X
```

---

# 69. CRITICAL ANTI-HALLUCINATION RULE

The following rule is absolute:

> If the source does not contain the information, the ingestion system must not create it.

Examples:

If page number is unknown:

```text
null
```

If effective date is unknown:

```text
null
```

If section heading is unreadable:

```text
review_required = true
```

If amendment target is ambiguous:

```text
amendment_status = "AMBIGUOUS"
```

Never guess.

---

# 70. ROLE OF THE LLM IN AMENDMENT INTERPRETATION

If deterministic parsing identifies:

```text
"in section 135, for sub-section (1), the following shall be substituted..."
```

The LLM may convert this into structured intent:

```json
{
  "target": "135(1)",
  "operation": "SUBSTITUTE",
  "confidence": 0.97
}
```

But the actual replacement must be taken from the source text.

The LLM must NOT invent:

```text
old_text
new_text
effective_date
```

when they are absent.

---

# 71. VALIDATION AGAINST OFFICIAL CONSOLIDATED TEXT

Where possible:

```text
Reconstructed current Act
        VS
Official consolidated Act
```

Perform:

1. Section-by-section comparison
2. Subsection comparison
3. Clause comparison
4. Schedule comparison
5. Text hash comparison
6. Structural comparison

Generate a diff.

Example:

```text
Section 135
MATCH

Section 136
MATCH

Section 137
MISMATCH

Reason:
deterministic reconstruction differs from official consolidated text.
```

Do not silently resolve.

---

# 72. WHAT YOU MUST DELIVER

Your response must provide a complete implementation plan for this ingestion system.

Provide:

## A. Architecture

Explain the full ingestion architecture.

## B. Folder structure

Provide the final exact structure.

## C. Canonical JSON schema

Provide the exact JSON schema.

## D. Amendment schema

Provide the exact amendment representation.

## E. Version schema

Provide the temporal model.

## F. Provenance schema

Provide the provenance model.

## G. Passage schema

Provide the retrieval-ready passage model.

## H. Python implementation

Generate production-quality Python code for:

```text
PDF discovery
PDF validation
SHA-256 hashing
text extraction
OCR fallback
page mapping
normalization
section parsing
subsection parsing
clause parsing
schedule parsing
cross-reference detection
amendment parsing
version creation
validation
review queue
JSON export
JSONL export
logging
```

Do not create fake legal content.

The implementation must operate on the PDFs I provide.

## I. Configuration

Create a configuration file for:

```text
input directories
output directories
OCR thresholds
parser settings
logging
validation strictness
```

## J. CLI

Provide commands such as:

```bash
python ingest.py discover
python ingest.py extract
python ingest.py parse
python ingest.py amendments
python ingest.py validate
python ingest.py export
python ingest.py all
```

## K. Tests

Provide unit tests and integration tests.

## L. Validation report

Define the exact validation report structure.

## M. Human review workflow

Explain exactly how uncertain documents are reviewed.

---

# 73. DO NOT DO THESE THINGS

NEVER:

* manually invent missing legal text
* use general LLM knowledge as a source
* merge amendments by blindly appending text
* overwrite original PDFs
* discard historical provisions
* remove repealed provisions entirely
* assume enactment date equals effective date
* assume every numbering gap is an error
* trust OCR without validation
* allow the LLM to generate IDs
* allow the LLM to generate citations
* allow the LLM to generate authoritative metadata
* silently resolve source conflicts
* silently resolve consolidation mismatches
* treat synthetic data as authoritative
* fabricate confidence
* hide parser failures

---

# 74. SUCCESS CRITERIA

The Companies Act ingestion is considered successful ONLY if:

### Source integrity

Every source PDF is hashed and preserved.

### Extraction integrity

Every page is accounted for.

### Structural integrity

Sections, subsections, clauses, provisos, explanations and schedules are represented correctly.

### Temporal integrity

Historical and current versions are distinguishable.

### Amendment integrity

Amendments are represented as explicit transformations.

### Provenance integrity

Every legal passage can be traced to its source.

### Validation integrity

The reconstructed current version agrees with the authoritative consolidated version where available.

### Failure integrity

Uncertainty is surfaced rather than hidden.

### Reproducibility

The dataset can be regenerated deterministically.

---

# 75. FINAL ACCEPTANCE TEST

Before declaring success, perform this exact test:

Choose at least 10 provisions from the Companies Act.

For each provision:

1. Find it in the final JSON.
2. Find its section ID.
3. Find its passage ID.
4. Find its source document.
5. Find its source page.
6. Open the original PDF.
7. Confirm the text.
8. Check whether it has amendments.
9. Check effective dates.
10. Verify the current version.
11. Verify the hash.
12. Verify provenance.
13. Verify the passage is suitable for retrieval.

Then intentionally test at least:

* one amended section
* one substituted subsection
* one omitted provision
* one cross-reference
* one schedule
* one multi-page section
* one OCR/problematic page
* one historical version
* one delayed commencement
* one consolidation mismatch

The system must correctly flag failures instead of guessing.

---

# 76. MOST IMPORTANT DESIGN PRINCIPLE

The final architecture must follow:

```text
SOURCE
  ↓
EXTRACT
  ↓
NORMALIZE
  ↓
STRUCTURE
  ↓
VERSION
  ↓
VALIDATE
  ↓
PROVENANCE
  ↓
EXPORT
```

NOT:

```text
PDF
 ↓
LLM
 ↓
"Trust me, this is the Act"
```

The goal is to build a legal corpus that a hostile legal expert can audit.

For every provision, the system should be able to answer:

> “Show me exactly where this came from.”

For every amendment:

> “Show me exactly what changed, when, and by which legal instrument.”

For every current provision:

> “Show me the chain from the original provision through every applicable amendment to the current text.”

For every uncertainty:

> “Show me why the system refused to make a decision.”

That is the standard for Dataset 1.

Do not optimize for producing a large JSON file.

Optimize for producing a **smallest possible amount of authoritative, verifiable, reproducible, legally traceable data with zero silently fabricated information.**
