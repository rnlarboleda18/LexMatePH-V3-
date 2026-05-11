import { useState, useCallback, useRef, useEffect } from 'react';

const DECISIONS_BASE = '/decisions';

/**
 * Returns the numeric case ID if the current URL is a case deep-link
 * (e.g. /decisions/12345), otherwise null.
 */
function getCaseIdFromUrl() {
  const match = window.location.pathname.match(/^\/decisions\/(\d+)(?:\/|$)/);
  return match ? match[1] : null;
}

/**
 * Manages the global case decision modal state shared between
 * Supreme Decisions and LexCode (Codex) views.
 *
 * URL behaviour:
 *   - Opening a case pushes  /decisions/{id}  to the history stack.
 *   - Closing via closeModal restores  /decisions  (or pops if we pushed).
 *   - The browser Back button automatically closes the modal via popstate.
 *
 * Ghost-tap prevention: re-opening the same case within 750 ms of closing it
 * is suppressed to avoid accidental re-opens from residual touch events.
 *
 * IMPORTANT: refs MUST be updated synchronously inside closeModal (not inside
 * the setSelectedCase updater callback) so that selectCase's suppress check
 * sees the correct values immediately — even before React commits the render.
 */
export function useGlobalCaseModal() {
  const [selectedCase, setSelectedCase] = useState(null);
  const lastClosedIdRef = useRef(null);
  const suppressUntilRef = useRef(0);
  /**
   * True when WE pushed a /decisions/{id} entry onto the history stack,
   * so closeModal knows to call history.back() instead of replaceState.
   */
  const didPushStateRef = useRef(false);

  const selectCase = useCallback((next) => {
    if (
      next != null &&
      lastClosedIdRef.current != null &&
      String(next.id) === String(lastClosedIdRef.current) &&
      Date.now() < suppressUntilRef.current
    ) {
      return;
    }

    if (next != null) {
      const targetPath = `${DECISIONS_BASE}/${next.id}`;
      if (window.location.pathname !== targetPath) {
        window.history.pushState({ lexmateCaseId: String(next.id) }, '', targetPath);
        didPushStateRef.current = true;
      }
    }

    setSelectedCase(next);
  }, []);

  const closeModal = useCallback(() => {
    // Update refs synchronously so the suppress check works immediately,
    // even within the same React event batch before the state update commits.
    if (selectedCase?.id != null) {
      lastClosedIdRef.current = selectedCase.id;
      suppressUntilRef.current = Date.now() + 750;
    }

    // Always clear React state immediately — do NOT rely on popstate firing
    // (jsdom's history.back() is a no-op; real browsers fire it async).
    setSelectedCase(null);

    if (didPushStateRef.current) {
      // We pushed a /decisions/{id} entry — go back to restore the previous URL.
      // In real browsers this also fires popstate, but setSelectedCase(null)
      // above already handled the state so the listener becomes a safe no-op.
      didPushStateRef.current = false;
      window.history.back();
    } else if (getCaseIdFromUrl()) {
      // Arrived via deep-link — rewrite URL back to /decisions.
      window.history.replaceState(null, '', DECISIONS_BASE);
    }
  }, [selectedCase]);

  /**
   * Handle the browser Back (and Forward) button.
   * When the user navigates away from a /decisions/{id} URL, close the modal.
   */
  useEffect(() => {
    const onPopState = () => {
      const caseId = getCaseIdFromUrl();
      if (!caseId) {
        // Navigated back to /decisions (or elsewhere) — close modal.
        didPushStateRef.current = false;
        setSelectedCase(null);
      }
      // If caseId is present the user went *forward* to a case URL — we don't
      // auto-open here; the normal selectCase flow handles that.
    };

    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  /** Merge fields into the open case (e.g. full text loaded after digest-only open). */
  const patchSelectedCase = useCallback((id, patch) => {
    if (id == null || patch == null) return;
    setSelectedCase((prev) => {
      if (prev == null || String(prev.id) !== String(id)) return prev;
      return { ...prev, ...patch };
    });
  }, []);

  return { selectedCase, selectCase, closeModal, patchSelectedCase };
}
