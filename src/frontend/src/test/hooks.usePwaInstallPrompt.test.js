import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { usePwaInstallPrompt } from '../hooks/usePwaInstallPrompt';

describe('usePwaInstallPrompt', () => {
  beforeEach(() => {
    vi.spyOn(window, 'matchMedia').mockImplementation((query) => ({
      matches: false,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('hides banner when inactive (marketing landing)', () => {
    const { result } = renderHook(() => usePwaInstallPrompt(false));
    expect(result.current.showBanner).toBe(false);
  });

  it('shows banner when active and not standalone', () => {
    const { result } = renderHook(() => usePwaInstallPrompt(true));
    expect(result.current.showBanner).toBe(true);
    expect(result.current.isStandalone).toBe(false);
  });

  it('hides banner when display-mode is standalone', () => {
    vi.spyOn(window, 'matchMedia').mockImplementation((query) => ({
      matches: query === '(display-mode: standalone)',
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
    const { result } = renderHook(() => usePwaInstallPrompt(true));
    expect(result.current.isStandalone).toBe(true);
    expect(result.current.showBanner).toBe(false);
  });

  it('dismiss closes banner', () => {
    const { result } = renderHook(() => usePwaInstallPrompt(true));
    expect(result.current.showBanner).toBe(true);
    act(() => {
      result.current.dismiss();
    });
    expect(result.current.showBanner).toBe(false);
  });

  it('install returns unavailable when no deferred prompt', async () => {
    const { result } = renderHook(() => usePwaInstallPrompt(true));
    let out;
    await act(async () => {
      out = await result.current.install();
    });
    expect(out.outcome).toBe('unavailable');
  });
});
