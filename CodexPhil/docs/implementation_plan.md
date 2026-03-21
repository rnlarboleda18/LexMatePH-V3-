# Codex Philippine Phase Implementation Plan

The goal is to establish the temporal legal database for the Revised Penal Code (RPC) and apply its first 5 historical amendments.

## User Review Required
No major breaking changes expected, but this will reset/repopulate the `legal_codes` and `article_versions` tables.

## Completed Changes


### Database Setup
#### [EXECUTE] [scripts/apply_codex_schema.py](file:///c:/Users/rnlar/.gemini/antigravity/scratch/bar_project_v2/scripts/apply_codex_schema.py)
- Runs `scripts/codex_init.sql` to ensure tables exist (`legal_codes`, `article_versions`, `jurisprudence_links`) with UUIDs and temporal columns.

### Base Ingestion
#### [EXECUTE] [scripts/ingest_codex_md.py](file:///c:/Users/rnlar/.gemini/antigravity/scratch/bar_project_v2/scripts/ingest_codex_md.py)
- Ingests `data/CodexPhil/Codals/md/RPC.md` as the base version (valid_from 1932-01-01).

### Amendment Application
#### [EXECUTE] [data/CodexPhil/scripts/process_amendment.py](file:///c:/Users/rnlar/.gemini/antigravity/scratch/bar_project_v2/data/CodexPhil/scripts/process_amendment.py)
(or `apply_amendment.py` depending on the script logic found)
- Will process the following markdown files in chronological order:
    5. `ra_18_1946.md`

### Refine Amendment Formatting & Markers
#### [MODIFY] [data/CodexPhil/scripts/apply_amendment.py](file:///c:/Users/rnlar/.gemini/antigravity/scratch/bar_project_v2/data/CodexPhil/scripts/apply_amendment.py)
- Updated AI prompt to enforce strict formatting:
    - No markdown headers (###) on article numbers
    - No brackets around "Article X."
    - Uniform bold/white text styling
- Ensured `amendment_id` is propagated correctly to trigger visual markers in frontend.

#### [EXECUTE] [data/CodexPhil/scripts/process_amendment.py](file:///c:/Users/rnlar/.gemini/antigravity/scratch/bar_project_v2/data/CodexPhil/scripts/process_amendment.py)
- Re-processed historical amendments with new logic to standardize database content:
    - Act No. 3999 (Art 329)
    - CA 99 (Art 80)
    - CA 235 (Art 195)
    - RA 12 (Arts 146, 295, 296, 306)
    - RA 18 (Arts 62, 267, 268, 271, 299)

## Verification Plan

### Automated Verification
- **Table Check**: Verify table counts in `legal_codes` and `article_versions` using a SQL query script.
- **Specific Article Check**: Verify Article 1 or other amended articles have multiple versions with correct `valid_from` and `valid_to` dates.
- **Run `scripts/verify_amendment.py`** if available to check data integrity.
