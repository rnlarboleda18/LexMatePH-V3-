# LexMatePH v3 — Claude Cheat Sheet

## What this project is
**Codex Philippines** — an AI-powered Philippine legal research platform. Users search statutes, jurisprudence, and codified law; the AI links related provisions and generates digests.

## Infrastructure
| Layer | Technology |
|---|---|
| Frontend | React 19, Next.js 16, TypeScript, Tailwind CSS 4 |
| Backend API | Python (Flask blueprints), Azure Functions |
| Database | PostgreSQL (primary), SQLite (local dev) |
| AI Engine | Google Gemini API (legal linking & digest generation) |
| Auth | Clerk (webhooks for user sync) |
| Payments | Xendit + PayMongo (subscription billing, PHP) |
| Deployment | Azure Static Web Apps (managed backend — `api/` is SWA-managed Functions) |
| Dev tooling | swa-cli (local SWA emulation) |

## Project layout
```
api/               Main Flask API
  blueprints/      Route modules (auth, search, payments, …)
  brain/           AI linking engine
  utils/           Shared helpers
LexCode/           Data ingestion pipeline
  pipelines/       Ingestion & processing scripts
  scripts/         AI linking, utilities
  Codals/          Raw legal corpus (large — excluded from Claude context)
src/
  backend/         Core backend modules
  frontend/        Public-facing Next.js app
scraper/           Web scrapers for legal sources
docs/              Architecture & planning docs
```

## Key conventions
- **Currency**: PHP (Philippine Peso). Subscription price is PHP 299/month (Amicus plan).
- **Subscription states**: `active`, `past_due`, `cancelled`, `trialing`.
- **Trial**: Controlled by `TRIAL_ENABLED` flag in the API.
- **Cancellation**: Paid access continues until end of billing period; past-due banner shown after grace period.
- **Recurring plans**: Created inside `payment_session.completed` webhook (Xendit).

## Files Claude should focus on
- `api/` — all Python source
- `src/` — frontend + backend source
- `LexCode/pipelines/`, `LexCode/scripts/` — data pipeline logic

## Files Claude should ignore
See `.claudeignore`. Key exclusions: `node_modules/`, `.venv/`, `LexCode/Codals/` (raw corpus), `data/`, root diagnostic scripts.
