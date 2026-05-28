# Favorites (Star) Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-user star/favorite button to the case digest modal, bar question modal, and flashcard card, with a `/favorites` page showing all saved items in three tabs.

**Architecture:** A new `favorites.py` API blueprint handles four REST endpoints and a lazily-created `user_favorites` table (subscriber/admin gated). A `useFavorites` hook with module-level cache drives optimistic toggling in all three content surfaces. A new `Favorites.jsx` page wired into the existing mode-based SPA router shows saved items by content type.

**Tech Stack:** Python / Azure Functions (backend), React 19 + Vite + Vitest + React Testing Library (frontend), PostgreSQL via psycopg2 connection pool, Clerk JWT auth, lucide-react `Star` icon, Tailwind CSS 4.

---

## File Map

**Create:**
- `api/blueprints/favorites.py` — 4 REST endpoints + table DDL guard
- `src/frontend/src/hooks/useFavorites.js` — module-level cache, optimistic toggle
- `src/frontend/src/test/hooks.useFavorites.test.js` — Vitest unit tests
- `src/frontend/src/components/Favorites.jsx` — `/favorites` page, 3 tabs

**Modify:**
- `api/function_app.py` — register `favorites_bp`
- `src/frontend/src/context/SubscriptionContext.jsx` — add `favorites: 'amicus'` gate
- `src/frontend/src/components/CaseDecisionModal.jsx` — star button in header
- `src/frontend/src/components/QuestionDetailModal.jsx` — star button in header, import Star
- `src/frontend/src/components/Flashcard.jsx` — star button in card header, import Star
- `src/frontend/src/App.jsx` — add `favorites` mode/route, lazy import, render block, sidebar prop
- `src/frontend/src/components/Sidebar.jsx` — add Favorites nav item

---

## Task 1: Backend blueprint

**Files:**
- Create: `api/blueprints/favorites.py`

- [ ] **Step 1: Create the file**

