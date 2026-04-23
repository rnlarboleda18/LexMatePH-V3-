# Amendment ingestion pipeline (LexCode)

This document **prepares** the amendment ingestion workflow for Codex/RPC (and related tooling). It lists prerequisites, entry points, and the **recommended dry-run order**. **No commands below are executed as part of authoring this doc**—run them locally when you are ready.

---

## 1. Choose a track

| Track | When to use | Primary scripts |
|--------|-------------|-------------------|
| **A. Markdown + AI merge** | New RA/PD/etc. as markdown under `LexCode/Codals/md/`; text merged with Gemini/Vertex per article. | **One file:** `LexCode/scripts/process_amendment.py --file …`. **Batch (full-AI extract):** `LexCode/scripts/ai_amendment_pipeline.py` → `process_amendment_full_ai.py` → `apply_amendment.py` |
| **B. Manual JSON (literal)** | Structural or hand-curated text; **no** generative rewrite of statute body. | `LexCode/scripts/process_amendment.py --amendment-json …` + specs under `LexCode/Codals/manual_amendments/specs/` |
| **C. Full RPC manual re-ingest** | Rebuild baseline from `RPC.md` then replay **all** manifest steps in order. | `scripts/reingest_rpc_manual_pipeline.py` |

Indirect / cross-law notes (separate tooling): `LexCode/scripts/ingest_indirect_amendments.py` (metadata + effects; review before use).

---

## 2. Prerequisites (all tracks)

1. **Repository root**  
   All paths below assume the repo root is `LexMatePH v3` (parent of `LexCode/` and `scripts/`).

2. **Python**  
   Same interpreter you use for `api/` (Python 3.11+ recommended). Install LexCode script dependencies if prompted when you first run a script.

3. **PostgreSQL connection**  
   - Prefer **`DB_CONNECTION_STRING`** in the environment (cloud DB per project policy).  
   - Else `api/local.settings.json` → `Values.DB_CONNECTION_STRING` (see `api/local.settings.sample.json`).  
   `LexCode/scripts/process_amendment.py` reads connection the same way as other LexCode DB tools.

4. **Track A only — Vertex / Gemini (AI merge)**  
   Per `LexCode/scripts/lexcode_genai_client.py`:  
   - `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`  
   - ADC: `GOOGLE_APPLICATION_CREDENTIALS` or `gcloud auth application-default login`  
   Optional: `GEMINI_AMENDMENT_MODEL`  
   **Track B/C** do not require Vertex for the amendment apply step itself (literal writes).

5. **Optional: RPC implied manifest**  
   `scripts/reingest_rpc_manual_pipeline.py` phase 3 writes `LexCode/Codals/generated/rpc_implied_sources_manifest.json` (skipped on `--dry-run`).

---

## 3. Authoring inputs

### Markdown (Track A)

1. Source HTML (optional): `LexCode/Codals/doc/`  
2. Converted markdown: `LexCode/Codals/md/<law>_<year>.md`  
3. Header style: see `.agent/workflows/add_codex_amendment.md` (Lawphil / ChanRobles workflow).

### Manual spec (Track B)

1. **Manifest**: `LexCode/Codals/manual_amendments/manifest.json` — ordered `steps` with `id` + `spec` path.  
2. **Spec JSON**: `LexCode/Codals/manual_amendments/specs/*.json` — schema via `LexCode/scripts/manual_amendment_spec.py`.  
3. Regenerate helpers: `LexCode/scripts/build_baseline_manual_specs.py` (when applicable).

---

## 4. Recommended command order (dry-run first)

### Single markdown file (Track A)

```powershell
# From repo root — validates / previews; no DB writes
python LexCode/scripts/process_amendment.py --file LexCode/Codals/md/ra_7659_1993.md --dry-run

# Live apply (only when dry-run is clean)
python LexCode/scripts/process_amendment.py --file LexCode/Codals/md/ra_7659_1993.md
```

Useful flags (see `process_amendment.py --help`): `--code RPC`, `--force`, `--only-article NUM`, `--offline-ra6968`, `--offline-ra10951-rpc`.

