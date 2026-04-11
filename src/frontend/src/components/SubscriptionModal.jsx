import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, Check, Zap, Star, Crown, Shield, Loader2 } from 'lucide-react';
import { useAuth } from '@clerk/clerk-react';
import { useSubscription } from '../context/SubscriptionContext';

const PLANS = [
  {
    id: 'free',
    name: 'Free',
    icon: <Shield className="w-6 h-6" />,
    price: { monthly: 0, yearly: 0 },
    color: 'from-gray-400 to-slate-500',
    borderColor: 'border-gray-200 dark:border-gray-700',
    accentColor: 'text-gray-600 dark:text-gray-400',
    badgeBg: 'bg-gray-100 dark:bg-gray-800',
    planKey: { monthly: null, yearly: null },
    features: [
      '5 Case Digests / day',
      '5 Bar Questions / day',
      '5 Flashcards / day',
      '5 Case Digest Downloads / day',
      'LexCode (read-only)',
      'LexPlay Codal (5 min / day)',
    ],
    locked: [
      'LexCode Jurisprudence + Case Digests',
      'Unlimited LexPlay',
      'LexPlay Flashcards',
      'LexPlay Bar Questions & Case Digests',
      'Download Tracks to Device',
      'Lexify Bar Simulator',
    ],
  },
  {
    id: 'amicus',
    name: 'Amicus',
    icon: <Zap className="w-6 h-6" />,
    price: { monthly: 199, yearly: 1990 },
    color: 'from-blue-500 to-indigo-600',
    borderColor: 'border-blue-300 dark:border-blue-700',
    accentColor: 'text-blue-600 dark:text-blue-400',
    badgeBg: 'bg-blue-50 dark:bg-blue-900/20',
    planKey: { monthly: 'amicus_monthly', yearly: 'amicus_yearly' },
    features: [
      'Unlimited Case Digests',
      'Unlimited Bar Questions',
      'Unlimited Flashcards',
      'Unlimited Case Digest Downloads',
      'LexCode (read-only)',
      'LexPlay Codal (10 min / day)',
    ],
    locked: [
      'LexCode Jurisprudence + Case Digests',
      'Unlimited LexPlay',
      'LexPlay Flashcards',
      'LexPlay Bar Questions & Case Digests',
      'Download Tracks to Device',
      'Lexify Bar Simulator',
    ],
  },
  {
    id: 'juris',
    name: 'Juris',
    icon: <Star className="w-6 h-6" />,
    price: { monthly: 499, yearly: 4990 },
    color: 'from-purple-500 to-violet-600',
    borderColor: 'border-purple-300 dark:border-purple-700',
    accentColor: 'text-purple-600 dark:text-purple-400',
    badgeBg: 'bg-purple-50 dark:bg-purple-900/20',
    planKey: { monthly: 'juris_monthly', yearly: 'juris_yearly' },
    popular: true,
    features: [
      'Everything in Amicus',
      'LexCode Jurisprudence + Case Digests',
      'Unlimited Codal LexPlay (no daily cap)',
      'LexPlay Flashcards (Concepts + Bar)',
      'Download Tracks to Device (Offline)',
    ],
    locked: [
      'LexPlay Bar Questions & Case Digests',
      'Lexify Bar Simulator',
    ],
  },
  {
    id: 'barrister',
    name: 'Barrister',
    icon: <Crown className="w-6 h-6" />,
    price: { monthly: 999, yearly: 9990 },
    color: 'from-amber-500 to-orange-600',
    borderColor: 'border-amber-300 dark:border-amber-700',
    accentColor: 'text-amber-600 dark:text-amber-400',
    badgeBg: 'bg-amber-50 dark:bg-amber-900/20',
    planKey: { monthly: 'barrister_monthly', yearly: 'barrister_yearly' },
    features: [
      'Everything in Juris',
      'LexPlay Bar Questions & Case Digests',
      'Lexify Bar Exam Simulator',
      'AI Essay Grading (ALAC Rubric)',
      'Mock Bar Attempt Tracking',
      'Full Bar History & Analytics',
    ],
    locked: [],
  },
];

/** Tailwind `md` is 768px — subscription shell matches case digest only below this. */
const MOBILE_SUBSCRIPTION_MQ = '(max-width: 767px)';

