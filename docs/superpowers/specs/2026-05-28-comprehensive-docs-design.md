# Comprehensive Documentation Overhaul — Design Spec

**Date:** 2026-05-28  
**Status:** Approved  
**Audience:** Contributors and team members

---

## Goal

Bring all project documentation to an accurate, complete, contributor-ready state that reflects the current product (LexMatePH v3) and conforms to best practices established in commit `3a25d91`.

---

## Scope

### Files to update (5)

| File | Problem | Fix |
|---|---|---|
| `README.md` | Wrong product name ("Codex Philippines"), v1 architecture, missing all current features | Full rewrite |
| `CONTRIBUTING.md` | React 18 (should be 19), PayMongo (replaced by Xendit), missing BAR 2026 and annotation sections | Targeted updates |
| `docs/USER_GUIDE.md` | Missing BAR 2026 Reviewer feature and annotation canvas | Add two sections |
| `docs/RUNBOOK.md` | Section 4 references PayMongo webhooks (replaced by Xendit) | Replace section 4 content |
| `docs/lexplay/README.md` | "Known Issues" section lists resolved bugs as open blockers | Remove resolved issues, update local dev notes |
| `docs/adr/004-paymongo-for-payments.md` | PayMongo was replaced; ADR has no superseded marker | Add `Status: Superseded by ADR 006` |

### Files to create (5)

| File | What it covers |
|---|---|
| `docs/adr/006-xendit-for-payments.md` | Why Xendit replaced PayMongo, recurring plan model, HTTP abstraction layer |
| `docs/ENV_VARS.md` | Every environment variable grouped by service: Core DB, Redis, Clerk, Xendit, AI, Azure, Vite, Dev flags |
| `docs/API_ROUTES.md` | Full route map grouped by domain with method, path, auth requirement, blueprint file, description |
| `docs/features/bar2026-reviewer.md` | BAR 2026 Reviewer: pipeline, syllabus alignment, case linking, annotation canvas (OffscreenCanvas + Web Worker) |
| `docs/INDEX.md` | Master navigation by reader role: new contributor, developer, operator/DevOps |

---

## Content design

### `README.md`

```
# LexMatePH
<one-paragraph product description>

## Features
<table: LexCode, SC Decisions, Bar Questions, Flashcards, Lexify, LexPlay, BAR 2026 Reviewer>

## Stack
<table: React 19, Next.js 16, Python Flask/Azure Functions, PostgreSQL, Redis, Gemini AI, Clerk, Xendit, Azure SWA>

## Quick start
<clone → configure → ./start_all.ps1>

## Documentation
<links: CONTRIBUTING.md, docs/INDEX.md>
```

### `CONTRIBUTING.md`

- Stack table: React 19, Xendit (not PayMongo)
- Added subsection: BAR 2026 pipeline scripts (`LexCode/pipelines/`, `scripts/elib_digest_pipeline.py`)
- Added note: annotation canvas in `src/frontend/src/features/bar-reviewer/`
- Keep all existing sections unchanged

### `docs/USER_GUIDE.md`

- Add BAR 2026 Reviewer to sidebar navigation table and step-by-step
- Add annotation canvas usage: drawing tools (pen, highlighter, eraser), toolbar location (left side), persistence per-page
- Update subscription plan table: Amicus plan at PHP 299/month (remove Juris/Barrister references)

### `docs/RUNBOOK.md`

- Section 4: Replace PayMongo content with Xendit
  - Webhook URL: `/api/xendit-webhook`
  - Env var: `XENDIT_WEBHOOK_TOKEN` (not a signing secret — Xendit uses a callback token)
  - Recurring plans created in `payment_session.completed` handler in `api/blueprints/xendit.py`
  - Add: recurring plan not created → check `payment_session.completed` event in xendit.py
  - Manual tier grant SQL stays unchanged
- Keep all other sections

### `docs/lexplay/README.md`

- Remove entire "🔴 Current Blocker" subsection (CORS, audio not playing — resolved)
- Update local dev prerequisites: Azure TTS primary, gTTS fallback; Azurite optional
- Update "Last updated" date to 2026-05-28

### `docs/adr/004-paymongo-for-payments.md`

- Change `**Status:** Accepted` → `**Status:** Superseded by [ADR 006](006-xendit-for-payments.md)`

### `docs/adr/006-xendit-for-payments.md`

