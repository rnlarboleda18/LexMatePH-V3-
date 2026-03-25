import React, { createContext, useContext, useState, useEffect } from 'react';
import { useAuth } from '@clerk/clerk-react';

const SubscriptionContext = createContext(null);

const TIER_ORDER = ['free', 'amicus', 'juris', 'barrister'];

const FEATURE_REQUIREMENTS = {
  case_digest_unlimited: 'amicus',
  bar_question_unlimited: 'amicus',
  flashcard_unlimited: 'amicus',
  codex_linked_cases: 'amicus',
  lexplay_unlimited: 'juris',
  lexify: 'barrister',
};

const TIER_LABELS = {
  free: 'Free',
  amicus: 'Amicus',
  juris: 'Juris',
  barrister: 'Barrister',
};

export function SubscriptionProvider({ children }) {
  const { getToken, isSignedIn } = useAuth();
  const [tier, setTier] = useState('free');
  const [status, setStatus] = useState('inactive');
  const [expiresAt, setExpiresAt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [upgradeContext, setUpgradeContext] = useState(null); // { feature, requiredTier }

  const fetchSubscriptionStatus = async () => {
    if (!isSignedIn) {
      setTier('free');
      setStatus('inactive');
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
        setTier(data.tier || 'free');
        setStatus(data.status || 'inactive');
        setExpiresAt(data.expires_at || null);
      }
    } catch (err) {
      console.error('Failed to fetch subscription status:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubscriptionStatus();
  }, [isSignedIn]);

  const canAccess = (feature) => {
    const required = FEATURE_REQUIREMENTS[feature];
    if (!required) return true;
    return TIER_ORDER.indexOf(tier) >= TIER_ORDER.indexOf(required);
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

  return (
    <SubscriptionContext.Provider
      value={{
        tier,
        status,
        expiresAt,
        loading,
        canAccess,
        requireAccess,
        showUpgradeModal,
        upgradeContext,
        openUpgradeModal,
        closeUpgradeModal,
        refreshStatus,
        tierLabel: TIER_LABELS[tier] || 'Free',
        TIER_LABELS,
        FEATURE_REQUIREMENTS,
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
