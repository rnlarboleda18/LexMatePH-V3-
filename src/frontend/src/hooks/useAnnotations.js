import { useState, useEffect, useRef, useCallback } from 'react';
import { apiUrl } from '../utils/apiUrl';

const MAX_UNDO = 50;

/**
 * useAnnotations — manages per-user per-topic ink annotations.
 *
 * @param {string} subject   - e.g. 'criminal', 'civil'
 * @param {string} topicId   - UUID of the selected topic (or null)
 * @param {Function} getToken - Clerk's getToken() from useAuth()
 *
 * Returns: { strokes, pushStroke, undo, redo, clearAll, isSaving, canSave, undoStack, redoStack }
 */
export function useAnnotations(subject, topicId, getToken) {
  const [strokes, setStrokes]         = useState([]);
  const [undoStack, setUndoStack]     = useState([]);
  const [redoStack, setRedoStack]     = useState([]);
  const [isSaving, setIsSaving]       = useState(false);
  const [canSave, setCanSave]         = useState(true);

  // Refs so callbacks always see fresh values without recreating on every stroke
  const strokesRef      = useRef([]);
  const topicIdRef      = useRef(topicId);
  const subjectRef      = useRef(subject);
  const getTokenRef     = useRef(getToken);
  const canSaveRef      = useRef(true);
  const skipSaveRef     = useRef(false); // true right after loading from API
  const saveTimerRef    = useRef(null);
  const pendingSaveRef  = useRef(false); // true when strokes changed but save hasn't fired

  useEffect(() => { strokesRef.current  = strokes;    }, [strokes]);
  useEffect(() => { topicIdRef.current  = topicId;    }, [topicId]);
  useEffect(() => { subjectRef.current  = subject;    }, [subject]);
  useEffect(() => { getTokenRef.current = getToken;   }, [getToken]);
  useEffect(() => { canSaveRef.current  = canSave;    }, [canSave]);

  // Build auth headers using Clerk token, falling back to unauthenticated if none
  async function authHeaders() {
    try {
      const token = getTokenRef.current ? await getTokenRef.current() : null;
      if (token) return { 'X-Clerk-Authorization': `Bearer ${token}` };
    } catch (_) { /* ignore — treat as unauthenticated */ }
    return {};
  }

  // Fire a save immediately (used when we'd otherwise lose the pending debounce)
  async function flushSave(sid, tid, snapshot) {
    if (!sid || !tid || !canSaveRef.current) return;
    const headers = await authHeaders();
    fetch(apiUrl(`/api/reviewer/${sid}/${tid}/annotations`), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...headers },
      credentials: 'include',
      body: JSON.stringify({ strokes: snapshot }),
    }).catch(() => {});
  }

  // ── Flush + cancel any pending debounce ──────────────────────────────────
  function cancelOrFlush(flush) {
    if (saveTimerRef.current) {
      clearTimeout(saveTimerRef.current);
      saveTimerRef.current = null;
    }
    if (flush && pendingSaveRef.current) {
      flushSave(subjectRef.current, topicIdRef.current, strokesRef.current);
    }
    pendingSaveRef.current = false;
  }

  // ── Flush on unmount so navigating away never loses strokes ─────────────
  useEffect(() => {
    return () => cancelOrFlush(true);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Load annotations when topic changes ───────────────────────────────────
  useEffect(() => {
    // Flush any unsaved strokes for the previous topic before switching
    cancelOrFlush(true);

    // Reset state for new topic
    skipSaveRef.current = true;
    setStrokes([]);
    setUndoStack([]);
    setRedoStack([]);
    setIsSaving(false);

    if (!topicId || !subject) return;

    (async () => {
      const headers = await authHeaders();
      fetch(apiUrl(`/api/reviewer/${subject}/${topicId}/annotations`), {
        credentials: 'include',
        headers,
      })
        .then(r => {
          if (r.status === 401 || r.status === 403) {
            setCanSave(false);
            return { strokes: [] };
          }
          setCanSave(true);
          return r.json();
        })
        .then(data => {
          setStrokes(Array.isArray(data.strokes) ? data.strokes : []);
          requestAnimationFrame(() => { skipSaveRef.current = false; });
        })
        .catch(() => {
          skipSaveRef.current = false;
        });
    })();
  }, [topicId, subject]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Debounced save whenever strokes change ─────────────────────────────────
  useEffect(() => {
    if (skipSaveRef.current) return;
    if (!topicIdRef.current || !subjectRef.current) return;
    if (!canSaveRef.current) return;

    setIsSaving(true);
    pendingSaveRef.current = true;
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);

    const sid      = subjectRef.current;
    const tid      = topicIdRef.current;
    const snapshot = strokesRef.current;

    saveTimerRef.current = setTimeout(async () => {
      saveTimerRef.current   = null;
      pendingSaveRef.current = false;
      const headers = await authHeaders();
      fetch(apiUrl(`/api/reviewer/${sid}/${tid}/annotations`), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...headers },
        credentials: 'include',
        body: JSON.stringify({ strokes: snapshot }),
      })
        .then(() => setIsSaving(false))
        .catch(() => setIsSaving(false));
    }, 800);
  }, [strokes]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── pushStroke ─────────────────────────────────────────────────────────────
  const pushStroke = useCallback((stroke) => {
    setUndoStack(prev => {
      const next = [...prev, strokesRef.current];
      return next.length > MAX_UNDO ? next.slice(1) : next;
    });
    setStrokes(prev => [...prev, stroke]);
    setRedoStack([]);
  }, []);

  // ── undo ───────────────────────────────────────────────────────────────────
  const undo = useCallback(() => {
    setUndoStack(prev => {
      if (prev.length === 0) return prev;
      const snapshot = prev[prev.length - 1];
      setRedoStack(rs => [strokesRef.current, ...rs]);
      setStrokes(snapshot);
      return prev.slice(0, -1);
    });
  }, []);

  // ── redo ───────────────────────────────────────────────────────────────────
  const redo = useCallback(() => {
    setRedoStack(prev => {
      if (prev.length === 0) return prev;
      const snapshot = prev[0];
      setUndoStack(us => [...us, strokesRef.current]);
      setStrokes(snapshot);
      return prev.slice(1);
    });
  }, []);

  // ── clearAll ───────────────────────────────────────────────────────────────
  const clearAll = useCallback(() => {
    const tid = topicIdRef.current;
    const sid = subjectRef.current;
    if (!tid) return;

    cancelOrFlush(false); // discard pending save — we're about to DELETE
    setUndoStack(prev => {
      const next = [...prev, strokesRef.current];
      return next.length > MAX_UNDO ? next.slice(1) : next;
    });
    setStrokes([]);
    setRedoStack([]);

    if (canSaveRef.current) {
      (async () => {
        const headers = await authHeaders();
        fetch(apiUrl(`/api/reviewer/${sid}/${tid}/annotations`), {
          method: 'DELETE',
          headers,
          credentials: 'include',
        }).catch(() => {});
      })();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    strokes,
    pushStroke,
    undo,
    redo,
    clearAll,
    isSaving,
    canSave,
    undoStack,
    redoStack,
  };
}
