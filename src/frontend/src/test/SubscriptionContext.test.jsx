/**
 * Smoke tests for SubscriptionContext – subscription gate (canAccess).
 *
 * Covers every tier boundary and the admin / guest-window overrides.
 * All external dependencies (Clerk, fetch, localStorage) are mocked so
 * the suite runs offline with no network or auth service.
 *
 * Run: cd src/frontend && npm test
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';

// ── Mock @clerk/clerk-react before importing anything that reads it ────────────
vi.mock('@clerk/clerk-react', () => ({
  useAuth: vi.fn(),
  useUser: vi.fn(),
}));

// ── Mock freeTierUsage so the guest-window branch is controllable ─────────────
vi.mock('../utils/freeTierUsage', () => ({
  isInGuestWindow:       vi.fn(() => false),
  consumeFreeTierUsage:  vi.fn(),
  notifyUsageBlocked:    vi.fn(),
  GUEST_WINDOW_MS:       86400000,
}));

import { useAuth, useUser } from '@clerk/clerk-react';
import { isInGuestWindow } from '../utils/freeTierUsage';
import { SubscriptionProvider, useSubscription } from '../context/SubscriptionContext';


// ── Test consumer components ──────────────────────────────────────────────────

/** Renders "allowed" / "blocked" based on canAccess(feature). */
function GateProbe({ feature }) {
  const { canAccess, loading } = useSubscription();
  if (loading) return <span data-testid="loading" />;
  return <span data-testid="gate">{canAccess(feature) ? 'allowed' : 'blocked'}</span>;
}

/** Renders tier, isAdmin flag, and tier label for inspection. */
function StateProbe() {
  const { tier, isAdmin, tierLabel, loading } = useSubscription();
  if (loading) return <span data-testid="loading" />;
  return (
    <>
      <span data-testid="tier">{tier}</span>
      <span data-testid="isAdmin">{String(isAdmin)}</span>
      <span data-testid="tierLabel">{tierLabel}</span>
    </>
  );
}

/**
 * Triggers requireAccess via a button click (never during render) and
 * exposes the return value + modal state for assertion.
 *
 * Calling requireAccess during render is illegal in React because it calls
 * setState on the parent provider.  Real call sites are always event handlers.
 */
function RequireProbe({ feature }) {
  const { requireAccess, showUpgradeModal, loading } = useSubscription();
  const [result, setResult] = React.useState(null);
  if (loading) return <span data-testid="loading" />;
  return (
    <>
      <button
        data-testid="triggerBtn"
        onClick={() => setResult(requireAccess(feature) ? 'granted' : 'denied')}
      >
        trigger
      </button>
      {result !== null && <span data-testid="requireResult">{result}</span>}
      <span data-testid="modalOpen">{String(showUpgradeModal)}</span>
    </>
  );
}


// ── Setup helper ──────────────────────────────────────────────────────────────

async function setup({
  feature = 'case_digest_unlimited',
  Probe = GateProbe,
  fetchResponse = null,
  isSignedIn = false,
  token = 'test-token',
} = {}) {
  useAuth.mockReturnValue({
    isSignedIn,
    isLoaded: true,
    getToken: vi.fn().mockResolvedValue(isSignedIn ? token : null),
  });
  useUser.mockReturnValue({
    user: isSignedIn ? { id: 'user_test001' } : null,
    isLoaded: true,
  });
  global.fetch = fetchResponse
    ? vi.fn().mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(fetchResponse),
      })
    : vi.fn().mockResolvedValue({ ok: false, status: 500 });

  render(
    <SubscriptionProvider>
      <Probe feature={feature} />
    </SubscriptionProvider>
  );

  await waitFor(() =>
    expect(screen.queryByTestId('loading')).not.toBeInTheDocument()
  );
}


// ── Tests ─────────────────────────────────────────────────────────────────────

