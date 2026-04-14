import { describe, it, expect } from 'vitest';
import { getFlashcardConceptPrimarySubject } from '../utils/flashcardPrimarySubject';

describe('getFlashcardConceptPrimarySubject', () => {
  it('uses modal digest_primary across sources, not stale top-level primary_subject', () => {
    const card = {
      primary_subject: 'Civil Law',
      sources: [
        { digest_primary: 'Political Law', subject: 'Civil Law' },
        { digest_primary: 'Political Law', subject: 'Civil Law' },
        { digest_primary: 'Labor Law', subject: 'Civil Law' },
      ],
    };
    expect(getFlashcardConceptPrimarySubject(card)).toBe('Political Law');
  });

  it('falls back to legacy subject modal when digest_primary absent', () => {
    const card = {
      primary_subject: '',
      sources: [{ subject: 'Remedial Law' }, { subject: 'Remedial Law' }],
    };
    expect(getFlashcardConceptPrimarySubject(card)).toBe('Remedial Law');
  });

  it('uses primary_subject only when no source signals exist', () => {
    const card = { primary_subject: 'Taxation Law', sources: [] };
    expect(getFlashcardConceptPrimarySubject(card)).toBe('Taxation Law');
  });
});
