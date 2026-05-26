import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { useAuth, useUser } from '@clerk/clerk-react';
import { isInGuestWindow } from '../utils/freeTierUsage';

const SubscriptionContext = createContext(null);

const TIER_ORDER = ['free', 'amicus', 'juris', 'barrister'];

const FEATURE_REQUIREMENTS = {
  // Amicus unlocks unlimited daily usage (see TRACK_USAGE_FEATURE_TO_UNLIMITED)
  case_digest_unlimited: 'amicus',
  bar_question_unlimited: 'amicus',
  flashcard_unlimited: 'amicus',
  case_digest_download_unlimited: 'amicus',

  // Juris unlocks deeper LexCode features, unlimited codal playback, track downloads, and flashcard audio
  codex_linked_cases: 'juris',   // covers both the jurisprudence panel and the inline case digest sidebar
  lexplay_unlimited: 'juris',    // unlimited codal audio only
  lexplay_flashcard: 'juris',    // concept + bar flashcard audio
  download_tracks: 'juris',

  // Barrister unlocks bar question and case digest audio
  lexplay_bar: 'barrister',
  lexplay_case_digest: 'barrister',

  // Barrister only
  lexify: 'barrister',
};

/** POST /api/track-usage `feature` → `canAccess` / FEATURE_REQUIREMENTS key (Amicus+ skips metering). */
export const TRACK_USAGE_FEATURE_TO_UNLIMITED = {
  case_digest: 'case_digest_unlimited',
  bar_question: 'bar_question_unlimited',
  flashcard: 'flashcard_unlimited',
  case_digest_download: 'case_digest_download_unlimited',
};

const TIER_LABELS = {
  free: 'Free',
  amicus: 'Amicus',
  juris: 'Juris',
  barrister: 'Barrister',
};

// ─── Test/Dev tier override ───────────────────────────────────────────────────
// To test a tier, open your browser console and run:
//   localStorage.setItem('lexmate_test_tier', 'amicus')   // or 'juris', 'barrister', 'free'
// To clear:
//   localStorage.removeItem('lexmate_test_tier')
// Then refresh the page.
function getTestTierOverride() {
  try {
    const val = localStorage.getItem('lexmate_test_tier');
    if (val && TIER_ORDER.includes(val)) return val;
  } catch (_) {}
  return null;
}

