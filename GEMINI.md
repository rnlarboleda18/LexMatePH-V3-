# LexMatePH — Gemini CLI agent instructions

Read this file fully before making any change to this repository.

---

## Stack

- **Frontend**: React 18, Vite, Tailwind, React Router — `src/frontend/`
- **API**: Azure Functions v2 Python 3.11 — `api/`
- **Database**: PostgreSQL on Azure — always `DB_CONNECTION_STRING` (cloud). Never switch to local DB unless the user explicitly asks.
- **Cache**: Redis (`REDIS_URL`)
- **Auth**: Clerk (`CLERK_*` env vars)
- **Payments**: PayMongo (`PAYMONGO_*` env vars)
- **Hosting**: Azure Static Web Apps + GitHub Actions CI

---

## File placement (hard rules — do not deviate)

| File type | Correct location |
|-----------|-----------------|
| Azure Functions HTTP handlers | `api/blueprints/` — must be registered in `api/function_app.py` |
| Shared Python modules | `api/` root (`config.py`, `cache.py`, `db_pool.py`, etc.) |
| Maintenance / diagnostic scripts | `api/tools/` (see `api/tools/README.md`) |
| Historical one-off fixes | `api/legacy/` |
| React components | `src/frontend/src/components/` |
| Custom hooks (`use*`) | `src/frontend/src/hooks/` |
| Feature modules | `src/frontend/src/features/<name>/` |
| Utilities | `src/frontend/src/utils/` |
| Frontend unit tests | `src/frontend/src/test/` |
| Maintenance scripts | `scripts/` |
| Architecture decisions | `docs/adr/NNN-title.md` |
| Incident playbooks | `docs/RUNBOOK.md` |

**Never** place non-route scripts in `api/blueprints/`. **Never** add Python, SQL, or non-JS files to `src/frontend/src/`. **Never** create backup file copies (e.g. `foo_backup.py`) — use Git branches instead.

---

## Before finishing any task

1. `npm run build` in `src/frontend/` must exit 0.
2. `npm run test` in `src/frontend/` must exit 0 (8 tests minimum; add tests for new hooks).
3. `python -c "import function_app"` in `api/` must exit 0.

---

## App.jsx — keep thin

Do **not** add new data-fetching `useEffect` blocks to `App.jsx`. Create a hook in `src/frontend/src/hooks/` and import it.

---

## New API blueprint

1. Create `api/blueprints/my_feature.py` with a `my_feature_bp = func.Blueprint()`.
2. Register in `api/function_app.py`.
3. Keep handler thin: parse → call helper → return response.
4. Use structured logging:
   ```python
   from utils.logging import get_logger
   log = get_logger(__name__, req)
   log.info("doing work")
   ```

---

## Debug endpoints

Any endpoint that exposes internal state must check:
```python
if os.environ.get("ALLOW_DEBUG_ROUTES", "").lower() not in ("1", "true", "yes"):
    return func.HttpResponse("Not found.", status_code=404)
```

---

## Webhooks (Clerk, PayMongo)

Every inbound webhook route must:
- Verify HMAC / Svix signature before reading the body.
- Deduplicate via `webhook_events` table (`INSERT … ON CONFLICT DO NOTHING`).
- Never log raw payloads that may contain PII.

---

## Secrets — never commit

Do not commit: `api/local.settings.json`, `src/frontend/.env.local`, `src/frontend/.env.production`, any key containing a password or API secret.
New required keys → add placeholder entry to `api/local.settings.sample.json`.

---

## Adding new maintenance tools

- New diagnostic Python scripts → `api/tools/` with an entry in `api/tools/README.md`.
- New architectural decisions → `docs/adr/NNN-title.md`.
- New incident patterns → `docs/RUNBOOK.md`.

---

## CI (GitHub Actions)

- `quality_gates` job runs before deploy and is blocking.
- Do not add `continue-on-error: true` to build, test, or smoke-test steps.
- Ruff lint on `api/` and ESLint on `src/frontend/` are advisory (non-blocking) until backlogs are cleared.
