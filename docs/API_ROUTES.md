# API Routes Reference

All routes are prefixed with `/api/` in the deployed app (Azure SWA + Functions). Auth column shows whether a valid Clerk JWT is required.

---

## Health

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| GET | `/api/ping` | No | `function_app.py` | Returns `pong`. Liveness probe. |
| GET | `/api/health` | No | `function_app.py` | Returns `OK`. |
| GET | `/api/health_db` | No | `function_app.py` | Tests PostgreSQL connectivity. Returns 500 on failure. |
| GET | `/api/debug_imports` | No* | `function_app.py` | Blueprint import diagnostics. Only active when `ALLOW_DEBUG_ROUTES=1`. |

---

## Auth / Clerk

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| POST | `/api/clerk-webhook` | Svix sig | `clerk_webhook.py` | Receives `user.created` / `user.updated` / `user.deleted` events from Clerk. Upserts `users` row. |
| POST | `/api/clerk_webhook` | Svix sig | `clerk_webhook.py` | Alias for `/api/clerk-webhook` (hyphen vs underscore). Same handler. |
| POST | `/api/register` | No | `auth_custom.py` | Custom registration flow. |
| POST | `/api/login` | No | `auth_custom.py` | Custom login flow. |

---

## Users

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| GET | `/api/history` | Yes | `user.py` | Returns search/view history for the authenticated user. |

---

## Subscription / Payments (Xendit)

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| GET | `/api/subscription-status` | Yes | `xendit.py` | Returns current subscription tier, status, and expiry for the authenticated user. |
| POST | `/api/create-checkout` | Yes | `xendit.py` | Creates a Xendit payment link for the Amicus plan. Returns checkout URL. |
| POST | `/api/cancel-subscription` | Yes | `xendit.py` | Cancels the active Xendit recurring subscription. Paid access continues to period end. |
| POST | `/api/track-usage` | Yes | `xendit.py` | Increments usage counter for free-tier gating. |
| GET | `/api/available-plans` | No | `xendit.py` | Returns available subscription plans and pricing. |
| POST | `/api/xendit-webhook` | Token | `xendit.py` | Receives Xendit payment lifecycle events. Verified via `x-callback-token` header matching `XENDIT_WEBHOOK_TOKEN`. Creates recurring plans on `payment_session.completed`. |

---

## SC Decisions

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| GET | `/api/sc_decisions` | No | `supreme.py` | List / search Supreme Court decisions. Supports `q`, `subject`, `year`, `ponente`, `page`, `limit` query params. Redis-cached (60 s TTL). |
| GET | `/api/sc_decisions/{id}` | No | `supreme.py` | Get a single decision by integer ID. Redis-cached (600 s). |
| GET | `/api/sc_decisions/ponentes` | No | `supreme.py` | List all ponentes for filter UI. Redis-cached (300 s). |
| GET | `/api/sc_decisions/divisions` | No | `supreme.py` | List SC divisions. Redis-cached (300 s). |
| GET | `/api/sc_decisions/models` | No | `supreme.py` | Returns model/schema metadata. |
| GET | `/api/sc_decisions/flashcard_concepts` | No | `supreme.py` | Returns flashcard concept list. Redis-cached (24 h, key versioned via `FLASHCARD_CONCEPTS_CACHE_KEY`). |
| GET | `/api/sc_judiciary_feed` | No | `supreme.py` | Proxied SC Judiciary RSS feed. Redis-cached (900 s). |
| GET | `/api/fc/all` | No | `const.py` | Full-context case list for linking. |

---

