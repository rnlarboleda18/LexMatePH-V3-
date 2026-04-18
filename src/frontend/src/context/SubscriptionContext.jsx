import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { useAuth, useUser } from '@clerk/clerk-react';
import { isFoundingPromoBarrister, isFoundingPromoModalActive } from '../utils/subscriptionFoundingPromo';

const SubscriptionContext = createContext(null);

/** Guest closed plans modal while founding promo was full — reopen after sign-up if they are not on founding promo. */
const SESSION_REOPEN_SUBSCRIPTION_AFTER_SIGNUP = 'lexmate_reopen_subscription_after_signup';

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

// ─── Hardcoded admin emails (purely frontend, no DB needed) ───────────────────
const ADMIN_EMAILS = [
  'rnlarboleda@gmail.com',
  'rnlarboleda18@gmail.com',
];

function isAdminEmail(emailAddresses = []) {
  return emailAddresses.some((ea) => {
    const addr = (ea.emailAddress || ea || '').trim().toLowerCase();
    return ADMIN_EMAILS.includes(addr);
  });
}

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
  const [foundingPromoSlot, setFoundingPromoSlot] = useState(null);
  const [foundingPromoPending, setFoundingPromoPending] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [upgradeContext, setUpgradeContext] = useState(null);
  const [testTier, setTestTier] = useState(() => getTestTierOverride());
  const [foundingPromoSlotsRemaining, setFoundingPromoSlotsRemaining] = useState(null);

  // Incremented to schedule a retry when getToken() returns null on cold start.
  const [tokenRetry, setTokenRetry] = useState(0);
  const retryTimerRef = useRef(null);
  const userRef = useRef(user);
  userRef.current = user;

  // Effective tier: admin override, then test tier override, then API tier.
  const effectiveTier = isAdmin ? 'barrister' : (testTier || tier);

  const hideSubscriptionModalForFoundingPromo = isFoundingPromoModalActive(
    foundingPromoPending,
    isFoundingPromoBarrister(tier, subscriptionSource, foundingPromoSlot),
  );

  useEffect(() => {
    fetch('/api/available-plans')
      .then((r) => r.json())
      .then((data) => {
        if (typeof data.founding_promo_slots_remaining === 'number') {
          setFoundingPromoSlotsRemaining(data.founding_promo_slots_remaining);
        }
      })
      .catch(() => {});
  }, []);

  const fetchSubscriptionStatus = useCallback(async () => {
    if (!isSignedIn) {
      setTier('free');
      setStatus('inactive');
      setIsAdmin(false);
      setSubscriptionSource(null);
      setFoundingPromoSlot(null);
      setFoundingPromoPending(false);
      setExpiresAt(null);
      setLoading(false);
      return;
    }

    const u = userRef.current;
    if (!u) return;

    const emails = u.emailAddresses || [];
    const clerkAdmin = isAdminEmail(emails);
    if (clerkAdmin) {
      console.log('[Subscription] 🔑 Admin access granted for:', u.primaryEmailAddress?.emailAddress);
      setIsAdmin(true);
      setTier('barrister');
      setStatus('active');
      setFoundingPromoSlot(null);
      setFoundingPromoPending(false);
      setLoading(false);
      return;
    }

    setIsAdmin(false);

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
        setFoundingPromoSlot(
          data.founding_promo_slot !== undefined && data.founding_promo_slot !== null
            ? data.founding_promo_slot
            : null,
        );
        setFoundingPromoPending(data.founding_promo_pending === true);
        setIsAdmin(backendAdmin);
        setTokenRetry(0);
        console.log(`[Subscription] Tier: ${effectiveTier}, Admin: ${backendAdmin}, Email: ${data.email || 'N/A'}`);
      } else {
        console.warn(`[Subscription] Backend API failed (${res.status}). Using test tier: ${testTier || 'free'}`);
        if (testTier) setTier(testTier);
        setFoundingPromoSlot(null);
        setFoundingPromoPending(false);
      }
    } catch (err) {
      console.error('[Subscription] Failed to fetch status:', err);
      if (testTier) setTier(testTier);
      setFoundingPromoSlot(null);
      setFoundingPromoPending(false);
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

  useEffect(() => {
    if (!showUpgradeModal) return;
    if (!hideSubscriptionModalForFoundingPromo) return;
    setShowUpgradeModal(false);
    setUpgradeContext(null);
  }, [showUpgradeModal, hideSubscriptionModalForFoundingPromo]);

  // After sign-up: reopen subscription modal if guest had dismissed it while founding promo was full
  // (so they are not steered away from choosing a paid plan).
  useEffect(() => {
    if (!isLoaded || !isSignedIn || loading) return;
    try {
      const flag = sessionStorage.getItem(SESSION_REOPEN_SUBSCRIPTION_AFTER_SIGNUP);
      if (flag !== '1') return;
      if (hideSubscriptionModalForFoundingPromo) {
        sessionStorage.removeItem(SESSION_REOPEN_SUBSCRIPTION_AFTER_SIGNUP);
        return;
      }
      sessionStorage.removeItem(SESSION_REOPEN_SUBSCRIPTION_AFTER_SIGNUP);
      setShowUpgradeModal(true);
    } catch (_) {}
  }, [isLoaded, isSignedIn, loading, hideSubscriptionModalForFoundingPromo]);

  const isTrial = !isAdmin && subscriptionSource === 'trial' && status === 'active';
  const trialExpiresAt = isTrial ? expiresAt : null;

  const canAccess = (feature) => {
    if (isAdmin) return true;
    const required = FEATURE_REQUIREMENTS[feature];
    if (!required) return true;
    return TIER_ORDER.indexOf(effectiveTier) >= TIER_ORDER.indexOf(required);
  };

  const requireAccess = (feature) => {
    if (canAccess(feature)) return true;
    if (hideSubscriptionModalForFoundingPromo) return false;
    const required = FEATURE_REQUIREMENTS[feature];
    setUpgradeContext({ feature, requiredTier: required });
    setShowUpgradeModal(true);
    return false;
  };

  const openUpgradeModal = (feature = null) => {
    if (hideSubscriptionModalForFoundingPromo) return;
    if (feature) {
      setUpgradeContext({ feature, requiredTier: FEATURE_REQUIREMENTS[feature] || 'amicus' });
    }
    setShowUpgradeModal(true);
  };

  const closeUpgradeModal = () => {
    setShowUpgradeModal(false);
    setUpgradeContext(null);
    try {
      if (
        isLoaded &&
        !isSignedIn &&
        foundingPromoSlotsRemaining === 0
      ) {
        sessionStorage.setItem(SESSION_REOPEN_SUBSCRIPTION_AFTER_SIGNUP, '1');
      }
    } catch (_) {}
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
        subscriptionSource,
        foundingPromoSlot,
        foundingPromoPending,
        hideSubscriptionModalForFoundingPromo,
        loading,
        canAccess,
        requireAccess,
        showUpgradeModal,
        upgradeContext,
        isAdmin,
        openUpgradeModal,
        closeUpgradeModal,
        refreshStatus,
        tierLabel: isAdmin
          ? 'Administrator'
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
