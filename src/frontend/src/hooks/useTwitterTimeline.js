import { useEffect } from 'react';

const SCRIPT_ID = 'twitter-wjs';
const WIDGETS_SRC = 'https://platform.twitter.com/widgets.js';

/**
 * Hydrate `.twitter-timeline` inside `containerRef` with X (Twitter) widgets.js.
 * `index.html` must define `window.twttr` and load widgets.js (same as publish.twitter.com) so
 * the API merges the `_e` queue. This hook schedules `twttr.widgets.load` and falls back
 * to a script tag in tests (no index) or if the id is missing.
 */
export function useTwitterTimeline(containerRef, deps) {
  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    let cancelled = false;
    let intervalId;

    const w = window;

    const doLoad = (t) => {
      if (cancelled) return;
      const root = containerRef.current;
      if (!t?.widgets?.load) return;
      if (root) t.widgets.load(root);
      else t.widgets.load();
    };

    if (w.twttr?.widgets?.load) {
      doLoad(w.twttr);
    } else {
      // Must match publish.twitter.com: queue until widgets.js flushes (see index.html).
      w.twttr = w.twttr || {};
      w.twttr._e = w.twttr._e || [];
      if (typeof w.twttr.ready !== 'function') {
        w.twttr.ready = function (f) {
          w.twttr._e.push(f);
        };
      }
      w.twttr.ready((t) => {
        doLoad(t);
      });
    }

    // After paint, try again in case the anchor was not in the DOM when the first load ran.
    const raf = requestAnimationFrame(() => {
      if (cancelled) return;
      if (w.twttr?.widgets?.load) doLoad(w.twttr);
    });
    const t0 = setTimeout(() => {
      if (cancelled) return;
      if (w.twttr?.widgets?.load) doLoad(w.twttr);
    }, 300);
    const t1 = setTimeout(() => {
      if (cancelled) return;
      if (w.twttr?.widgets?.load) doLoad(w.twttr);
    }, 1500);

    const startPollTwttr = () => {
      if (intervalId) {
        clearInterval(intervalId);
        intervalId = undefined;
      }
      let tries = 0;
      intervalId = window.setInterval(() => {
        if (cancelled) {
          clearInterval(intervalId);
          intervalId = undefined;
          return;
        }
        tries += 1;
        if (w.twttr?.widgets?.load) {
          doLoad(w.twttr);
          clearInterval(intervalId);
          intervalId = undefined;
        } else if (tries > 100) {
          clearInterval(intervalId);
          intervalId = undefined;
        }
      }, 100);
    };

    if (!document.getElementById(SCRIPT_ID)) {
      const script = document.createElement('script');
      script.id = SCRIPT_ID;
      script.src = WIDGETS_SRC;
      script.async = true;
      script.setAttribute('charset', 'utf-8');
      script.addEventListener('load', startPollTwttr, { once: true });
      document.body.appendChild(script);
    } else if (!w.twttr?.widgets?.load) {
      startPollTwttr();
    }

    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      clearTimeout(t0);
      clearTimeout(t1);
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}
