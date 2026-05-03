import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { adminApiUrl, formatAdminApiError } from '../utils/adminApi';

describe('adminApiUrl', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_API_BASE_URL', '');
  });
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('returns relative path when VITE_API_BASE_URL is unset', () => {
    expect(adminApiUrl('/api/ops/db-stats')).toBe('/api/ops/db-stats');
  });

  it('prefixes base when VITE_API_BASE_URL is set', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://127.0.0.1:7071');
    expect(adminApiUrl('/api/ops/ping')).toBe('http://127.0.0.1:7071/api/ops/ping');
  });
});

describe('formatAdminApiError', () => {
  it('returns restart hint for HTTP 404', () => {
    const res = { status: 404, statusText: 'Not Found' };
    const msg = formatAdminApiError(res, 'Not Found');
    expect(msg.toLowerCase()).toContain('restart');
    expect(msg).toContain('func start');
  });

  it('passes through body error for non-404', () => {
    const res = { status: 500, statusText: 'Internal Server Error' };
    expect(formatAdminApiError(res, 'db down')).toBe('db down');
  });
});
