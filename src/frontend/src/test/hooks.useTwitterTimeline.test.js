import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useTwitterTimeline } from '../hooks/useTwitterTimeline';

describe('useTwitterTimeline', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    delete window.twttr;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
    delete window.twttr;
  });

  it('appends widgets script when missing', () => {
    const appendSpy = vi.spyOn(document.body, 'appendChild').mockImplementation((el) => el);
    const ref = { current: document.createElement('div') };
    renderHook(() => useTwitterTimeline(ref, []));
    const appended = appendSpy.mock.calls.map((c) => c[0]).find((el) => el?.id === 'twitter-wjs');
    expect(appended).toBeTruthy();
    expect(String(appended.src || '')).toContain('platform.twitter.com/widgets.js');
    appendSpy.mockRestore();
  });

  it('calls twttr.widgets.load when script exists and twttr is ready', () => {
    const load = vi.fn();
    window.twttr = { widgets: { load } };
    const script = document.createElement('script');
    script.id = 'twitter-wjs';
    document.body.appendChild(script);

    const ref = { current: document.createElement('div') };
    renderHook(() => useTwitterTimeline(ref, []));

    expect(load).toHaveBeenCalledWith(ref.current);
  });

  it('re-runs load when deps change', () => {
    const load = vi.fn();
    window.twttr = { widgets: { load } };
    const script = document.createElement('script');
    script.id = 'twitter-wjs';
    document.body.appendChild(script);

    const ref = { current: document.createElement('div') };
    const { rerender } = renderHook(({ theme }) => useTwitterTimeline(ref, [theme]), {
      initialProps: { theme: 'light' },
    });
    expect(load).toHaveBeenCalledTimes(1);

    load.mockClear();
    rerender({ theme: 'dark' });
    expect(load).toHaveBeenCalledTimes(1);
    expect(load).toHaveBeenCalledWith(ref.current);
  });
});
