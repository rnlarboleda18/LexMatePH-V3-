# Comprehensive Documentation Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring all LexMatePH v3 docs to accurate, contributor-ready state — rewrite README, fix stale references across 5 existing docs, add 5 new reference files, and create a master navigation index.

**Architecture:** Pure documentation — no code changes. Each task produces one file (write or update), verified against source, then committed. Tasks are independent and can be done in any order after Task 1.

**Tech Stack:** Markdown, verified against `api/config.py`, `api/function_app.py`, and blueprint source files.

---

## File Map

| Action | File | Notes |
|--------|------|-------|
| Rewrite | `README.md` | Wrong product name + v1 architecture |
| Update | `CONTRIBUTING.md` | React 18→19, PayMongo→Xendit, add BAR 2026 |
| Update | `docs/USER_GUIDE.md` | Add BAR 2026 Reviewer + annotation canvas |
| Update | `docs/RUNBOOK.md` | Section 4: PayMongo→Xendit |
| Update | `docs/lexplay/README.md` | Remove resolved "🔴 Current Blocker" section |
| Update | `docs/adr/004-paymongo-for-payments.md` | Mark superseded |
| Create | `docs/adr/006-xendit-for-payments.md` | Xendit ADR |
| Create | `docs/ENV_VARS.md` | All env vars from `api/config.py` |
| Create | `docs/API_ROUTES.md` | Full route map from blueprints |
| Create | `docs/features/bar2026-reviewer.md` | BAR 2026 + annotation canvas feature doc |
| Create | `docs/INDEX.md` | Master navigation by reader role |

---

## Task 1: Rewrite README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace README.md with current-state content**

Replace the entire file with:

```markdown
# LexMatePH

AI-powered Philippine legal research and bar review platform. Search statutes, browse Supreme Court jurisprudence, study with flashcards and mock exams, and listen to legal text as audio — all in one place.

## Features

| Feature | Description |
|---------|-------------|
| **LexCode** | Read codals and statutes (RPC, Civil Code, Rules of Court, Constitution, Labor Code) in a distraction-free reader with AI-linked case references |
| **SC Decisions** | Browse and search Supreme Court case digests; AI-generated doctrine summaries |
| **Bar Questions** | Past Philippine Bar exam questions with suggested answers, filterable by subject |
| **Flashcards** | Study decks built from key legal concepts drawn from SC digests, aligned to BAR 2026 subjects |
| **Lexify** | Timed mock Bar exam simulator with AI grading |
| **LexPlay** | Text-to-speech audio of codal provisions and case digests; offline caching, playlist support |
| **BAR 2026 Reviewer** | Syllabus-aligned topic browser with linked SC cases and S Pen page annotation |

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Next.js 16, TypeScript, Tailwind CSS 4 |
| Backend API | Python (Flask blueprints), Azure Functions v2 |
| Database | PostgreSQL (Azure Flexible Server) |
| Cache | Azure Cache for Redis |
| AI Engine | Google Gemini API (Vertex AI) — legal linking, digest generation, grading |
| Auth | Clerk |
| Payments | Xendit (PHP subscriptions — GCash, Maya, cards) |
| Hosting | Azure Static Web Apps (SWA-managed Functions in `api/`) |
| Dev tooling | swa-cli (local SWA emulation), Azure Functions Core Tools |

## Quick start

### Prerequisites

- Node.js LTS
- Python 3.10+
- Azure Functions Core Tools (`npm install -g azure-functions-core-tools@4`)

### Setup

```powershell
git clone <repo>
cd "LexMatePH v3"

# Backend
cd api
python -m venv .venv
.venv\Scripts\Activate
pip install -r requirements.txt
cp local.settings.sample.json local.settings.json
# Edit local.settings.json — add DB_CONNECTION_STRING (cloud Postgres) and VITE_CLERK_PUBLISHABLE_KEY

# Frontend
cd ..\src\frontend
npm install
cp .env.example .env.local
# Edit .env.local — add VITE_CLERK_PUBLISHABLE_KEY
```

### Run

```powershell
# From repo root — starts API (port 7071) + Vite (port 5173)
./start_all.ps1
```

Open: http://localhost:5173

## Documentation

| Document | Audience |
|----------|---------|
| [CONTRIBUTING.md](CONTRIBUTING.md) | New contributors — setup, conventions, PR flow |
| [docs/INDEX.md](docs/INDEX.md) | Navigation index by reader role |
| [docs/ENV_VARS.md](docs/ENV_VARS.md) | All environment variables reference |
| [docs/API_ROUTES.md](docs/API_ROUTES.md) | Full API route map |
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | Production incident playbook |
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | End-user feature guide |

## Subscription

Single plan: **Amicus** at PHP 299/month. Payments via Xendit (GCash, Maya, cards). Free tier available with usage limits.

## Disclaimer

Study tools are for educational purposes only. Not legal advice. Not affiliated with the Supreme Court of the Philippines or the Office of the Bar Confidant.
```

- [ ] **Step 2: Verify**

```powershell
# Confirm file saved correctly and has correct product name
Select-String "LexMatePH" README.md
Select-String "Codex Philippines" README.md  # should return nothing
```

Expected: `LexMatePH` matches appear; `Codex Philippines` returns nothing.

- [ ] **Step 3: Commit**

```powershell
git add README.md
git commit -m "docs: rewrite README — correct product name, current stack, all features"
```

---

## Task 2: Update CONTRIBUTING.md

**Files:**
- Modify: `CONTRIBUTING.md`

- [ ] **Step 1: Fix stack table — React version and payment processor**

Find this line in the stack table:
```
| Frontend SPA + PWA | React 18, Vite, Tailwind | `src/frontend/` |
```
Replace with:
```
| Frontend SPA + PWA | React 19, Vite, Tailwind CSS 4 | `src/frontend/` |
```

Find this line:
```
| Payments | PayMongo | `PAYMONGO_*` env vars |
```
Replace with:
```
| Payments | Xendit | `XENDIT_*` env vars |
```

- [ ] **Step 2: Add BAR 2026 pipeline subsection**

After the "Admin case digest pipeline (local)" section, add:

