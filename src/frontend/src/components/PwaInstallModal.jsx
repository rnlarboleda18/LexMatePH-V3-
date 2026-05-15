import React from 'react';
import { createPortal } from 'react-dom';
import { X, Globe, Share2, Smartphone, Download, MoreVertical } from 'lucide-react';

/** Shown when the browser exposes `beforeinstallprompt` (Chrome / Edge / Android Chrome, etc.). */
const DEFERRED_INSTALL_STEPS = [
  {
    step: '1',
    title: 'Stay on LexMatePH',
    body: "Keep this tab open. Install Now uses your browser's built-in installer.",
    Icon: Globe,
  },
  {
    step: '2',
    title: 'Confirm install',
    body: 'Tap Install Now below, then confirm in the prompt. Or use the install icon in the address bar / menu.',
    Icon: Share2,
  },
  {
    step: '3',
    title: 'Open like an app',
    body: 'Launch LexMatePH from your home screen or app drawer for quicker access and offline use.',
    Icon: Smartphone,
  },
];

/** Add to Home Screen — Safari, Chrome, and other browsers on iPhone / iPad all use WebKit here. */
const IOS_INSTALL_STEPS = [
  {
    step: '1',
    title: 'Open the share menu',
    body: 'Tap Share (square with arrow) in Safari or Chrome on your iPhone or iPad.',
    Icon: Share2,
  },
  {
    step: '2',
    title: 'Add to Home Screen',
    body: 'Scroll the share sheet and tap Add to Home Screen, then Add.',
    Icon: Smartphone,
  },
  {
    step: '3',
    title: 'Launch from the home screen',
    body: 'Tap the LexMatePH icon. If you see Open as Web App, turn it on for a full-screen app feel.',
    Icon: Globe,
  },
];

/** Fallback for Android Chrome when beforeinstallprompt did not fire (e.g. first visit, cooldown). */
const ANDROID_INSTALL_STEPS = [
  {
    step: '1',
    title: 'Open Chrome menu',
    body: 'Tap the three-dot menu in the top-right corner of Chrome.',
    Icon: MoreVertical,
  },
  {
    step: '2',
    title: 'Add to Home Screen',
    body: 'Tap "Add to Home screen" or "Install app" and confirm.',
    Icon: Smartphone,
  },
  {
    step: '3',
    title: 'Launch like a native app',
    body: 'Find LexMatePH on your home screen or app drawer — no browser bar, works offline.',
    Icon: Globe,
  },
];

/** `deferred`: browser install prompt available. `ios`: WebKit. `android`: Android Chrome manual fallback. */
export default function PwaInstallModal({ onClose, deferredPrompt, variant = 'deferred' }) {
  const steps =
    variant === 'ios' ? IOS_INSTALL_STEPS :
    variant === 'android' ? ANDROID_INSTALL_STEPS :
    DEFERRED_INSTALL_STEPS;

  const handleInstallNow = async () => {
    const prompt = deferredPrompt ?? (typeof window !== 'undefined' ? window.__pwaInstallPrompt ?? null : null);
    if (!prompt) return;
    prompt.prompt();
    await prompt.userChoice;
    onClose();
  };

  const intro =
    variant === 'ios' ? (
      <>
        <span className="font-bold text-violet-700 dark:text-violet-400">On iPhone and iPad,</span>{' '}
        add LexMatePH to your Home Screen — it opens like an app and works offline after your first visit.
      </>
    ) : variant === 'android' ? (
      <>
        <span className="font-bold text-violet-700 dark:text-violet-400">On Android,</span>{' '}
        install LexMatePH via Chrome menu — it opens like a native app and works offline.
      </>
    ) : (
      <>
        <span className="font-bold text-violet-700 dark:text-violet-400">Enjoying so far?</span>{' '}
        Install LexMatePH with one tap below, or use your browser install option — launch it like a native app from
        your home screen.
      </>
    );

  return createPortal(
    <div
      className="fixed inset-0 z-[560] flex items-end justify-center sm:items-center bg-black/40 backdrop-blur-sm animate-in fade-in duration-200 p-0 sm:p-4"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-lg overflow-hidden rounded-t-2xl sm:rounded-2xl bg-white shadow-2xl animate-in slide-in-from-bottom duration-300 sm:zoom-in-95 dark:bg-slate-900 dark:shadow-[0_24px_64px_-12px_rgba(109,40,217,0.3)]"
        role="dialog"
        aria-modal="true"
        aria-labelledby="pwa-modal-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="pointer-events-none absolute -left-12 -top-12 h-48 w-48 rounded-full bg-violet-400/15 blur-3xl" />
        <div className="pointer-events-none absolute -right-12 bottom-0 h-40 w-40 rounded-full bg-indigo-400/15 blur-3xl" />

        <div className="mx-auto mt-3 h-1 w-10 rounded-full bg-gray-300 dark:bg-slate-700 sm:hidden" />

        <div className="relative flex items-start justify-between gap-3 px-5 pt-4 pb-3 sm:pt-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-indigo-700 shadow-md shadow-indigo-900/25">
              <Download className="h-5 w-5 text-white" />
            </div>
            <div>
              <h2
                id="pwa-modal-title"
                className="text-sm font-extrabold leading-tight text-gray-900 dark:text-white"
              >
                Install LexMatePH
              </h2>
              <p className="text-[11px] text-gray-500 dark:text-gray-400">
                No app store needed · Works offline
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="mt-0.5 shrink-0 rounded-full p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-slate-800 dark:hover:text-gray-300"
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </div>

        <div className="relative z-10 px-5 pb-5">
          <p className="mb-4 text-sm leading-relaxed text-gray-700 dark:text-gray-300">{intro}</p>

          <ol className="space-y-2.5">
            {steps.map(({ step, title, body, Icon }) => (
              <li
                key={step}
                className="flex gap-3 rounded-xl border border-gray-100 bg-gray-50 p-3 dark:border-slate-700/60 dark:bg-slate-800/50"
              >
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-violet-600 to-indigo-700 shadow-md shadow-indigo-900/20">
                  <Icon className="h-4 w-4 text-white" strokeWidth={2} />
                </div>
                <div className="min-w-0">
                  <p className="text-[10px] font-bold uppercase tracking-widest text-indigo-600 dark:text-indigo-400">
                    Step {step}
                  </p>
                  <p className="mt-0.5 text-xs font-semibold leading-snug text-gray-900 dark:text-white">{title}</p>
                  <p className="mt-0.5 text-[11px] leading-snug text-gray-500 dark:text-gray-400">{body}</p>
                </div>
              </li>
            ))}
          </ol>

          <div className="mt-4 flex gap-2">
            {variant !== 'ios' ? (
              <>
                <button
                  type="button"
                  onClick={handleInstallNow}
                  className="flex-1 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 px-4 py-2.5 text-sm font-bold text-white shadow-md shadow-indigo-900/20 transition-opacity hover:opacity-90 active:scale-[0.99]"
                >
                  Install Now
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm font-bold text-gray-700 transition-colors hover:bg-gray-50 active:scale-[0.99] dark:border-slate-700 dark:bg-slate-800 dark:text-gray-300 dark:hover:bg-slate-700"
                >
                  Got it!
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={onClose}
                className="w-full rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 px-4 py-2.5 text-sm font-bold text-white shadow-md shadow-indigo-900/20 transition-opacity hover:opacity-90 active:scale-[0.99]"
              >
                Got it!
              </button>
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}