## Codex / Statutes / Codals

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| GET | `/api/codex/issuance` | No | `codex.py` | Fetches a statute by issuance identifier. |
| GET | `/api/codex/jurisprudence` | No | `codex.py` | Returns jurisprudence linked to a codal provision. |
| GET | `/api/codex/amendments` | No | `codex.py` | Returns amendment history for a provision. |
| GET | `/api/codex/versions` | No | `codex.py` | Returns version history. |
| GET | `/api/statutes` | No | `statutes.py` | Full-text statute search with ILIKE. Input length limited. |
| GET | `/api/rpc/article/{article_num}` | No | `rpc.py` | Revised Penal Code article by number. |
| GET | `/api/rpc/book/{book_num}` | No | `rpc.py` | RPC book. |
| GET | `/api/rpc/title/{title_num}` | No | `rpc.py` | RPC title. |
| GET | `/api/civ/article/{article_num}` | No | `civ.py` | Civil Code article. |
| GET | `/api/civ/book/{book_num}` | No | `civ.py` | Civil Code book. |
| GET | `/api/civ/title/{title_num}` | No | `civ.py` | Civil Code title. |
| GET | `/api/civ/preliminary` | No | `civ.py` | Civil Code preliminary title. |
| GET | `/api/const/book/{book_num}` | No | `const.py` | Constitution section/article. |
| GET | `/api/labor/books` | No | `labor.py` | Labor Code — all books. |
| GET | `/api/labor/books/{book_id}` | No | `labor.py` | Labor Code book by ID. |
| GET | `/api/roc/all` | No | `roc.py` | Rules of Court — all rules. |
| GET | `/api/roc/book/{book_num}` | No | `roc.py` | Rules of Court book. |

---

## Bar Questions

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| GET | `/api/questions` | No | `questions.py` | Paginated bar questions. Supports `subject`, `year`, `limit` (input-validated). |

---

## BAR 2026 Reviewer

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| GET | `/api/reviewer/{subject}` | No | `bar_reviewer.py` | Topics list for a BAR 2026 subject (e.g. `civil-law`, `criminal-law`). |
| GET | `/api/reviewer/{subject}/{topic_id}` | No | `bar_reviewer.py` | Single topic detail with linked SC cases. |
| GET/POST | `/api/reviewer/generate` | No | `bar_reviewer.py` | AI-generated reviewer content for a topic. |
| POST | `/api/reviewer/publish` | No | `bar_reviewer.py` | Publish generated reviewer content (admin). |
| POST | `/api/reviewer/flag` | No | `bar_reviewer.py` | Flag reviewer content for review. |
| GET | `/api/reviewer/gen/log` | No | `bar_reviewer.py` | Generation log for admin monitoring. |
| GET/PUT/DELETE | `/api/reviewer/{subject}/{topic_id}/annotations` | No | `bar_reviewer.py` | Per-user per-topic ink annotations (S Pen / Apple Pencil). |

---

## Lexify (Mock Exams)

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| GET | `/api/lexify_exams` | Yes | `questions.py` | Available mock exam papers. |
| GET | `/api/lexify_questions` | Yes | `questions.py` | Questions for a given exam. Supports `limit` (input-validated). |
| POST | `/api/lexify_grade` | Yes | `lexify.py` | Grade a single Lexify answer via Vertex AI. |
| POST | `/api/lexify_grade_batch` | Yes | `lexify.py` | Batch grading for a full exam submission. |

---

## LexPlay / Audio

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| GET | `/api/audio/{content_type}/{content_id}` | No | `audio_provider.py` | Generate or serve cached TTS audio. `content_type`: `codal` or `case`. Returns JSON `{url, cached: true}` on cache hit; raw `audio/mpeg` bytes on miss. |
| GET | `/api/lexplay/state` | Yes | `playlists.py` | Returns saved LexPlay playback state for authenticated user. |
| POST | `/api/lexplay/state` | Yes | `playlists.py` | Saves LexPlay playback state for authenticated user. |
| GET | `/api/playlists` | Yes | `playlists.py` | List user's saved playlists. |
| POST | `/api/playlists` | Yes | `playlists.py` | Create a new playlist. |
| GET | `/api/playlists/{playlist_id}` | Yes | `playlists.py` | Get a playlist with items. |
| PUT | `/api/playlists/{playlist_id}` | Yes | `playlists.py` | Update playlist metadata. |
| DELETE | `/api/playlists/{playlist_id}` | Yes | `playlists.py` | Delete a playlist. |
| GET | `/api/playlists/{playlist_id}/items` | Yes | `playlists.py` | List items in a playlist. |
| POST | `/api/playlists/{playlist_id}/items` | Yes | `playlists.py` | Add item to playlist. |
| DELETE | `/api/playlists/{playlist_id}/items/{item_id}` | Yes | `playlists.py` | Remove item from playlist. |
| POST | `/api/playlists/{playlist_id}/bulk_items` | Yes | `playlists.py` | Bulk add items. |

