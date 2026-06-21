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

**Frontend:**

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
| `RAG_REGION` | No | `europe-west4` | GCP region for RAG Engine corpus. |
| `GCP_SA_JSON_B64` | **Yes** (production AI) | — | Base64-encoded service account JSON. Preferred over `GCP_SA_JSON` — survives shell escaping in Azure Application Settings. |
| `GCP_SA_JSON` | No | — | Raw service account JSON string (fallback for local dev). |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | `lexmateph-rag-key.json` | Path to service account JSON file. Set automatically from `GCP_SA_JSON_B64` / `GCP_SA_JSON` at startup. |
| `GEMINI_PRO_MODEL` | No | `gemini-2.5-pro` | Vertex AI model for complex tasks (digest generation, grading). |
| `GEMINI_FLASH_MODEL` | No | `gemini-2.5-flash` | Vertex AI model for fast tasks. |
| `RAG_CORPUS_NAME` | No | — | Vertex AI RAG Engine corpus resource name. Set after corpus creation. |
| `COMPLEXITY_FLASH_MAX` | No | `0` | Complexity threshold (1–5). Requests ≤ this value use Flash; higher use Pro. `0` = always Pro. |
| `GCS_CORPUS_BUCKET` | No | `lexmateph-legal-corpus` | GCS bucket for legal corpus files. |

---

## Azure Services

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AZURE_STORAGE_CONNECTION_STRING` | No | `UseDevelopmentStorage=true` | Azure Blob Storage connection. Required for LexPlay audio caching. Use `UseDevelopmentStorage=true` locally (requires Azurite). |
| `SPEECH_KEY` | No | — | Azure Cognitive Services Speech key. If missing, LexPlay falls back to gTTS. |
| `SPEECH_REGION` | No | `japaneast` | Azure region for Speech service. |
| `LEXPLAY_USE_AZURE_SPEECH` | No | `false` | Set `1` / `true` to force Azure TTS. |

---

## Frontend (Vite)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_CLERK_PUBLISHABLE_KEY` | **Yes** | — | See Clerk section above. |
| `VITE_API_BASE_URL` | No | — | Base URL for API calls. Leave empty for same-origin `/api` (correct for SWA). Set to `http://localhost:7071` when running Vite and Functions separately without the SWA emulator. |

---

## Dev / Feature Flags

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | No | `production` | Set to `local` to enable local-dev mode. |
| `TRIAL_ENABLED` | No | — | Controls whether trial subscriptions are available. |
| `ADMIN_EMAILS` | No | — | Comma-separated admin email addresses. Fallback only — DB `is_admin` column is authoritative. |
| `ALLOW_DEBUG_ROUTES` | No | `false` | Set `1` to enable `GET /api/debug_imports`. Never enable in production. |
| `FRONTEND_URL` | No | `https://lexmateph.com` | Frontend origin for CORS and redirects. |
| `GUEST_FULL_ACCESS_HOURS` | No | `24` | Hours of full guest access before tier gating. |
| `RATE_LIMIT_GUEST` | No | `3` | AI questions per day for unauthenticated users. |
| `RATE_LIMIT_FREE` | No | `10` | AI questions per day for free-tier users. |
| `RATE_LIMIT_AMICUS` | No | `-1` | AI questions per day for Amicus subscribers (`-1` = unlimited). |
