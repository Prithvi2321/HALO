# HALO Dataset 2: Source Authority & Snapshot Policy

**Objective**: Ensure the legal source layer preserves strict evidentiary provenance, adheres to licensing terms, and guarantees total reproducibility of the judicial corpus.

---

## 1. Source Authority Hierarchy

HALO establishes an explicit 3-tier hierarchy of source authority:

```text
┌───────────────────────────────────────────────┐
│ TIER 1: OFFICIAL COURT REPOSITORY (Preferred) │
│ - Supreme Court Reports (SCR) Digital Archive │
│ - Official eCourts Judgment Portal            │
│ - Official NCLAT / Tribunal Gazette Orders    │
└───────────────────────┬───────────────────────┘
                        │ if unavailable
                        ▼
┌───────────────────────────────────────────────┐
│ TIER 2: TRUSTED OPEN LEGAL REPOSITORIES       │
│ - Registry of Open Data on AWS (CC-BY-4.0)    │
│ - Open Justice India Archives                 │
│ - Public Court API Mirrors                    │
└───────────────────────┬───────────────────────┘
                        │ if unavailable
                        ▼
┌───────────────────────────────────────────────┐
│ TIER 3: TERTIARY MIRRORS / AGGREGATORS        │
│ - Permissible only for metadata verification  │
│ - Never used as primary document source       │
└───────────────────────────────────────────────┘
```

### Ingestion Rule
- Always attempt Tier 1 first.
- If Tier 1 is inaccessible or lacks digital format, fallback to Tier 2 with explicit provenance note.
- Never ingest from Tier 3 or unverified sources. If no Tier 1 or Tier 2 source exists, the document is rejected (`REJECTED_UNVERIFIED_SOURCE`).

---

## 2. Source Snapshot Preservation

Because external online repositories and endpoints evolve over time, every acquired document in Dataset 2 must preserve a permanent **Source Snapshot** in its provenance record:

```json
{
  "source_snapshot": {
    "source_id": "SRC_SC_OPEN_DATA",
    "source_authority": "OFFICIAL",
    "source_url": "https://indian-supreme-court-judgments.s3.amazonaws.com/data/pdf/year=2020/english/2020_10_1132_1150_EN.pdf",
    "retrieval_timestamp": "2026-09-06T17:15:00Z",
    "http_metadata": {
      "status_code": 200,
      "etag": "\"de8bae9cf5a81a79021ed48510280cce\"",
      "content_length": 580776,
      "content_type": "application/pdf"
    },
    "file_size": 580776,
    "sha256": "de8bae9cf5a81a79021ed48510280cce...",
    "license": "CC-BY-4.0"
  }
}
```

---

## 3. Licensing & Attribution Compliance

1. **Public Domain & Creative Commons**: All primary judicial decisions from Indian courts are public documents under Indian law. Source mirrors licensed under Creative Commons (e.g. CC-BY-4.0 on AWS Open Data) are fully attributed with source URI, creator credits, and license declaration.
2. **Exclusion of Proprietary Content**: No copyrighted headnotes, editorial syllabi, or proprietary case summaries from commercial legal publishers (e.g. SCC, Manupatra) are scraped or incorporated. Only the original judicial text and public court metadata are ingested.
