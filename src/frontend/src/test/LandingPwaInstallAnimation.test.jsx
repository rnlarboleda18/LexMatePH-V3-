import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import LandingPwaInstallAnimation from '../components/LandingPwaInstallAnimation';

describe('LandingPwaInstallAnimation', () => {
  it('renders the install demo with an accessible description', () => {
    render(<LandingPwaInstallAnimation />);
    expect(
      screen.getByRole('img', {
        name: /animated loop \(20 seconds\).*inside each device preview/i,
      })
    ).toBeInTheDocument();
    expect(screen.getByText(/Phone \(iOS\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Tablet \(Android\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Desktop \(Chrome \/ Edge\)/i)).toBeInTheDocument();
    expect(screen.getByText(/① Open LexMatePH in Safari/)).toBeInTheDocument();
  });

  it('compact hero layout omits step captions and uses short Desktop label', () => {
    render(<LandingPwaInstallAnimation compact />);
    expect(screen.queryByText(/① Open LexMatePH in Safari/)).not.toBeInTheDocument();
    expect(screen.getByText(/^Desktop$/)).toBeInTheDocument();
  });
});
