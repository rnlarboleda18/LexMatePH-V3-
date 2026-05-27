/**
 * Self-contained subscription modal wrappers.
 *
 * Both components read their open/close state directly from SubscriptionContext,
 * so App.jsx does not need to destructure showUpgradeModal / closeUpgradeModal /
 * showAccountBillingModal / closeAccountBillingModal and thread them as props.
 *
 * Usage in App.jsx:
 *   import { UpgradeModal, BillingModal } from './components/SubscriptionModals';
 *   // …inside JSX:
 *   <UpgradeModal />
 *   <BillingModal />
 */
import React, { Suspense, lazy } from 'react';
import { useSubscription } from '../context/SubscriptionContext';

const SubscriptionModal  = lazy(() => import('./SubscriptionModal'));
const AccountBillingModal = lazy(() => import('./AccountBillingModal'));

/**
 * Global upgrade / paywall modal.
 * Controlled entirely by SubscriptionContext.openUpgradeModal / closeUpgradeModal.
 */
export function UpgradeModal() {
  const { showUpgradeModal, closeUpgradeModal } = useSubscription();
  if (!showUpgradeModal) return null;
  return (
    <Suspense fallback={null}>
      <SubscriptionModal onClose={closeUpgradeModal} />
    </Suspense>
  );
}

/**
 * Account & Billing modal.
 * Controlled entirely by SubscriptionContext.openAccountBillingModal / closeAccountBillingModal.
 */
export function BillingModal() {
  const { showAccountBillingModal, closeAccountBillingModal } = useSubscription();
  if (!showAccountBillingModal) return null;
  return (
    <Suspense fallback={null}>
      <AccountBillingModal onClose={closeAccountBillingModal} />
    </Suspense>
  );
}
