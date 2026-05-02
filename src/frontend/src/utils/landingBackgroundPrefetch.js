import { apiUrl } from './apiUrl';

/** Matches App default codal; warms the same network URL LexCode will request. */
const DEFAULT_CODAL_SHORT = 'RPC';

/**
 * When true, skip all optional work (saves data / very slow link).
 * Does not throw.
 */
export function shouldSkipAllLandingWarm() {
  if (typeof navigator === 'undefined') return true;
  const c = navigator.connection;
  if (c && c.saveData) return true;
  const t = c && c.effectiveType;
  if (t === 'slow-2g' || t === '2g') return true;
  return false;
}

/**
 * When true, skip a background GET that only warms the HTTP / SW path for the default codal.
 * Still allows chunk preloads (script cache) on 3g+.
 */
function shouldSkipOptionalCodexWarm() {
  if (shouldSkipAllLandingWarm()) return true;
  const t = typeof navigator !== 'undefined' && navigator.connection && navigator.connection.effectiveType;
  if (t === '2g') return true;
  return false;
}

/**
 * @param {{ isCancelled: () => boolean }} opts
 * @returns {() => void} cancel pending timers + idle work
 */
export function startLandingBackgroundPrefetch({ isCancelled }) {
  const cleanups = [];

  const clearAll = () => {
    while (cleanups.length) {
      const fn = cleanups.pop();
      try {
        fn();
      } catch {
        /* ignore */
      }
    }
  };

  if (shouldSkipAllLandingWarm()) {
    return clearAll;
  }

  // Phase 1: defer so landing paint + first SupremeDecisions fetches get priority; then load heavy chunks in idle.
  const phase1 = setTimeout(() => {
    if (isCancelled()) return;
    const runChunks = () => {
      if (isCancelled() || shouldSkipAllLandingWarm()) return;
      void Promise.allSettled([import('../components/LexCodeViewer'), import('../components/CaseDecisionModal')]);
    };
    if (typeof window !== 'undefined' && typeof window.requestIdleCallback === 'function') {
      const id = window.requestIdleCallback(() => !isCancelled() && runChunks(), { timeout: 5000 });
      cleanups.push(() => window.cancelIdleCallback(id));
    } else {
      const id = setTimeout(runChunks, 0);
      cleanups.push(() => clearTimeout(id));
    }
  }, 1200);
  cleanups.push(() => clearTimeout(phase1));

  // Phase 2: optional; warms the same API URL LexCode uses. LexCode SWR/IndexedDB remains authoritative.
  const phase2 = setTimeout(() => {
    if (isCancelled() || shouldSkipOptionalCodexWarm()) return;
    const runFetch = () => {
      if (isCancelled() || shouldSkipOptionalCodexWarm()) return;
      const path = `/api/codex/versions?short_name=${DEFAULT_CODAL_SHORT}`;
      void fetch(apiUrl(path), { method: 'GET', credentials: 'same-origin' }).catch(() => {});
    };
    if (typeof window !== 'undefined' && typeof window.requestIdleCallback === 'function') {
      const id = window.requestIdleCallback(() => !isCancelled() && runFetch(), { timeout: 10000 });
      cleanups.push(() => window.cancelIdleCallback(id));
    } else {
      const id = setTimeout(runFetch, 0);
      cleanups.push(() => clearTimeout(id));
    }
  }, 4000);
  cleanups.push(() => clearTimeout(phase2));

  return clearAll;
}
