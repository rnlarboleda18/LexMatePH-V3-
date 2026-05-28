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
        return true; // success
      } catch {
        // Rollback
        const rollback = new Set(_idCache.get(contentType) || []);
        if (wasStarred) rollback.add(idStr);
        else rollback.delete(idStr);
        _idCache.set(contentType, rollback);
        forceUpdate();
        alert('Failed to update favorite. Please try again.');
        return false; // failure
      }
    },
    [isSignedIn, contentType, contentId, getToken, forceUpdate]
  );

  return { isFavorited, toggleFavorite, loading };
}
