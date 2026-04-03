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
      'LexCode (read-only)',
      'LexPlay (5 min / day)',
    ],
    locked: [
      'Linked Jurisprudence',
      'Unlimited LexPlay',
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
      'LexCode + Linked Jurisprudence',
      'LexPlay (5 min / day)',
      'Case Detail Sidebar',
    ],
    locked: [
      'Unlimited LexPlay',
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
      'Unlimited LexPlay',
      'Full Codal Audio Listening',
      'Add to LexPlaylist — No Limits',
    ],
    locked: ['Lexify Bar Simulator'],
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
      'Lexify Bar Exam Simulator',
      'AI Essay Grading (ALAC Rubric)',
      'Mock Bar Attempt Tracking',
      'Full Bar History & Analytics',
    ],
    locked: [],
  },
];

export default function SubscriptionModal({ onClose }) {
  const { tier, refreshStatus } = useSubscription();
  const { getToken } = useAuth();
  const [billing, setBilling] = useState('monthly');
  const [availablePlans, setAvailablePlans] = useState({});
  const [bypassMode, setBypassMode] = useState(false);
  const [loadingPlan, setLoadingPlan] = useState(null);
  const [successPlan, setSuccessPlan] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');

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

  const panel = (
    <>
      {/* Same bottom anchor as QuestionDetailModal / CaseDecisionModal — sits above mini LexPlayer */}
      <div
        className="glass absolute left-1/2 flex w-full max-w-5xl -translate-x-1/2 flex-col overflow-hidden rounded-t-2xl border-x border-t border-slate-300/85 bg-white/90 shadow-[0_10px_50px_rgba(0,0,0,0.25)] backdrop-blur-2xl dark:border-white/10 dark:bg-slate-900/90 bottom-[var(--player-height,0px)] top-[max(0.75rem,env(safe-area-inset-top,0px))] min-h-0 sm:rounded-2xl sm:border-2 md:bottom-auto md:top-1/2 md:max-h-[min(90vh,calc(100dvh-var(--player-height,0px)-min(5vh,3rem)))] md:min-h-0 md:-translate-x-1/2 md:-translate-y-1/2 md:rounded-3xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="subscription-modal-title"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header: always reachable; not inside scroll (fixes overlap with badges / LexPlayer) */}
        <div className="relative z-20 flex shrink-0 items-center justify-between gap-3 border-b-2 border-slate-200/90 bg-white/95 px-4 py-3 backdrop-blur-sm dark:border-white/10 dark:bg-slate-900/95">
          <h2 id="subscription-modal-title" className="min-w-0 text-lg font-extrabold tracking-tight text-gray-900 dark:text-white sm:text-xl">
            Upgrade Your Plan
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="touch-manipulation shrink-0 rounded-full p-2.5 text-gray-500 transition-colors hover:bg-gray-100 dark:hover:bg-gray-800"
            aria-label="Close"
          >
            <X size={22} />
          </button>
        </div>

        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto overscroll-contain">
          <div className="px-4 pb-2 pt-4 text-center sm:px-6">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Choose the plan that fits your study needs. All subscriptions support GCash, Maya, Card, and GrabPay.
            </p>

            <div className="mt-4 inline-flex items-center gap-1 rounded-xl border border-gray-200 bg-gray-100 p-1 dark:border-gray-700 dark:bg-gray-800">
              {['monthly', 'yearly'].map((b) => (
                <button
                  key={b}
                  type="button"
                  onClick={() => setBilling(b)}
                  className={`rounded-lg px-4 py-2 text-sm font-bold transition-all sm:px-5 ${
                    billing === b
                      ? 'bg-white text-gray-900 shadow-sm dark:bg-slate-700 dark:text-white'
                      : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
                  }`}
                >
                  {b === 'monthly' ? 'Monthly' : 'Yearly'}
                  {b === 'yearly' && (
                    <span className="ml-2 rounded-full bg-green-100 px-1.5 py-0.5 text-[10px] font-extrabold text-green-700 dark:bg-green-900/30 dark:text-green-400">
                      SAVE 17%
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>

        {/* Plan Cards */}
        <div className="grid grid-cols-1 gap-4 px-4 pb-6 sm:grid-cols-2 sm:px-6 lg:grid-cols-4 lg:pb-8">
          {PLANS.map(plan => {
            const isCurrent = plan.id === tier;
            const isDisabled = plan.id === 'free' || isCurrent || loadingPlan;
            const price = plan.price[billing];

            return (
              <div
                key={plan.id}
                className={`relative flex flex-col overflow-visible rounded-2xl border-2 ${plan.borderColor} ${isCurrent ? plan.badgeBg : 'bg-white/60 dark:bg-slate-800/60'} p-5 pt-6 transition-all hover:shadow-lg`}
              >
                {/* Badges inside card top (no negative offset — avoids overlapping modal chrome) */}
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
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${plan.color} flex items-center justify-center text-white mb-3 shadow`}>
                  {plan.icon}
                </div>
                <h3 className={`text-lg font-extrabold ${plan.accentColor} mb-1`}>{plan.name}</h3>

                {/* Price */}
                <div className="mb-4">
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
                <ul className="flex-1 space-y-2 mb-5">
                  {plan.features.map(f => (
                    <li key={f} className="flex items-start gap-2 text-xs text-gray-700 dark:text-gray-300">
                      <Check className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${plan.accentColor}`} />
                      {f}
                    </li>
                  ))}
                  {plan.locked.map(f => (
                    <li key={f} className="flex items-start gap-2 text-xs text-gray-400 dark:text-gray-600 line-through opacity-60">
                      <X className="w-3.5 h-3.5 mt-0.5 shrink-0 text-gray-300 dark:text-gray-700" />
                      {f}
                    </li>
                  ))}
                </ul>

                {/* CTA */}
                <button
                  disabled={!!isDisabled}
                  onClick={() => handleSubscribe(plan)}
                  className={`w-full py-2.5 rounded-xl text-sm font-extrabold transition-all flex items-center justify-center gap-2
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
            <div className="mx-4 mb-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-600 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400 sm:mx-6">
              {errorMsg}
            </div>
          )}

          <p className="px-4 pb-6 text-center text-xs text-gray-400 dark:text-gray-600 sm:px-6">
            Payments processed securely by PayMongo · Cancel anytime · BSP Regulated
          </p>
        </div>
      </div>
    </>
  );

  return createPortal(
    <div className="fixed inset-0 z-[540] animate-in fade-in duration-200">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-md"
        aria-hidden
        onClick={onClose}
      />
      {panel}
    </div>,
    document.body
  );
}
