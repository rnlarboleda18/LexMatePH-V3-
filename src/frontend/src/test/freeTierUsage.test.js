import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { consumeFreeTierUsage, getOrCreateAnonymousUsageId } from '../utils/freeTierUsage';

describe('consumeFreeTierUsage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    try {
      localStorage.removeItem('lexmate_anonymous_usage_id');
    } catch (_) {
      /* ignore */
    }
  });

  afterEach(() => {
    try {
      localStorage.removeItem('lexmate_anonymous_usage_id');
    } catch (_) {
      /* ignore */
    }
  });

  it('sends anonymousId when not signed in to Clerk', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ allowed: true, used: 1, limit: 5, anonymous: true }),
    });
    const r = await consumeFreeTierUsage({
      feature: 'case_digest',
      getToken: async () => 'should-not-be-used',
      isSignedIn: false,
    });
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [, init] = fetchSpy.mock.calls[0];
    expect(init.headers['X-Clerk-Authorization']).toBeUndefined();
    const parsed = JSON.parse(init.body);
    expect(parsed.feature).toBe('case_digest');
    expect(parsed.anonymousId).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
    );
    expect(r.allowed).toBe(true);
  });

  it('POSTs Bearer auth when signed in (never sends anonymousId)', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ allowed: true, used: 1, limit: 5 }),
    });
    const r = await consumeFreeTierUsage({
      feature: 'case_digest',
      getToken: async () => 'test-token',
      isSignedIn: true,
    });
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [, init] = fetchSpy.mock.calls[0];
    expect(init.headers['X-Clerk-Authorization']).toBe('Bearer test-token');
    const parsed = JSON.parse(init.body);
    expect(parsed).toEqual({ feature: 'case_digest' });
    expect(r.allowed).toBe(true);
  });

  it('returns allowed false when the server reports the daily limit', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ allowed: false, used: 5, limit: 5, anonymous: true }),
    });
    const r = await consumeFreeTierUsage({
      feature: 'bar_question',
      getToken: async () => null,
      isSignedIn: false,
    });
    expect(r.allowed).toBe(false);
    expect(r.blockedByLimit).toBe(true);
    expect(r.used).toBe(5);
    expect(r.limit).toBe(5);
  });

  it('does not allow usage when the HTTP response is not OK (e.g. 404)', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ error: 'Not found' }),
    });
    const r = await consumeFreeTierUsage({
      feature: 'bar_question',
      getToken: async () => null,
      isSignedIn: false,
    });
    expect(r.allowed).toBe(false);
    expect(r.verifyFailed).toBe(true);
    expect(r.status).toBe(404);
  });

  it('falls back to anonymousId when signed in but getToken returns null', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ allowed: true, used: 1, limit: 5, anonymous: true }),
    });
    const r = await consumeFreeTierUsage({
      feature: 'bar_question',
      getToken: async () => null,
      isSignedIn: true,
    });
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [, init] = fetchSpy.mock.calls[0];
    expect(init.headers['X-Clerk-Authorization']).toBeUndefined();
    const parsed = JSON.parse(init.body);
    expect(parsed.feature).toBe('bar_question');
    expect(parsed.anonymousId).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
    );
    expect(r.allowed).toBe(true);
  });

  it('skips track-usage when canAccess allows the mapped unlimited feature', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    const r = await consumeFreeTierUsage({
      feature: 'flashcard',
      getToken: async () => 'session-jwt',
      isSignedIn: true,
      canAccess: (key) => key === 'flashcard_unlimited',
    });
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(r).toEqual(
      expect.objectContaining({ allowed: true, skipped: true, unlimited: true }),
    );
  });

  it('skips track-usage while subscription is loading for signed-in users', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    const r = await consumeFreeTierUsage({
      feature: 'case_digest',
      getToken: async () => 'session-jwt',
      isSignedIn: true,
      canAccess: () => false,
      subscriptionLoading: true,
    });
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(r).toEqual(expect.objectContaining({ allowed: true, skipped: true, reason: 'subscription_loading' }));
  });
});

describe('getOrCreateAnonymousUsageId', () => {
  beforeEach(() => {
    try {
      localStorage.removeItem('lexmate_anonymous_usage_id');
    } catch (_) {
      /* ignore */
    }
  });

  it('returns the same id on repeat calls', () => {
    const a = getOrCreateAnonymousUsageId();
    const b = getOrCreateAnonymousUsageId();
    expect(a).toBeTruthy();
    expect(a).toBe(b);
  });
});
