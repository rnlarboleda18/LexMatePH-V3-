import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import PwaInstallModal from '../components/PwaInstallModal';

describe('PwaInstallModal', () => {
  it('ios variant shows home-screen steps without Install Now', () => {
    render(<PwaInstallModal variant="ios" onClose={() => {}} />);
    expect(screen.getByText(/On iPhone and iPad/i)).toBeInTheDocument();
    expect(screen.getByText(/Scroll the share sheet/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^Install Now$/i })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Got it!$/i })).toBeInTheDocument();
  });

  it('deferred variant with prompt shows Install Now and Chromium-oriented steps', () => {
    const deferredPrompt = {
      prompt: vi.fn(),
      userChoice: Promise.resolve({ outcome: 'accepted' }),
    };
    render(<PwaInstallModal variant="deferred" deferredPrompt={deferredPrompt} onClose={() => {}} />);
    expect(screen.getByRole('button', { name: /^Install Now$/i })).toBeInTheDocument();
    expect(screen.getByText(/built-in installer/i)).toBeInTheDocument();
  });
});
