import { useState, useCallback } from 'react';

const STORAGE_KEY = 'lex-reader-font-size';
const DEFAULT_SIZE = 15;
const MIN_SIZE = 11;
const MAX_SIZE = 24;
const STEP = 1;

export function useFontSize() {
    const [fontSize, setFontSize] = useState(() => {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored) {
                const n = parseInt(stored, 10);
                if (!isNaN(n) && n >= MIN_SIZE && n <= MAX_SIZE) return n;
            }
        } catch {}
        return DEFAULT_SIZE;
    });

    const increase = useCallback(() => {
        setFontSize(prev => {
            const next = Math.min(prev + STEP, MAX_SIZE);
            try { localStorage.setItem(STORAGE_KEY, String(next)); } catch {}
            return next;
        });
    }, []);

    const decrease = useCallback(() => {
        setFontSize(prev => {
            const next = Math.max(prev - STEP, MIN_SIZE);
            try { localStorage.setItem(STORAGE_KEY, String(next)); } catch {}
            return next;
        });
    }, []);

    return { fontSize, increase, decrease };
}
