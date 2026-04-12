# LexMatePH Operations Runbook

Quick reference for diagnosing and resolving common production incidents.

---

## 1. Database connection failures

**Symptoms:** 500 errors on any API endpoint; `Database connection failed` in logs.

**Steps:**

1. Check `/api/health_db` — if it returns 500, confirm Azure PostgreSQL is reachable.
2. Verify `DB_CONNECTION_STRING` is set in Azure Functions Application Settings (Azure Portal → Function App → Configuration → Application settings).
3. Check the PostgreSQL **firewall rules** — Azure Functions outbound IPs change; use "Allow Azure services" option or update IP allowlist.
4. Check SSL: connection string must include `?sslmode=require`.
5. Check `max_connections` on the DB — if exhausted, connections queue or fail. Consider increasing the pool size limit in `api/db_pool.py`.

**Emergency:** If DB is down and you need the app to degrade gracefully, the frontend will show a "Data Load Failed" error on the bar questions section; other features (LexPlay audio cache, codal content) may still work from Redis/Blob cache.

---

## 2. Redis / cache unavailability

**Symptoms:** Slow responses (300–3000 ms instead of <100 ms); no visible errors.

**Steps:**

1. Confirm `REDIS_ENABLED` is not set to `false` in Application Settings.
2. Check Azure Cache for Redis **connection strings** and SSL port (6380 for TLS).
3. Redis URL format: `rediss://:<password>@<host>:6380` (note: `rediss://` for TLS).
4. `api/cache.py` fails silently on Redis errors and falls back to direct DB. No user-visible error is expected.

**Invalidate flashcard cache manually:**

```powershell
# From api/ directory with DB_CONNECTION_STRING set
python -c "
from cache import get_redis_client, cache_delete
from config import FLASHCARD_CONCEPTS_CACHE_KEY
client = get_redis_client()
if client: client.delete(FLASHCARD_CONCEPTS_CACHE_KEY)
print('Deleted', FLASHCARD_CONCEPTS_CACHE_KEY)
"
```

Or bump `FLASHCARD_CONCEPTS_CACHE_KEY` in Application Settings (e.g. `flashcard_concepts:v12:bar_2026`) to force all workers to use a new key.

---

## 3. Audio (LexPlay) not generating / serving

**Symptoms:** LexPlay shows "No audio" or loading spinner indefinitely.

**Steps:**

1. Check `AZURE_STORAGE_CONNECTION_STRING` in Application Settings — Blob Storage is used for audio caching.
2. Check `SPEECH_KEY` and `SPEECH_REGION` if Azure Speech TTS is enabled (`LEXPLAY_USE_AZURE_SPEECH=1`).
3. Check Azure Speech F0 tier concurrent synthesis limit: only 1 concurrent real-time request is allowed. High traffic causes 429s; the API falls back to Edge TTS.
4. If the `lexplay-audio-cache` container is missing in Blob Storage, the API will create it on first use.
5. Use `/api/health_db` and check logs in Azure Monitor → Log Analytics.

**Cache version bump** (forces new audio generation for all content):

In `api/blueprints/audio_provider.py`, increment `CACHE_VERSION` (e.g. `"v23"` → `"v24"`) and redeploy.

---

## 4. Subscription not activating after payment

**Symptoms:** User paid on PayMongo but their account still shows Free tier.

**Steps:**

1. Check PayMongo Dashboard → Webhooks → delivery logs for the event.
2. If webhook delivery failed, manually re-trigger from PayMongo Dashboard.
3. Check Azure Functions logs for the `paymongo-webhook` route — look for signature verification failures.
4. Check `PAYMONGO_WEBHOOK_SECRET` in Application Settings — it must match the webhook signing secret in PayMongo Dashboard.
5. The idempotency check: re-delivered events with the same `event_id` are safe to re-process (the handler is idempotent on subscription status).
6. Manual tier grant (admin only):

```sql
UPDATE users
SET subscription_tier = 'amicus',
    subscription_status = 'active',
    subscription_source = 'manual_admin',
    subscription_expires_at = NOW() + INTERVAL '1 year'
WHERE clerk_id = '<clerk_id>';
```

---

## 5. Clerk webhook not syncing users

**Symptoms:** New users can sign up but are not in the database; subscription features not available.

**Steps:**

1. Check Clerk Dashboard → Webhooks → delivery logs.
2. Verify `CLERK_WEBHOOK_SECRET` in Application Settings matches the webhook signing secret in Clerk Dashboard.
3. The handler at `api/blueprints/clerk_webhook.py` verifies the Svix HMAC signature — a wrong secret returns 400.
4. Check Clerk webhook endpoint URL is set to `https://<your-app>/api/clerk-webhook` (hyphen variant).

---

## 6. Ruff / CI failing after API changes

**Steps:**

1. Install Ruff locally: `pip install ruff`
2. Run: `ruff check api/ --ignore E501,F401`
3. Auto-fix safe issues: `ruff check api/ --fix`

---

## 7. Deploy stuck or deploy job failed

**Steps:**

1. Check GitHub Actions → the `quality_gates` job runs before `build_and_deploy_job` — if gates fail, deploy does not start.
2. Common gate failure: `npm run build` fails due to missing env var in CI (check `VITE_CLERK_PUBLISHABLE_KEY` in repo secrets).
3. Azure SWA deploy token: if it expires, re-download from Azure Portal → Static Web App → Manage deployment token → regenerate, then update `AZURE_STATIC_WEB_APPS_API_TOKEN_CALM_DUNE_0466B8110` in repo secrets.

---

## 8. Who to contact

This is a solo / small-team project. For production incidents, the developer can be reached via the contact information in the repo or organization settings.
