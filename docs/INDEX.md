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
