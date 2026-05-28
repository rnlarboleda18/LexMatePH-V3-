# Favorites (Star) Feature — Design Spec
**Date:** 2026-05-28  
**Status:** Approved

## Overview

Add a star/favorite button to three content modals — case digest, bar question, and flashcard — allowing subscribers and admins to bookmark items for quick retrieval. Favorites are stored per user and accessible from a dedicated `/favorites` page.

---

## Access Control

- Available to **subscribers** (`subscription_status = 'active'`) and **admins** (`is_admin = true`) only.
- The star button is hidden entirely for non-subscribers (same `canAccess` pattern used by LexPlay in existing modals).
- Unauthenticated users never see the button.

---

## Data Layer

### New table: `user_favorites`

```sql
CREATE TABLE IF NOT EXISTS user_favorites (
    id           SERIAL PRIMARY KEY,
    user_id      VARCHAR(255) NOT NULL,
    content_type TEXT NOT NULL CHECK (content_type IN ('case', 'bar_question', 'flashcard')),
    content_id   TEXT NOT NULL,
    title        TEXT,
    subtitle     TEXT,
    created_at   TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, content_type, content_id)
);
CREATE INDEX ON user_favorites(user_id, content_type);
```

- `user_id` — Clerk ID string (matches all other user tables).
- `content_type` — one of `'case'`, `'bar_question'`, `'flashcard'`.
- `content_id` — the item's unique identifier:
  - Cases: GR number / case `id`
  - Bar questions: question `id`
  - Flashcards: card `id`
- `title` / `subtitle` — stored at save time (same pattern as `playlist_items`). Cases have no bulk-fetch endpoint so titles must be denormalized here. Bar questions and flashcards could look up from in-memory hooks but storing them keeps the favorites page simple and consistent.

---

## API — `api/blueprints/favorites.py`

All endpoints require a valid Clerk session token. All endpoints verify `is_admin OR subscription_status = 'active'` from the `users` table before proceeding (returns 403 otherwise).

Table creation is handled via an `_ensure_tables` guard on first request (same pattern as `playlists.py`).

| Method | Route | Body | Response |
|--------|-------|------|----------|
| `GET` | `/api/favorites/ids?type={content_type}` | — | `["id1", "id2", ...]` |
| `GET` | `/api/favorites?type={content_type}` | — | `[{content_type, content_id, created_at}, ...]` |
| `POST` | `/api/favorites` | `{content_type, content_id, title?, subtitle?}` | `{ok: true}` |
| `DELETE` | `/api/favorites` | `{content_type, content_id}` | `{ok: true}` |

- `GET /ids` returns only IDs — used on modal open to cheaply determine star state without fetching full metadata.
- `GET /favorites` returns full rows — used by the `/favorites` page to list saved items.
- POST is idempotent (insert or ignore on duplicate).
- DELETE is idempotent (no error if row doesn't exist).

Registered in `api/function_app.py` alongside existing blueprints.

---

## Frontend

### Hook: `src/frontend/src/hooks/useFavorites.js`

```js
const { isFavorited, toggleFavorite, loading } = useFavorites(contentType, contentId);
```

- On first call for a given `contentType`, fetches `/api/favorites/ids?type={contentType}` and stores the result in a module-level `Map<contentType, Set<contentId>>`.
- Subsequent calls for the same type use the cached set — no re-fetch on each modal open.
- `toggleFavorite()` updates the set optimistically, then calls POST or DELETE. Rolls back the optimistic update on network error.
- `loading` is `true` only during the initial fetch for a type.
- Cache is cleared on sign-out (listen to Clerk's `useAuth` `isSignedIn` going false).

### Star button — shared behavior across all surfaces

- Icon: `lucide-react` `Star` — filled + `text-yellow-400` when starred, outline + `text-gray-400` when not.
- Single tap toggles. No confirmation dialog.
- Rendered only when `canAccess('favorites')` is true (uses existing `useSubscription` hook).
- Position varies per surface (see below).

### `CaseDecisionModal.jsx`

Star button placed in the modal header row, to the left of the close (X) button. `Star` is already imported in this file.

### `QuestionDetailModal.jsx`

Star button placed in the modal header row, to the left of the close (X) button. Import `Star` from `lucide-react`.

### `Flashcard.jsx`

Star button placed on the card face alongside the existing LexPlay (headphones) button. Import `Star` from `lucide-react`.

### Favorites page: `src/frontend/src/components/Favorites.jsx`

- Route: `/favorites`
- Requires subscription (redirects or shows upgrade wall if not subscribed).
- Three tabs: **Cases · Bar Questions · Flashcards**.
- Each tab fetches `GET /api/favorites?type={type}` — the response includes `title` and `subtitle` stored at save time, so no secondary lookups are needed.
- Each card: title/subject, date favorited, click to reopen modal, star icon to un-favorite (removes from list immediately).
- Empty state per tab: "No favorites yet — star items while browsing."
- Linked from the sidebar nav.

---

## Error Handling

- Network error on toggle: roll back optimistic state, show a brief toast (`alert` is acceptable for now, consistent with existing modals).
- `/favorites` page load error: show inline error message with retry button.

---

## Out of Scope

- Sorting or filtering favorites beyond the three content-type tabs.
- Sharing favorites with other users.
- Favorites count or public-facing indicators.
- Free-tier favorites (subscribers only).
