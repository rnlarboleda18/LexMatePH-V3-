import { useState, useCallback, useRef } from 'react';

/**
 * Manages the global case decision modal state shared between
 * Supreme Decisions and LexCode (Codex) views.
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
    // Update refs synchronously so the suppress check works immediately,
    // even within the same React event batch before the state update commits.
    if (selectedCase?.id != null) {
      lastClosedIdRef.current = selectedCase.id;
      suppressUntilRef.current = Date.now() + 750;
    }
    setSelectedCase(null);
  }, [selectedCase]); // selectedCase in deps so we read the current value

  return { selectedCase, selectCase, closeModal };
}
