# BAR 2026 Reviewer — Feature Documentation

**Last updated:** 2026-05-28

The BAR 2026 Reviewer is a syllabus-aligned study tool that lets bar examinees browse topics by subject, read linked Supreme Court cases, and annotate pages directly with a stylus or finger.

---

## Table of Contents

1. [Feature Overview](#1-feature-overview)
2. [Data Pipeline](#2-data-pipeline)
3. [Syllabus Alignment](#3-syllabus-alignment)
4. [Case Linking](#4-case-linking)
5. [Annotation Canvas](#5-annotation-canvas)
6. [API Routes](#6-api-routes)
7. [Local Development](#7-local-development)

---

## 1. Feature Overview

| Capability | Status |
|-----------|--------|
| Subject browser (Civil, Criminal, Labor, etc.) | ✅ Implemented |
| Syllabus-aligned topic list per subject | ✅ Implemented |
| Linked SC cases per topic | ✅ Implemented |
| Case digest view from reviewer | ✅ Implemented |
| Page annotation (pen, highlighter, eraser) | ✅ Implemented |
| Annotation persistence per page | ✅ Implemented |
| S Pen / stylus optimised input | ✅ Implemented |

---

## 2. Data Pipeline

The reviewer content is built by a multi-stage pipeline run from **Admin → Digest Pipeline**:

```
eLib scraper
    └── scripts/elib_digest_pipeline.py
        ├── Scrapes SC E-Library for new decisions
        ├── Generates AI digests (Gemini via Vertex AI)
        └── Inserts into sc_decided_cases (PostgreSQL)

Syllabus alignment
    └── LexCode/pipelines/
        └── Maps sc_decided_cases to BAR 2026 TOS subjects/topics

Case linker
    └── api/brain/
        └── Gemini-based semantic linking: codal provisions ↔ cases
```

The pipeline runs **locally** (workstation + cloud DB). See `docs/RUNBOOK.md` § Admin Digest Pipeline for operations.

---

## 3. Syllabus Alignment

Topics are aligned to the 2026 Bar Examination Table of Specifications (TOS). Each topic has:

- `subject` — one of the eight bar subjects (Civil Law, Criminal Law, Labor Law, Political Law, Commercial Law, Remedial Law, Legal Ethics, Taxation)
- `topic_id` — stable identifier used in URLs
- `title` — the TOS topic name
- `linked_cases` — SC decisions linked to this topic

Alignment scores are stored in `sc_decided_cases`. The `FLASHCARD_BAR_MIN_TOS_SCORE` env var sets the minimum score for inclusion in the default flashcard deck.

---

## 4. Case Linking

AI-powered semantic linking is run by `api/brain/` using Gemini (Vertex AI):

1. Each SC decision digest is embedded.
2. Each BAR 2026 topic/provision is embedded.
3. Cosine similarity identifies semantically related case-provision pairs.
4. High-confidence links are stored and surfaced in the reviewer UI.

Linking runs as part of the admin pipeline. See `scripts/README.md` for the unified linker script.

---

## 5. Annotation Canvas

Page annotations are drawn on an HTML5 Canvas overlaid on the reviewer content.

### Architecture

```
Bar2026.jsx
    └── AnnotationCanvas.jsx
            ├── Renders on <canvas> element (direct 2D Context)
            ├── Listens to pointer events (pen, touch, mouse)
            └── Persists strokes via useAnnotations.js → API (Clerk auth)
```

### Drawing tools

- **Pen** — smooth Catmull-Rom cubic Bézier curves with EMA smoothing for natural stroke feel.
- **Highlighter** — semi-transparent overlay; opacity is non-stacking (applied at render time, not per-event).
- **Eraser** — removes stroke segments by proximity.

### S Pen / stylus optimisation

- `pointerrawupdate` events used for hardware-rate input on Samsung Galaxy Tab and similar devices.
- Strokes drawn immediately on `pointermove` (no rAF delay).
- `passive: false` on pointer listeners to prevent scroll interference.

### Persistence

- Strokes are saved per-page to `sc_annotation_strokes` in PostgreSQL.
- A debounce fires on navigation away to flush unsaved strokes.
- Clerk JWT (Bearer token) is sent with save requests — not cookies.

### Toolbar

The annotation toolbar is pinned to the **left side** of the screen. Tools: pen, highlighter, eraser; color pickers per tool; size options.

---

## 6. API Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/reviewer/{subject}` | Topic list for a subject |
| GET | `/api/reviewer/{subject}/{topic_id}` | Topic detail with linked cases |
| GET/POST | `/api/reviewer/generate` | AI-generate reviewer content |
| POST | `/api/reviewer/publish` | Publish generated content (admin) |
| POST | `/api/reviewer/flag` | Flag content for review |
| GET | `/api/reviewer/gen/log` | Generation log (admin) |

See `docs/API_ROUTES.md` for full details including annotation routes.

---

## 7. Local Development

No additional environment variables are required beyond the standard database connection:

```json
{
  "Values": {
    "DB_CONNECTION_STRING": "postgresql://user:pass@host:5432/lexmateph-ea-db?sslmode=require"
  }
}
```

The reviewer reads from the cloud PostgreSQL instance like all other features. To populate reviewer content locally, run the digest pipeline from **Admin → Digest Pipeline** (requires `func start` with cloud DB).

**Key source files:**

| File | Purpose |
|------|---------|
| `api/blueprints/bar_reviewer.py` | API route handlers |
| `src/frontend/src/components/Bar2026.jsx` | Main reviewer UI component |
| `src/frontend/src/components/AnnotationCanvas.jsx` | Canvas overlay and drawing logic |
| `src/frontend/src/hooks/useAnnotations.js` | Annotation state, persistence, debounce |
| `LexCode/pipelines/` | Syllabus alignment pipeline scripts |
| `api/brain/` | AI case linker |