```python
"""
Favorites blueprint — per-user starred items.

Routes (all require Clerk JWT; subscriber or admin only):
  GET  /api/favorites/ids?type={content_type}          → ["id1", ...]
  GET  /api/favorites?type={content_type}              → [{content_type, content_id, title, subtitle, created_at}, ...]
  POST /api/favorites   {content_type, content_id, title?, subtitle?}  → {ok: true}
  DELETE /api/favorites {content_type, content_id}                     → {ok: true}
"""

import json
import logging
import traceback
import azure.functions as func

from db_pool import get_db_connection, put_db_connection
from utils.clerk_auth import get_authenticated_user_id

favorites_bp = func.Blueprint()

_tables_ensured = False

_ENSURE_TABLES_SQL = """
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
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'user_favorites' AND indexname = 'user_favorites_user_type_idx'
    ) THEN
        CREATE INDEX user_favorites_user_type_idx ON user_favorites(user_id, content_type);
    END IF;
END $$;
"""

VALID_TYPES = {'case', 'bar_question', 'flashcard'}


def _json(body, status=200):
    return func.HttpResponse(
        json.dumps(body, default=str),
        status_code=status,
        mimetype="application/json",
    )


def _ensure_tables(conn):
    global _tables_ensured
    if _tables_ensured:
        return
    cur = conn.cursor()
    try:
        cur.execute(_ENSURE_TABLES_SQL)
        conn.commit()
        _tables_ensured = True
        logging.info("user_favorites table ensured.")
    except Exception as e:
        logging.error("Failed to ensure user_favorites table: %s", e)
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        cur.close()


def _check_access(req):
    """Returns (clerk_id, error_response). Checks auth + subscriber/admin gate."""
    clerk_id, err = get_authenticated_user_id(req)
    if not clerk_id:
        return None, _json({"error": "Unauthorized", "detail": err}, 401)

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT is_admin, subscription_status FROM users WHERE clerk_id = %s",
                (clerk_id,),
            )
            row = cur.fetchone()
            if not row:
                return None, _json({"error": "Forbidden"}, 403)
            is_admin, sub_status = row
            if not is_admin and sub_status != 'active':
                return None, _json({"error": "Forbidden", "detail": "Subscription required"}, 403)
    except Exception as exc:
        logging.error("_check_access DB error: %s", exc)
        return None, _json({"error": "Server error"}, 500)
    finally:
        put_db_connection(conn)

    return clerk_id, None


@favorites_bp.route(route="favorites/ids", methods=["GET"])
def get_favorite_ids(req: func.HttpRequest) -> func.HttpResponse:
    clerk_id, err = _check_access(req)
    if err:
        return err

    content_type = req.params.get("type")
    if content_type not in VALID_TYPES:
        return _json({"error": f"type must be one of {sorted(VALID_TYPES)}"}, 400)

    conn = None
    try:
        conn = get_db_connection()
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT content_id FROM user_favorites WHERE user_id = %s AND content_type = %s",
                (clerk_id, content_type),
            )
            ids = [row[0] for row in cur.fetchall()]
        return _json(ids)
    except Exception as e:
        logging.error("get_favorite_ids error: %s\n%s", e, traceback.format_exc())
        return _json({"error": str(e)}, 500)
    finally:
        if conn:
            put_db_connection(conn)


@favorites_bp.route(route="favorites", methods=["GET"])
def get_favorites(req: func.HttpRequest) -> func.HttpResponse:
    clerk_id, err = _check_access(req)
    if err:
        return err

    content_type = req.params.get("type")
    if content_type not in VALID_TYPES:
        return _json({"error": f"type must be one of {sorted(VALID_TYPES)}"}, 400)

    conn = None
    try:
        conn = get_db_connection()
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT content_type, content_id, title, subtitle, created_at
                FROM user_favorites
                WHERE user_id = %s AND content_type = %s
                ORDER BY created_at DESC
                """,
                (clerk_id, content_type),
            )
            rows = cur.fetchall()
        items = [
            {
                "content_type": r[0],
                "content_id": r[1],
                "title": r[2],
                "subtitle": r[3],
                "created_at": r[4].isoformat() if r[4] else None,
            }
            for r in rows
        ]
        return _json(items)
    except Exception as e:
        logging.error("get_favorites error: %s\n%s", e, traceback.format_exc())
        return _json({"error": str(e)}, 500)
    finally:
        if conn:
            put_db_connection(conn)


@favorites_bp.route(route="favorites", methods=["POST"])
def add_favorite(req: func.HttpRequest) -> func.HttpResponse:
    clerk_id, err = _check_access(req)
    if err:
        return err

    try:
        body = req.get_json()
    except Exception:
        return _json({"error": "Invalid JSON body"}, 400)

    content_type = body.get("content_type")
    content_id = body.get("content_id")
    if content_type not in VALID_TYPES or not content_id:
        return _json({"error": "content_type and content_id required"}, 400)

    title = body.get("title") or None
    subtitle = body.get("subtitle") or None

    conn = None
    try:
        conn = get_db_connection()
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_favorites (user_id, content_type, content_id, title, subtitle)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id, content_type, content_id) DO NOTHING
                """,
                (clerk_id, content_type, str(content_id), title, subtitle),
            )
            conn.commit()
        return _json({"ok": True})
    except Exception as e:
        logging.error("add_favorite error: %s\n%s", e, traceback.format_exc())
        return _json({"error": str(e)}, 500)
    finally:
        if conn:
            put_db_connection(conn)


@favorites_bp.route(route="favorites", methods=["DELETE"])
def remove_favorite(req: func.HttpRequest) -> func.HttpResponse:
    clerk_id, err = _check_access(req)
    if err:
        return err

    try:
        body = req.get_json()
    except Exception:
        return _json({"error": "Invalid JSON body"}, 400)

    content_type = body.get("content_type")
    content_id = body.get("content_id")
    if content_type not in VALID_TYPES or not content_id:
        return _json({"error": "content_type and content_id required"}, 400)

    conn = None
    try:
        conn = get_db_connection()
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_favorites WHERE user_id = %s AND content_type = %s AND content_id = %s",
                (clerk_id, content_type, str(content_id)),
            )
            conn.commit()
        return _json({"ok": True})
    except Exception as e:
        logging.error("remove_favorite error: %s\n%s", e, traceback.format_exc())
        return _json({"error": str(e)}, 500)
    finally:
        if conn:
            put_db_connection(conn)
```

- [ ] **Step 2: Commit**

```bash
git add api/blueprints/favorites.py
git commit -m "feat: add favorites API blueprint"
```

---

## Task 2: Register blueprint

**Files:**
- Modify: `api/function_app.py`

- [ ] **Step 1: Add import and registration**

In `api/function_app.py`, inside the core `try` block (after the `bar_reviewer_bp` import line), add:

```python
    from blueprints.favorites import favorites_bp
```

And after `app.register_functions(bar_reviewer_bp)`:

```python
    app.register_functions(favorites_bp)
```

- [ ] **Step 2: Verify the server starts**

```bash
cd api
swa emulator start   # or: func host start
```

Expected: no import error. Then:

```bash
curl http://localhost:7071/api/ping
```

Expected: `pong`

- [ ] **Step 3: Commit**

```bash
git add api/function_app.py
git commit -m "feat: register favorites blueprint"
```

---

## Task 3: Frontend hook