### Batch full-AI RPC laws (Track A, chronological queue)

`LexCode/scripts/ai_amendment_pipeline.py` runs a fixed ordered list of amendatory markdown files through **`process_amendment_full_ai`** (AI parses the whole statute into JSON, then merges each article). After a **successful live** run with no per-file failures, it rebuilds **`structural_map`** for every `rpc_codal` row that has a non-empty **`amendments`** array.

```powershell
python LexCode/scripts/ai_amendment_pipeline.py --dry-run
python LexCode/scripts/ai_amendment_pipeline.py --only ra_10951 --dry-run
python LexCode/scripts/ai_amendment_pipeline.py
```

Flags: `--start-from N` (0-based index into the built-in file list), `--only SUBSTR`, `--dry-run`.

### Single manual JSON (Track B)

```powershell
python LexCode/scripts/process_amendment.py --amendment-json LexCode/Codals/manual_amendments/specs/ra_6968.json --code RPC --dry-run
python LexCode/scripts/process_amendment.py --amendment-json LexCode/Codals/manual_amendments/specs/ra_6968.json --code RPC
```

### Full manual RPC pipeline (Track C)

```powershell
# Prints subprocesses; no DB writes, no manifest file write
python scripts/reingest_rpc_manual_pipeline.py --dry-run

# Phase 1 only + implied manifest (still use --dry-run to preview)
python scripts/reingest_rpc_manual_pipeline.py --dry-run --only-base

# Live full run (only when ready)
python scripts/reingest_rpc_manual_pipeline.py
```

Other orchestrator flags: `--skip-amendments`, `--from-step N`, `--only-id <manifest id>`, `--pause`, `--continue-on-errors`, `--wipe-rpc-links`, `--manifest <path>`.

---

## 5. After a live run (verification)

1. **DB**: `article_versions` for affected `code_id` / `article_number` — new row `valid_to IS NULL`, prior row `valid_to` set to amendment date.  
2. **UI**: Codex viewer shows amended text and amendment rail where wired.  
3. **Ad hoc**: project may have scratch SQL or `LexCode/scripts/verify_amendment.py`-style checks—align with your environment (avoid hardcoded localhost in committed tools).

---

## 6. Related files (quick index)

| Purpose | Path |
|---------|------|
| Orchestrator (manual RPC) | `scripts/reingest_rpc_manual_pipeline.py` |
| RPC baseline from `RPC.md` (phase 1 of full re-ingest) | `LexCode/scripts/ingest_rpc_base_from_md.py` |
| Main processor CLI | `LexCode/scripts/process_amendment.py` |
| Batch full-AI RPC driver | `LexCode/scripts/ai_amendment_pipeline.py` |
| Full-AI single-file processor | `LexCode/scripts/process_amendment_full_ai.py` |
| AI apply / descriptions | `LexCode/scripts/apply_amendment.py` |
| Parse markdown → change list | `LexCode/scripts/parse_amendment.py` |
| Manual spec loader | `LexCode/scripts/manual_amendment_spec.py` |
| Large / batch maintenance | `LexCode/maintenance/batch_process_amendments.py`, `LexCode/scripts/process_large_amendment.py` |
| Agent workflow (fetch → md → process) | `.agent/workflows/add_codex_amendment.md` |

---

## 7. Checklist before first **live** execution

- [ ] `DB_CONNECTION_STRING` (or `api/local.settings.json`) points at the **intended** database.  
- [ ] For Track A: Vertex env + ADC verified (`lexcode_genai_client` requirements).  
- [ ] Markdown or JSON reviewed for the correct law id and article numbers.  
- [ ] `--dry-run` completed successfully for the same arguments you plan for live.  
- [ ] Backup / snapshot policy agreed for production (outside this repo).  
- [ ] Stakeholders notified if reingest touches many articles (`reingest_rpc_manual_pipeline.py`).

When this checklist is satisfied, run the same commands **without** `--dry-run` (and without `reingest_rpc_manual_pipeline.py --dry-run`).
