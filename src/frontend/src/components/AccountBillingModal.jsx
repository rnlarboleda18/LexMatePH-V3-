import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, Loader2 } from 'lucide-react';
import { useAuth } from '@clerk/clerk-react';
import { useSubscription } from '../context/SubscriptionContext';

const MOBILE_MQ = '(max-width: 767px)';

function formatSource(src) {
  if (!src) return null;
  const map = {
    xendit: 'Xendit subscription',
    trial: 'Trial',
    founding_promo: 'Founding promo',
    admin_override: 'Admin',
  };
  return map[src] || src;
}

export default function AccountBillingModal({ onClose }) {
  const {
    tier,
    tierLabel,
    status,
    expiresAt,
    subscriptionSource,
    canCancelXendit,
    isAdmin,
    refreshStatus,
    openUpgradeModal,
  } = useSubscription();
  const { getToken } = useAuth();
  const [busy, setBusy] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [isMobileLayout, setIsMobileLayout] = useState(() =>
    typeof window !== 'undefined' && window.matchMedia(MOBILE_MQ).matches
  );

  useEffect(() => {
    const mq = window.matchMedia(MOBILE_MQ);
    const apply = () => setIsMobileLayout(mq.matches);
    apply();
    mq.addEventListener('change', apply);
    return () => mq.removeEventListener('change', apply);
  }, []);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const handleCancelSubscription = async () => {
    if (!canCancelXendit || isAdmin) return;
    if (!window.confirm(
      'Cancel your subscription? You will keep full access until the end of your current paid period, then automatically move to the Free plan.'
    )) {
      return;
    }
    setBusy(true);
    setErrorMsg('');
    try {
      const token = await getToken();
      if (!token) {
        setErrorMsg('Could not get a session token. Please try again.');
        return;
      }
      const res = await fetch('/api/cancel-subscription', {
        method: 'POST',
        headers: { 'X-Clerk-Authorization': `Bearer ${token}` },
      });
      let data = {};
      const text = await res.text();
      try {
        data = text ? JSON.parse(text) : {};
      } catch {
        data = { error: text || `HTTP ${res.status}` };
      }
      if (!res.ok) {
        setErrorMsg(data.error || data.message || `Request failed (${res.status})`);
        return;
      }
      await refreshStatus();
      onClose();
    } catch (err) {
      setErrorMsg(err.message || 'Network error');
    } finally {
      setBusy(false);
    }
  };

  const sourceLabel = formatSource(subscriptionSource);
  const alreadyCancelled = status === 'cancelled';
  const showCancel = !isAdmin && canCancelXendit && !alreadyCancelled;

  const overlayClass = isMobileLayout
    ? 'fixed inset-0 z-[540] lex-modal-overlay bg-black/60 backdrop-blur-md animate-in fade-in duration-200'
    : 'fixed inset-0 z-[540] flex items-center justify-center overflow-y-auto overscroll-contain bg-black/60 p-4 backdrop-blur-md animate-in fade-in duration-200 sm:p-6';

  const cardClass = isMobileLayout
    ? 'lex-modal-card relative mx-3 flex max-w-md flex-col overflow-hidden rounded-2xl border border-lex bg-white shadow-2xl dark:border-lex dark:bg-zinc-900'
    : 'relative mx-auto flex w-full max-w-md flex-col overflow-hidden rounded-2xl border border-lex bg-white shadow-2xl dark:border-lex dark:bg-zinc-900';

  return createPortal(
    <div className={overlayClass} onClick={onClose}>
      <div
        className={cardClass}
        role="dialog"
        aria-modal="true"
        aria-labelledby="account-billing-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 border-b border-violet-200/60 bg-gradient-to-br from-violet-600 via-purple-600 to-indigo-600 px-4 py-3 sm:px-5 sm:py-4">
          <div className="min-w-0">
            <h2 id="account-billing-title" className="text-lg font-extrabold tracking-tight text-white">
              Account & Billing
            </h2>
            <p className="mt-0.5 text-xs font-medium text-white/75">Plan and subscription management</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="touch-manipulation shrink-0 rounded-full p-2 text-white/80 transition-colors hover:bg-white/15 hover:text-white"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>

        <div className="space-y-4 p-4 sm:p-5">
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between gap-3">
              <dt className="text-gray-500 dark:text-gray-400">Current plan</dt>
              <dd className="font-semibold text-gray-900 dark:text-zinc-100">{tierLabel}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-gray-500 dark:text-gray-400">Status</dt>
              <dd className="font-medium capitalize text-gray-800 dark:text-zinc-200">{status || '—'}</dd>
            </div>
            {sourceLabel && (
              <div className="flex justify-between gap-3">
                <dt className="text-gray-500 dark:text-gray-400">Billing type</dt>
                <dd className="text-right text-gray-800 dark:text-zinc-200">{sourceLabel}</dd>
              </div>
            )}
            {expiresAt && status === 'cancelled' && (
              <div className="flex justify-between gap-3">
                <dt className="text-gray-500 dark:text-gray-400">Access until</dt>
                <dd className="text-right font-medium text-amber-700 dark:text-amber-400">
                  {new Date(expiresAt).toLocaleDateString()}
                </dd>
              </div>
            )}
            {expiresAt && status !== 'cancelled' && (
              <div className="flex justify-between gap-3">
                <dt className="text-gray-500 dark:text-gray-400">Next renewal</dt>
                <dd className="text-right text-gray-800 dark:text-zinc-200">
                  {new Date(expiresAt).toLocaleDateString()}
                </dd>
              </div>
            )}
          </dl>

          {status === 'cancelled' && expiresAt && tier !== 'free' && (
            <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
              Your subscription is cancelled. You keep full {tierLabel} access until <strong>{new Date(expiresAt).toLocaleDateString()}</strong>, then your account moves to the Free plan automatically.
            </p>
          )}

          {errorMsg && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-300">
              {errorMsg}
            </div>
          )}

          <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
            {!isAdmin && tier === 'free' && (
              <button
                type="button"
                onClick={() => {
                  onClose();
                  openUpgradeModal();
                }}
                className="order-2 rounded-xl bg-gradient-to-r from-violet-600 to-purple-700 px-4 py-2.5 text-sm font-bold text-white shadow-md transition-opacity hover:opacity-95 sm:order-1"
              >
                View plans
              </button>
            )}
            {showCancel && (
              <button
                type="button"
                disabled={busy}
                onClick={handleCancelSubscription}
                className="order-1 rounded-xl border-2 border-red-300 bg-white px-4 py-2.5 text-sm font-bold text-red-700 transition-colors hover:bg-red-50 disabled:opacity-60 dark:border-red-800 dark:bg-zinc-900 dark:text-red-400 dark:hover:bg-red-950/40 sm:order-2"
              >
                {busy ? (
                  <span className="inline-flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                    Cancelling…
                  </span>
                ) : (
                  'Cancel subscription'
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}