**Files:**
- Create: `src/frontend/src/hooks/useFavorites.js`
- Create: `src/frontend/src/test/hooks.useFavorites.test.js`

- [ ] **Step 1: Write the failing test**

Create `src/frontend/src/test/hooks.useFavorites.test.js`:

```js
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';

vi.mock('@clerk/clerk-react', () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from '@clerk/clerk-react';

// Import after mock so module-level cache starts fresh each vi.resetModules()
// We export _clearFavoritesCache for test isolation.
let useFavorites, _clearFavoritesCache;

beforeEach(async () => {
  vi.resetModules();
  const mod = await import('../hooks/useFavorites.js');
  useFavorites = mod.useFavorites;
  _clearFavoritesCache = mod._clearFavoritesCache;

  useAuth.mockReturnValue({
    getToken: vi.fn().mockResolvedValue('mock-token'),
    isSignedIn: true,
  });

  vi.spyOn(global, 'fetch').mockResolvedValue({
    ok: true,
    json: async () => ['42', '99'],
  });
});

afterEach(() => {
  _clearFavoritesCache?.();
  vi.restoreAllMocks();
});

describe('useFavorites', () => {
  it('loading is true before fetch resolves', () => {
    // Delay fetch
    vi.spyOn(global, 'fetch').mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(() => useFavorites('case', '42'));
    expect(result.current.loading).toBe(true);
  });

  it('isFavorited is true for a returned id', async () => {
    const { result } = renderHook(() => useFavorites('case', '42'));
    await waitFor(() => !result.current.loading);
    expect(result.current.isFavorited).toBe(true);
  });

  it('isFavorited is false for an unknown id', async () => {
    const { result } = renderHook(() => useFavorites('case', '999'));
    await waitFor(() => !result.current.loading);
    expect(result.current.isFavorited).toBe(false);
  });

  it('toggleFavorite optimistically adds and then POSTs', async () => {
    vi.spyOn(global, 'fetch')
      .mockResolvedValueOnce({ ok: true, json: async () => [] }) // GET /ids → empty
      .mockResolvedValueOnce({ ok: true, json: async () => ({}) }); // POST → ok

    const { result } = renderHook(() => useFavorites('case', '10'));
    await waitFor(() => !result.current.loading);
    expect(result.current.isFavorited).toBe(false);

    await act(() => result.current.toggleFavorite('My Case', 'GR 12345'));
    expect(result.current.isFavorited).toBe(true);

    const calls = global.fetch.mock.calls;
    const postCall = calls.find(([_url, opts]) => opts?.method === 'POST');
    expect(postCall).toBeTruthy();
    const body = JSON.parse(postCall[1].body);
    expect(body.content_type).toBe('case');
    expect(body.content_id).toBe('10');
    expect(body.title).toBe('My Case');
  });

  it('toggleFavorite rolls back on network error', async () => {
    vi.spyOn(global, 'fetch')
      .mockResolvedValueOnce({ ok: true, json: async () => ['10'] }) // GET /ids
      .mockResolvedValueOnce({ ok: false, status: 500 });             // DELETE fails

    vi.spyOn(window, 'alert').mockImplementation(() => {});

    const { result } = renderHook(() => useFavorites('case', '10'));
    await waitFor(() => !result.current.loading);
    expect(result.current.isFavorited).toBe(true);

    await act(() => result.current.toggleFavorite());
    expect(result.current.isFavorited).toBe(true); // rolled back
    expect(window.alert).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

```bash
cd src/frontend && npm test -- hooks.useFavorites
```

Expected: FAIL — `Cannot find module '../hooks/useFavorites.js'`

- [ ] **Step 3: Create the hook**

Create `src/frontend/src/hooks/useFavorites.js`:

```js
import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { apiUrl } from '../utils/apiUrl';

// Module-level cache — shared across all hook instances, survives re-renders
const _idCache = new Map(); // contentType -> Set<string>
const _inFlight = new Map(); // contentType -> Promise

export function _clearFavoritesCache() {
  _idCache.clear();
  _inFlight.clear();
}

