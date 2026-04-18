import React from 'react';
import { Download, Share2, X } from 'lucide-react';

/**
 * Non-landing routes: encourages PWA install. Chromium gets an Install button when
 * `beforeinstallprompt` was captured; iOS shows Share-sheet instructions.
 */
const PwaInstallBanner = ({
  isDarkMode,
  visible,
  canPrompt,
  isIos,
  isAndroid = false,
  onInstall,
  onDismiss,
}) => {
  if (!visible) return null;

  return (
    <div
      className={`pointer-events-auto fixed inset-x-0 bottom-0 z-[60] border-t px-3 py-3 shadow-[0_-8px_32px_rgba(0,0,0,0.12)] backdrop-blur-md sm:px-4 ${
        isDarkMode
          ? 'border-zinc-700 bg-zinc-900/95 text-zinc-100'
          : 'border-violet-200/80 bg-white/95 text-neutral-900'
      }`}
      style={{ paddingBottom: 'max(0.75rem, env(safe-area-inset-bottom))' }}
      role="region"
      aria-label="Install LexMatePH"
    >
      <div className="mx-auto flex max-w-4xl flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold leading-snug">Install LexMatePH</p>
          {isIos ? (
            <div className="mt-0.5 space-y-1.5 text-xs text-neutral-600 dark:text-zinc-400">
              <p>
                Tap{' '}
                <span className="inline-flex items-center gap-0.5 font-medium text-violet-700 dark:text-violet-300">
                  <Share2 className="inline h-3.5 w-3.5" aria-hidden />
                  Share
                </span>{' '}
                → <strong>Add to Home Screen</strong> for a full-screen app icon and offline access.
              </p>
              <p>
                <span className="font-semibold text-neutral-700 dark:text-zinc-300">iPad / iPhone Chrome:</span> Apple
                does not allow the usual “Install app” store-style flow in third-party browsers; use{' '}
                <strong>Share → Add to Home Screen</strong> (same as Safari).
              </p>
            </div>
          ) : (
            <div className="mt-0.5 space-y-1.5 text-xs text-neutral-600 dark:text-zinc-400">
              <p>Add LexMatePH to your home screen for faster launch and offline-ready study.</p>
              {isAndroid && canPrompt && (
                <p className="text-[11px] leading-snug text-neutral-500 dark:text-zinc-500">
                  On Android Chrome you may not see an address bar install icon (that is normal) — use{' '}
                  <strong>Install</strong> here or <strong>⋮ → Install app</strong>.
                </p>
              )}
              {isAndroid && !canPrompt && (
                <p>
                  <span className="font-semibold text-neutral-700 dark:text-zinc-300">Android (tablet or phone):</span>{' '}
                  Chrome often <strong>does not show</strong> an install icon in the address bar anymore. Open{' '}
                  <strong>⋮</strong> → <strong>Install app</strong> or <strong>Add to Home screen</strong>. If missing,
                  turn off <strong>Desktop site</strong> (⋮ menu) so the page is in mobile layout, then check again. Not
                  available in <strong>Incognito</strong>.
                </p>
              )}
              {!isAndroid && !canPrompt && (
                <p>
                  <span className="font-semibold text-neutral-700 dark:text-zinc-300">No install button here?</span>{' '}
                  Chrome does not offer PWA install in <strong>Incognito</strong>. In a normal tab, use the{' '}
                  <strong>⋮</strong> menu → install or add to home; on some versions{' '}
                  <strong>Save and share → Install page as app</strong>.
                </p>
              )}
            </div>
          )}
        </div>
        <div className="flex shrink-0 items-center justify-end gap-2">
          {!isIos && canPrompt && (
            <button
              type="button"
              onClick={() => void onInstall()}
              className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 px-3 py-2 text-xs font-bold uppercase tracking-wide text-white shadow-md shadow-indigo-900/20 transition hover:opacity-95 sm:text-sm"
            >
              <Download className="h-4 w-4" aria-hidden />
              Install
            </button>
          )}
          <button
            type="button"
            onClick={onDismiss}
            className={`rounded-lg p-2 transition ${
              isDarkMode
                ? 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100'
                : 'text-neutral-500 hover:bg-neutral-100 hover:text-neutral-800'
            }`}
            aria-label="Dismiss install reminder"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default PwaInstallBanner;
