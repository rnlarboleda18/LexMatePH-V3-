import { useState, useCallback } from 'react';

const MAX_HISTORY = 8;

/**
 * Persists recent search terms in localStorage under `storageKey`.
 *
 * Returns:
 *   history      - array of recent search strings (most recent first)
 *   addToHistory - call with a term after a successful search
 *   clearHistory - wipes the list and the localStorage entry
 *
 * Usage:
 *   const { history, addToHistory, clearHistory } =
 *     useSearchHistory('lexmate_sc_search_history');
 */
export function useSearchHistory(storageKey) {
  const [history, setHistory] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(storageKey) || '[]');
    } catch {
      return [];
    }
  });

  const addToHistory = useCallback(
    (term) => {
      const trimmed = term?.trim();
      if (!trimmed) return;
      setHistory((prev) => {
        const deduped = [trimmed, ...prev.filter((t) => t !== trimmed)].slice(
          0,
          MAX_HISTORY
        );
        try {
          localStorage.setItem(storageKey, JSON.stringify(deduped));
        } catch {
          /* private mode or storage quota exceeded — silently ignore */
        }
        return deduped;
      });
    },
    [storageKey]
  );

  const clearHistory = useCallback(() => {
    setHistory([]);
    try {
      localStorage.removeItem(storageKey);
    } catch {
      /* ignore */
    }
  }, [storageKey]);

  return { history, addToHistory, clearHistory };
}