```markdown
---

## BAR 2026 Reviewer pipeline

The BAR 2026 Reviewer content (subjects, topics, linked SC cases) is built by:

1. **eLib scraper** — `scripts/elib_digest_pipeline.py` ingests SC decisions into `sc_decided_cases`.
2. **Case linker** — `api/brain/` runs Gemini-based semantic linking between codal provisions and cases.
3. **Syllabus alignment** — `LexCode/pipelines/` scripts map topics to BAR 2026 TOS subjects.

Run from **Admin → Digest Pipeline** (local `func start` + cloud DB). See `docs/features/bar2026-reviewer.md` for architecture details.

**Annotation canvas** — S Pen / stylus page annotations are stored per-page in `sc_annotation_strokes` (PostgreSQL). The canvas lives in `src/frontend/src/components/Bar2026.jsx` and renders via `src/frontend/src/components/AnnotationCanvas.jsx`.
```

- [ ] **Step 3: Verify**

```powershell
Select-String "React 19" CONTRIBUTING.md      # should match
Select-String "Xendit" CONTRIBUTING.md        # should match
Select-String "BAR 2026" CONTRIBUTING.md      # should match
Select-String "React 18" CONTRIBUTING.md      # should return nothing
Select-String "PayMongo" CONTRIBUTING.md      # should return nothing
```

- [ ] **Step 4: Commit**

```powershell
git add CONTRIBUTING.md
git commit -m "docs: update CONTRIBUTING — React 19, Xendit, add BAR 2026 pipeline section"
```

---

## Task 3: Mark ADR 004 superseded + create ADR 006

**Files:**
- Modify: `docs/adr/004-paymongo-for-payments.md`
- Create: `docs/adr/006-xendit-for-payments.md`

- [ ] **Step 1: Mark ADR 004 as superseded**

In `docs/adr/004-paymongo-for-payments.md`, change:
```
**Status:** Accepted  
```
to:
```
**Status:** Superseded by [ADR 006](006-xendit-for-payments.md)  
```

- [ ] **Step 2: Create ADR 006**

Create `docs/adr/006-xendit-for-payments.md` with:

```markdown
# ADR 006: Xendit for Subscription Payments

**Status:** Accepted  
**Date:** 2026  
**Supersedes:** [ADR 004 — PayMongo](004-paymongo-for-payments.md)

## Context

PayMongo was the original payment processor but was replaced because Xendit became the preferred PHP payment platform. The PayMongo blueprint was removed entirely (commit `ad0ec96`). Requirements remain the same: PHP subscriptions, GCash/Maya/card support, webhook-based lifecycle events.

## Decision

Use **Xendit** as the subscription payment processor with:

1. **`api/utils/xendit_client.py`** — HTTP abstraction layer with retry + exponential backoff, centralising all Xendit API calls.
2. **Recurring plan model** — recurring plans are created inside the `payment_session.completed` webhook handler (`api/blueprints/xendit.py`), not at checkout time. This decouples plan creation from the redirect flow.
3. **`XENDIT_WEBHOOK_TOKEN`** for callback token verification (not HMAC — Xendit uses a shared token).
4. **`XENDIT_BYPASS=true`** flag for local development without real payment flows.

## Reasons

- Xendit supports GCash, Maya, cards, OTC — dominant payment methods in the Philippines.
- HTTP abstraction (`xendit_client.py`) isolates retry/backoff logic from blueprint handlers.
- Webhook-first subscription model keeps subscription state in PostgreSQL, independent of Xendit API availability at read time.
- Plan IDs stored as `XENDIT_PLAN_*` env vars — pricing updates require no code change.

## Consequences

- **Positive:** Retry/backoff centralised in `xendit_client.py`; blueprint code is thin.
- **Positive:** Recurring plans created on webhook event — idempotent re-delivery is safe.
- **Positive:** `XENDIT_BYPASS=true` enables local development without real credentials.
- **Negative:** `XENDIT_WEBHOOK_TOKEN` is a shared token, not HMAC-signed — must be rotated if leaked. Set in Azure Application Settings.
- **Negative:** Subscription state can lag by one webhook delivery window after payment.
- **Negative:** PHP-only; international subscriptions not supported.

## Key files

| File | Role |
|------|------|
| `api/blueprints/xendit.py` | All Xendit HTTP routes (checkout, webhook, cancel, status) |
| `api/utils/xendit_client.py` | HTTP abstraction with retry + backoff |
| `api/config.py` | `XENDIT_API_KEY`, `XENDIT_WEBHOOK_TOKEN`, `XENDIT_BYPASS`, `XENDIT_PLAN_*` |
```

- [ ] **Step 3: Verify**

```powershell
Select-String "Superseded" docs/adr/004-paymongo-for-payments.md  # should match
Select-String "ADR 006" docs/adr/006-xendit-for-payments.md        # should match
```

- [ ] **Step 4: Commit**

```powershell
git add docs/adr/004-paymongo-for-payments.md docs/adr/006-xendit-for-payments.md
git commit -m "docs: add ADR 006 (Xendit), mark ADR 004 (PayMongo) superseded"
```

---

## Task 4: Create docs/ENV_VARS.md

**Files:**
- Create: `docs/ENV_VARS.md`

All values sourced from `api/config.py` (read it first to confirm defaults before writing).

- [ ] **Step 1: Verify current defaults from source**

```powershell
Select-String "os.getenv" api/config.py | head -40
```

Confirm the defaults match what's written in Step 2.

- [ ] **Step 2: Create ENV_VARS.md**

Create `docs/ENV_VARS.md` with:

````markdown
# Environment Variables Reference

Set API variables in `api/local.settings.json` (local) or Azure Application Settings (production).  
Set frontend variables in `src/frontend/.env.local` (local) or GitHub Actions secrets (CI).

---

## Core — Database

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DB_CONNECTION_STRING` | **Yes** | — | PostgreSQL connection string (cloud Azure Flexible Server). Also accepted as `DATABASE_URL`. Must include `?sslmode=require` for Azure. |
| `LOCAL_DB_CONNECTION_STRING` | No | — | Optional local Postgres URI for admin backup mirror (`pg_restore` only). Not used for API queries. |
| `DB_POOL_MIN_CONN` | No | `2` | Minimum connections in `ThreadedConnectionPool`. |
| `DB_POOL_MAX_CONN` | No | `15` | Maximum connections. Keep `instances × maxconn` below Azure server `max_connections`. |

---

## Cache — Redis

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | No | `redis://localhost:6379` | Redis connection URL. Use `rediss://:<password>@<host>:6380` for Azure Cache for Redis (TLS). |
| `REDIS_ENABLED` | No | `true` | Set `false` to disable caching entirely (all requests hit PostgreSQL). Useful in test environments. |
| `FLASHCARD_CONCEPTS_CACHE_KEY` | No | `flashcard_concepts:v11:bar_2026` | Versioned Redis key for flashcard concepts. Bump to force cache invalidation after a data refresh. |
| `CACHE_TTL_DECISIONS` | No | `60` | TTL in seconds for SC decisions list. |
| `CACHE_TTL_DECISION_DETAIL` | No | `600` | TTL in seconds for individual case detail. |
| `CACHE_TTL_PONENTES` | No | `300` | TTL for ponente/filter lists. |
| `CACHE_TTL_SC_JUDICIARY_FEED` | No | `900` | TTL for proxied SC judiciary RSS feed. |
| `CACHE_TTL_FLASHCARD_CONCEPTS` | No | `86400` | TTL for flashcard concepts (24 h). |
| `CACHE_TTL_CODAL_STATIC` | No | `86400` | TTL for LexCode static JSON. |

