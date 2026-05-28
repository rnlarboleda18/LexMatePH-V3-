import { useState, useEffect, useRef, useCallback } from 'react';
import { apiUrl } from '../utils/apiUrl';

const MAX_UNDO = 50;

/**
 * useAnnotations — manages per-user per-topic ink annotations.
 *
 * @param {string} subject   - e.g. 'criminal', 'civil'
 * @param {string} topicId   - UUID of the selected topic (or null)
 *
 * Returns: { strokes, pushStroke, undo, redo, clearAll, isSaving, canSave, undoStack, redoStack }
 */
export function useAnnotations(subject, topicId) {
  const [strokes, setStrokes]         = useState([]);
  const [undoStack, setUndoStack]     = useState([]);
  const [redoStack, setRedoStack]     = useState([]);
  const [isSaving, setIsSaving]       = useState(false);
  const [canSave, setCanSave]         = useState(true);

  // Refs so callbacks always see fresh values without recreating on every stroke
  const strokesRef    = useRef([]);
  const topicIdRef    = useRef(topicId);
  const subjectRef    = useRef(subject);
  const canSaveRef    = useRef(true);
  const skipSaveRef   = useRef(false); // true right after loading from API
  const saveTimerRef  = useRef(null);

  useEffect(() => { strokesRef.current = strokes; }, [strokes]);
  useEffect(() => { topicIdRef.current = topicId; }, [topicId]);
  useEffect(() => { subjectRef.current = subject; }, [subject]);
  useEffect(() => { canSaveRef.current = canSave; }, [canSave]);

  // ── Load annotations when topic changes ───────────────────────────────────
  useEffect(() => {
    // Cancel any pending save for the old topic
    if (saveTimerRef.current) {
      clearTimeout(saveTimerRef.current);
      saveTimerRef.current = null;
    }

    // Reset state for new topic
    skipSaveRef.current = true;
    setStrokes([]);
    setUndoStack([]);
    setRedoStack([]);
    setIsSaving(false);

    if (!topicId || !subject) return;

    fetch(apiUrl(`/api/reviewer/${subject}/${topicId}/annotations`), {
      credentials: 'include',
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
        // skipSaveRef is still true — setting strokes here won't trigger save
        setStrokes(Array.isArray(data.strokes) ? data.strokes : []);
        // After this render cycle, allow saving again
        // (we set to false AFTER this tick so the save effect sees it during re-render)
        requestAnimationFrame(() => { skipSaveRef.current = false; });
      })
      .catch(() => {
        skipSaveRef.current = false;
      });
  }, [topicId, subject]);

  // ── Debounced save whenever strokes change ─────────────────────────────────
  useEffect(() => {
    if (skipSaveRef.current) return;
    if (!topicIdRef.current || !subjectRef.current) return;
    if (!canSaveRef.current) return;

    setIsSaving(true);
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);

    const sid = subjectRef.current;
    const tid = topicIdRef.current;
    const snapshot = strokesRef.current;

    saveTimerRef.current = setTimeout(() => {
      fetch(apiUrl(`/api/reviewer/${sid}/${tid}/annotations`), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ strokes: snapshot }),
      })
        .then(() => setIsSaving(false))
        .catch(() => setIsSaving(false));
    }, 1500);

    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    };
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

    setUndoStack(prev => {
      const next = [...prev, strokesRef.current];
      return next.length > MAX_UNDO ? next.slice(1) : next;
    });
    setStrokes([]);
    setRedoStack([]);

    if (canSaveRef.current) {
      fetch(apiUrl(`/api/reviewer/${sid}/${tid}/annotations`), {
        method: 'DELETE',
        credentials: 'include',
      }).catch(() => {});
    }
  }, []);

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
