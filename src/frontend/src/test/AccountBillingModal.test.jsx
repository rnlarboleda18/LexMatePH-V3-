import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

const mockUseSubscription = vi.fn();
const mockGetToken = vi.fn();

vi.mock('@clerk/clerk-react', () => ({
  useAuth: () => ({ getToken: mockGetToken }),
}));

vi.mock('../context/SubscriptionContext', () => ({
  useSubscription: () => mockUseSubscription(),
}));

import AccountBillingModal from '../components/AccountBillingModal';

function baseSub(overrides = {}) {
  return {
    tier: 'amicus',
    tierLabel: 'Amicus',
    status: 'active',
    expiresAt: null,
    subscriptionSource: 'xendit',
    canCancelXendit: true,
    isAdmin: false,
    refreshStatus: vi.fn().mockResolvedValue(undefined),
    openUpgradeModal: vi.fn(),
    ...overrides,
  };
}

describe('AccountBillingModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetToken.mockResolvedValue('test-jwt');
    mockUseSubscription.mockImplementation(() => baseSub());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders account and billing heading', () => {
    const onClose = vi.fn();
    render(<AccountBillingModal onClose={onClose} />);
    expect(screen.getByRole('heading', { name: /account & billing/i })).toBeInTheDocument();
  });

  it('shows cancel subscription when user has a cancellable Xendit plan', () => {
    render(<AccountBillingModal onClose={vi.fn()} />);
    expect(screen.getByRole('button', { name: /cancel subscription/i })).toBeInTheDocument();
  });

  it('hides cancel for admins', () => {
    mockUseSubscription.mockImplementation(() => baseSub({ isAdmin: true, canCancelXendit: true }));
    render(<AccountBillingModal onClose={vi.fn()} />);
    expect(screen.queryByRole('button', { name: /cancel subscription/i })).not.toBeInTheDocument();
  });

  it('hides cancel when no recurring plan', () => {
    mockUseSubscription.mockImplementation(() => baseSub({ canCancelXendit: false }));
    render(<AccountBillingModal onClose={vi.fn()} />);
    expect(screen.queryByRole('button', { name: /cancel subscription/i })).not.toBeInTheDocument();
  });

  it('posts cancel-subscription when confirmed', async () => {
    const onClose = vi.fn();
    const refreshStatus = vi.fn().mockResolvedValue(undefined);
    mockUseSubscription.mockImplementation(() => baseSub({ refreshStatus }));
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ message: 'ok' }),
    });
    vi.stubGlobal('confirm', vi.fn(() => true));
    vi.stubGlobal('fetch', fetchMock);

    render(<AccountBillingModal onClose={onClose} />);
    await userEvent.click(screen.getByRole('button', { name: /cancel subscription/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/cancel-subscription',
        expect.objectContaining({
          method: 'POST',
          headers: { 'X-Clerk-Authorization': 'Bearer test-jwt' },
        })
      );
    });
    expect(refreshStatus).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });
});