export default function SubscriptionModal({ onClose }) {
  const { tier, refreshStatus } = useSubscription();
  const { getToken } = useAuth();
  const [billing, setBilling] = useState('monthly');
  const [availablePlans, setAvailablePlans] = useState({});
  const [bypassMode, setBypassMode] = useState(false);
  const [loadingPlan, setLoadingPlan] = useState(null);
  const [successPlan, setSuccessPlan] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [isMobileLayout, setIsMobileLayout] = useState(() =>
    typeof window !== 'undefined' && window.matchMedia(MOBILE_SUBSCRIPTION_MQ).matches
  );

  useEffect(() => {
    const mq = window.matchMedia(MOBILE_SUBSCRIPTION_MQ);
    const apply = () => setIsMobileLayout(mq.matches);
    apply();
    mq.addEventListener('change', apply);
    return () => mq.removeEventListener('change', apply);
  }, []);

  useEffect(() => {
    fetch('/api/available-plans')
      .then(r => r.json())
      .then(data => {
        setAvailablePlans(data);
        setBypassMode(data.bypass_mode === true);
      })
      .catch(() => {});
  }, []);

  const handleSubscribe = async (plan) => {
    if (plan.id === 'free' || plan.id === tier) return;
    setLoadingPlan(plan.id);
    setErrorMsg('');
    setSuccessPlan(null);

    try {
      const token = await getToken();

      // ── BYPASS MODE: skip PayMongo, grant tier instantly ──────────────────
      if (bypassMode) {
        const planKey = plan.planKey[billing]; // e.g. 'amicus_monthly'
        const res = await fetch('/api/create-checkout', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Clerk-Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({ plan_key: planKey }),
        });
        const data = await res.json();
        if (data.bypass && data.tier) {
          setSuccessPlan(data.tier);
          await refreshStatus();
          setTimeout(() => onClose(), 1500);
        } else {
          setErrorMsg(data.error || 'Bypass failed.');
        }
        return;
      }
      // ─────────────────────────────────────────────────────────────────────

      // Normal PayMongo flow
      const key = plan.planKey[billing];
      const planId = availablePlans[key];
      if (!planId) {
        setErrorMsg('Plan not configured yet. Please try again later.');
        return;
      }
      const res = await fetch('/api/create-checkout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Clerk-Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ plan_id: planId }),
      });
      const data = await res.json();
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else {
        setErrorMsg(data.error || 'Failed to create checkout session.');
      }
    } catch (err) {
      setErrorMsg('Network error. Please try again.');
    } finally {
      setLoadingPlan(null);
    }
  };

  const MAX_LOCKED_SHOWN = 3;

  const billingToggleDesktop = (
    <div className="inline-flex max-w-full shrink-0 items-center gap-0.5 rounded-xl border border-white/20 bg-white/10 p-1 backdrop-blur-sm">
      {['monthly', 'yearly'].map((b) => (
        <button
          key={b}
          type="button"
          onClick={() => setBilling(b)}
          className={`rounded-lg px-2.5 py-1.5 text-[11px] font-bold transition-all sm:px-4 sm:text-xs ${
            billing === b
              ? 'bg-white text-purple-700 shadow-md'
              : 'text-white/80 hover:text-white'
          }`}
        >
          {b === 'monthly' ? (
            'Monthly'
          ) : (
            <>
              Yearly{' '}
              <span className="ml-1 rounded-full bg-green-400/20 px-1.5 py-px text-[10px] font-extrabold text-green-300">
                -17%
              </span>
            </>
          )}
        </button>
      ))}
    </div>
  );

  const panelContent = (
    <>
      {isMobileLayout && (
        <>
          <div className="pointer-events-none absolute left-[-10%] top-[-20%] z-0 h-[500px] w-[500px] rounded-full bg-violet-500/15 blur-[120px]" />
          <div className="pointer-events-none absolute bottom-[-20%] right-[-10%] z-0 h-[500px] w-[500px] rounded-full bg-indigo-500/15 blur-[120px]" />
        </>
      )}

      {/* Header — same purple gradient on mobile and desktop */}
      <div className="relative z-30 shrink-0 overflow-hidden bg-gradient-to-br from-violet-600 via-purple-600 to-indigo-600">
        <div className="pointer-events-none absolute -left-10 -top-10 h-40 w-40 rounded-full bg-white/10 blur-3xl" />
        <div className="pointer-events-none absolute -right-6 -top-6 h-32 w-32 rounded-full bg-fuchsia-400/20 blur-2xl" />
        <div className="pointer-events-none absolute bottom-0 left-1/2 h-24 w-64 -translate-x-1/2 rounded-full bg-indigo-400/20 blur-2xl" />

        <div className="relative flex flex-col gap-3 px-4 py-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between sm:gap-4 sm:px-6 sm:py-4">
          <div className="min-w-0 sm:mr-auto">
            <h2
              id="subscription-modal-title"
              className="text-lg font-extrabold tracking-tight text-white drop-shadow-sm sm:text-xl"
            >
              Upgrade Your Plan
            </h2>
            <p className="mt-0.5 text-[11px] font-medium text-white/70">
              GCash · Maya · Card · GrabPay · BSP Regulated
            </p>
          </div>
          <div className="flex w-full min-w-0 shrink-0 items-center justify-between gap-2 sm:w-auto sm:justify-end sm:gap-3">
            <div className="min-w-0 flex-1 overflow-x-auto pb-0.5 sm:flex-initial sm:overflow-visible">
              {billingToggleDesktop}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="touch-manipulation shrink-0 rounded-full p-2 text-white/70 transition-colors hover:bg-white/15 hover:text-white"
              aria-label="Close"
            >
              <X size={20} />
            </button>
          </div>
        </div>
      </div>

      <div
        className={
          isMobileLayout
            ? 'relative z-10 flex min-h-0 flex-1 flex-col overflow-y-auto lex-modal-scroll bg-gradient-to-b from-slate-50 to-white dark:from-slate-900 dark:to-slate-950 custom-scrollbar'
            : 'relative z-10 flex min-h-0 flex-1 flex-col overflow-y-auto bg-gradient-to-b from-slate-50 to-white dark:from-slate-900 dark:to-slate-950 custom-scrollbar'
        }
      >
        <div
          className={`grid grid-cols-1 gap-4 md:grid-cols-4 md:items-stretch ${isMobileLayout ? 'p-4 sm:p-5' : 'p-5'}`}
        >
          {PLANS.map(plan => {
            const isCurrent = plan.id === tier;
            const isDisabled = plan.id === 'free' || isCurrent || loadingPlan;
            const price = plan.price[billing];
            const visibleLocked = plan.locked.slice(0, MAX_LOCKED_SHOWN);
            const hiddenCount = plan.locked.length - visibleLocked.length;

            return (
              <div
                key={plan.id}
                className={`relative flex flex-col overflow-visible rounded-2xl border-2 ${plan.borderColor} ${isCurrent ? plan.badgeBg : 'bg-white/60 dark:bg-slate-800/60'} p-4 pt-6 transition-all hover:shadow-lg`}
              >
                {/* Badges */}
                {plan.popular && !isCurrent && (
                  <div className="absolute left-1/2 top-2 z-[1] -translate-x-1/2 whitespace-nowrap rounded-full bg-gradient-to-r from-purple-500 to-violet-600 px-3 py-1 text-[10px] font-extrabold uppercase tracking-wide text-white shadow">
                    Most Popular
                  </div>
                )}
                {isCurrent && (
                  <div className="absolute left-1/2 top-2 z-[1] -translate-x-1/2 whitespace-nowrap rounded-full bg-gradient-to-r from-gray-600 to-slate-700 px-3 py-1 text-[10px] font-extrabold uppercase tracking-wide text-white shadow">
                    Current Plan
                  </div>
                )}

                {/* Icon + Name */}
                <div className="mb-2.5 flex items-center gap-2">
                  <div className={`h-9 w-9 rounded-xl bg-gradient-to-br ${plan.color} flex items-center justify-center text-white shadow`}>
                    {React.cloneElement(plan.icon, { className: 'w-5 h-5' })}
                  </div>
                  <h3 className={`text-base font-extrabold ${plan.accentColor}`}>{plan.name}</h3>
                </div>

                {/* Price */}
                <div className="mb-3">
                  {price === 0 ? (
                    <span className="text-2xl font-extrabold text-gray-900 dark:text-white">Free</span>
                  ) : (
                    <>
                      <span className="text-2xl font-extrabold text-gray-900 dark:text-white">
                        ₱{price.toLocaleString()}
                      </span>
                      <span className="text-sm text-gray-400 dark:text-gray-500">/{billing === 'yearly' ? 'yr' : 'mo'}</span>
                    </>
                  )}
                </div>

                {/* Features */}
                <ul className="mb-4 flex-1 space-y-1.5">
                  {plan.features.map(f => (
                    <li key={f} className="flex items-start gap-2 text-xs leading-snug text-gray-700 dark:text-gray-300">
                      <Check className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${plan.accentColor}`} />
                      {f}
                    </li>
                  ))}
                  {visibleLocked.map(f => (
                    <li key={f} className="flex items-start gap-2 text-xs leading-snug text-gray-400 line-through opacity-50 dark:text-gray-600">
                      <X className="mt-0.5 h-3.5 w-3.5 shrink-0 text-gray-300 dark:text-gray-700" />
                      {f}
                    </li>
                  ))}
                  {hiddenCount > 0 && (
                    <li className="pl-5 text-[11px] text-gray-400 dark:text-gray-600">
                      +{hiddenCount} more locked
                    </li>
                  )}
                </ul>

                {/* CTA */}
                <button
                  disabled={!!isDisabled}
                  onClick={() => handleSubscribe(plan)}
                  className={`w-full rounded-xl py-2.5 text-xs font-extrabold transition-all flex items-center justify-center gap-2
                    ${successPlan === plan.id
                      ? 'bg-green-500 text-white'
                      : isCurrent
                        ? 'bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-default'
                        : plan.id === 'free'
                          ? 'bg-gray-100 dark:bg-gray-700 text-gray-400 cursor-default'
                          : `text-white bg-gradient-to-r ${plan.color} hover:opacity-90 active:scale-95 shadow-md`
                    }
                  `}
                >
                  {successPlan === plan.id ? (
                    <><Check className="w-4 h-4" /> Activated!</>
                  ) : loadingPlan === plan.id ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : isCurrent ? (
                    'Current Plan'
                  ) : plan.id === 'free' ? (
                    'Basic Access'
                  ) : (
                    bypassMode ? `⚡ Activate ${plan.name}` : `Get ${plan.name}`
                  )}
                </button>
              </div>
            );
          })}
        </div>

        {errorMsg && (
          <div
            className={`mb-3 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-600 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400 ${isMobileLayout ? 'mx-4 sm:mx-5' : 'mx-5'}`}
          >
            {errorMsg}
          </div>
        )}

        <p
          className={`text-center text-xs text-gray-400 dark:text-gray-600 ${isMobileLayout ? 'px-4 pb-4 sm:px-5 sm:pb-5' : 'px-5 pb-5'}`}
        >
          Secured by PayMongo · Cancel anytime
        </p>
      </div>
    </>
  );

  const overlayClass = isMobileLayout
    ? 'fixed inset-0 z-[540] lex-modal-overlay bg-black/60 backdrop-blur-md animate-in fade-in duration-200'
    : 'fixed inset-0 z-[540] flex items-center justify-center overflow-y-auto overscroll-contain bg-black/60 p-4 backdrop-blur-md animate-in fade-in duration-200 sm:p-6 md:p-8';

  const cardClass = isMobileLayout
    ? 'lex-modal-card glass relative flex max-w-5xl flex-col overflow-hidden rounded-2xl border-2 border-slate-300/85 bg-white/92 shadow-2xl animate-in zoom-in-95 duration-300 dark:border-white/10 dark:bg-slate-900/45'
    : 'relative mx-auto flex w-full max-w-5xl max-h-[min(92vh,56rem)] flex-col overflow-hidden rounded-2xl border-0 bg-white shadow-[0_24px_64px_-12px_rgba(109,40,217,0.35)] animate-in zoom-in-95 duration-300 dark:bg-slate-900 dark:shadow-[0_24px_64px_-12px_rgba(88,28,135,0.45)]';

  return createPortal(
    <div className={overlayClass} onClick={onClose}>
      <div
        className={cardClass}
        role="dialog"
        aria-modal="true"
        aria-labelledby="subscription-modal-title"
        onClick={(e) => e.stopPropagation()}
      >
        {panelContent}
      </div>
    </div>,
    document.body
  );
}
