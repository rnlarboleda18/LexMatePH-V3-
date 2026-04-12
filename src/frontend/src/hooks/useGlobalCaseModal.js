import { useState, useCallback, useRef } from 'react';

/**
 * Manages the global case decision modal state shared between
 * Supreme Decisions and LexCode (Codex) views.
 *
 * Ghost-tap prevention: re-opening the same case within 750 ms of closing it
 * is suppressed to avoid accidental re-opens from residual touch events.
 */
export function useGlobalCaseModal() {
  const [selectedCase, setSelectedCase] = useState(null);
  const lastClosedIdRef = useRef(null);
  const suppressUntilRef = useRef(0);

  const selectCase = useCallback((next) => {
    if (
      next != null &&
      lastClosedIdRef.current != null &&
      next.id === lastClosedIdRef.current &&
      Date.now() < suppressUntilRef.current
    ) {
      return;
    }
    setSelectedCase(next);
  }, []);

  const closeModal = useCallback(() => {
    setSelectedCase((prev) => {
      if (prev?.id != null) {
        lastClosedIdRef.current = prev.id;
        suppressUntilRef.current = Date.now() + 750;
      }
      return null;
    });
  }, []);

  return { selectedCase, selectCase, closeModal };
}
