import { useEffect } from 'react';

/**
 * Writes window.visualViewport into :root so fixed layers (modals, LexPlayer) track
 * the visible iOS area after Reachability, virtual keyboard, and similar changes.
 * Falls back to full-layout viewport when VisualViewport is missing.
 */
export function applyVisualViewportToCssVars() {
    if (typeof document === 'undefined') return;
    const el = document.documentElement;
    const vv = typeof window !== 'undefined' && window.visualViewport;
    if (!vv) {
        el.style.setProperty('--lex-vv-top', '0px');
        el.style.setProperty('--lex-vv-left', '0px');
        el.style.setProperty('--lex-vv-width', '100vw');
        el.style.setProperty('--lex-vv-height', '100dvh');
        return;
    }
    const px = (n) => `${Math.max(0, Math.round(n * 100) / 100)}px`;
    el.style.setProperty('--lex-vv-top', px(vv.offsetTop));
    el.style.setProperty('--lex-vv-left', px(vv.offsetLeft));
    el.style.setProperty('--lex-vv-width', px(vv.width));
    el.style.setProperty('--lex-vv-height', px(vv.height));
}

function createRafThrottledSync() {
    let raf = 0;
    let settle = 0;

    function run() {
        // Debounce: cancel any queued RAF so the last event's values always win.
        // The old "skip if pending" approach could drop the final keyboard-dismiss
        // resize, leaving --lex-vv-height permanently stuck at the keyboard height.
        if (raf) cancelAnimationFrame(raf);
        raf = requestAnimationFrame(() => {
            raf = 0;
            applyVisualViewportToCssVars();
            // Settle pass: iOS keyboard animations complete ~300 ms after the last
            // resize event — re-sync once to pick up the fully-restored height.
            clearTimeout(settle);
            settle = setTimeout(applyVisualViewportToCssVars, 300);
        });
    }

    run.cancel = () => {
        cancelAnimationFrame(raf);
        clearTimeout(settle);
        raf = 0;
        settle = 0;
    };

    return run;
}

/**
 * Subscribes once at app root; keeps --lex-vv-* in sync.
 */
export function useVisualViewportCssVars() {
    useEffect(() => {
        if (typeof window === 'undefined') return undefined;

        const run = createRafThrottledSync();
        const vv = window.visualViewport;

        applyVisualViewportToCssVars();

        window.addEventListener('resize', run);
        window.addEventListener('orientationchange', run);
        document.addEventListener('visibilitychange', run);
        window.addEventListener('focus', run);
        window.addEventListener('pageshow', run);

        if (vv) {
            vv.addEventListener('resize', run);
            // 'scroll' intentionally omitted: visualViewport.scroll fires on every
            // page scroll but offsetTop/offsetLeft don't change during normal
            // scrolling — only during Reachability/keyboard transitions, which
            // already fire 'resize'. Listening to 'scroll' caused the header and
            // mini player to jitter on iOS during rubber-band / Reachability scroll.
        }

        return () => {
            run.cancel();
            window.removeEventListener('resize', run);
            window.removeEventListener('orientationchange', run);
            document.removeEventListener('visibilitychange', run);
            window.removeEventListener('focus', run);
            window.removeEventListener('pageshow', run);
            if (vv) {
                vv.removeEventListener('resize', run);
            }
        };
    }, []);
}
