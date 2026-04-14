# Admin tools

Operational documentation and entry points for **internal data and content pipelines** (not shipped Azure Function routes).

| Tool | Folder | Purpose |
|------|--------|---------|
| **Case digest pipeline** | [`case-digest-pipeline/`](./case-digest-pipeline/README.md) | How SC case text becomes `full_text_md` in Postgres and how AI digests are produced. |

All runnable scripts remain in their canonical locations (`scripts/`, `scraper/`, etc.). This folder holds **maps and runbooks** so operators know which script to run and in what order.
