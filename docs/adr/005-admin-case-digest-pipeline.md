# ADR 005: Admin-triggered case digest pipeline (local subprocess)

**Status:** Accepted  
**Date:** 2026

## Context

Operators need to **scan**, **ingest**, **digest**, and **link** new Supreme Court E-Library decisions into the cloud database. This work is driven from **Admin → Digest Pipeline** during **local development** (Azure Functions host + Vite), not as a separate batch service.

## Decision

1. **Process model:** The admin API (`api/blueprints/admin.py`) starts a **`subprocess.Popen`** that runs repo scripts with **`sys.executable`** (the same Python as the Functions worker). That keeps one virtual environment and one dependency set (`api/requirements.txt`) for both HTTP handlers and pipeline children.

2. **Script location:** Locally, the repo root is resolved so `scripts/elib_digest_pipeline.py` (and related scripts) run against the real tree. Deployed bundles may only ship `api/`; pipeline buttons are expected for **workstation + cloud DB**, not for running full scrapes inside the tiny Azure Functions package unless explicitly bundled.

3. **Progress for the UI:** The pipeline writes **`admin-tools/case-digest-pipeline/pipeline_progress.json`** (via `scripts/digest_pipeline_progress.py`) so **`GET /api/ops/pipeline/status`** can return per-case stages without polling the DB.

4. **Frontend API base:** Admin tabs use **`src/frontend/src/utils/adminApi.js`** (`adminApiUrl` built from `VITE_API_BASE_URL` / same-origin `/api`) so **HTTPS Vite** and **direct Functions** hosts both work.

5. **Atomic progress file on Windows:** Progress updates use **temp file + replace** with **retries** on access denied (short file locks from editors or AV).

## Consequences

- **Positive:** One place to install Python deps for admin + pipeline (`pip install -r api/requirements.txt` in the venv used for `func start`).
- **Positive:** Clear subprocess log and progress JSON for operators when a run fails.
- **Negative:** After changing blueprints or dependencies, operators must **restart `func start`**; a stale host can answer `/api/ping` but return **404** on `/api/ops/*`.
- **Negative:** `created_at` on `sc_decided_cases` is **`timestamp without time zone`** (UTC wall time from `NOW()`); “today” reports must use an explicit zone—see `scripts/list_cases_added_today.py`.

## Related

- `scripts/README.md` — script index for pipeline maintenance.
- `api/local.settings.sample.json` — `DB_CONNECTION_STRING`, Vertex/Gemini/XAI keys for digests.
