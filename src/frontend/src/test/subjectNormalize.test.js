import { describe, it, expect } from 'vitest';
import {
  normalizeBarSubject,
  normalizeBarQuestionSubject,
  barQuestionSubjectRaw,
} from '../utils/subjectNormalize';

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

  it('matches tax as a whole word only for Taxation Law (not surtax / overtax substrings)', () => {
    expect(normalizeBarSubject('income tax')).toBe('Taxation Law');
    expect(normalizeBarSubject('Taxation')).toBe('Taxation Law');
    expect(normalizeBarSubject('surtax')).toBe('surtax');
    expect(normalizeBarSubject('overtax')).toBe('overtax');
  });

  it('maps Land Titles and Deeds to Civil Law', () => {
    expect(normalizeBarSubject('Land Titles and Deeds')).toBe('Civil Law');
  });

  it('does not map unrelated words via penal/labor/criminal substrings', () => {
    expect(normalizeBarSubject('Contractual penalties')).toBe('Contractual penalties');
    expect(normalizeBarSubject('belabor the point')).toBe('belabor the point');
    expect(normalizeBarSubject('apolitical stance')).toBe('apolitical stance');
  });

  it('still maps Special Penal Laws and Criminal Law phrases', () => {
    expect(normalizeBarSubject('Special Penal Laws')).toBe('Criminal Law');
    expect(normalizeBarSubject('Criminal procedure basics')).toBe('Criminal Law');
  });
});

describe('normalizeBarQuestionSubject', () => {
  it('prefers sub_topic over combined exam subject', () => {
    const q = {
      subject: 'Commercial and Taxation Laws',
      sub_topic: 'Taxation',
    };
    expect(barQuestionSubjectRaw(q)).toBe('Taxation');
    expect(normalizeBarQuestionSubject(q)).toBe('Taxation Law');
  });

  it('falls back to subject when sub_topic empty', () => {
    expect(normalizeBarQuestionSubject({ subject: 'Criminal Law', sub_topic: '' })).toBe('Criminal Law');
  });

  it('trusts subject when sub_topic disagrees but subject is not a combined paper', () => {
    const q = { subject: 'Criminal Law', sub_topic: 'Civil Law' };
    expect(barQuestionSubjectRaw(q)).toBe('Criminal Law');
    expect(normalizeBarQuestionSubject(q)).toBe('Criminal Law');
  });
});
