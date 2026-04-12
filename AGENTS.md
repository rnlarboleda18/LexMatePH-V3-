# LexMatePH — agent instructions (universal)

This file is read by AI coding agents (Claude Code, OpenAI Codex, etc.).  
**Google Gemini CLI users**: see `GEMINI.md` (same content, same rules).  
**Cursor users**: `.cursor/rules/` files are loaded automatically.

---

## Stack

- **Frontend**: React 18, Vite, Tailwind, React Router — `src/frontend/`
- **API**: Azure Functions v2 Python 3.11 — `api/`
- **Database**: PostgreSQL — always use `DB_CONNECTION_STRING` (cloud). Never switch to local DB unless explicitly asked.
- **Cache**: Redis (`REDIS_URL`) — cache module at `api/cache.py`
- **Auth**: Clerk
- **Payments**: PayMongo
- **Hosting**: Azure Static Web Apps + GitHub Actions

---

## File placement (must follow)

| File type | Location |
|-----------|----------|
| HTTP route handlers | `api/blueprints/` + registered in `api/function_app.py` |
| Shared Python modules | `api/` root |
| Diagnostic / maintenance scripts | `api/tools/` |
| Historical fix scripts | `api/legacy/` |
| React components | `src/frontend/src/components/` |
| Custom React hooks | `src/frontend/src/hooks/` |
| Frontend tests | `src/frontend/src/test/` |
| General scripts | `scripts/` |
| ADRs | `docs/adr/` |

Never create backup copies of files. Never put non-route scripts in `api/blueprints/`.

---

## Mandatory checks before completing any task

```bash
# Frontend
cd src/frontend && npm run build   # must exit 0
cd src/frontend && npm run test    # must exit 0

# API
cd api && python -c "import function_app; print('ok')"  # must exit 0
```

---

## Core rules

**App.jsx stays thin** — new data-fetching logic belongs in a hook under `src/frontend/src/hooks/`.

**Thin blueprints** — HTTP handlers parse request, call shared helper, return response. No inline SQL.

**Structured logging** — use `from utils.logging import get_logger; log = get_logger(__name__, req)`.

**Debug endpoints gated** — check `ALLOW_DEBUG_ROUTES` env var; return 404 if not set.

**Webhooks** — verify signature, deduplicate via `webhook_events` table, never log raw PII payloads.

**Secrets** — never commit real credentials. New keys → `api/local.settings.sample.json` as empty placeholder.

**Documentation** — new decisions → `docs/adr/`, new scripts → README entry in `api/tools/` or `scripts/`.

---

## Reference docs

- Contributing guide: `CONTRIBUTING.md`
- Incident runbook: `docs/RUNBOOK.md`
- ADRs: `docs/adr/`
- API tools index: `api/tools/README.md`
- Legacy scripts: `api/legacy/README.md`
