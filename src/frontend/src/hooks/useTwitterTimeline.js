import { useEffect } from 'react';

const SCRIPT_ID = 'twitter-wjs';

/**
 * Load X (Twitter) widgets.js once and hydrate `.twitter-timeline` inside `containerRef`.
 * In-project iframe proxies often fail; embedding on the same document avoids nested iframe issues.
 *
 * @param {React.MutableRefObject<HTMLElement | null>} containerRef
 * @param {unknown[]} deps — e.g. `[isDarkMode]` to re-run after `data-theme` changes
 */
export function useTwitterTimeline(containerRef, deps) {
  useEffect(() => {
    const runLoad = () => {
      const root = containerRef.current;
      if (!root || typeof window === 'undefined' || !window.twttr?.widgets) return;
      window.twttr.widgets.load(root);
    };

    const existing = document.getElementById(SCRIPT_ID);
    if (existing) {
      if (window.twttr?.widgets) {
        runLoad();
      } else {
        existing.addEventListener('load', runLoad, { once: true });
      }
      return;
    }

    const script = document.createElement('script');
    script.id = SCRIPT_ID;
    script.src = 'https://platform.twitter.com/widgets.js';
    script.async = true;
    script.setAttribute('charset', 'utf-8');
    script.addEventListener('load', runLoad, { once: true });
    document.body.appendChild(script);
    // Intentionally no cleanup: one shared script; removing it breaks Strict Mode remounts.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}
