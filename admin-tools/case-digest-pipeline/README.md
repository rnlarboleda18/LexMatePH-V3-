# Case digest pipeline

End-to-end view of how **Supreme Court case digests** in LexMatePH are produced: from raw sources through **markdown** in **`sc_decided_cases.full_text_md`**, then **AI digest fields** on the same table.

---

## 1. Data model (where everything lands)

Primary table: **`sc_decided_cases`**

| Stage | Important columns |
|--------|-------------------|
| After ingestion | `full_text_md`, `sc_url`, `scrape_source`, `case_number`, `title` / `short_title`, `date`, `ponente`, … |
| After digest AI | `digest_facts`, `digest_issues`, `digest_ruling`, `digest_ratio`, `digest_significance`, `main_doctrine`, `keywords`, `legal_concepts`, `flashcards`, `spoken_script`, `ai_model`, … |

The app **Case Digest** UI reads from this table (via API blueprints such as `api/blueprints/supreme.py`).

---

## 2. Pipeline stages (conceptual)

```
Sources (Lawphil / SC E-Library / batch HTML)
        → scrape or export HTML
        → convert HTML → Markdown (.md)
        → ingest MD (+ metadata) → Postgres (sc_decided_cases.full_text_md)
        → digest AI (Gemini) reads full_text_md → UPDATE digest_* columns
```

Steps **do not** have to all run on one machine; paths in older scripts often point at a local `bar_project_v2\data\...` tree—**normalize `DATA_DIR` / env vars** for your workstation.

---

## 3. Path A — SC E-Library (common for “official shelf” IDs)

| Step | What happens | Code in this repo |
|------|----------------|-------------------|
| **Scrape** | Download decision HTML from `elibrary.judiciary.gov.ph/.../showdocs/1/{id}` | [`scraper/elib_scraper.py`](../../scraper/elib_scraper.py), [`scraper/elib_scraper_sync.py`](../../scraper/elib_scraper_sync.py) |
| **Convert → MD** | E-Library HTML → clean MD (strips site chrome, starts at EN BANC / division / case header) | [`scraper/elib_html_to_markdown.py`](../../scraper/elib_html_to_markdown.py) (core), [`scripts/sc_elib_converter.py`](../../scripts/sc_elib_converter.py) (batch dir + footnote renumbering); Lawphil: [`scraper/lawphil_converter_v2.py`](../../scraper/lawphil_converter_v2.py), etc. |
| **Ingest MD → DB** | Upsert `full_text_md`, URL, source; later jobs fill `case_number` / title via merges | [`scripts/ingest_sc_elib.py`](../../scripts/ingest_sc_elib.py) (paths + dedupe), [`scripts/ingest_unique_sc_elib.py`](../../scripts/ingest_unique_sc_elib.py) (insert raw MD + `scrape_source`), [`scripts/merge_unmatched_optimized.py`](../../scripts/merge_unmatched_optimized.py), [`scripts/patch_fill_missing.py`](../../scripts/patch_fill_missing.py) |

**Ingest pattern (example):** `ingest_unique_sc_elib.py` inserts `full_text_md` and `sc_url` built from the E-Lib doc id, with `scrape_source` like `E-Library Scraper`.

---

## 4. Path B — Lawphil (alternate / historical corpus)

| Step | What happens | Code in this repo |
|------|----------------|-------------------|
| **Scrape** | Crawl Lawphil year indexes, download HTML | [`scraper/lawphil_scraper.py`](../../scraper/lawphil_scraper.py), [`scraper/download_decisions.py`](../../scraper/download_decisions.py) |
| **Convert → MD** | Lawphil table unwrap, footnotes, `markdownify` | [`scraper/lawphil_convert_html_to_markdown.py`](../../scraper/lawphil_convert_html_to_markdown.py), [`scraper/lawphil_converter_html_to_md.py`](../../scraper/lawphil_converter_html_to_md.py) |
| **Ingest** | MD dir → Postgres (various batch / dedupe scripts) | e.g. [`scripts/ingest_md_files.py`](../../scripts/ingest_md_files.py), [`scripts/ingest_batch_results.py`](../../scripts/ingest_batch_results.py) |

---

## 5. Path C — “Auto” demo pipeline (Lawphil, self-contained folder)

Folder: [`auto_case_scrape_convert_ingest_digest/`](../../auto_case_scrape_convert_ingest_digest/)

| Script | Role |
|--------|------|
| [`run_pipeline.py`](../../auto_case_scrape_convert_ingest_digest/run_pipeline.py) | Orchestrates scrape → convert → [`ingester.py`](../../auto_case_scrape_convert_ingest_digest/ingester.py) → digest step |
| [`crawler.py`](../../auto_case_scrape_convert_ingest_digest/crawler.py) | Target list → Lawphil HTML on disk |
| [`converter.py`](../../auto_case_scrape_convert_ingest_digest/converter.py) | HTML → MD |
| [`ingester.py`](../../auto_case_scrape_convert_ingest_digest/ingester.py) | Reads `.md`, parses header, **UPSERT** `sc_decided_cases` (`full_text_md`, titles, dates) |
| [`digester.py`](../../auto_case_scrape_convert_ingest_digest/digester.py) | Calls Gemini on `full_text_md` (⚠️ **legacy file: may contain hardcoded DB URL—do not copy; use env + `generate_sc_digests_gemini.py` instead**) |

