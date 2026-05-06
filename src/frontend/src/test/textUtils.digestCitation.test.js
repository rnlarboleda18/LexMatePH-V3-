import { describe, it, expect } from 'vitest';
import { normalizeDigestCitationDisplayText } from '../utils/textUtils';

describe('normalizeDigestCitationDisplayText', () => {
    it('removes "No date found" and trailing comma noise', () => {
        const s = 'People v. Example, G.R. No. 12345, No date found';
        expect(normalizeDigestCitationDisplayText(s)).toBe('People v. Example, G.R. No. 12345');
    });

    it('removes "date not found" case-insensitively', () => {
        expect(normalizeDigestCitationDisplayText('Foo v. Bar, DATE NOT FOUND')).toBe('Foo v. Bar');
    });

    it('passes through unrelated strings', () => {
        expect(normalizeDigestCitationDisplayText('People v. Cruz, G.R. No. 1, January 1, 2020')).toBe(
            'People v. Cruz, G.R. No. 1, January 1, 2020',
        );
    });
});
