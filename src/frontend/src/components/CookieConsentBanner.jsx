import React, { useState, useEffect } from 'react';
import { Cookie, X } from 'lucide-react';

const STORAGE_KEY = 'lex_cookie_consent';

export default function CookieConsentBanner({ onGoToLegal }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    try {
      if (!localStorage.getItem(STORAGE_KEY)) setVisible(true);
    } catch {
      // localStorage blocked (private mode, etc.) — show banner, consent won't persist
      setVisible(true);
    }
  }, []);

  const save = (value) => {
    try {
      localStorage.setItem(STORAGE_KEY, value);
    } catch { /* ignore */ }
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div
      role="dialog"
      aria-modal="false"
      aria-label="Cookie consent"
      className="fixed bottom-0 left-0 right-0 z-[600] border-t border-slate-200 bg-white/95 shadow-[0_-4px_24px_rgba(0,0,0,0.08)] backdrop-blur-sm dark:border-slate-700 dark:bg-zinc-900/95"
    >
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:gap-5 sm:px-6 lg:px-8">
        <div className="flex min-w-0 flex-1 items-start gap-3">
          <Cookie
            className="mt-0.5 shrink-0 text-violet-500 dark:text-violet-400"
            size={18}
            strokeWidth={2}
          />
          <p className="min-w-0 text-sm leading-relaxed text-slate-700 dark:text-slate-300">
            <span className="font-semibold text-slate-900 dark:text-white">We use cookies</span>{' '}
            for authentication (Clerk) and core app functionality. No advertising or third-party tracking cookies are used.{' '}
            <button
              type="button"
              onClick={onGoToLegal}
              className="font-medium text-violet-600 underline decoration-violet-400/60 underline-offset-2 hover:text-violet-700 dark:text-violet-400 dark:hover:text-violet-300"
            >
              Privacy policy &amp; terms
            </button>
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={() => save('essential')}
            className="rounded-lg border border-slate-300 bg-transparent px-3.5 py-2 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-50 dark:border-slate-600 dark:text-slate-400 dark:hover:bg-slate-800"
          >
            Essential only
          </button>
          <button
            type="button"
            onClick={() => save('all')}
            className="rounded-lg bg-violet-600 px-4 py-2 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-violet-700 active:bg-violet-800"
          >
            Accept all
          </button>
          <button
            type="button"
            aria-label="Dismiss cookie notice"
            onClick={() => save('essential')}
            className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-300"
          >
            <X size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}

/** Returns the stored consent value, or null if not yet given. */
export function getCookieConsent() {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}
