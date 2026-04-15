import { describe, it, expect } from 'vitest';
import { normalizeScDecisionsRouteId } from '../utils/apiUrl';

describe('normalizeScDecisionsRouteId', () => {
  it('accepts positive integers and digit-only strings', () => {
    expect(normalizeScDecisionsRouteId(52845)).toBe('52845');
    expect(normalizeScDecisionsRouteId('52845')).toBe('52845');
    expect(normalizeScDecisionsRouteId('  99  ')).toBe('99');
  });

  it('rejects null, non-numeric, and non-positive', () => {
    expect(normalizeScDecisionsRouteId(null)).toBeNull();
    expect(normalizeScDecisionsRouteId(undefined)).toBeNull();
    expect(normalizeScDecisionsRouteId('')).toBeNull();
    expect(normalizeScDecisionsRouteId('not-a-number')).toBeNull();
    expect(normalizeScDecisionsRouteId(0)).toBeNull();
    expect(normalizeScDecisionsRouteId(-1)).toBeNull();
    expect(normalizeScDecisionsRouteId(3.14)).toBeNull();
    expect(normalizeScDecisionsRouteId('550e8400-e29b-41d4-a716-446655440000')).toBeNull();
  });
});
