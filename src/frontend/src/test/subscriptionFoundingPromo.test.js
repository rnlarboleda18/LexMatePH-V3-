import { describe, it, expect } from 'vitest';
import {
  isFoundingPromoBarrister,
  isFoundingPromoModalActive,
} from '../utils/subscriptionFoundingPromo';

describe('isFoundingPromoBarrister', () => {
  it('returns true when source is founding_promo on barrister', () => {
    expect(isFoundingPromoBarrister('barrister', 'founding_promo', null)).toBe(true);
  });

  it('returns true when slot is set on barrister', () => {
    expect(isFoundingPromoBarrister('barrister', 'trial', 3)).toBe(true);
  });

  it('returns false for non-barrister', () => {
    expect(isFoundingPromoBarrister('free', 'founding_promo', 1)).toBe(false);
  });

  it('returns false for paid barrister without founding markers', () => {
    expect(isFoundingPromoBarrister('barrister', 'paymongo', null)).toBe(false);
  });
});

describe('isFoundingPromoModalActive', () => {
  it('is true when pending grant even before tier flips to barrister', () => {
    expect(isFoundingPromoModalActive(true, false)).toBe(true);
  });

  it('is true when founding barrister already granted', () => {
    expect(isFoundingPromoModalActive(false, true)).toBe(true);
  });

  it('is false when neither pending nor granted', () => {
    expect(isFoundingPromoModalActive(false, false)).toBe(false);
  });
});
