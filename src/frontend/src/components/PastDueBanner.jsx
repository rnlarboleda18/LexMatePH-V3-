import React, { useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { useSubscription } from '../context/SubscriptionContext';

/**
 * Shows a sticky warning when subscription payment failed and the account is
 * in grace (status === 'past_due'). Grace length comes from the API
 * (PAST_DUE_GRACE_DAYS, default 5). After subscription_expires_at passes,
 * the backend downgrades to Free.
 */
export default function PastDueBanner() {
  const { status, expiresAt, isAdmin, pastDueGraceDays } = useSubscription();
  const [dismissed, setDismissed] = useState(false);

  if (isAdmin || status !== 'past_due' || dismissed) return null;

  const graceDays = typeof pastDueGraceDays === 'number' && pastDueGraceDays > 0 ? pastDueGraceDays : 5;

  const deadlineText = expiresAt
    ? new Date(expiresAt).toLocaleString('en-PH', {
        month: 'long',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        timeZoneName: 'short',
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
        We could not complete your subscription charge for this billing cycle. Our payment partner may retry automatically;
        please ensure your payment method and balance are in good standing.{' '}
        You have a <strong className="font-semibold">{graceDays}-day</strong> grace period (see deadline below).{' '}
        <strong className="font-semibold">
          Full access continues until {deadlineText}. If payment is still not settled after that, your account will be
          downgraded to the Free plan.
        </strong>
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
