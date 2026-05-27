/**
 * useGatedFeature — encapsulates the daily-usage metering + upgrade-modal pattern.
 *
 * Reads canAccess / openUpgradeModal / subscriptionLoading from SubscriptionContext
 * and getToken / isSignedIn / isLoaded from Clerk, so callers (e.g. App.jsx) do not
 * need to pass those values around.
 *
 * Usage:
 *   const checkCaseDigest = useGatedFeature('case_digest', 'case_digest_unlimited');
 *   // then in an event handler or async callback:
 *   if (!await checkCaseDigest()) return;
 *
 * @param {string} trackFeature     - Feature key for POST /api/track-usage
 *                                    e.g. 'case_digest' | 'bar_question' | 'flashcard'
 * @param {string} unlimitedFeature - canAccess key that grants unlimited access
 *                                    e.g. 'case_digest_unlimited'
 * @returns {() => Promise<boolean>} Async gate function — true = allowed, false = blocked.
 */
import { useCallback } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { useSubscription } from '../context/SubscriptionContext';
import { consumeFreeTierUsage, notifyUsageBlocked } from '../utils/freeTierUsage';

export function useGatedFeature(trackFeature, unlimitedFeature) {
  const {
    canAccess,
    openUpgradeModal,
    loading: subscriptionLoading,
  } = useSubscription();
  const { getToken, isSignedIn, isLoaded: authLoaded } = useAuth();

  return useCallback(async () => {
    const usage = await consumeFreeTierUsage({
      feature: trackFeature,
      getToken,
      isSignedIn,
      canAccess,
      subscriptionLoading,
      authLoaded,
    });
    if (!usage.allowed) {
      notifyUsageBlocked(usage, openUpgradeModal, unlimitedFeature);
      return false;
    }
    return true;
  }, [
    trackFeature,
    unlimitedFeature,
    getToken,
    isSignedIn,
    canAccess,
    subscriptionLoading,
    authLoaded,
    openUpgradeModal,
  ]);
}