---

## Auth — Clerk

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CLERK_SECRET_KEY` | **Yes** | — | Clerk secret key (`sk_live_...` or `sk_test_...`). Used to call Clerk API when webhook has not fired yet. |
| `CLERK_WEBHOOK_SECRET` | **Yes** (webhook) | — | Svix signing secret (`whsec_...`) from Clerk Dashboard → Webhooks → your endpoint. Verifies `user.created` / `user.updated` / `user.deleted` events. |

Frontend:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_CLERK_PUBLISHABLE_KEY` | **Yes** | — | Clerk publishable key (`pk_live_...` or `pk_test_...`). Safe to embed in the frontend bundle. Required in GitHub Actions secrets for CI builds. |

---

## Payments — Xendit

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `XENDIT_API_KEY` | **Yes** (payments) | — | Xendit secret API key. Used in `api/utils/xendit_client.py` for all Xendit API calls. |
| `XENDIT_WEBHOOK_TOKEN` | **Yes** (webhook) | — | Xendit callback token. Verified against the `x-callback-token` header on `POST /api/xendit-webhook`. Rotate immediately if leaked. |
| `XENDIT_BYPASS` | No | `false` | Set `true` to skip real payment flows in local development. |
| `XENDIT_PLAN_AMICUS` | No | — | Xendit recurring plan ID for the Amicus subscription (PHP 299/month). |

---

## AI — Gemini / Vertex AI / RAG

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GCP_PROJECT` | **Yes** (AI features) | `gen-lang-client-0545071081` | Google Cloud project ID for Vertex AI calls. |
| `GCP_LOCATION` | No | `us-central1` | GCP region for Gemini model calls. |
| `RAG_REGION` | No | `europe-west4` | GCP region for RAG Engine corpus (avoids Spanner capacity limits). |
| `GCP_SA_JSON_B64` | **Yes** (production AI) | — | Base64-encoded service account JSON. Preferred over `GCP_SA_JSON` — survives shell escaping in Azure Application Settings. |
| `GCP_SA_JSON` | No | — | Raw service account JSON string (fallback for local dev). |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | `lexmateph-rag-key.json` | Path to service account JSON file. Set automatically from `GCP_SA_JSON_B64` / `GCP_SA_JSON` at startup. |
| `GEMINI_PRO_MODEL` | No | `gemini-2.5-pro` | Vertex AI model ID for complex tasks (digest generation, grading). |
| `GEMINI_FLASH_MODEL` | No | `gemini-2.5-flash` | Vertex AI model ID for fast tasks. |
| `RAG_CORPUS_NAME` | No | — | Vertex AI RAG Engine corpus resource name. Set after corpus creation. |
| `COMPLEXITY_FLASH_MAX` | No | `0` | Complexity threshold (1–5). Requests ≤ this value use Flash; higher use Pro. `0` = always Pro. |
| `GCS_CORPUS_BUCKET` | No | `lexmateph-legal-corpus` | GCS bucket for legal corpus files. |

---

## Azure Services

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AZURE_STORAGE_CONNECTION_STRING` | No | `UseDevelopmentStorage=true` | Azure Blob Storage connection string. Required for LexPlay audio caching. Use `UseDevelopmentStorage=true` locally (requires Azurite). |
| `SPEECH_KEY` | No | — | Azure Cognitive Services Speech key. If missing, LexPlay falls back to gTTS. |
| `SPEECH_REGION` | No | `japaneast` | Azure region for Speech service. |
| `LEXPLAY_USE_AZURE_SPEECH` | No | `false` | Set `1` / `true` to force Azure TTS even when `SPEECH_KEY` is available (it is auto-detected; this flag overrides). |

---

## Frontend (Vite)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_CLERK_PUBLISHABLE_KEY` | **Yes** | — | See Clerk section above. |
| `VITE_API_BASE_URL` | No | — | Base URL for API calls. Leave empty to use same-origin `/api` (correct for SWA). Set to `http://localhost:7071` when running Vite and Functions separately without the SWA emulator. |

---

## Dev / Feature Flags

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | No | `production` | Set to `local` to enable local-dev mode (`IS_LOCAL_DEV=True`). |
| `TRIAL_ENABLED` | No | — | Controls whether trial subscriptions are available. |
| `ADMIN_EMAILS` | No | — | Comma-separated list of admin email addresses. Used only as fallback when auto-creating a user row before the Clerk webhook fires. DB `is_admin` column is authoritative after sync. |
| `ALLOW_DEBUG_ROUTES` | No | `false` | Set `1` to enable `GET /api/debug_imports` diagnostic endpoint. Never enable in production. |
| `FRONTEND_URL` | No | `https://lexmateph.com` | Frontend origin URL. Used for CORS and redirect URLs. |
| `GUEST_FULL_ACCESS_HOURS` | No | `24` | Hours of full guest access before tier gating kicks in. |
| `RATE_LIMIT_GUEST` | No | `3` | AI questions per day for unauthenticated users. |
| `RATE_LIMIT_FREE` | No | `10` | AI questions per day for free-tier users. |
| `RATE_LIMIT_AMICUS` | No | `-1` | AI questions per day for Amicus subscribers (`-1` = unlimited). |
````

- [ ] **Step 3: Verify key entries against source**

```powershell
# Spot-check: confirm XENDIT_WEBHOOK_TOKEN is in config.py
Select-String "XENDIT_WEBHOOK_TOKEN" api/config.py

# Spot-check: confirm REDIS_ENABLED default
Select-String "REDIS_ENABLED" api/config.py

# Spot-check: confirm DB pool defaults
Select-String "DB_POOL" api/config.py
```

All three should return matches with defaults matching what's in the ENV_VARS table.

- [ ] **Step 4: Commit**

```powershell
git add docs/ENV_VARS.md
git commit -m "docs: add ENV_VARS.md — complete environment variables reference"
```

