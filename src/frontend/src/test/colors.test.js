import { describe, it, expect } from 'vitest';
import {
  getSubjectColorForBarQuestion,
  getSubjectColorForRawSubject,
  getSubjectColor,
} from '../utils/colors';

describe('getSubjectColorForBarQuestion', () => {
  it('uses canonical subject for combined exam row so pill matches color map', () => {
    const q = { subject: 'Commercial and Taxation Laws', sub_topic: 'Taxation' };
    expect(getSubjectColorForBarQuestion(q)).toBe(getSubjectColor('Taxation Law'));
  });

  it('falls back to Political Law palette for unknown bucket', () => {
    expect(getSubjectColorForBarQuestion(null)).toBe(getSubjectColor('Political Law'));
  });
});

describe('getSubjectColorForRawSubject', () => {
  it('normalizes free text to canonical key for pill classes', () => {
    const raw = 'something about Criminal Law procedure';
    expect(getSubjectColorForRawSubject(raw)).toBe(getSubjectColor('Criminal Law'));
  });
});
