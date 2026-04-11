import React, { createContext, useContext, useState, useEffect } from 'react';
import { useAuth, useUser } from '@clerk/clerk-react';

const SubscriptionContext = createContext(null);

const TIER_ORDER = ['free', 'amicus', 'juris', 'barrister'];

const FEATURE_REQUIREMENTS = {
  // Amicus unlocks unlimited daily usage
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
  const { getToken, isSignedIn } = useAuth();
  const { user } = useUser();
  const [tier, setTier] = useState('free');
  const [status, setStatus] = useState('inactive');
  const [expiresAt, setExpiresAt] = useState(null);
  const [subscriptionSource, setSubscriptionSource] = useState(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [upgradeContext, setUpgradeContext] = useState(null);
  const [testTier, setTestTier] = useState(() => getTestTierOverride());

  // ── Step 1: Check admin PURELY from Clerk's user object (no backend needed) ──
  useEffect(() => {
    if (!user) {
      setIsAdmin(false);
      return;
    }
    const emails = user.emailAddresses || [];
    const admin = isAdminEmail(emails);
    if (admin) {
      console.log('[Subscription] 🔑 Admin access granted for:', user.primaryEmailAddress?.emailAddress);
      setIsAdmin(true);
      setTier('barrister');
      setStatus('active');
      setLoading(false);
    }
  }, [user]);

  // ── Step 2: Fetch from backend (for non-admin users) ──────────────────────────
  const fetchSubscriptionStatus = async () => {
    if (!isSignedIn) {
      setTier('free');
      setStatus('inactive');
      setIsAdmin(false);
      setLoading(false);
      return;
    }
    // Already determined admin via Clerk — skip the potentially failing API call
    if (isAdmin) {
      setLoading(false);
      return;
    }
    try {
      const token = await getToken();
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
        setIsAdmin(backendAdmin);
        console.log(`[Subscription] Tier: ${effectiveTier}, Admin: ${backendAdmin}, Email: ${data.email || 'N/A'}`);
      } else {
        console.warn(`[Subscription] Backend API failed (${res.status}). Using test tier: ${testTier || 'free'}`);
        if (testTier) setTier(testTier);
      }
    } catch (err) {
      console.error('[Subscription] Failed to fetch status:', err);
      if (testTier) setTier(testTier);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubscriptionStatus();
  }, [isSignedIn, isAdmin]);

  // Effective tier takes admin override first, then test tier, then real tier
  const effectiveTier = isAdmin ? 'barrister' : (testTier || tier);

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
