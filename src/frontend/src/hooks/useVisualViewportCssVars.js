import { useEffect } from 'react';

// Change-detection cache — style.setProperty is only called when a value actually
// changes. This makes the visualViewport 'scroll' listener a true no-op during normal
// page scroll (offsetTop stays 0), eliminating the iOS fixed-element repaint jitter
// that the original implementation had.
const _cache = { top: null, left: null, width: null, height: null, keyboardHeight: null };

/**
 * Writes window.visualViewport into :root so fixed layers (header, modals, LexPlayer)
 * track the visible iOS area after Reachability, virtual keyboard, and orientation changes.
 * Falls back to CSS units when VisualViewport API is unavailable.
 */
export function applyVisualViewportToCssVars() {
    if (typeof document === 'undefined') return;
    const el = document.documentElement;
    const vv = typeof window !== 'undefined' && window.visualViewport;

    let top, left, width, height, keyboardHeight;
    if (!vv) {
        top = '0px'; left = '0px'; width = '100vw'; height = '100dvh'; keyboardHeight = '0px';
    } else {
        const px = (n) => `${Math.max(0, Math.round(n * 100) / 100)}px`;
        top    = px(vv.offsetTop);
        left   = px(vv.offsetLeft);
        width  = px(vv.width);
        height = px(vv.height);
        // Keyboard height = layout viewport minus visual viewport height minus Reachability offset.
        // Subtracting vv.offsetTop removes Reachability so only the actual keyboard contributes.
        keyboardHeight = px(Math.max(0, (window.innerHeight || 0) - vv.height - vv.offsetTop));
    }

    let changed = false;
    if (top            !== _cache.top)            { el.style.setProperty('--lex-vv-top',           top);           _cache.top           = top;           changed = true; }
    if (left           !== _cache.left)           { el.style.setProperty('--lex-vv-left',          left);          _cache.left          = left;          changed = true; }
    if (width          !== _cache.width)          { el.style.setProperty('--lex-vv-width',         width);         _cache.width         = width;         changed = true; }
    if (height         !== _cache.height)         { el.style.setProperty('--lex-vv-height',        height);        _cache.height        = height;        changed = true; }
    if (keyboardHeight !== _cache.keyboardHeight) { el.style.setProperty('--lex-keyboard-height',  keyboardHeight); _cache.keyboardHeight = keyboardHeight; changed = true; }

    // Force WebKit to flush its CSS-var dependency cache so elements that use
    // --lex-vv-height / --lex-keyboard-height re-layout synchronously.
    if (changed) void document.body.offsetHeight;
}

function createRafThrottledSync() {
    let raf = 0;
    let settle1 = 0;
    let settle2 = 0;

    function run() {
        // Debounce: cancel any pending RAF so the last event's values always win.
        if (raf) cancelAnimationFrame(raf);
        raf = requestAnimationFrame(() => {
            raf = 0;
            applyVisualViewportToCssVars();
            // Two settle passes cover keyboard-dismiss animations that fire a single
            // resize event mid-animation (leaving --lex-vv-height at a stale value):
            // first pass at 200 ms catches most devices; second at 600 ms catches slow
            // ones whose keyboard animation outlasts the first settle.
            clearTimeout(settle1);
            clearTimeout(settle2);
            settle1 = setTimeout(applyVisualViewportToCssVars, 200);
            settle2 = setTimeout(applyVisualViewportToCssVars, 600);
        });
    }

    run.cancel = () => {
        cancelAnimationFrame(raf);
        clearTimeout(settle1);
        clearTimeout(settle2);
        raf = 0; settle1 = 0; settle2 = 0;
    };

    return run;
}

/**
 * Subscribes once at app root; keeps --lex-vv-* in sync with the iOS visual viewport.
 */
export function useVisualViewportCssVars() {
    useEffect(() => {
        if (typeof window === 'undefined') return undefined;

        // Reset cache so the first applyVisualViewportToCssVars call always writes all vars.
        _cache.top = null; _cache.left = null; _cache.width = null; _cache.height = null; _cache.keyboardHeight = null;

        const run = createRafThrottledSync();
        const vv = window.visualViewport;

        applyVisualViewportToCssVars();

        window.addEventListener('resize', run);
        window.addEventListener('orientationchange', run);
        document.addEventListener('visibilitychange', run);
        window.addEventListener('focus', run);
        window.addEventListener('pageshow', run);

        // focusout fires when any input loses focus (keyboard dismiss). On iOS,
        // visualViewport.resize sometimes does not fire after a programmatic keyboard
        // dismiss — this is a reliable fallback to restore --lex-vv-height.
        const onFocusOut = () => {
            setTimeout(applyVisualViewportToCssVars, 350);
            setTimeout(applyVisualViewportToCssVars, 750);
        };
        document.addEventListener('focusout', onFocusOut, true);

        if (vv) {
            vv.addEventListener('resize', run);
            // 'scroll' fires when the visual viewport scrolls within the layout viewport,
            // which includes iOS Reachability (offsetTop changes). With change detection
            // in applyVisualViewportToCssVars, this is a no-op during normal page scroll
            // (offsetTop stays 0), so it cannot cause fixed-element repaint jitter.
            vv.addEventListener('scroll', run);
        }

        return () => {
            run.cancel();
            window.removeEventListener('resize', run);
            window.removeEventListener('orientationchange', run);
            document.removeEventListener('visibilitychange', run);
            window.removeEventListener('focus', run);
            window.removeEventListener('pageshow', run);
            document.removeEventListener('focusout', onFocusOut, true);
            if (vv) {
                vv.removeEventListener('resize', run);
                vv.removeEventListener('scroll', run);
            }
        };
    }, []);
}
