# Admin tools

Operational documentation and entry points for **internal data and content pipelines** (not shipped Azure Function routes).

| Tool | Folder | Purpose |
|------|--------|---------|
| **Case digest pipeline** | [`case-digest-pipeline/`](./case-digest-pipeline/README.md) | How SC case text becomes `full_text_md` in Postgres and how AI digests are produced. |
| **Lexify Vertex on Azure** | [`configure_lexify_vertex_azure.ps1`](./configure_lexify_vertex_azure.ps1) | Push `GOOGLE_*` / `GEMINI_VERTEX_MODEL` / `GOOGLE_SERVICE_ACCOUNT_JSON` to the Static Web App via `az rest`. |

All runnable scripts remain in their canonical locations (`scripts/`, `scraper/`, etc.). This folder holds **maps and runbooks** so operators know which script to run and in what order.