```
# ADR 006: Xendit for Subscription Payments (replaces PayMongo)

Status: Accepted
Date: 2026

## Context
PayMongo was replaced because Xendit was adopted as the primary PHP payment processor. PayMongo blueprint removed in full (commit `ad0ec96`). Need recurring subscriptions + GCash/Maya support in PHP.

## Decision
Use Xendit as the subscription payment processor with:
- api/utils/xendit_client.py — HTTP abstraction with retry + exponential backoff
- Recurring plan creation inside payment_session.completed webhook
- XENDIT_WEBHOOK_TOKEN for callback verification

## Reasons
- Xendit supports GCash, Maya, cards, OTC in Philippines
- Xendit's payment link + webhook model maps cleanly to subscription lifecycle
- HTTP abstraction (xendit_client.py) decouples retry logic from blueprint code

## Consequences
+ Retry/backoff centralized in xendit_client.py
+ Recurring plans created on webhook, not at checkout time
- XENDIT_WEBHOOK_TOKEN must be rotated if leaked; no HMAC — callback token only
- plan IDs stored as XENDIT_PLAN_* env vars (same pattern as PayMongo)
```

### `docs/ENV_VARS.md`

Sections:
1. Core (DB_CONNECTION_STRING, LOCAL_DB_CONNECTION_STRING)
2. Cache (REDIS_URL, REDIS_ENABLED)
3. Auth — Clerk (CLERK_SECRET_KEY, CLERK_JWKS_URL, CLERK_WEBHOOK_SECRET)
4. Payments — Xendit (XENDIT_SECRET_KEY, XENDIT_WEBHOOK_TOKEN, XENDIT_PLAN_*)
5. AI (GEMINI_API_KEY, GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, GEMINI_VERTEX_MODEL, GOOGLE_SERVICE_ACCOUNT_JSON / GOOGLE_APPLICATION_CREDENTIALS)
6. Azure Services (AZURE_STORAGE_CONNECTION_STRING, SPEECH_KEY, SPEECH_REGION, LEXPLAY_USE_AZURE_SPEECH)
7. Frontend / Vite (VITE_CLERK_PUBLISHABLE_KEY, VITE_API_BASE_URL)
8. Dev / Feature flags (TRIAL_ENABLED, PAYMONGO_BYPASS, REDIS_ENABLED, DB_POOL_MIN_CONN, DB_POOL_MAX_CONN)

Each row: variable | required | default | description

### `docs/API_ROUTES.md`

Route groups:
- Health (`GET /api/ping`, `GET /api/health_db`)
- Auth / Users (`POST /api/clerk-webhook`, `GET /api/user/subscription-status`, `POST /api/user/create-checkout`)
- SC Decisions (`GET /api/cases`, `GET /api/cases/{id}`, `GET /api/cases/{id}/digest`)
- Codex / Statutes (`GET /api/codex/rpc`, `GET /api/statutes`, etc.)
- Bar Questions (`GET /api/questions`, `GET /api/bar-questions`)
- Lexify (`GET/POST /api/lexify/*`)
- LexPlay / Audio (`GET /api/audio/{type}/{id}`, `GET /api/playlists/*`)
- BAR 2026 (`GET /api/bar-reviewer/*`)
- Payments — Xendit (`POST /api/xendit-webhook`, `POST /api/create-payment-session`)
- Admin / Ops (`GET /api/ops/pipeline/status`, `POST /api/ops/pipeline/start`, etc.)

Each row: method | path | auth | blueprint file | description

### `docs/features/bar2026-reviewer.md`

Sections:
1. What it is — BAR 2026 syllabus-aligned reviewer with linked SC cases
2. Data pipeline — `api/blueprints/bar_reviewer.py`, `LexCode/pipelines/`, eLib scraping
3. Syllabus alignment — how topics map to cases
4. Case linking — `brain/` AI linker, Gemini-based semantic linking
5. Annotation canvas — OffscreenCanvas + Web Worker thread, S Pen/pointer events, tool types (pen/highlighter/eraser), persistence model
6. Local dev — no special env vars; uses existing DB connection

### `docs/INDEX.md`

Three reader paths:
- **New contributor** → README → CONTRIBUTING → ENV_VARS → first PR checklist
- **Developer** → API_ROUTES → ADRs (001–006) → feature docs → RUNBOOK
- **Operator / DevOps** → RUNBOOK → ENV_VARS → ADRs

---

## Standards (best practice compliance)

All docs must:
- Use consistent heading hierarchy (H1 title, H2 sections, H3 subsections)
- Include a table of contents for docs longer than 3 sections
- Reference environment variables by exact name in backticks
- Reference file paths relative to repo root
- Not include resolved issues as open bugs
- Not reference removed systems (PayMongo, standalone PayMongo blueprint)
- Not include hardcoded credentials or example secrets
- Be dated (ADRs use year; feature docs use YYYY-MM-DD)

---

## Out of scope

- Database schema / ER diagram (DB is cloud-only; schema changes via migration scripts)
- Deployment runbook beyond what exists in RUNBOOK.md
- API authentication deep-dive (covered by ADR 002 + clerk_auth.py comments)
