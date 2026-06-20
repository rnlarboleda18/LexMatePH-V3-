import React from 'react';
import { createPortal } from 'react-dom';
import { useClerk } from '@clerk/clerk-react';
import { Gift, X, Sparkles, Star, Crown } from 'lucide-react';

export default function FoundingPromoModal({
  onClose,
  promoDurationDays = 30,
  postPromoTrialHours = 24,
}) {
  const { openSignUp } = useClerk();

  const handleClaim = () => {
    const redirectUrl = `${window.location.origin}${window.location.pathname}${window.location.search}${window.location.hash}`;
    openSignUp({
      redirectUrl,
      unsafeMetadata: { signup_source: 'founding_promo_modal' },
    });
    onClose();
  };

  return createPortal(
    <div
      className="fixed inset-0 z-[540] flex items-center justify-center overflow-y-auto sm:overflow-hidden bg-black/60 backdrop-blur-md animate-in fade-in duration-200 p-4"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-md max-h-[90vh] sm:max-h-none overflow-y-auto sm:overflow-hidden rounded-2xl bg-white shadow-[0_24px_64px_-12px_rgba(245,158,11,0.4)] animate-in zoom-in-95 duration-300 dark:bg-slate-900 dark:shadow-[0_24px_64px_-12px_rgba(180,83,9,0.45)]"
        role="dialog"
        aria-modal="true"
        aria-labelledby="founding-promo-modal-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="pointer-events-none absolute -left-16 -top-16 h-64 w-64 rounded-full bg-amber-400/20 blur-3xl" />
        <div className="pointer-events-none absolute -right-16 bottom-0 h-48 w-48 rounded-full bg-purple-500/15 blur-3xl" />

        <div className="relative overflow-hidden bg-gradient-to-br from-amber-500 via-orange-500 to-amber-600 px-6 py-5">
          <div className="pointer-events-none absolute -left-8 -top-8 h-40 w-40 rounded-full bg-white/10 blur-3xl" />
          <div className="pointer-events-none absolute -right-6 bottom-0 h-32 w-32 rounded-full bg-white/10 blur-2xl" />

          <div className="relative flex items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-white/25 shadow">
                <Gift className="h-6 w-6 text-white" />
              </div>
              <div>
                <div className="text-[10px] font-bold uppercase tracking-widest text-amber-100/80">
                  Limited · Founding Promo
                </div>
                <h2
                  id="founding-promo-modal-title"
                  className="text-lg font-extrabold leading-tight text-white"
                >
                  {promoDurationDays}-Day Barrister Access
                </h2>
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="shrink-0 rounded-full p-2 text-white/70 transition-colors hover:bg-white/15 hover:text-white"
              aria-label="Close"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="relative z-10 px-6 py-6">
          <div className="mb-2 flex items-center gap-1.5 text-amber-500 dark:text-amber-400">
            <Sparkles className="h-3.5 w-3.5 shrink-0" />
            <span className="text-[11px] font-bold uppercase tracking-wider">Congratulations!</span>
          </div>

          <p className="mb-3 text-[17px] font-extrabold leading-snug text-gray-900 dark:text-white">
            You&apos;re eligible for our{' '}
            <span className="text-amber-500 dark:text-amber-400">Founding {promoDurationDays}-day Barrister</span>{' '}
            offer while spots last.
          </p>

          <p className="mb-5 text-sm leading-relaxed text-gray-500 dark:text-gray-400">
            Create a free account from this screen or from the Sign up button in the sidebar — you get the same founding
            slot if one is still open. Full Barrister access (case digests, LexPlay, Lexify, and more) applies right after
            sign-up. Close this window to keep exploring with full access for 24 hours.
          </p>

          <div className="mb-5 flex flex-wrap gap-2">
            {['Unlimited LexPlay', 'Lexify Simulator', 'All Case Digests', 'Bar Questions'].map((perk) => (
              <span
                key={perk}
                className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-1 text-[11px] font-semibold text-amber-700 dark:bg-amber-900/25 dark:text-amber-300"
              >
                <Star className="h-2.5 w-2.5 shrink-0" />
                {perk}
              </span>
            ))}
            <span className="inline-flex items-center gap-1 rounded-full bg-purple-50 px-2.5 py-1 text-[11px] font-semibold text-purple-700 dark:bg-purple-900/25 dark:text-purple-300">
              <Crown className="h-2.5 w-2.5 shrink-0" />
              Founding Barrister
            </span>
          </div>

          <button
            type="button"
            onClick={handleClaim}
            className="w-full rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 px-6 py-3.5 text-sm font-bold text-white shadow-lg shadow-amber-500/30 transition-all hover:from-amber-400 hover:to-orange-400 active:scale-[0.99]"
          >
            Claim with Clerk Sign-Up →
          </button>

          <button
            type="button"
            onClick={onClose}
            className="mt-3 w-full rounded-xl px-6 py-2 text-sm text-gray-400 transition-colors hover:text-gray-600 dark:text-gray-600 dark:hover:text-gray-400"
          >
            Not now — I'll explore for 24 hours first
          </button>

          <p className="mt-4 text-center text-[11px] text-gray-400 dark:text-gray-600">
            No credit card for this promo · After founding spots fill, new accounts typically get a{' '}
            {postPromoTrialHours}-hour trial on the paid tier they pick, then paid plans renew until cancelled
          </p>
        </div>
      </div>
    </div>,
    document.body,
  );
}
