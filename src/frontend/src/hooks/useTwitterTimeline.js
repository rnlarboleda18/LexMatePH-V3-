import { useEffect } from 'react';

const SCRIPT_ID = 'twitter-wjs';
const WIDGETS_SRC = 'https://platform.twitter.com/widgets.js';

/**
 * Hydrate `.twitter-timeline` inside `containerRef` with X (Twitter) widgets.js.
 * The script is only injected once the container enters the viewport (IntersectionObserver),
 * keeping widgets.js out of the initial page load critical path entirely.
 */
export function useTwitterTimeline(containerRef, deps) {
  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    let cancelled = false;
    let intervalId;
    let observer;

    const w = window;

    const doLoad = (t) => {
      if (cancelled) return;
      const root = containerRef.current;
      if (!t?.widgets?.load) return;
      if (root) t.widgets.load(root);
      else t.widgets.load();
    };

    const startPollTwttr = () => {
      if (intervalId) { clearInterval(intervalId); intervalId = undefined; }
      let tries = 0;
      intervalId = window.setInterval(() => {
        if (cancelled) { clearInterval(intervalId); intervalId = undefined; return; }
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

    /** Called once the container is near the viewport — injects or hydrates the widget. */
    const bootstrap = () => {
      if (cancelled) return;

      if (w.twttr?.widgets?.load) {
        doLoad(w.twttr);
      } else {
        // Queue callback until widgets.js flushes.
        w.twttr = w.twttr || {};
        w.twttr._e = w.twttr._e || [];
        if (typeof w.twttr.ready !== 'function') {
          w.twttr.ready = (f) => w.twttr._e.push(f);
        }
        w.twttr.ready((t) => doLoad(t));
      }

      // Retry after paint and at 1.5s in case anchor was not in DOM at first load.
      const raf = requestAnimationFrame(() => { if (!cancelled && w.twttr?.widgets?.load) doLoad(w.twttr); });
      const t0 = setTimeout(() => { if (!cancelled && w.twttr?.widgets?.load) doLoad(w.twttr); }, 300);
      const t1 = setTimeout(() => { if (!cancelled && w.twttr?.widgets?.load) doLoad(w.twttr); }, 1500);

      // Attach script only once.
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
        cancelAnimationFrame(raf);
        clearTimeout(t0);
        clearTimeout(t1);
      };
    };

    const el = containerRef.current;

    // Use IntersectionObserver so widgets.js is only loaded when the embed
    // scrolls into view (200px ahead). Falls back to immediate bootstrap if
    // IntersectionObserver is unavailable or element is already visible.
    if (el && 'IntersectionObserver' in window) {
      let cleanupBootstrap;
      observer = new IntersectionObserver(
        (entries) => {
          if (entries[0].isIntersecting) {
            observer.disconnect();
            cleanupBootstrap = bootstrap();
          }
        },
        { rootMargin: '200px' }
      );
      observer.observe(el);
    } else {
      bootstrap();
    }

    return () => {
      cancelled = true;
      observer?.disconnect();
      if (intervalId) clearInterval(intervalId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}