`run_pipeline.py` still references an external `bar_project_v2\data\...` layout; treat as a **template** and align paths with your machine.

---

## 6. Digest generation (AI on rows that already have `full_text_md`)

| Role | Script | Notes |
|------|--------|--------|
| **Main fleet / workers** | [`scripts/generate_sc_digests_gemini.py`](../../scripts/generate_sc_digests_gemini.py) | Claims rows (`digest_significance = 'PROCESSING'`), calls **Google GenAI**, writes digest JSON back to `sc_decided_cases`. Many CLI flags (date range, `smart_backfill`, `force`, etc.). |
| **Import pre-batched JSONL** | [`scripts/ingest_batch_results.py`](../../scripts/ingest_batch_results.py) | Maps AI keys → DB columns (`transform_digest_data` + `save_digest_result`). |

**Env:** `DB_CONNECTION_STRING` (cloud Postgres), `GOOGLE_API_KEY` / Gemini client env as used in the script—see script headers (never commit real keys).

---

## 7. Related maintenance / quality scripts (non-linear)

These support the same corpus but are not a strict linear pipeline:

- [`scripts/generate_priority_fleet.py`](../../scripts/generate_priority_fleet.py), [`scripts/force_unlock_processing.py`](../../scripts/force_unlock_processing.py) — queue / stuck `PROCESSING`
- [`scripts/ai_date_extraction.py`](../../scripts/ai_date_extraction.py), [`scraper/verify_dates_with_gemini.py`](../../scraper/verify_dates_with_gemini.py) — dates vs sources
- [`scripts/backfill_statutes.py`](../../scripts/backfill_statutes.py) — statutes from `full_text_md`
- [`scripts/analyze_case_number_patterns.py`](../../scripts/analyze_case_number_patterns.py) — DB hygiene / reporting

---

## 8. Suggested operator order (today’s production-style flow)

1. **Scrape / convert** using the path you actually maintain (E-Lib vs Lawphil).
2. **Ingest** MD so every decision has **`full_text_md`** (+ `sc_url` / `scrape_source` as applicable).
3. **Merge / patch** metadata (`case_number`, `date`, `short_title`) until rows are searchable.
4. **Run** `generate_sc_digests_gemini.py` (or batch export → `ingest_batch_results.py`) to fill **digest** columns.

---

## 9. Security reminder

- Use **`DB_CONNECTION_STRING`** (and API keys) only from **gitignored** `local.settings.json` / `.env`—see repo rules.
- Do **not** duplicate connection strings into new tools; **reference env vars** only.

## 10. Automated E-Library pipeline (unified: ingest + digest)

One script runs the **full** flow for each **new** document: fetch HTML → Markdown on disk → `INSERT` into `sc_decided_cases` → **Gemini digest** via [`scripts/generate_sc_digests_gemini.py`](../../scripts/generate_sc_digests_gemini.py) (default model **`gemini-2.5-flash`**). There are no “convert only” or “skip digest” modes on this entrypoint.

**Scan mode:** probes ascending `showdocs/1/{id}` after the highest E-Lib id already in the DB; skips blank/error pages (e.g. [missing doc](https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/70042)); stops after consecutive misses.

**Environment:** `DB_CONNECTION_STRING` (always). `GOOGLE_API_KEY` whenever at least one new row is ingested.

| Piece | Location |
|--------|----------|
| Pipeline CLI | [`scripts/elib_digest_pipeline.py`](../../scripts/elib_digest_pipeline.py) |
| **Converted Markdown (default)** | This folder: [`md/`](./md/) (`{elib_id}.md`). Override with `--md-dir`. HTML defaults to [`html/`](./html/) (`{elib_id}.html`). Override with `--html-dir`. |
| Double-click | Repo root [`run-elib-pipeline.cmd`](../../run-elib-pipeline.cmd) or [`Shortcuts.cmd`](../../Shortcuts.cmd) |
| PowerShell | [`run-elib-pipeline.ps1`](./run-elib-pipeline.ps1) |
| Monthly index (optional discovery) | [`scraper/scrape_metadata.py`](../../scraper/scrape_metadata.py) — e.g. [Sep 2025 decisions](https://elibrary.judiciary.gov.ph/thebookshelf/docmonth/Sep/2025/1) |

**Examples:**

```bash
python scripts/elib_digest_pipeline.py
python scripts/elib_digest_pipeline.py --ids 70193
python scripts/elib_digest_pipeline.py --ids 70193,70194 --digest-model gemini-2.5-flash
```

**Finish digests** after a failed or partial digest run (clears stale `PROCESSING`, selects rows whose digest matches the same **holes** as Gemini `--smart-backfill`, then runs `--force --smart-backfill` in chunks): [`scripts/finish_elib_pipeline_digests.py`](../../scripts/finish_elib_pipeline_digests.py). Examples: `python scripts/finish_elib_pipeline_digests.py --dry-run`, `--export-ids path/to/ids.txt`, `--all-sources`, or `--max-passes 3` to re-query pending after each sweep until empty or the cap.
