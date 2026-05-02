import { describe, it, expect, afterEach } from 'vitest';
import { applyVisualViewportToCssVars } from '../hooks/useVisualViewportCssVars';

describe('applyVisualViewportToCssVars', () => {
    afterEach(() => {
        document.documentElement.removeAttribute('style');
    });

    it('maps visualViewport to --lex-vv-* on :root', () => {
        const vv = {
            offsetTop: 12.4,
            offsetLeft: 0,
            width: 390.5,
            height: 700.1,
        };
        const prev = window.visualViewport;
        Object.defineProperty(window, 'visualViewport', { value: vv, configurable: true, writable: true });
        try {
            applyVisualViewportToCssVars();
        } finally {
            Object.defineProperty(window, 'visualViewport', { value: prev, configurable: true, writable: true });
        }
        const el = document.documentElement;
        expect(el.style.getPropertyValue('--lex-vv-top').trim()).toBe('12.4px');
        expect(el.style.getPropertyValue('--lex-vv-left').trim()).toBe('0px');
        expect(el.style.getPropertyValue('--lex-vv-width').trim()).toBe('390.5px');
        expect(el.style.getPropertyValue('--lex-vv-height').trim()).toBe('700.1px');
    });

    it('falls back when visualViewport is missing', () => {
        const prev = window.visualViewport;
        Object.defineProperty(window, 'visualViewport', { value: undefined, configurable: true, writable: true });
        try {
            applyVisualViewportToCssVars();
        } finally {
            Object.defineProperty(window, 'visualViewport', { value: prev, configurable: true, writable: true });
        }
        const el = document.documentElement;
        expect(el.style.getPropertyValue('--lex-vv-top').trim()).toBe('0px');
        expect(el.style.getPropertyValue('--lex-vv-height').trim()).toBe('100dvh');
    });
});