---

## AI Features

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| POST | `/api/ai-search` | Yes | `ai_search.py` | AI-powered semantic search over cases and statutes. Rate-limited by tier. |
| POST | `/api/legal-chat` | Yes | `legal_chat.py` | RAG-backed legal Q&A. Rate-limited by tier (`RATE_LIMIT_*`). Semantically cached (7-day TTL). |
| POST | `/api/legal-chat-clear` | Yes | `legal_chat.py` | Clear user's legal chat session. |
| GET | `/api/legal-chat-status` | Yes | `legal_chat.py` | Returns rate limit and session status. |
| POST | `/api/ai/digest/{id}` | Admin | `ai_processor.py` | Generate AI digest for a case. |
| POST | `/api/ai/mock-exam/{id}` | Admin | `ai_processor.py` | Generate mock exam questions from a case. |
| POST | `/api/ai/clean/{id}` | Admin | `ai_processor.py` | Clean/normalize case text. |
| POST | `/api/ai/tts` | Admin | `ai_processor.py` | Generate TTS spoken script for a case. |

---

## Admin / Ops

All `/api/ops/*` routes require admin authentication. Available only when the Functions host is running with admin blueprints loaded.

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| GET | `/api/ops/pipeline/status` | Admin | `admin_pipeline.py` | Returns pipeline progress from `pipeline_progress.json`. |
| POST | `/api/ops/pipeline/start` | Admin | `admin_pipeline.py` | Start a full eLib digest pipeline run. |
| POST | `/api/ops/pipeline/resume` | Admin | `admin_pipeline.py` | Resume an interrupted pipeline run. |
| POST | `/api/ops/pipeline/stop` | Admin | `admin_pipeline.py` | Stop the running pipeline. |
| POST | `/api/ops/pipeline/scan` | Admin | `admin_pipeline.py` | Scan eLib for new decisions without digesting. |
| GET | `/api/ops/pipeline/scan-results` | Admin | `admin_pipeline.py` | Results of last scan. |
| POST | `/api/ops/pipeline/scan-gaps` | Admin | `admin_pipeline.py` | Scan for cases with missing digests. |
| GET | `/api/ops/pipeline/gap-results` | Admin | `admin_pipeline.py` | Results of gap scan. |
| POST | `/api/ops/pipeline/stop-gap-scan` | Admin | `admin_pipeline.py` | Stop gap scan. |
| GET | `/api/ops/pipeline-stats` | Admin | `admin_pipeline.py` | Pipeline statistics. |
| GET | `/api/ops/db-stats` | Admin | `admin.py` | Database row counts and size metrics. |
| GET | `/api/ops/observations` | Admin | `admin_metrics.py` | Observation log entries. |
| POST | `/api/ops/observations` | Admin | `admin_metrics.py` | Create a new observation log entry. |
| DELETE | `/api/ops/observations/{obs_id}` | Admin | `admin_metrics.py` | Delete a single observation. |
| GET | `/api/ops/azure-metrics` | Admin | `admin_metrics.py` | Azure Functions invocation metrics. |
| POST | `/api/ops/backup/start` | Admin | `admin_backup.py` | Trigger a cloud database backup (pg_dump). |
| GET | `/api/ops/backup/status` | Admin | `admin_backup.py` | Backup progress and last run status. |
| GET | `/api/ops/backup/download` | Admin | `admin_backup.py` | Download the latest backup file. |
| POST | `/api/backfill_per_curiam` | Admin | `supreme.py` | Backfill per curiam fields on cases. |
| POST | `/api/fix_ponentes` | Admin | `supreme.py` | Fix ponente normalisation. |

---

## Other

| Method | Path | Auth | Blueprint | Description |
|--------|------|------|-----------|-------------|
| GET | `/api/schedule` | Yes | `schedule.py` | Returns scheduled content or user schedule state. |
| GET | `/api/sitemap_decisions.xml` | No | `sitemap.py` | XML sitemap of SC decisions for SEO. |
| GET | `/api/decision_page/{case_id}` | No | `decision_page.py` | SSR-friendly decision page data for a case (used for social/SEO previews). |
