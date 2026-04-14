import React, { useState } from 'react';
import { CreditCard, Lock, Loader2, Check, AlertCircle, ArrowLeft } from 'lucide-react';

const PAYMONGO_BASE = 'https://api.paymongo.com/v1';

/**
 * PaymentForm — collects card details client-side and processes payment via
 * the PayMongo PaymentMethod + PaymentIntent attach workflow.
 *
 * Props:
 *   publicKey        {string}  PayMongo public key (pk_test_... / pk_live_...)
 *   paymentIntentId  {string}  PI id returned by /api/create-checkout
 *   clientKey        {string}  PI client key (pi_..._client_key_...)
 *   subscriptionId   {string}  Sub id — passed back to parent for UI
 *   planLabel        {string}  e.g. "Juris Monthly" — shown in UI
 *   clerkToken       {string}  Bearer token for our API
 *   onSuccess        {fn}      Called with no args on successful payment
 *   onCancel         {fn}      Called when user clicks "Back"
 */
export default function PaymentForm({
  publicKey,
  paymentIntentId,
  clientKey,
  subscriptionId,
  planLabel,
  clerkToken,
  onSuccess,
  onCancel,
}) {
  const [cardNumber, setCardNumber] = useState('');
  const [expiry, setExpiry] = useState('');
  const [cvc, setCvc] = useState('');
  const [cardName, setCardName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);

  // ── Formatting helpers ─────────────────────────────────────────────────────
  function formatCardNumber(val) {
    return val
      .replace(/\D/g, '')
      .slice(0, 16)
      .replace(/(.{4})/g, '$1 ')
      .trim();
  }

  function formatExpiry(val) {
    const digits = val.replace(/\D/g, '').slice(0, 4);
    if (digits.length >= 3) return digits.slice(0, 2) + '/' + digits.slice(2);
    return digits;
  }

  // ── Submit ─────────────────────────────────────────────────────────────────
  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // Parse expiry MM/YY
      const [expMonth, expYear] = expiry.split('/').map(s => parseInt(s.trim(), 10));
      if (!expMonth || !expYear || expMonth < 1 || expMonth > 12) {
        setError('Invalid expiry date. Use MM/YY format.');
        setLoading(false);
        return;
      }

      const rawNumber = cardNumber.replace(/\s/g, '');
      if (rawNumber.length < 13) {
        setError('Please enter a valid card number.');
        setLoading(false);
        return;
      }

      // Step 1 — Create PaymentMethod via PayMongo public key
      const pmRes = await fetch(`${PAYMONGO_BASE}/payment_methods`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Basic ${btoa(publicKey + ':')}`,
        },
        body: JSON.stringify({
          data: {
            attributes: {
              type: 'card',
              details: {
                card_number: rawNumber,
                exp_month: expMonth,
                exp_year: expYear < 100 ? 2000 + expYear : expYear,
                cvc,
              },
              billing: {
                name: cardName.trim() || undefined,
              },
            },
          },
        }),
      });

      const pmData = await pmRes.json();
      if (!pmRes.ok) {
        const msg =
          pmData?.errors?.[0]?.detail ||
          pmData?.errors?.[0]?.code ||
          'Failed to create payment method. Check your card details.';
        setError(msg);
        setLoading(false);
        return;
      }

      const paymentMethodId = pmData?.data?.id;
      if (!paymentMethodId) {
        setError('Unexpected response from payment provider. Please try again.');
        setLoading(false);
        return;
      }

      // Step 2 — Attach to our backend (which calls PayMongo attach API)
      const attachRes = await fetch('/api/attach-payment-method', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Clerk-Authorization': `Bearer ${clerkToken}`,
        },
        body: JSON.stringify({
          payment_intent_id: paymentIntentId,
          payment_method_id: paymentMethodId,
          return_url: `${window.location.origin}/?payment=complete`,
        }),
      });

      const attachData = await attachRes.json();

      if (!attachRes.ok || attachData.error) {
        setError(attachData.error || 'Payment failed. Please try again.');
        setLoading(false);
        return;
      }

      const { status, redirect_url } = attachData;

      if (status === 'succeeded') {
        setDone(true);
        setTimeout(() => onSuccess(), 1500);
        return;
      }

      // 3DS required — redirect to PayMongo authentication page
      if (status === 'awaiting_next_action' && redirect_url) {
        window.location.href = redirect_url;
        return;
      }

      setError(`Payment not completed (status: ${status}). Please try again.`);
    } catch (err) {
      setError('Network error. Please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  }

  // ── Success state ──────────────────────────────────────────────────────────
  if (done) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-12 px-6 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-500 shadow-lg">
          <Check className="h-8 w-8 text-white" />
        </div>
        <div>
          <p className="text-lg font-extrabold text-gray-900 dark:text-white">Payment Successful!</p>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Your <span className="font-semibold text-purple-600 dark:text-purple-400">{planLabel}</span> subscription is now active.
          </p>
        </div>
      </div>
    );
  }

  // ── Form ───────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-gray-100 dark:border-white/10 px-5 py-4">
        <button
          type="button"
          onClick={onCancel}
          disabled={loading}
          className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-white/10 dark:hover:text-gray-300 transition-colors"
          aria-label="Back to plans"
        >
          <ArrowLeft size={18} />
        </button>
        <div>
          <p className="text-sm font-extrabold text-gray-900 dark:text-white">
            Complete your payment
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">{planLabel}</p>
        </div>
        <div className="ml-auto flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500">
          <Lock size={11} />
          <span>Secured by PayMongo</span>
        </div>
      </div>

      {/* Card Form */}
      <form onSubmit={handleSubmit} className="flex flex-col gap-4 p-5">
        {/* Card number */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">
            Card Number
          </label>
          <div className="relative">
            <input
              id="pm-card-number"
              type="text"
              inputMode="numeric"
              autoComplete="cc-number"
              placeholder="1234 5678 9012 3456"
              value={cardNumber}
              onChange={e => setCardNumber(formatCardNumber(e.target.value))}
              required
              disabled={loading}
              className="w-full rounded-xl border border-gray-200 dark:border-white/10 bg-white dark:bg-slate-800 px-4 py-3 pr-10 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:border-purple-500 focus:outline-none focus:ring-2 focus:ring-purple-500/20 transition disabled:opacity-50"
            />
            <CreditCard
              size={16}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
            />
          </div>
        </div>

        {/* Cardholder name */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">
            Name on Card
          </label>
          <input
            id="pm-card-name"
            type="text"
            autoComplete="cc-name"
            placeholder="Juan dela Cruz"
            value={cardName}
            onChange={e => setCardName(e.target.value)}
            disabled={loading}
            className="w-full rounded-xl border border-gray-200 dark:border-white/10 bg-white dark:bg-slate-800 px-4 py-3 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:border-purple-500 focus:outline-none focus:ring-2 focus:ring-purple-500/20 transition disabled:opacity-50"
          />
        </div>

        {/* Expiry + CVC */}
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">
              Expiry
            </label>
            <input
              id="pm-expiry"
              type="text"
              inputMode="numeric"
              autoComplete="cc-exp"
              placeholder="MM/YY"
              value={expiry}
              onChange={e => setExpiry(formatExpiry(e.target.value))}
              required
              disabled={loading}
              className="w-full rounded-xl border border-gray-200 dark:border-white/10 bg-white dark:bg-slate-800 px-4 py-3 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:border-purple-500 focus:outline-none focus:ring-2 focus:ring-purple-500/20 transition disabled:opacity-50"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">
              CVC / CVV
            </label>
            <input
              id="pm-cvc"
              type="text"
              inputMode="numeric"
              autoComplete="cc-csc"
              placeholder="123"
              value={cvc}
              onChange={e => setCvc(e.target.value.replace(/\D/g, '').slice(0, 4))}
              required
              disabled={loading}
              className="w-full rounded-xl border border-gray-200 dark:border-white/10 bg-white dark:bg-slate-800 px-4 py-3 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:border-purple-500 focus:outline-none focus:ring-2 focus:ring-purple-500/20 transition disabled:opacity-50"
            />
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-start gap-2 rounded-xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 px-3.5 py-3 text-sm text-red-600 dark:text-red-400">
            <AlertCircle size={15} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Submit */}
        <button
          id="pm-pay-btn"
          type="submit"
          disabled={loading}
          className="mt-1 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 py-3.5 text-sm font-extrabold text-white shadow-md hover:opacity-90 active:scale-95 transition disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {loading ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Processing…
            </>
          ) : (
            <>
              <Lock size={14} />
              Pay Now
            </>
          )}
        </button>

        <p className="text-center text-[11px] text-gray-400 dark:text-gray-600">
          Your card info is sent directly to PayMongo and never stored on our servers.
          Payments are BSP-regulated and PCI-DSS compliant.
        </p>
      </form>
    </div>
  );
}