---

## Task 5: Create docs/API_ROUTES.md

**Files:**
- Create: `docs/API_ROUTES.md`

Route paths sourced from `api/function_app.py` and all `api/blueprints/*.py`.

- [ ] **Step 1: Verify key route paths from source**

```powershell
grep -rn "\.route(" api/blueprints/ --include="*.py" | grep -v "^Binary" | sort
```

Confirm the routes in Step 2 match.

- [ ] **Step 2: Create API_ROUTES.md**

Create `docs/API_ROUTES.md` with:

````markdown
# API Routes Reference

All routes are prefixed with `/api/` in the deployed app (Azure SWA + Functions). Auth column shows whether a valid Clerk JWT is required.

---

## Health

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| GET | `/api/ping` | No | `function_app.py` | Returns `pong`. Liveness probe. |
| GET | `/api/health` | No | `function_app.py` | Returns `OK`. |
| GET | `/api/health_db` | No | `function_app.py` | Tests PostgreSQL connectivity. Returns 500 on failure. |
| GET | `/api/debug_imports` | No* | `function_app.py` | Blueprint import diagnostics. Only active when `ALLOW_DEBUG_ROUTES=1`. |

---

## Auth / Clerk

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| POST | `/api/clerk-webhook` | Svix sig | `clerk_webhook.py` | Receives `user.created` / `user.updated` / `user.deleted` events from Clerk. Upserts `users` row. |
| POST | `/api/register` | No | `auth_custom.py` | Custom registration flow. |
| POST | `/api/login` | No | `auth_custom.py` | Custom login flow. |

---

## Users

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| GET | `/api/history` | Yes | `user.py` | Returns search/view history for the authenticated user. |

---

## Subscription / Payments (Xendit)

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| GET | `/api/subscription-status` | Yes | `xendit.py` | Returns current subscription tier, status, and expiry for the authenticated user. |
| POST | `/api/create-checkout` | Yes | `xendit.py` | Creates a Xendit payment link for the Amicus plan. Returns checkout URL. |
| POST | `/api/cancel-subscription` | Yes | `xendit.py` | Cancels the active Xendit recurring subscription. Paid access continues to period end. |
| POST | `/api/track-usage` | Yes | `xendit.py` | Increments usage counter for free-tier gating. |
| GET | `/api/available-plans` | No | `xendit.py` | Returns available subscription plans and pricing. |
| POST | `/api/xendit-webhook` | Token | `xendit.py` | Receives Xendit payment lifecycle events. Verified via `x-callback-token` header matching `XENDIT_WEBHOOK_TOKEN`. Creates recurring plans on `payment_session.completed`. |

---

## SC Decisions

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| GET | `/api/sc_decisions` | No | `supreme.py` | List / search Supreme Court decisions. Supports `q`, `subject`, `year`, `ponente`, `page`, `limit` query params. Redis-cached (60 s TTL). |
| GET | `/api/sc_decisions/{id}` | No | `supreme.py` | Get a single decision by integer ID. Redis-cached (600 s). |
| GET | `/api/sc_decisions/ponentes` | No | `supreme.py` | List all ponentes for filter UI. Redis-cached (300 s). |
| GET | `/api/sc_decisions/divisions` | No | `supreme.py` | List SC divisions. Redis-cached (300 s). |
| GET | `/api/sc_decisions/models` | No | `supreme.py` | Returns model/schema metadata. |
| GET | `/api/sc_decisions/flashcard_concepts` | No | `supreme.py` | Returns flashcard concept list. Redis-cached (24 h, key versioned via `FLASHCARD_CONCEPTS_CACHE_KEY`). |
| GET | `/api/sc_judiciary_feed` | No | `supreme.py` | Proxied SC Judiciary RSS feed. Redis-cached (900 s). |
| GET | `/api/fc/all` | No | `supreme.py` | Full-context case list for linking. |

---

## Codex / Statutes / Codals

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| GET | `/api/codex/issuance` | No | `codex.py` | Fetches a statute by issuance identifier. |
| GET | `/api/codex/jurisprudence` | No | `codex.py` | Returns jurisprudence linked to a codal provision. |
| GET | `/api/codex/amendments` | No | `codex.py` | Returns amendment history for a provision. |
| GET | `/api/codex/versions` | No | `codex.py` | Returns version history. |
| GET | `/api/statutes` | No | `statutes.py` | Full-text statute search with ILIKE. Input length limited. |
| GET | `/api/rpc/article/{article_num}` | No | `rpc.py` | Revised Penal Code article by number. |
| GET | `/api/rpc/book/{book_num}` | No | `rpc.py` | RPC book. |
| GET | `/api/rpc/title/{title_num}` | No | `rpc.py` | RPC title. |
| GET | `/api/civ/article/{article_num}` | No | `civ.py` | Civil Code article. |
| GET | `/api/civ/book/{book_num}` | No | `civ.py` | Civil Code book. |
| GET | `/api/civ/title/{title_num}` | No | `civ.py` | Civil Code title. |
| GET | `/api/civ/preliminary` | No | `civ.py` | Civil Code preliminary title. |
| GET | `/api/const/book/{book_num}` | No | `const.py` | Constitution section/article. |
| GET | `/api/labor/books` | No | `labor.py` | Labor Code — all books. |
| GET | `/api/labor/books/{book_id}` | No | `labor.py` | Labor Code book by ID. |
| GET | `/api/roc/all` | No | `roc.py` | Rules of Court — all rules. |
| GET | `/api/roc/book/{book_num}` | No | `roc.py` | Rules of Court book. |

---

## Bar Questions

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| GET | `/api/questions` | No | `questions.py` | Paginated bar questions. Supports `subject`, `year`, `limit` (input-validated). |

---

## BAR 2026 Reviewer

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| GET | `/api/reviewer/{subject}` | No | `bar_reviewer.py` | Topics list for a BAR 2026 subject (e.g. `civil-law`, `criminal-law`). |
| GET | `/api/reviewer/{subject}/{topic_id}` | No | `bar_reviewer.py` | Single topic detail with linked SC cases. |
| GET/POST | `/api/reviewer/generate` | No | `bar_reviewer.py` | AI-generated reviewer content for a topic. |
| POST | `/api/reviewer/publish` | No | `bar_reviewer.py` | Publish generated reviewer content (admin). |
| POST | `/api/reviewer/flag` | No | `bar_reviewer.py` | Flag reviewer content for review. |
| GET | `/api/reviewer/gen/log` | No | `bar_reviewer.py` | Generation log for admin monitoring. |

