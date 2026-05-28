import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';

vi.mock('@clerk/clerk-react', () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from '@clerk/clerk-react';

// Import after mock so module-level cache starts fresh each vi.resetModules()
// We export _clearFavoritesCache for test isolation.
let useFavorites, _clearFavoritesCache;

beforeEach(async () => {
  vi.resetModules();
  const mod = await import('../hooks/useFavorites.js');
  useFavorites = mod.useFavorites;
  _clearFavoritesCache = mod._clearFavoritesCache;

  useAuth.mockReturnValue({
    getToken: vi.fn().mockResolvedValue('mock-token'),
    isSignedIn: true,
  });

  vi.spyOn(global, 'fetch').mockResolvedValue({
    ok: true,
    json: async () => ['42', '99'],
  });
});

afterEach(() => {
  _clearFavoritesCache?.();
  vi.restoreAllMocks();
});

describe('useFavorites', () => {
  it('loading is true before fetch resolves', () => {
    // Delay fetch
    vi.spyOn(global, 'fetch').mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(() => useFavorites('case', '42'));
    expect(result.current.loading).toBe(true);
  });

  it('isFavorited is true for a returned id', async () => {
    const { result } = renderHook(() => useFavorites('case', '42'));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.isFavorited).toBe(true);
  });

  it('isFavorited is false for an unknown id', async () => {
    const { result } = renderHook(() => useFavorites('case', '999'));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.isFavorited).toBe(false);
  });

  it('toggleFavorite optimistically adds and then POSTs', async () => {
    vi.spyOn(global, 'fetch')
      .mockResolvedValueOnce({ ok: true, json: async () => [] }) // GET /ids → empty
      .mockResolvedValueOnce({ ok: true, json: async () => ({}) }); // POST → ok

    const { result } = renderHook(() => useFavorites('case', '10'));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.isFavorited).toBe(false);

    await act(() => result.current.toggleFavorite('My Case', 'GR 12345'));
    expect(result.current.isFavorited).toBe(true);

    const calls = global.fetch.mock.calls;
    const postCall = calls.find(([_url, opts]) => opts?.method === 'POST');
    expect(postCall).toBeTruthy();
    const body = JSON.parse(postCall[1].body);
    expect(body.content_type).toBe('case');
    expect(body.content_id).toBe('10');
    expect(body.title).toBe('My Case');
  });

  it('toggleFavorite rolls back on network error', async () => {
    vi.spyOn(global, 'fetch')
      .mockResolvedValueOnce({ ok: true, json: async () => ['10'] }) // GET /ids
      .mockResolvedValueOnce({ ok: false, status: 500 });             // DELETE fails

    window.alert = window.alert ?? (() => {});
    vi.spyOn(window, 'alert').mockImplementation(() => {});

    const { result } = renderHook(() => useFavorites('case', '10'));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.isFavorited).toBe(true);

    await act(() => result.current.toggleFavorite());
    expect(result.current.isFavorited).toBe(true); // rolled back
    expect(window.alert).toHaveBeenCalled();
  });
});
