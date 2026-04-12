# Contributing to LexMatePH

## Stack at a glance

| Layer | Technology | Path |
|-------|-----------|------|
| Frontend SPA + PWA | React 18, Vite, Tailwind | `src/frontend/` |
| API | Azure Functions v2 (Python 3.11) | `api/` |
| Database | PostgreSQL on Azure (cloud by default) | `DB_CONNECTION_STRING` |
| Cache | Redis (Azure Cache for Redis) | `REDIS_URL` |
| Auth | Clerk | `CLERK_*` env vars |
| Payments | PayMongo | `PAYMONGO_*` env vars |
| Hosting | Azure Static Web Apps | `.github/workflows/` |

---

## Local development

### 1. Clone and install

```powershell
git clone <repo>
cd "LexMatePH v3"

# Backend (Python)
cd api
python -m venv .venv
.venv\Scripts\Activate
pip install -r requirements.txt

# Frontend
cd ..\src\frontend
npm install
```

### 2. Configure environment

```powershell
# API — copy sample and fill in cloud credentials
cp api/local.settings.sample.json api/local.settings.json
# Edit api/local.settings.json: DB_CONNECTION_STRING, CLERK_*, PAYMONGO_*, etc.

# Frontend
cp src/frontend/.env.example src/frontend/.env.local
# Edit .env.local: VITE_CLERK_PUBLISHABLE_KEY=pk_test_...
```

### 3. Start both servers

```powershell
# From repo root
./start_all.ps1
```

Or separately:

```powershell
# Terminal 1 — API (port 7071)
cd api
func start

# Terminal 2 — Frontend (port 5173)
cd src/frontend
npm run dev
```

The Vite dev server proxies `/api/*` to `http://127.0.0.1:7071` (see `vite.config.js`).  
Open: http://localhost:5173

---

## Where files belong

| What | Where |
|------|-------|
| HTTP route handlers | `api/blueprints/` — **must** be registered in `api/function_app.py` |
| Shared Python modules | `api/` root (`config.py`, `cache.py`, `db_pool.py`, `codal_text.py`, `codal_structural.py`) |
| Maintenance / diagnostic scripts | `api/tools/` (see `api/tools/README.md`) |
| Historical one-off fixes | `api/legacy/` (see `api/legacy/README.md`) |
| Frontend components | `src/frontend/src/components/` |
| Custom hooks | `src/frontend/src/hooks/` |
| Feature folders | `src/frontend/src/features/` |
| Utility functions | `src/frontend/src/utils/` |
| Frontend tests | `src/frontend/src/test/` |
| Database migration scripts | `scripts/` |
| Architecture decisions | `docs/adr/` |

**Do not** commit:
- `api/local.settings.json`, `src/frontend/.env.local`, `src/frontend/.env.production`
- Database credentials, API keys, or secrets of any kind (see `api/local.settings.sample.json`)

---

## Adding a blueprint (API route)

1. Create `api/blueprints/my_feature.py`:

```python
import azure.functions as func

my_feature_bp = func.Blueprint()

@my_feature_bp.route(route="my-endpoint", methods=["GET"])
def my_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("Hello", status_code=200)
```

2. Register in `api/function_app.py`:

```python
from blueprints.my_feature import my_feature_bp
app.register_functions(my_feature_bp)
```

3. Keep the blueprint **thin**: parse request → call helpers in `services/` or shared modules → return response.

---

## Running tests

```powershell
# Frontend
cd src/frontend
npm run test          # run once
npm run test:watch    # watch mode
npm run test:ui       # browser UI

# Lint
npm run lint

# API import check
cd api
python -c "import function_app; print('ok')"
```

---

## Branch and PR expectations

- Branch from `main`. Suggested naming: `feat/`, `fix/`, `chore/`.
- CI runs **quality gates** (build, tests, API smoke) before deploy. PRs must pass the `quality_gates` job.
- ESLint is advisory until the backlog is cleared — do fix issues in files you touch.
- Do not commit secrets; rotate any accidentally committed key immediately.

---

## Database

Always work against the **cloud** PostgreSQL instance unless you explicitly need local DB.  
See `.cursor/rules/database-cloud-default.mdc` for the workspace rule.

New migrations go in `scripts/` as plain SQL files or Python scripts following the pattern in `api/tools/run_migration.py`.

---

## Disclaimer

LexMatePH uses AI-assisted digests. All content is for educational purposes only and does not constitute legal advice.