---

## Lexify (Mock Exams)

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| GET | `/api/lexify_exams` | Yes | `lexify.py` | Available mock exam papers. |
| GET | `/api/lexify_questions` | Yes | `lexify.py` | Questions for a given exam. Supports `limit` (input-validated). |
| POST | `/api/lexify_grade` | Yes | `lexify.py` | Grade a single Lexify answer via Vertex AI. |
| POST | `/api/lexify_grade_batch` | Yes | `lexify.py` | Batch grading for a full exam submission. |

---

## LexPlay / Audio

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| GET | `/api/audio/{content_type}/{content_id}` | No | `audio_provider.py` | Generate or serve cached TTS audio. `content_type`: `codal` or `case`. Returns JSON `{url, cached: true}` on cache hit; raw `audio/mpeg` bytes on miss. |
| GET | `/api/lexplay/state` | Yes | `schedule.py` | Returns saved LexPlay playback state for authenticated user. |
| GET | `/api/playlists` | Yes | `playlists.py` | List user's saved playlists. |
| POST | `/api/playlists` | Yes | `playlists.py` | Create a new playlist. |
| GET | `/api/playlists/{playlist_id}` | Yes | `playlists.py` | Get a playlist with items. |
| PUT | `/api/playlists/{playlist_id}` | Yes | `playlists.py` | Update playlist metadata. |
| DELETE | `/api/playlists/{playlist_id}` | Yes | `playlists.py` | Delete a playlist. |
| POST | `/api/playlists/{playlist_id}/items` | Yes | `playlists.py` | Add item to playlist. |
| DELETE | `/api/playlists/{playlist_id}/items/{item_id}` | Yes | `playlists.py` | Remove item from playlist. |
| POST | `/api/playlists/{playlist_id}/bulk_items` | Yes | `playlists.py` | Bulk add items. |

---

## AI Features

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| POST | `/api/ai-search` | Yes | `ai_search.py` | AI-powered semantic search over cases and statutes. Rate-limited by tier. |
| POST | `/api/legal-chat` | Yes | `legal_chat.py` | RAG-backed legal Q&A. Rate-limited by tier (`RATE_LIMIT_*`). Semantically cached (7-day TTL). |
| POST | `/api/legal-chat-clear` | Yes | `legal_chat.py` | Clear user's legal chat session. |
| GET | `/api/legal-chat-status` | Yes | `legal_chat.py` | Returns rate limit and session status. |
| POST | `/api/ai/digest/{id}` | Admin | `ai_processor.py` | Generate AI digest for a case. |
| POST | `/api/ai/mock-exam/{id}` | Admin | `ai_processor.py` | Generate mock exam questions from a case. |
| POST | `/api/ai/clean/{id}` | Admin | `ai_processor.py` | Clean/normalize case text. |
| POST | `/api/ai/tts` | Admin | `ai_processor.py` | Generate TTS spoken script for a case. |

---

## Admin / Ops

All `/api/ops/*` routes require admin authentication. They are available only when the Functions host is running (local or deployed) with admin blueprints loaded.

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| GET | `/api/ops/pipeline/status` | Admin | `admin_pipeline.py` | Returns pipeline progress from `pipeline_progress.json`. |
| POST | `/api/ops/pipeline/start` | Admin | `admin_pipeline.py` | Start a full eLib digest pipeline run. |
| POST | `/api/ops/pipeline/resume` | Admin | `admin_pipeline.py` | Resume an interrupted pipeline run. |
| POST | `/api/ops/pipeline/stop` | Admin | `admin_pipeline.py` | Stop the running pipeline. |
| POST | `/api/ops/pipeline/scan` | Admin | `admin_pipeline.py` | Scan eLib for new decisions without digesting. |
| GET | `/api/ops/pipeline/scan-results` | Admin | `admin_pipeline.py` | Results of last scan. |
| POST | `/api/ops/pipeline/scan-gaps` | Admin | `admin_pipeline.py` | Scan for cases with missing digests. |
| GET | `/api/ops/pipeline/gap-results` | Admin | `admin_pipeline.py` | Results of gap scan. |
| POST | `/api/ops/pipeline/stop-gap-scan` | Admin | `admin_pipeline.py` | Stop gap scan. |
| GET | `/api/ops/pipeline-stats` | Admin | `admin_pipeline.py` | Pipeline statistics. |
| GET | `/api/ops/db-stats` | Admin | `admin_metrics.py` | Database row counts and size metrics. |
| GET | `/api/ops/observations` | Admin | `admin_metrics.py` | Observation log entries. |
| GET/PUT | `/api/ops/observations/{obs_id}` | Admin | `admin_metrics.py` | Get or update a single observation. |
| GET | `/api/ops/azure-metrics` | Admin | `admin_metrics.py` | Azure Functions invocation metrics. |
| POST | `/api/ops/backup/start` | Admin | `admin_backup.py` | Trigger a cloud database backup (pg_dump). |
| GET | `/api/ops/backup/status` | Admin | `admin_backup.py` | Backup progress and last run status. |
| GET | `/api/ops/backup/download` | Admin | `admin_backup.py` | Download the latest backup file. |
| POST | `/api/backfill_per_curiam` | Admin | `admin.py` | Backfill per curiam fields on cases. |
| POST | `/api/fix_ponentes` | Admin | `admin.py` | Fix ponente normalisation. |

---

## Other

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| GET | `/api/schedule` | Yes | `schedule.py` | Returns scheduled content or user schedule state. |
| GET | `/api/sitemap` | No | `sitemap.py` | XML sitemap for SEO. |
| GET | `/api/decision_page/{case_id}` | No | `decision_page.py` | SSR-friendly decision page data for a case (used for social/SEO previews). |
````

- [ ] **Step 3: Verify spot checks**

```powershell
# Confirm xendit-webhook route exists
Select-String "xendit-webhook" api/blueprints/xendit.py

# Confirm reviewer routes exist
Select-String "reviewer" api/blueprints/bar_reviewer.py

# Confirm audio route exists
Select-String "audio" api/blueprints/audio_provider.py
```

All three should return matches.

- [ ] **Step 4: Commit**

```powershell
git add docs/API_ROUTES.md
git commit -m "docs: add API_ROUTES.md — full route map with auth and blueprint references"
```

---

## Task 6: Update docs/RUNBOOK.md — Section 4

**Files:**
- Modify: `docs/RUNBOOK.md`

- [ ] **Step 1: Replace Section 4 (PayMongo → Xendit)**

