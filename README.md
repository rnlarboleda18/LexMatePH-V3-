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

Single plan: **Amicus** at PHP 299/month. Payments via Xendit (GCash, Maya, or card). Free tier available with usage limits.

## Disclaimer

Study tools are for educational purposes only. Not legal advice. Not affiliated with the Supreme Court of the Philippines or the Office of the Bar Confidant.
