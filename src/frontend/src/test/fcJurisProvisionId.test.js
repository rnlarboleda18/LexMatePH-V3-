import { describe, it, expect } from 'vitest';
import { fcJurisProvisionIdFromArticle } from '../utils/fcJurisProvisionId';

describe('fcJurisProvisionIdFromArticle', () => {
  it('prefers article_num (last segment from /api/fc/all)', () => {
    expect(fcJurisProvisionIdFromArticle({ article_num: '1', key_id: 'FC-I-1' }, 'x')).toBe('1');
  });

  it('derives tail from key_id when article_num missing', () => {
    expect(fcJurisProvisionIdFromArticle({ key_id: 'FC-I-1' }, 'db')).toBe('1');
    expect(fcJurisProvisionIdFromArticle({ key_id: 'II-15' }, '')).toBe('15');
  });

  it('falls back to key_id or stableId', () => {
    expect(fcJurisProvisionIdFromArticle({ key_id: 'Preamble' }, '99')).toBe('Preamble');
    expect(fcJurisProvisionIdFromArticle({}, '42')).toBe('42');
  });
});