In `docs/RUNBOOK.md`, replace section 4 entirely. Find:

```
## 4. Subscription not activating after payment
```

And replace everything from that heading through the end of the section (up to `---`) with:

```markdown
## 4. Subscription not activating after payment (Xendit)

**Symptoms:** User paid via Xendit but account still shows Free tier.

**Steps:**

1. Check Xendit Dashboard → Webhooks → delivery logs for the `payment_session.completed` event.
2. If webhook delivery failed, manually re-trigger from Xendit Dashboard.
3. Check Azure Functions logs for the `xendit-webhook` route — look for token verification failures or JSON parse errors.
4. Check `XENDIT_WEBHOOK_TOKEN` in Application Settings — it must match the callback token configured in Xendit Dashboard → Settings → Webhooks.
5. **Recurring plan not created:** The recurring plan is created inside the `payment_session.completed` handler in `api/blueprints/xendit.py`. If a user paid but has no recurring plan, check the Functions log for errors in that handler.
6. The webhook handler is idempotent — re-delivered events with the same session ID are safe to re-process.
7. Manual tier grant (admin only):

```sql
UPDATE users
SET subscription_tier = 'amicus',
    subscription_status = 'active',
    subscription_source = 'manual_admin',
    subscription_expires_at = NOW() + INTERVAL '1 year'
WHERE clerk_id = '<clerk_id>';
```
```

- [ ] **Step 2: Verify**

```powershell
Select-String "Xendit" docs/RUNBOOK.md        # should match section 4
Select-String "PayMongo" docs/RUNBOOK.md       # should return nothing (or only in comments)
Select-String "xendit-webhook" docs/RUNBOOK.md # should match
```

- [ ] **Step 3: Commit**

```powershell
git add docs/RUNBOOK.md
git commit -m "docs: update RUNBOOK section 4 — PayMongo replaced by Xendit"
```

---

## Task 7: Update docs/USER_GUIDE.md

**Files:**
- Modify: `docs/USER_GUIDE.md`

- [ ] **Step 1: Add BAR 2026 Reviewer to the step-by-step section**

After the "Bar Questions" step-by-step block, add:

```markdown
### BAR 2026 Reviewer

1. Sidebar → **BAR 2026**.
2. Choose a **subject** tile (e.g. Civil Law, Criminal Law).
3. Browse the **topic list** aligned to the 2026 Bar syllabus.
4. Open a topic to read the outline and see **linked SC cases**.
5. Tap any case to open the case digest.

**Annotation:** While on a reviewer page, use the **toolbar on the left** to draw, highlight, or erase directly on the page using a stylus or finger. Annotations are saved per-page and persist across sessions.
```

- [ ] **Step 2: Add BAR 2026 Reviewer to the sidebar navigation table**

In the "Main navigation" table, add:

```markdown
| **BAR 2026** | Syllabus-aligned BAR 2026 reviewer with linked SC cases and page annotation. |
```

- [ ] **Step 3: Update subscription plans table**

Replace the plans table content (which currently mentions Amicus, Juris, Barrister) with:

```markdown
## Plans and access

LexMatePH offers a free tier and a single paid plan:

| Plan | Price | Access |
|------|-------|--------|
| **Free** | Free | Limited digests, bar questions, flashcards per day |
| **Amicus** | PHP 299/month | Unlimited access to all features including Lexify mock exams, LexPlay, and the BAR 2026 Reviewer |

Subscribe via **Upgrade** in the sidebar. Payments via GCash, Maya, or card through Xendit. Paid access continues to the end of the billing period after cancellation.
```

- [ ] **Step 4: Verify**

```powershell
Select-String "BAR 2026" docs/USER_GUIDE.md       # should match
Select-String "annotation" docs/USER_GUIDE.md      # should match
Select-String "PHP 299" docs/USER_GUIDE.md         # should match
Select-String "Barrister" docs/USER_GUIDE.md       # should return nothing
```

- [ ] **Step 5: Commit**

```powershell
git add docs/USER_GUIDE.md
git commit -m "docs: update USER_GUIDE — add BAR 2026 Reviewer, annotation, correct plans"
```

---

## Task 8: Update docs/lexplay/README.md

**Files:**
- Modify: `docs/lexplay/README.md`

- [ ] **Step 1: Remove the resolved "🔴 Current Blocker" section**

In `docs/lexplay/README.md`, find and delete everything from:

```
### 🔴 Current Blocker: Audio not playing end-to-end
```

through to the end of the numbered list under it (items 1–5 about CORS, Content-Type, gTTS network timeout, Azure Functions streaming, Azurite not running). Keep the `### 🟡 Future Enhancements` section.

- [ ] **Step 2: Update the feature status table**

Find:
```
| Audio plays successfully end-to-end | ⚠️ Partially working — see Known Issues |
```
Replace with:
```
| Audio plays successfully end-to-end | ✅ Implemented |
```

- [ ] **Step 3: Update "Last updated" date**

Find:
```
*Last updated: March 2026*
```
Replace with:
```
*Last updated: May 2026*
```

- [ ] **Step 4: Verify**

```powershell
Select-String "Current Blocker" docs/lexplay/README.md   # should return nothing
Select-String "Partially working" docs/lexplay/README.md  # should return nothing
Select-String "May 2026" docs/lexplay/README.md           # should match
```

- [ ] **Step 5: Commit**

```powershell
git add docs/lexplay/README.md
git commit -m "docs: update LexPlay README — remove resolved blocker, mark audio working"
```

---

## Task 9: Create docs/features/bar2026-reviewer.md

**Files:**
- Create: `docs/features/bar2026-reviewer.md`

- [ ] **Step 1: Create the features/ directory and verify source paths**

```powershell
New-Item -ItemType Directory -Force docs/features
Test-Path api/blueprints/bar_reviewer.py               # should be True
Test-Path src/frontend/src/components/Bar2026.jsx       # confirm path
```

- [ ] **Step 2: Create the feature doc**

Create `docs/features/bar2026-reviewer.md` with:

````markdown
# BAR 2026 Reviewer — Feature Documentation

**Last updated:** 2026-05-28

The BAR 2026 Reviewer is a syllabus-aligned study tool that lets bar examinees browse topics by subject, read linked Supreme Court cases, and annotate pages directly with a stylus or finger.

---

## Table of Contents