export function SubscriptionProvider({ children }) {
  const { getToken, isSignedIn, isLoaded } = useAuth();
  const { user, isLoaded: userLoaded } = useUser();
  const [tier, setTier] = useState('free');
  const [status, setStatus] = useState('inactive');
  const [expiresAt, setExpiresAt] = useState(null);
  const [subscriptionSource, setSubscriptionSource] = useState(null);
  const [canCancelXendit, setCanCancelXendit] = useState(false);
  const [pastDueGraceDays, setPastDueGraceDays] = useState(5);
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [showAccountBillingModal, setShowAccountBillingModal] = useState(false);
  const [upgradeContext, setUpgradeContext] = useState(null);
  const [testTier, setTestTier] = useState(() => getTestTierOverride());

  // Incremented to schedule a retry when getToken() returns null on cold start.
  const [tokenRetry, setTokenRetry] = useState(0);
  const retryTimerRef = useRef(null);
  const userRef = useRef(user);
  userRef.current = user;

  const fetchSubscriptionStatus = useCallback(async () => {
    if (!isSignedIn) {
      setTier('free');
      setStatus('inactive');
      setIsAdmin(false);
      setSubscriptionSource(null);
      setCanCancelXendit(false);
      setExpiresAt(null);
      setPastDueGraceDays(5);
      setLoading(false);
      return 'free';
    }

    const u = userRef.current;
    if (!u) {
      setLoading(true);
      return null;
    }

    try {
      setLoading(true);
      const token = await getToken();

      if (!token) {
        // Clerk session is active but the JWT isn't ready yet (common on cold start).
        // Schedule a retry with exponential backoff (up to ~16 s, 5 attempts).
        setTokenRetry((n) => {
          const attempt = n + 1;
          if (attempt > 5) {
            console.warn('[Subscription] getToken() still null after 5 retries; giving up.');
            setLoading(false);
            return n;
          }
          const delay = Math.min(500 * Math.pow(2, n), 16000); // 500 ms, 1 s, 2 s, 4 s, 8 s…
          console.warn(`[Subscription] getToken() returned null; retry ${attempt} in ${delay}ms`);
          clearTimeout(retryTimerRef.current);
          retryTimerRef.current = setTimeout(() => setTokenRetry(attempt), delay);
          return n;
        });
        return;
      }

      // Token obtained — clear any pending retry.
      clearTimeout(retryTimerRef.current);

      const res = await fetch('/api/subscription-status', {
        headers: { 'X-Clerk-Authorization': `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        const effectiveTier = testTier || data.tier || 'free';
        const backendAdmin = data.is_admin || false;
        setTier(effectiveTier);
        setStatus(data.status || 'inactive');
        setExpiresAt(data.expires_at || null);
        setSubscriptionSource(data.subscription_source || null);
        setCanCancelXendit(data.can_cancel_xendit === true);
        setIsAdmin(backendAdmin);
        const g = data.past_due_grace_days;
        if (typeof g === 'number' && g > 0) setPastDueGraceDays(g);
        setTokenRetry(0);
        console.log(`[Subscription] Tier: ${effectiveTier}, Admin: ${backendAdmin}, Email: ${data.email || 'N/A'}`);
        return effectiveTier;
      } else {
        console.warn(`[Subscription] Backend API failed (${res.status}). Using test tier: ${testTier || 'free'}`);
        if (testTier) setTier(testTier);
        return testTier || 'free';
      }
    } catch (err) {
      console.error('[Subscription] Failed to fetch status:', err);
      if (testTier) setTier(testTier);
      return testTier || null;
    } finally {
      setLoading(false);
    }
  }, [isSignedIn, getToken, testTier]);

  useEffect(() => {
    // Wait until both Clerk auth and user are fully loaded.
    if (!isLoaded || !userLoaded) return;
    if (isSignedIn && !user) return;
    void fetchSubscriptionStatus();
  // tokenRetry re-runs the effect when a scheduled retry fires.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, userLoaded, isSignedIn, user?.id, tokenRetry, fetchSubscriptionStatus]);

  // Cleanup pending retry timers on unmount.
  useEffect(() => () => clearTimeout(retryTimerRef.current), []);

  // After sign-up redirect: if ?subscribe=<plan_id> is in the URL, open the
  // upgrade modal automatically so the user can complete their purchase.
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (!isLoaded || !userLoaded || !isSignedIn) return;
    const params = new URLSearchParams(window.location.search);
    if (!params.get('subscribe')) return;
    // Clean URL immediately
    window.history.replaceState({}, '', window.location.pathname + window.location.hash);
    setShowUpgradeModal(true);
  }, [isLoaded, userLoaded, isSignedIn]);

  // When Xendit redirects the user back after payment (success_return_url includes
  // ?xendit_payment=success), poll subscription-status until the tier is upgraded
  // (webhook may fire a few seconds after return) then clean up the URL.
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    if (params.get('xendit_payment') !== 'success') return;
    if (!isLoaded || !userLoaded || !isSignedIn || !user) return;

    // Remove the query params from the URL immediately (cosmetic)
    const cleanUrl = window.location.pathname + window.location.hash;
    window.history.replaceState({}, '', cleanUrl);

    let attempts = 0;
    let cancelled = false;
    let timer = null;
    const MAX_ATTEMPTS = 20;  // up to ~40 s
    const INTERVAL_MS  = 2000;

    const poll = async () => {
      if (cancelled) return;
      attempts += 1;
      const latestTier = await fetchSubscriptionStatus();
      if (cancelled || latestTier !== 'free' || attempts >= MAX_ATTEMPTS) return;
      timer = setTimeout(poll, INTERVAL_MS);
    };

    void poll();

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [isLoaded, userLoaded, isSignedIn, user, fetchSubscriptionStatus]);

  // Auto-open Account & Billing modal once per browser session when a founding promo user signs in
  useEffect(() => {
    if (loading || !isSignedIn || !user?.id) return;
    const isPromo = subscriptionSource === 'founding_promo' && status === 'active';
    if (!isPromo) return;
    const key = `fp_welcome_${user.id}`;
    if (sessionStorage.getItem(key)) return;
    sessionStorage.setItem(key, '1');
    setShowAccountBillingModal(true);
  }, [loading, isSignedIn, user?.id, subscriptionSource, status]);

  // Effective tier takes admin override first, then test tier, then real tier
  const effectiveTier = isAdmin ? 'barrister' : (testTier || tier);

  const isTrial = !isAdmin && subscriptionSource === 'trial' && status === 'active';
  const trialExpiresAt = isTrial ? expiresAt : null;
  const isFoundingPromo = !isAdmin && subscriptionSource === 'founding_promo' && status === 'active';
  const foundingPromoDaysLeft = isFoundingPromo && expiresAt
    ? Math.max(0, Math.ceil((new Date(expiresAt) - Date.now()) / (1000 * 60 * 60 * 24)))
    : null;

  const canAccess = (feature) => {
    if (isAdmin) return true;
    // 24-hour full access guest window
    if (!isSignedIn && isInGuestWindow()) return true;
    
    const required = FEATURE_REQUIREMENTS[feature];
    if (!required) return true;
    return TIER_ORDER.indexOf(effectiveTier) >= TIER_ORDER.indexOf(required);
  };

  const requireAccess = (feature) => {
    if (canAccess(feature)) return true;
    const required = FEATURE_REQUIREMENTS[feature];
    setUpgradeContext({ feature, requiredTier: required });
    setShowUpgradeModal(true);
    return false;
  };

  const openUpgradeModal = (feature = null) => {
    if (feature) {
      setUpgradeContext({ feature, requiredTier: FEATURE_REQUIREMENTS[feature] || 'amicus' });
    }
    setShowUpgradeModal(true);
  };

  const closeUpgradeModal = () => {
    setShowUpgradeModal(false);
    setUpgradeContext(null);
  };

  const openAccountBillingModal = () => {
    setShowAccountBillingModal(true);
  };

  const closeAccountBillingModal = () => {
    setShowAccountBillingModal(false);
  };

  const refreshStatus = () => fetchSubscriptionStatus();

  // Dev helper: switch test tier from the browser console
  const setTestTierOverride = (newTier) => {
    if (newTier && TIER_ORDER.includes(newTier)) {
      localStorage.setItem('lexmate_test_tier', newTier);
      setTestTier(newTier);
      setTier(newTier);
      console.log(`[Subscription] 🧪 Test tier set to: ${newTier}`);
    } else {
      localStorage.removeItem('lexmate_test_tier');
      setTestTier(null);
      fetchSubscriptionStatus();
      console.log('[Subscription] 🧪 Test tier cleared.');
    }
  };

  return (
    <SubscriptionContext.Provider
      value={{
        tier: effectiveTier,
        status,
        expiresAt,
        isTrial,
        trialExpiresAt,
        isFoundingPromo,
        foundingPromoDaysLeft,
        subscriptionSource,
        canCancelXendit,
        pastDueGraceDays,
        loading,
        canAccess,
        requireAccess,
        showUpgradeModal,
        showAccountBillingModal,
        upgradeContext,
        isAdmin,
        openUpgradeModal,
        closeUpgradeModal,
        openAccountBillingModal,
        closeAccountBillingModal,
        refreshStatus,
        tierLabel: isAdmin
          ? 'Administrator'
          : isFoundingPromo
            ? 'Founding Promo 30-Days Trial'
            : isTrial
              ? `${TIER_LABELS[effectiveTier] || 'Free'} (Trial)`
              : (TIER_LABELS[effectiveTier] || 'Free'),
        TIER_LABELS,
        FEATURE_REQUIREMENTS,
        testTier,
        setTestTierOverride,
      }}
    >
      {children}
    </SubscriptionContext.Provider>
  );
}

export function useSubscription() {
  const ctx = useContext(SubscriptionContext);
  if (!ctx) throw new Error('useSubscription must be used within SubscriptionProvider');
  return ctx;
}