describe('SubscriptionContext — subscription gate (canAccess)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    isInGuestWindow.mockReturnValue(false);
    localStorage.clear();
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ── Signed-out user ─────────────────────────────────────────────────────────

  it('blocks amicus-tier features for a signed-out user', async () => {
    await setup({ feature: 'case_digest_unlimited' });
    expect(screen.getByTestId('gate').textContent).toBe('blocked');
  });

  it('allows features with no tier requirement (signed-out)', async () => {
    // Any key absent from FEATURE_REQUIREMENTS => canAccess returns true
    await setup({ feature: 'nonexistent_open_feature' });
    expect(screen.getByTestId('gate').textContent).toBe('allowed');
  });

  it('allows all features for a signed-out user inside the 24-hour guest window', async () => {
    isInGuestWindow.mockReturnValue(true);
    await setup({ feature: 'case_digest_unlimited' });
    expect(screen.getByTestId('gate').textContent).toBe('allowed');
  });

  // ── Free tier (signed-in) ───────────────────────────────────────────────────

  it('blocks amicus features for a free-tier user', async () => {
    await setup({
      feature: 'case_digest_unlimited',
      isSignedIn: true,
      fetchResponse: { tier: 'free', status: 'inactive', is_admin: false },
    });
    expect(screen.getByTestId('gate').textContent).toBe('blocked');
  });

  it('blocks juris features for a free-tier user', async () => {
    await setup({
      feature: 'codex_linked_cases',
      isSignedIn: true,
      fetchResponse: { tier: 'free', status: 'inactive', is_admin: false },
    });
    expect(screen.getByTestId('gate').textContent).toBe('blocked');
  });

  it('blocks barrister features for a free-tier user', async () => {
    await setup({
      feature: 'lexify',
      isSignedIn: true,
      fetchResponse: { tier: 'free', status: 'inactive', is_admin: false },
    });
    expect(screen.getByTestId('gate').textContent).toBe('blocked');
  });

  // ── Amicus tier ─────────────────────────────────────────────────────────────

  it('allows amicus features for an amicus user', async () => {
    await setup({
      feature: 'case_digest_unlimited',
      isSignedIn: true,
      fetchResponse: { tier: 'amicus', status: 'active', is_admin: false },
    });
    expect(screen.getByTestId('gate').textContent).toBe('allowed');
  });

  it('blocks juris features for an amicus user', async () => {
    await setup({
      feature: 'codex_linked_cases',
      isSignedIn: true,
      fetchResponse: { tier: 'amicus', status: 'active', is_admin: false },
    });
    expect(screen.getByTestId('gate').textContent).toBe('blocked');
  });

  it('blocks barrister features for an amicus user', async () => {
    await setup({
      feature: 'lexify',
      isSignedIn: true,
      fetchResponse: { tier: 'amicus', status: 'active', is_admin: false },
    });
    expect(screen.getByTestId('gate').textContent).toBe('blocked');
  });

  // ── Juris tier ──────────────────────────────────────────────────────────────

  it('allows juris features for a juris user', async () => {
    await setup({
      feature: 'codex_linked_cases',
      isSignedIn: true,
      fetchResponse: { tier: 'juris', status: 'active', is_admin: false },
    });
    expect(screen.getByTestId('gate').textContent).toBe('allowed');
  });

  it('allows amicus features for a juris user (tier is inclusive)', async () => {
    await setup({
      feature: 'case_digest_unlimited',
      isSignedIn: true,
      fetchResponse: { tier: 'juris', status: 'active', is_admin: false },
    });
    expect(screen.getByTestId('gate').textContent).toBe('allowed');
  });

  it('blocks barrister features for a juris user', async () => {
    await setup({
      feature: 'lexify',
      isSignedIn: true,
      fetchResponse: { tier: 'juris', status: 'active', is_admin: false },
    });
    expect(screen.getByTestId('gate').textContent).toBe('blocked');
  });

  // ── Barrister tier ──────────────────────────────────────────────────────────

  it('allows all features for a barrister user', async () => {
    await setup({
      feature: 'lexify',
      isSignedIn: true,
      fetchResponse: { tier: 'barrister', status: 'active', is_admin: false },
    });
    expect(screen.getByTestId('gate').textContent).toBe('allowed');
  });

  // ── Admin override ──────────────────────────────────────────────────────────

  it('allows any feature for an admin regardless of stored tier', async () => {
    await setup({
      feature: 'lexify',
      isSignedIn: true,
      // Backend reports free tier but is_admin=true
      fetchResponse: { tier: 'free', status: 'inactive', is_admin: true },
    });
    expect(screen.getByTestId('gate').textContent).toBe('allowed');
  });

  it('reports tier=barrister, isAdmin=true, and label="Administrator" for admin', async () => {
    await setup({
      Probe: StateProbe,
      isSignedIn: true,
      fetchResponse: { tier: 'free', status: 'inactive', is_admin: true },
    });
    expect(screen.getByTestId('tier').textContent).toBe('barrister');
    expect(screen.getByTestId('isAdmin').textContent).toBe('true');
    expect(screen.getByTestId('tierLabel').textContent).toBe('Administrator');
  });

  // ── testTier localStorage override ──────────────────────────────────────────

  it('applies the localStorage testTier override (free -> barrister)', async () => {
    localStorage.setItem('lexmate_test_tier', 'barrister');
    await setup({
      feature: 'lexify',
      isSignedIn: true,
      fetchResponse: { tier: 'free', status: 'inactive', is_admin: false },
    });
    expect(screen.getByTestId('gate').textContent).toBe('allowed');
  });

  it('ignores an invalid localStorage testTier value', async () => {
    localStorage.setItem('lexmate_test_tier', 'superuser'); // not in TIER_ORDER
    await setup({
      feature: 'lexify',
      isSignedIn: true,
      fetchResponse: { tier: 'free', status: 'inactive', is_admin: false },
    });
    // Falls back to real tier (free) => lexify blocked
    expect(screen.getByTestId('gate').textContent).toBe('blocked');
  });

  // ── requireAccess side-effect ────────────────────────────────────────────────

  it('requireAccess opens the upgrade modal when access is denied', async () => {
    const user = userEvent.setup();
    await setup({
      Probe: RequireProbe,
      feature: 'lexify',
      isSignedIn: true,
      fetchResponse: { tier: 'free', status: 'inactive', is_admin: false },
    });
    await user.click(screen.getByTestId('triggerBtn'));
    expect(screen.getByTestId('requireResult').textContent).toBe('denied');
    await waitFor(() =>
      expect(screen.getByTestId('modalOpen').textContent).toBe('true')
    );
  });

  it('requireAccess does not open the upgrade modal when access is granted', async () => {
    const user = userEvent.setup();
    await setup({
      Probe: RequireProbe,
      feature: 'case_digest_unlimited',
      isSignedIn: true,
      fetchResponse: { tier: 'amicus', status: 'active', is_admin: false },
    });
    await user.click(screen.getByTestId('triggerBtn'));
    expect(screen.getByTestId('requireResult').textContent).toBe('granted');
    expect(screen.getByTestId('modalOpen').textContent).toBe('false');
  });
});