1. [Feature Overview](#1-feature-overview)
2. [Data Pipeline](#2-data-pipeline)
3. [Syllabus Alignment](#3-syllabus-alignment)
4. [Case Linking](#4-case-linking)
5. [Annotation Canvas](#5-annotation-canvas)
6. [API Routes](#6-api-routes)
7. [Local Development](#7-local-development)

---

## 1. Feature Overview

| Capability | Status |
|-----------|--------|
| Subject browser (Civil, Criminal, Labor, etc.) | ✅ Implemented |
| Syllabus-aligned topic list per subject | ✅ Implemented |
| Linked SC cases per topic | ✅ Implemented |
| Case digest view from reviewer | ✅ Implemented |
| Page annotation (pen, highlighter, eraser) | ✅ Implemented |
| Annotation persistence per page | ✅ Implemented |
| S Pen / stylus optimised input | ✅ Implemented |

---

## 2. Data Pipeline

The reviewer content is built by a multi-stage pipeline run from **Admin → Digest Pipeline**:

```
eLib scraper
    └── scripts/elib_digest_pipeline.py
        ├── Scrapes SC E-Library for new decisions
        ├── Generates AI digests (Gemini via Vertex AI)
        └── Inserts into sc_decided_cases (PostgreSQL)

Syllabus alignment
    └── LexCode/pipelines/
        └── Maps sc_decided_cases to BAR 2026 TOS subjects/topics

Case linker
    └── api/brain/
        └── Gemini-based semantic linking: codal provisions ↔ cases
```

The pipeline runs **locally** (workstation + cloud DB). See `docs/RUNBOOK.md` § Admin Digest Pipeline for operations.

---

## 3. Syllabus Alignment

Topics are aligned to the 2026 Bar Examination Table of Specifications (TOS). Each topic has:

- `subject` — one of the eight bar subjects (Civil Law, Criminal Law, Labor Law, Political Law, Commercial Law, Remedial Law, Legal Ethics, Taxation)
- `topic_id` — stable identifier used in URLs
- `title` — the TOS topic name
- `linked_cases` — SC decisions linked to this topic

Alignment scores are stored in `sc_decided_cases.bar_2026_tos_score`. The `FLASHCARD_BAR_MIN_TOS_SCORE` env var sets the minimum score for inclusion in the default flashcard deck.

---

## 4. Case Linking

AI-powered semantic linking is run by `api/brain/` using Gemini (Vertex AI):

1. Each SC decision digest is embedded.
2. Each BAR 2026 topic/provision is embedded.
3. Cosine similarity identifies semantically related case-provision pairs.
4. High-confidence links are stored and surfaced in the reviewer UI.

Linking runs as part of the admin pipeline. See `scripts/README.md` for the unified linker script.

---

## 5. Annotation Canvas

Page annotations are drawn on an HTML5 Canvas overlaid on the reviewer content.

### Architecture

```
Bar2026.jsx
    └── AnnotationCanvas.jsx
            ├── Renders on <canvas> element (direct 2D Context)
            ├── Listens to pointer events (pen, touch, mouse)
            └── Persists strokes to PostgreSQL via /api/reviewer/... (Clerk auth)
```

### Drawing

- **Pen** — smooth Catmull-Rom cubic Bézier curves with EMA smoothing for natural stroke feel.
- **Highlighter** — semi-transparent overlay; opacity is non-stacking (applied at render time, not per-event).
- **Eraser** — removes stroke segments by proximity.

### S Pen / stylus optimisation

- `pointerrawupdate` events used for hardware-rate input on Samsung Galaxy Tab and similar devices.
- Strokes drawn immediately on `pointermove` (no rAF delay).
- `passive: false` on pointer listeners to prevent scroll interference.

### Persistence

- Strokes are saved per-page to `sc_annotation_strokes` in PostgreSQL.
- A debounce fires on navigation away to flush unsaved strokes.
- Clerk JWT (Bearer token) is sent with save requests — not cookies.

### Toolbar

The annotation toolbar is pinned to the **left side** of the screen. Tools: pen, highlighter, eraser; color pickers per tool; size options.

---

## 6. API Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/reviewer/{subject}` | Topic list for a subject |
| GET | `/api/reviewer/{subject}/{topic_id}` | Topic detail with linked cases |
| GET/POST | `/api/reviewer/generate` | AI-generate reviewer content |
| POST | `/api/reviewer/publish` | Publish generated content (admin) |
| POST | `/api/reviewer/flag` | Flag content for review |
| GET | `/api/reviewer/gen/log` | Generation log (admin) |

See `docs/API_ROUTES.md` for full details.

---

## 7. Local Development

No additional environment variables are required beyond the standard database connection:

```json
{
  "Values": {
    "DB_CONNECTION_STRING": "postgresql://user:pass@host:5432/lexmateph-ea-db?sslmode=require"
  }
}
```

The reviewer reads from the cloud PostgreSQL instance like all other features. To populate reviewer content locally, run the digest pipeline from **Admin → Digest Pipeline** (requires `func start` with cloud DB).

**Key source files:**

| File | Purpose |
|------|---------|
| `api/blueprints/bar_reviewer.py` | API route handlers |
| `src/frontend/src/components/Bar2026.jsx` | Main reviewer UI component |
| `src/frontend/src/components/AnnotationCanvas.jsx` | Canvas overlay and drawing logic |
| `src/frontend/src/hooks/useAnnotations.js` | Annotation state, persistence, debounce |
| `LexCode/pipelines/` | Syllabus alignment pipeline scripts |
| `api/brain/` | AI case linker |
````

- [ ] **Step 3: Verify file paths are real**

```powershell
Test-Path src/frontend/src/components/AnnotationCanvas.jsx  # True
Test-Path src/frontend/src/hooks/useAnnotations.js          # True
Test-Path api/blueprints/bar_reviewer.py                    # True
```

- [ ] **Step 4: Commit**

```powershell
git add docs/features/bar2026-reviewer.md
git commit -m "docs: add BAR 2026 Reviewer feature doc (pipeline, annotation canvas, routes)"
```

---

## Task 10: Create docs/INDEX.md

**Files:**
- Create: `docs/INDEX.md`

- [ ] **Step 1: Create INDEX.md**

Create `docs/INDEX.md` with:

```markdown
# LexMatePH Documentation Index

Quick navigation by reader role. All paths are relative to the repo root.

---

## New contributor

You just cloned the repo and want to make your first change.

1. **[README.md](../README.md)** — Product overview, stack, quick start command
2. **[CONTRIBUTING.md](../CONTRIBUTING.md)** — Local dev setup, file layout, adding blueprints, running tests, PR expectations
3. **[docs/ENV_VARS.md](ENV_VARS.md)** — Every environment variable you need to set in `api/local.settings.json` and `src/frontend/.env.local`
4. **[docs/adr/](adr/)** — Architecture Decision Records (why we use Clerk, Xendit, Redis, Azure SWA, etc.)
5. Make your change → `npm run test` + `pytest api/tests/` → open PR → CI runs quality gates

---

## Developer

You're working on a feature or bug fix and need to understand the system.

| Need | Document |
|------|---------|
| Find which route handles a request | [docs/API_ROUTES.md](API_ROUTES.md) |
| Understand auth flow | [docs/adr/002-clerk-for-auth.md](adr/002-clerk-for-auth.md) |
| Understand payment/subscription flow | [docs/adr/006-xendit-for-payments.md](adr/006-xendit-for-payments.md) |
| Understand caching behaviour | [docs/adr/003-redis-cache-strategy.md](adr/003-redis-cache-strategy.md) |
| Understand hosting/deploy model | [docs/adr/001-azure-static-web-apps-plus-functions.md](adr/001-azure-static-web-apps-plus-functions.md) |
| Work on BAR 2026 / annotation canvas | [docs/features/bar2026-reviewer.md](features/bar2026-reviewer.md) |
| Work on LexPlay audio | [docs/lexplay/README.md](lexplay/README.md) |
| Add a new API blueprint | [CONTRIBUTING.md — Adding a blueprint](../CONTRIBUTING.md#adding-a-blueprint-api-route) |
| All env vars at a glance | [docs/ENV_VARS.md](ENV_VARS.md) |

---

## Operator / DevOps

You're diagnosing a production incident or configuring the deployment.

| Situation | Document |
|-----------|---------|
| Production incident playbook | [docs/RUNBOOK.md](RUNBOOK.md) |
| Configure environment variables | [docs/ENV_VARS.md](ENV_VARS.md) + Azure Portal → SWA → Environment variables |
| Deploy stuck / CI failing | [docs/RUNBOOK.md — Section 7](RUNBOOK.md#7-deploy-stuck-or-deploy-job-failed) |
| Database connection failure | [docs/RUNBOOK.md — Section 1](RUNBOOK.md#1-database-connection-failures) |
| Redis unavailable | [docs/RUNBOOK.md — Section 2](RUNBOOK.md#2-redis--cache-unavailability) |
| Subscription not activating | [docs/RUNBOOK.md — Section 4](RUNBOOK.md#4-subscription-not-activating-after-payment-xendit) |
| Clerk webhook not syncing | [docs/RUNBOOK.md — Section 5](RUNBOOK.md#5-clerk-webhook-not-syncing-users) |
| Vertex AI / Lexify grading broken | [docs/RUNBOOK.md — Section 8](RUNBOOK.md#8-lexify-ai-grading-vertex-ai) |
| Admin pipeline: 404 on /ops/* | [docs/RUNBOOK.md — Section 9](RUNBOOK.md#9-admin-digest-pipeline-local-func-start--cloud-db) |
| Architecture decision history | [docs/adr/](adr/) |

---

## All documents

| Document | Type | Description |
|----------|------|-------------|
| [README.md](../README.md) | Overview | Product description, stack, quick start |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Guide | Local dev setup, conventions, PR flow |
| [docs/USER_GUIDE.md](USER_GUIDE.md) | Guide | End-user feature guide |
| [docs/RUNBOOK.md](RUNBOOK.md) | Reference | Production incident playbook |
| [docs/ENV_VARS.md](ENV_VARS.md) | Reference | All environment variables |
| [docs/API_ROUTES.md](API_ROUTES.md) | Reference | Full API route map |
| [docs/lexplay/README.md](lexplay/README.md) | Feature | LexPlay audio architecture and setup |
| [docs/features/bar2026-reviewer.md](features/bar2026-reviewer.md) | Feature | BAR 2026 Reviewer and annotation canvas |
| [docs/adr/001](adr/001-azure-static-web-apps-plus-functions.md) | ADR | Azure SWA + Functions |
| [docs/adr/002](adr/002-clerk-for-auth.md) | ADR | Clerk for authentication |
| [docs/adr/003](adr/003-redis-cache-strategy.md) | ADR | Redis cache strategy |
| [docs/adr/004](adr/004-paymongo-for-payments.md) | ADR | PayMongo (superseded) |
| [docs/adr/005](adr/005-admin-case-digest-pipeline.md) | ADR | Admin case digest pipeline |
| [docs/adr/006](adr/006-xendit-for-payments.md) | ADR | Xendit for payments |
```

- [ ] **Step 2: Verify all linked files exist**

```powershell
Test-Path README.md
Test-Path CONTRIBUTING.md
Test-Path docs/USER_GUIDE.md
Test-Path docs/RUNBOOK.md
Test-Path docs/ENV_VARS.md
Test-Path docs/API_ROUTES.md
Test-Path docs/lexplay/README.md
Test-Path "docs/features/bar2026-reviewer.md"
Test-Path docs/adr/001-azure-static-web-apps-plus-functions.md
Test-Path docs/adr/006-xendit-for-payments.md
```

All should return `True`.

- [ ] **Step 3: Commit**

```powershell
git add docs/INDEX.md
git commit -m "docs: add INDEX.md — master navigation by contributor, developer, and operator role"
```

---

## Task 11: Final verification pass

- [ ] **Step 1: Run tests to confirm no code was accidentally changed**

```powershell
cd api
python -m pytest --tb=short -q
cd ..\src\frontend
npx vitest run --reporter=verbose 2>&1 | tail -10
```

Expected: 68 backend tests pass, 140 frontend tests pass.

- [ ] **Step 2: Check for stale references across all updated docs**

```powershell
# Should find nothing in updated docs
Select-String "PayMongo" README.md CONTRIBUTING.md docs/RUNBOOK.md docs/USER_GUIDE.md
Select-String "Codex Philippines" README.md
Select-String "React 18" CONTRIBUTING.md
Select-String "Current Blocker" docs/lexplay/README.md
Select-String "Juris\|Barrister" docs/USER_GUIDE.md
```

All should return nothing (no matches).

- [ ] **Step 3: Check all new files exist**

```powershell
Test-Path docs/ENV_VARS.md
Test-Path docs/API_ROUTES.md
Test-Path docs/INDEX.md
Test-Path "docs/features/bar2026-reviewer.md"
Test-Path docs/adr/006-xendit-for-payments.md
```

All should return `True`.

- [ ] **Step 4: Final commit if any loose changes remain**

```powershell
git status  # should be clean; if not, commit remaining changes
git log --oneline -12  # verify all task commits are present
```
