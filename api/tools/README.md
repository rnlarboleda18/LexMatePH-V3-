# api/tools/

Maintenance, diagnostic, and migration scripts for the LexMatePH API backend.

These scripts are **not** deployed as Azure Functions. They are run manually by developers for data ingestion, inspection, and one-off fixes.

## Running scripts

Run from the `api/` directory so imports resolve correctly:

```powershell
cd api
python tools/run_migration.py
# or
python tools/check_admin.py
```

Set `DB_CONNECTION_STRING` in your environment or ensure `local.settings.json` is present (see `api/local.settings.sample.json`).

## Required env vars (for most scripts)

- `DB_CONNECTION_STRING` — cloud PostgreSQL connection string
- `REDIS_URL` — optional, for cache-related scripts
- `OPENAI_API_KEY` / `GEMINI_API_KEY` / `GOOGLE_API_KEY` — for AI classification scripts

---

## Script index

### Data ingestion

| Script | Purpose |
|--------|---------|
| `run_migration.py` | Run SQL schema migration against cloud DB |
| `run_billing_migrations.py` | Run billing-related schema migrations |
| `ingest_questions.py` | Ingest bar exam questions into DB |
| `ingest_roc.py` / `ingest_roc_cloud.py` / `ingest_roc_combined.py` | Ingest Rules of Court data |
| `clerk_migration.py` | Migrate legacy users to Clerk-linked rows |
| `migrate_playlists.py` | Playlist schema migration |
| `create_roc_table.py` | Create RoC table structure |
| `rename_cloud_columns.py` | Column rename migration |

### Inspection / verification

| Script | Purpose |
|--------|---------|
| `check_admin.py` | Verify admin user rows |
| `check_all_counts.py` | Count rows across tables |
| `check_cloud_count.py` | Count cloud DB rows |
| `check_codal_links.py` | Verify codal cross-links |
| `check_count_after.py` / `check_count_filtered.py` | Post-migration row counts |
| `check_deleted_concepts.py` / `check_filtered_concepts.py` | Flashcard concept audit |
| `check_one_concept.py` | Debug a single concept row |
| `check_overlap.py` | Find duplicate/overlapping rows |
| `check_progress.py` | Migration progress check |
| `check_roc_years.py` / `_alt` / `_local` | RoC year range checks |
| `inspect_db_state.py` | General DB state dump |
| `inspect_mcq.py` | MCQ question inspection |
| `inspect_roc_detail.py` / `inspect_roc_rules.py` / `_v2` | RoC content inspection |
| `inspect_row_3.py` / `inspect_rpc_schema.py` / `inspect_section_7.py` / `inspect_tables.py` | Targeted DB inspection |
| `final_check.py` / `final_user_check.py` | Post-migration QA checks |
| `verify_filter.py` | Verify filter logic against DB |
| `unique_concepts.py` | List unique concept categories |
| `count_questions.py` / `count_with_concepts.py` | Row count helpers |
| `debug_codex_roc.py` | Debug codex RoC content |

### AI / classification

| Script | Purpose |
|--------|---------|
| `classify_subtopics.py` / `classify_subtopics_parallel.py` | AI subtopic labeling |
| `ai_fix_typos.py` / `_chunked` / `_v2` | AI-assisted typo correction |
| `list_models.py` / `list_models_unfiltered.py` | List available AI models |
| `dump_models.py` | Dump model info |

### Data fixes / maintenance

| Script | Purpose |
|--------|---------|
| `clean_roc_criminal.py` | Clean criminal-law RoC data |
| `fix_ligatures.py` | Fix text ligature encoding issues |
| `manual_fix_admins.py` | Manually fix admin flags |
| `polish_fixes.py` | Final polish on codal content |
| `precache_rpc.py` | Pre-warm RPC audio cache |
| `print_all_pdf.py` | Debug PDF content dump |
| `get_sample_subtopic.py` | Sample a subtopic from DB |
| `dump_pdf_text.py` | Dump PDF text for inspection |
| `find_exact_article_2_sec_1.py` | Locate specific article row |

### Test / endpoint checks

| Script | Purpose |
|--------|---------|
| `test_audio_bug.py` | Reproduce audio bug scenario |
| `test_audio_endpoint.py` / `_sec1` / `_standalone` / `_section_1` / `_section_7` | Audio API endpoint tests |
| `test_audio_headers.py` | Check audio response headers |
| `test_db.py` | DB connectivity check |
| `test_endpoint.py` | Generic endpoint test |
| `test_extract_pdf.py` | PDF extraction test |
| `test_provided_key.py` / `test_root_key.py` | Auth key tests |
| `test_real_view_functions.py` | View function integration tests |
| `test_remote_db.py` | Remote DB connectivity test |
| `test_roman_conversion.py` / `test_split_behaviour.py` / `test_state_parser.py` | Unit tests for helpers |
