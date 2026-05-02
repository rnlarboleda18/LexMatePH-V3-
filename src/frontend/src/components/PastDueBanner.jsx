import React, { useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { useSubscription } from '../context/SubscriptionContext';

/**
 * Shows a sticky warning banner when the user's payment has failed and the
 * account is in a grace period (status === 'past_due').
 *
 * The backend sets subscription_expires_at = NOW() + 30 days on the first
 * failed cycle, so expiresAt here is the last day of free access. After
 * that, expire_past_due_xendit_sub() downgrades the account to Free.
 */
export default function PastDueBanner() {
  const { status, expiresAt, isAdmin } = useSubscription();
  const [dismissed, setDismissed] = useState(false);

  if (isAdmin || status !== 'past_due' || dismissed) return null;

  const deadlineText = expiresAt
    ? new Date(expiresAt).toLocaleDateString('en-PH', {
        month: 'long', day: 'numeric', year: 'numeric',
      })
    : 'soon';

  return (
    <div
      role="alert"
      aria-live="assertive"
      className="sticky top-0 z-50 flex items-start gap-3 px-4 py-3
                 bg-amber-50 border-b border-amber-300
                 dark:bg-amber-900/30 dark:border-amber-700
                 text-amber-900 dark:text-amber-200
                 text-sm leading-relaxed"
    >
      <AlertTriangle className="mt-0.5 shrink-0 text-amber-500 dark:text-amber-400" size={16} />

      <p className="flex-1">
        <strong className="font-semibold">Payment failed.</strong>{' '}
        We were unable to charge your payment method for this billing cycle.
        Xendit will retry automatically — please ensure your account has sufficient funds.{' '}
        Your {'\u00a0'}
        <strong className="font-semibold">full access is maintained until {deadlineText}</strong>.
        After that, your account will move to the Free plan if payment remains unsettled.
      </p>

      <button
        type="button"
        aria-label="Dismiss payment warning"
        onClick={() => setDismissed(true)}
        className="shrink-0 mt-0.5 rounded p-0.5 hover:bg-amber-100
                   dark:hover:bg-amber-800/50 transition-colors"
      >
        <X size={14} />
      </button>
    </div>
  );
}
