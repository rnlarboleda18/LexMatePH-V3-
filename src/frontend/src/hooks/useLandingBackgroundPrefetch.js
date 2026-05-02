import { useEffect, useRef } from 'react';
import { startLandingBackgroundPrefetch, shouldSkipAllLandingWarm } from '../utils/landingBackgroundPrefetch';

/**
 * While the user is on the marketing landing, preload LexCode and case-modal chunks (and idly
 * warm the default codal HTTP response). Fires at most once per full page load. Respects
 * save-data and very slow network hints; cleans up on leaving landing or unmount.
 */
export function useLandingBackgroundPrefetch(isLanding) {
  const didRunRef = useRef(false);

  useEffect(() => {
    if (!isLanding) {
      return undefined;
    }
    if (didRunRef.current) {
      return undefined;
    }
    didRunRef.current = true;

    if (shouldSkipAllLandingWarm()) {
      return undefined;
    }

    const cancelled = { v: false };
    const stop = startLandingBackgroundPrefetch({ isCancelled: () => cancelled.v });
    return () => {
      cancelled.v = true;
      stop();
    };
  }, [isLanding]);
}
