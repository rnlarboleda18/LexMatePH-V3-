import { describe, it, expect } from 'vitest';
import { normalizeBarSubject } from '../utils/subjectNormalize';

describe('normalizeBarSubject', () => {
  it('maps civil service / CSC to Labor Law before generic civil', () => {
    expect(normalizeBarSubject('Civil Service')).toBe('Labor Law');
    expect(normalizeBarSubject('Civil Service Commission')).toBe('Labor Law');
    expect(normalizeBarSubject('CSC rules')).toBe('Labor Law');
  });

  it('still maps plain civil law phrases to Civil Law', () => {
    expect(normalizeBarSubject('Civil Law')).toBe('Civil Law');
    expect(normalizeBarSubject('civil obligations')).toBe('Civil Law');
  });
});
