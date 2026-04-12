import { useState, useEffect, useCallback, useMemo } from 'react';
import { normalizeBarSubject } from '../utils/subjectNormalize';
import { apiUrl } from '../utils/apiUrl';

const FLASHCARD_FETCH_MS = 300000;

/**
 * Loads SC digest key legal concepts for the flashcard feature.
 * Prefetches on mount; exposes retry / filter controls.
 */
export function useFlashcardConcepts() {
  const [conceptPool, setConceptPool] = useState([]);
  const [busy, setBusy] = useState(false);
  const [conceptsError, setConceptsError] = useState(null);
  const [fetchNonce, setFetchNonce] = useState(0);
  const [relaxedBarMatch, setRelaxedBarMatch] = useState(false);
  const [bar2026Only, setBar2026Only] = useState(false);

  useEffect(() => {
    const ac = new AbortController();
    const tid = setTimeout(() => ac.abort(), FLASHCARD_FETCH_MS);
    let cancelled = false;

    const load = async () => {
      setBusy(true);
      setConceptsError(null);
      if (fetchNonce > 0) setConceptPool([]);

      try {
        const params = new URLSearchParams();
        if (fetchNonce > 0) params.set('nocache', '1');
        if (relaxedBarMatch) params.set('bar_focus', '0');
        if (bar2026Only) params.set('bar_2026_only', '1');
        const qs = params.toString();
        const res = await fetch(
          apiUrl(`/api/sc_decisions/flashcard_concepts${qs ? `?${qs}` : ''}`),
          { signal: ac.signal }
        );
        const raw = await res.text();
        if (cancelled) return;
        if (!res.ok) {
          let msg = 'Failed to load key legal concepts';
          try {
            const j = JSON.parse(raw);
            if (j.error) msg = String(j.error);
          } catch (_) {
            if (raw) msg = raw.slice(0, 200);
          }
          throw new Error(msg);
        }
        const data = JSON.parse(raw);
        if (cancelled) return;
        setConceptPool(Array.isArray(data.concepts) ? data.concepts : []);
      } catch (e) {
        if (cancelled) return;
        if (e.name === 'AbortError') {
          setConceptsError(
            'Request timed out (5 min). The API merges digests from the database when the flashcard_concepts table is empty or the cache is cold—that can take several minutes. Fix: run scripts/populate_flashcard_concepts_from_digest.py on your cloud DB so the API reads the prebuilt table (fast). Also ensure the API and DB are reachable; retry once Redis has cached the response.'
          );
        } else {
          let msg = e.message || 'Load failed';
          if (msg === 'Failed to fetch' || /network/i.test(msg)) {
            msg =
              'Could not reach the API. For local dev, start the backend on port 7071 so Vite can proxy /api (see vite.config.js).';
          }
          setConceptsError(msg);
        }
        setConceptPool([]);
      } finally {
        clearTimeout(tid);
        if (!cancelled) setBusy(false);
      }
    };

    load();
    return () => {
      cancelled = true;
      ac.abort();
    };
  }, [fetchNonce, relaxedBarMatch, bar2026Only]);

  const refetch = useCallback(() => setFetchNonce((n) => n + 1), []);

  const getPrimarySubject = useCallback((card) => {
    if (card.primary_subject) return normalizeBarSubject(card.primary_subject);
    return normalizeBarSubject((card.sources || [])[0]?.subject) || null;
  }, []);

  const subjectCounts = useMemo(() => {
    const subjects = [
      'Civil Law', 'Commercial Law', 'Criminal Law', 'Labor Law',
      'Legal Ethics', 'Political Law', 'Remedial Law', 'Taxation Law',
    ];
    const counts = { all: conceptPool.length };
    subjects.forEach((s) => {
      counts[s] = conceptPool.filter((c) => getPrimarySubject(c) === s).length;
    });
    return counts;
  }, [conceptPool, getPrimarySubject]);

  return {
    conceptPool,
    busy,
    conceptsError,
    relaxedBarMatch,
    setRelaxedBarMatch,
    bar2026Only,
    setBar2026Only,
    refetch,
    getPrimarySubject,
    subjectCounts,
  };
}