export function useFavorites(contentType, contentId) {
  const { getToken, isSignedIn } = useAuth();
  const [tick, setTick] = useState(0);
  const forceUpdate = useCallback(() => setTick((t) => t + 1), []);

  // Clear cache on sign-out
  useEffect(() => {
    if (!isSignedIn) {
      _idCache.clear();
      _inFlight.clear();
      forceUpdate();
    }
  }, [isSignedIn, forceUpdate]);

  // Load IDs for this content type (deduplicated across instances)
  useEffect(() => {
    if (!isSignedIn || !contentType) return;
    if (_idCache.has(contentType)) return;

    if (_inFlight.has(contentType)) {
      _inFlight.get(contentType).then(forceUpdate).catch(() => {});
      return;
    }

    const promise = getToken()
      .then((token) => {
        if (!token) return;
        return fetch(apiUrl(`/api/favorites/ids?type=${contentType}`), {
          headers: { 'X-Clerk-Authorization': `Bearer ${token}` },
        })
          .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
          .then((ids) => {
            _idCache.set(contentType, new Set(Array.isArray(ids) ? ids.map(String) : []));
          });
      })
      .catch(() => {
        _idCache.set(contentType, new Set()); // fail open with empty set
      })
      .finally(() => {
        _inFlight.delete(contentType);
        forceUpdate();
      });

    _inFlight.set(contentType, promise);
  }, [isSignedIn, contentType, getToken, forceUpdate]);

  const isFavorited = Boolean(
    isSignedIn &&
    contentType &&
    contentId != null &&
    _idCache.has(contentType) &&
    _idCache.get(contentType).has(String(contentId))
  );

  const loading = Boolean(isSignedIn && contentType && !_idCache.has(contentType));

  const toggleFavorite = useCallback(
    async (title, subtitle) => {
      if (!isSignedIn || !contentType || contentId == null) return;
      const idStr = String(contentId);
      const existing = _idCache.get(contentType) || new Set();
      const wasStarred = existing.has(idStr);

      // Optimistic update
      const next = new Set(existing);
      if (wasStarred) next.delete(idStr);
      else next.add(idStr);
      _idCache.set(contentType, next);
      forceUpdate();

      try {
        const token = await getToken();
        if (!token) throw new Error('No token');

        const method = wasStarred ? 'DELETE' : 'POST';
        const body = { content_type: contentType, content_id: idStr };
        if (!wasStarred) {
          if (title) body.title = title;
          if (subtitle) body.subtitle = subtitle;
        }

        const r = await fetch(apiUrl('/api/favorites'), {
          method,
          headers: {
            'Content-Type': 'application/json',
            'X-Clerk-Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify(body),
        });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
      } catch {
        // Rollback
        const rollback = new Set(_idCache.get(contentType) || []);
        if (wasStarred) rollback.add(idStr);
        else rollback.delete(idStr);
        _idCache.set(contentType, rollback);
        forceUpdate();
        alert('Failed to update favorite. Please try again.');
      }
    },
    [isSignedIn, contentType, contentId, getToken, forceUpdate]
  );

  return { isFavorited, toggleFavorite, loading };
}
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
cd src/frontend && npm test -- hooks.useFavorites
```

Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/hooks/useFavorites.js src/frontend/src/test/hooks.useFavorites.test.js
git commit -m "feat: add useFavorites hook with optimistic toggle and module cache"
```

---

## Task 4: Subscription gate

**Files:**
- Modify: `src/frontend/src/context/SubscriptionContext.jsx:9-28`

- [ ] **Step 1: Add the gate**

In `src/frontend/src/context/SubscriptionContext.jsx`, find the `FEATURE_REQUIREMENTS` object (line 9) and add the `favorites` entry:

```js
const FEATURE_REQUIREMENTS = {
  favorites: 'amicus',          // ← add this line
  case_digest_unlimited: 'amicus',
  // ... rest unchanged
```

- [ ] **Step 2: Run existing subscription tests**

```bash
cd src/frontend && npm test -- SubscriptionContext
```

Expected: all existing tests PASS (no regressions)

- [ ] **Step 3: Commit**

```bash
git add src/frontend/src/context/SubscriptionContext.jsx
git commit -m "feat: add favorites subscription gate (amicus+)"
```

---

## Task 5: Star button in CaseDecisionModal

**Files:**
- Modify: `src/frontend/src/components/CaseDecisionModal.jsx`

`Star` is already imported (line 6). Add `useFavorites` import, hook call, and button.

- [ ] **Step 1: Add useFavorites import**

At the top of `CaseDecisionModal.jsx`, after the existing hook imports, add:

```js
import { useFavorites } from '../hooks/useFavorites';
```

- [ ] **Step 2: Add hook call inside the component**

Inside `const CaseDecisionModal = ({ decision, onClose, onCaseSelect }) => {` (line 331), after the existing hook calls (e.g. after `useFontSize`), add:

```js
    const canFavorite = canAccess('favorites');
    const { isFavorited, toggleFavorite } = useFavorites(
        'case',
        fullDecision?.id
    );
    const handleToggleFavorite = useCallback(() => {
        toggleFavorite(
            fullDecision?.short_title || fullDecision?.title || fullDecision?.case_number,
            fullDecision?.case_number
        );
    }, [toggleFavorite, fullDecision]);
```

- [ ] **Step 3: Add star button in the modal header**

In the header right cluster (the comment reads `{/* Right cluster: A-/A+ · close */}`, around line 810), add the star button **before** `<FontSizeControl`:

```jsx
                        {canFavorite && (
                            <button
                                type="button"
                                onClick={handleToggleFavorite}
                                className={`touch-manipulation flex h-6 w-6 shrink-0 items-center justify-center rounded-full border transition-all hover:scale-110 active:scale-95 sm:h-7 sm:w-7 ${
                                    isFavorited
                                        ? 'border-yellow-300/80 bg-yellow-50/90 text-yellow-500 dark:border-yellow-600/60 dark:bg-yellow-900/40 dark:text-yellow-400'
                                        : 'border-gray-200/80 bg-white/80 text-gray-400 hover:text-yellow-400 dark:border-zinc-700 dark:bg-zinc-800/60 dark:text-zinc-500'
                                }`}
                                title={isFavorited ? 'Remove from favorites' : 'Add to favorites'}
                                aria-label={isFavorited ? 'Remove from favorites' : 'Add to favorites'}
                            >
                                <Star
                                    className="h-3 w-3"
                                    strokeWidth={2}
                                    fill={isFavorited ? 'currentColor' : 'none'}
                                />
                            </button>
                        )}
```

- [ ] **Step 4: Manual verification**

Start dev server (`cd src/frontend && npm run dev`). Open a case digest modal while logged in as a subscriber. Confirm:
- Star button appears to the left of the font-size control
- Clicking fills it gold
- Clicking again returns it to outline
- Verify `POST /api/favorites` and `DELETE /api/favorites` requests in Network tab

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/components/CaseDecisionModal.jsx
git commit -m "feat: add star button to CaseDecisionModal"
```

---

## Task 6: Star button in QuestionDetailModal

**Files:**
- Modify: `src/frontend/src/components/QuestionDetailModal.jsx`

- [ ] **Step 1: Add imports**

At line 3, add `Star` to the lucide-react import:

```js
import { X, Star, Headphones, ListMusic, Plus, ChevronLeft, ChevronRight } from 'lucide-react';
```

After the other hook imports (around line 8), add:

```js
import { useFavorites } from '../hooks/useFavorites';
```

- [ ] **Step 2: Add hook call inside the component**

Inside `const QuestionDetailModal = (...)`, after the `useFontSize` call (around line 43), add:

```js
    const { canAccess } = useSubscription();
    const canFavorite = canAccess('favorites');
    const { isFavorited, toggleFavorite } = useFavorites('bar_question', question?.id);
    const handleToggleFavorite = useCallback(() => {
        toggleFavorite(
            `${question.year} Bar Exam`,
            question.subject
        );
    }, [toggleFavorite, question]);
```

- [ ] **Step 3: Add star button in the header right cluster**

In the header right section (the `div` starting at line 127 with `className="flex shrink-0 items-center gap-1.5 sm:gap-2"`), add the star button **before** `<FontSizeControl`:

```jsx
                    <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
                        {canFavorite && (
                            <button
                                type="button"
                                onClick={handleToggleFavorite}
                                className={`touch-manipulation flex h-7 w-7 shrink-0 items-center justify-center rounded-full border transition-all hover:scale-110 active:scale-95 ${
                                    isFavorited
                                        ? 'border-yellow-300/80 bg-yellow-50/90 text-yellow-500 dark:border-yellow-600/60 dark:bg-yellow-900/40 dark:text-yellow-400'
                                        : 'border-gray-200/80 bg-white/80 text-gray-400 hover:text-yellow-400 dark:border-zinc-700 dark:bg-zinc-800/60 dark:text-zinc-500'
                                }`}
                                title={isFavorited ? 'Remove from favorites' : 'Add to favorites'}
                                aria-label={isFavorited ? 'Remove from favorites' : 'Add to favorites'}
                            >
                                <Star className="h-3.5 w-3.5" strokeWidth={2} fill={isFavorited ? 'currentColor' : 'none'} />
                            </button>
                        )}
                        <FontSizeControl fontSize={fontSize} onIncrease={increaseFontSize} onDecrease={decreaseFontSize} />
```

- [ ] **Step 4: Manual verification**

Open a bar question modal. Confirm star button appears and toggles correctly.

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/components/QuestionDetailModal.jsx
git commit -m "feat: add star button to QuestionDetailModal"
```

---

## Task 7: Star button in Flashcard

**Files:**
- Modify: `src/frontend/src/components/Flashcard.jsx`

The flashcard has two variants: `'concepts'` (concept cards — `content_id = encodeURIComponent(card.term)`) and `'bar'` (bar year cards — `content_id = String(card.id)`).

- [ ] **Step 1: Add imports**

At line 2, add `Star` to lucide-react import:

```js
import { ChevronRight, RotateCcw, X, Headphones, Lock, Star } from 'lucide-react';
```

After the `useSubscription` import (around line 11), add:

```js
import { useFavorites } from '../hooks/useFavorites';
```

- [ ] **Step 2: Add hook call inside the component**

Inside `const Flashcard = (...)` (line 16), after `useSubscription` (around line 22), add:

```js
    const { canAccess } = useSubscription();
    const canFavorite = canAccess('favorites');

    const favoriteId = isBar
        ? String(card?.id ?? '')
        : encodeURIComponent(card?.term || '');
    const { isFavorited, toggleFavorite } = useFavorites('flashcard', favoriteId || null);

    const handleToggleFavorite = useCallback(
        (e) => {
            e?.stopPropagation?.();
            const title = isBar
                ? `${card?.year} Bar — ${rawSubjectLabel}`
                : (card?.term || 'Flashcard');
            const subtitle = rawSubjectLabel || '';
            toggleFavorite(title, subtitle);
        },
        [toggleFavorite, isBar, card, rawSubjectLabel]
    );
```

- [ ] **Step 3: Add star button in renderFaceHeader**

In `renderFaceHeader` (line 81), inside the `div.flex.shrink-0.items-center.gap-1` (around line 109), add the star button **before** `<FontSizeControl`:

```jsx
            <div className="flex shrink-0 items-center gap-1">
                {canFavorite && card && (
                    <button
                        type="button"
                        onClick={handleToggleFavorite}
                        className={`touch-manipulation -mr-0.5 -mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border transition-all hover:scale-110 active:scale-95 ${
                            isFavorited
                                ? 'border-yellow-300/80 bg-yellow-50/90 text-yellow-500 dark:border-yellow-600/60 dark:bg-yellow-900/40 dark:text-yellow-400'
                                : 'border-gray-200/80 bg-white/80 text-gray-400 hover:text-yellow-400 dark:border-zinc-700 dark:bg-zinc-800/60 dark:text-zinc-500'
                        }`}
                        title={isFavorited ? 'Remove from favorites' : 'Add to favorites'}
                        aria-label={isFavorited ? 'Remove from favorites' : 'Add to favorites'}
                    >
                        <Star className="h-3.5 w-3.5" strokeWidth={2} fill={isFavorited ? 'currentColor' : 'none'} />
                    </button>
                )}
                <FontSizeControl fontSize={fontSize} onIncrease={increaseFontSize} onDecrease={decreaseFontSize} />
```

- [ ] **Step 4: Manual verification**

Open a flashcard (concepts or bar mode). Confirm star appears in the header and toggles.

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/components/Flashcard.jsx
git commit -m "feat: add star button to Flashcard"
```

---

## Task 8: Favorites page

**Files:**
- Create: `src/frontend/src/components/Favorites.jsx`

The page shows 3 tabs. For each type it fetches `GET /api/favorites?type={type}`. Clicking a case calls `onCaseSelect`; clicking a bar question or flashcard opens a local modal using the in-memory data hooks.

- [ ] **Step 1: Create the component**

Create `src/frontend/src/components/Favorites.jsx`:

```jsx
import React, { useState, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { Star, Gavel, BookOpen, CreditCard, Loader2, AlertTriangle } from 'lucide-react';
import { useAuth } from '@clerk/clerk-react';
import { apiUrl } from '../utils/apiUrl';
import { useFavorites } from '../hooks/useFavorites';
import { useBarQuestions } from '../hooks/useBarQuestions';
import { useFlashcardConcepts } from '../hooks/useFlashcardConcepts';
import { useSubscription } from '../context/SubscriptionContext';
import QuestionDetailModal from './QuestionDetailModal';
import Flashcard from './Flashcard';

const TABS = [
  { key: 'case', label: 'Cases', icon: Gavel },
  { key: 'bar_question', label: 'Bar Questions', icon: BookOpen },
  { key: 'flashcard', label: 'Flashcards', icon: CreditCard },
];

function FavoriteCard({ item, onClick, onRemove }) {
  const { isFavorited, toggleFavorite } = useFavorites(item.content_type, item.content_id);

  const handleRemove = useCallback(
    async (e) => {
      e.stopPropagation();
      await toggleFavorite();
      onRemove(item.content_id);
    },
    [toggleFavorite, onRemove, item.content_id]
  );

  return (
    <div
      className="group flex cursor-pointer items-start gap-3 rounded-xl border border-lex bg-white p-3 shadow-sm transition-all hover:border-yellow-300 hover:shadow-md dark:border-lex dark:bg-zinc-900 dark:hover:border-yellow-600"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick?.()}
    >
      <div className="min-w-0 flex-1">
        <p className="line-clamp-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
          {item.title || item.content_id}
        </p>
        {item.subtitle && (
          <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">{item.subtitle}</p>
        )}
        {item.created_at && (
          <p className="mt-1 text-[10px] text-gray-400 dark:text-gray-500">
            Saved {new Date(item.created_at).toLocaleDateString('en-PH', { month: 'short', day: 'numeric', year: 'numeric' })}
          </p>
        )}
      </div>
      <button
        type="button"
        onClick={handleRemove}
        className="shrink-0 rounded-full border border-yellow-300/80 bg-yellow-50/90 p-1 text-yellow-500 transition-all hover:bg-red-50 hover:text-red-500 dark:border-yellow-600/60 dark:bg-yellow-900/40 dark:text-yellow-400 dark:hover:bg-red-900/40 dark:hover:text-red-400"
        title="Remove from favorites"
        aria-label="Remove from favorites"
      >
        <Star className="h-3.5 w-3.5" fill="currentColor" strokeWidth={2} />
      </button>
    </div>
  );
}

export default function Favorites({ onCaseSelect }) {
  const { getToken, isSignedIn } = useAuth();
  const { canAccess } = useSubscription();
  const [activeTab, setActiveTab] = useState('case');
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [openQuestion, setOpenQuestion] = useState(null);
  const [openFlashcard, setOpenFlashcard] = useState(null);

  // Load data needed for modal re-open
  const { questions } = useBarQuestions({ enabled: activeTab === 'bar_question' });
  const { conceptPool } = useFlashcardConcepts({ enabled: activeTab === 'flashcard' });

  const fetchItems = useCallback(async () => {
    if (!isSignedIn) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getToken();
      if (!token) throw new Error('Not authenticated');
      const r = await fetch(apiUrl(`/api/favorites?type=${activeTab}`), {
        headers: { 'X-Clerk-Authorization': `Bearer ${token}` },
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      setItems(data);
    } catch (err) {
      setError(err.message || 'Failed to load favorites');
    } finally {
      setLoading(false);
    }
  }, [isSignedIn, getToken, activeTab]);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  const handleRemove = useCallback((contentId) => {
    setItems((prev) => prev.filter((i) => i.content_id !== contentId));
  }, []);

  const handleItemClick = useCallback(
    (item) => {
      if (item.content_type === 'case') {
        onCaseSelect?.({ id: item.content_id });
      } else if (item.content_type === 'bar_question') {
        const q = questions.find((q) => String(q.id) === String(item.content_id));
        if (q) setOpenQuestion(q);
      } else if (item.content_type === 'flashcard') {
        const isBar = /^\d+$/.test(item.content_id);
        if (isBar) {
          const q = questions.find((q) => String(q.id) === String(item.content_id));
          if (q) setOpenFlashcard({ card: q, variant: 'bar' });
        } else {
          const c = conceptPool.find(
            (c) => encodeURIComponent(c.term || '') === item.content_id
          );
          if (c) setOpenFlashcard({ card: c, variant: 'concepts' });
        }
      }
    },
    [onCaseSelect, questions, conceptPool]
  );

  if (!canAccess('favorites')) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center p-8 text-center">
        <div>
          <Star className="mx-auto mb-3 h-10 w-10 text-gray-300 dark:text-gray-600" />
          <p className="font-semibold text-gray-600 dark:text-gray-400">Favorites require an Amicus plan or higher.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto min-h-screen w-full max-w-4xl px-3 py-6 sm:px-5 lg:px-6">
      <div className="mb-6 flex items-center gap-3">
        <Star className="h-6 w-6 text-yellow-500" fill="currentColor" />
        <h1 className="text-2xl font-black tracking-tight text-gray-900 dark:text-gray-100">Favorites</h1>
      </div>

      {/* Tabs */}
      <div className="mb-4 flex gap-2 border-b border-lex pb-1">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            type="button"
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-1.5 rounded-t-lg px-3 py-2 text-sm font-semibold transition-colors ${
              activeTab === key
                ? 'border-b-2 border-yellow-500 text-yellow-600 dark:text-yellow-400'
                : 'text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200'
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading && (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-yellow-500" />
        </div>
      )}

      {error && !loading && (
        <div className="flex flex-col items-center gap-3 py-12 text-center">
          <AlertTriangle className="h-8 w-8 text-red-400" />
          <p className="text-sm text-red-500">{error}</p>
          <button
            type="button"
            onClick={fetchItems}
            className="rounded-lg border border-red-300 px-4 py-1.5 text-xs font-bold text-red-500 hover:bg-red-50"
          >
            Retry
          </button>
        </div>
      )}

      {!loading && !error && items.length === 0 && (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <Star className="h-10 w-10 text-gray-300 dark:text-gray-600" />
          <p className="text-base font-semibold text-gray-500 dark:text-gray-400">No favorites yet</p>
          <p className="text-sm text-gray-400 dark:text-gray-500">Star items while browsing to save them here.</p>
        </div>
      )}

      {!loading && !error && items.length > 0 && (
        <div className="space-y-2">
          {items.map((item) => (
            <FavoriteCard
              key={item.content_id}
              item={item}
              onClick={() => handleItemClick(item)}
              onRemove={handleRemove}
            />
          ))}
        </div>
      )}

      {/* Bar question modal */}
      {openQuestion && (
        <QuestionDetailModal
          question={openQuestion}
          onClose={() => setOpenQuestion(null)}
        />
      )}

      {/* Flashcard modal */}
      {openFlashcard &&
        createPortal(
          <div
            className="fixed inset-0 z-[540] flex items-center justify-center bg-black/40 backdrop-blur-md"
            onClick={() => setOpenFlashcard(null)}
          >
            <div
              className="relative flex max-w-5xl flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              <Flashcard
                variant={openFlashcard.variant}
                card={openFlashcard.card}
                total={1}
                currentIndex={0}
                onClose={() => setOpenFlashcard(null)}
              />
            </div>
          </div>,
          document.body
        )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/frontend/src/components/Favorites.jsx
git commit -m "feat: add Favorites page with 3-tab layout"
```

---

## Task 9: Wire into App.jsx and Sidebar

**Files:**
- Modify: `src/frontend/src/App.jsx`
- Modify: `src/frontend/src/components/Sidebar.jsx`

- [ ] **Step 1: Add mode + lazy import to App.jsx**

**a)** After line 80 (`const Flashcard = lazy(...)`), add:

```js
const Favorites = lazy(() => import('./components/Favorites'));
```

**b)** In `MODE_TO_PATH` (line 110), add:

```js
  favorites: '/favorites',
```

**c)** In the Sidebar JSX block (around line 902), add the new prop:

```jsx
          onToggleFavorites={() => navigateToTab('favorites')}
```

**d)** After the `{effectiveMode === 'about' && <About />}` block (around line 982), add:

```jsx
                  {effectiveMode === 'favorites' && (
                    <Suspense fallback={<PageLoadingFallback label="Loading Favorites…" />}>
                      <Favorites onCaseSelect={selectGlobalCaseGuarded} />
                    </Suspense>
                  )}
```

- [ ] **Step 2: Add nav item to Sidebar.jsx**

In `src/frontend/src/components/Sidebar.jsx`, add `onToggleFavorites` to the prop list (around line 80):

```js
const Sidebar = ({
  onToggleQuiz,
  onToggleFavorites,   // ← add
  onToggleAbout,
  // ... rest unchanged
```

Then add a nav button. A good location is after the admin divider block and before the "About" button (around line 246). `Star` is already imported at line 2:

```jsx
            {/* Favorites — subscribers only */}
            <SignedIn>
              <button
                onClick={onToggleFavorites}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2 text-left text-base font-medium transition-colors
                ${mode === 'favorites'
                    ? SIDEBAR_NAV_ACTIVE
                    : SIDEBAR_NAV_IDLE
                }`}
              >
                <Star size={18} className={`${mode === 'favorites' ? 'text-yellow-500 dark:text-yellow-400' : 'text-yellow-500/70 dark:text-yellow-500/60'} group-hover:scale-110 transition-all duration-200`} fill={mode === 'favorites' ? 'currentColor' : 'none'} />
                Favorites
              </button>
            </SignedIn>
```

- [ ] **Step 3: Manual end-to-end verification**

1. Start dev server: `cd src/frontend && npm run dev`
2. Log in as a subscriber
3. Click **Favorites** in the sidebar → `/favorites` route loads with 3 tabs
4. Go to Decisions, star a case → star fills gold
5. Return to Favorites → case appears in Cases tab
6. Click the case card → CaseDecisionModal opens
7. In Favorites, click the star on the card → card disappears from the list
8. Log in as a free-tier user → star buttons are not visible in modals

- [ ] **Step 4: Run full test suite**

```bash
cd src/frontend && npm test
```

Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/App.jsx src/frontend/src/components/Sidebar.jsx
git commit -m "feat: wire Favorites page into app routing and sidebar nav"
```
