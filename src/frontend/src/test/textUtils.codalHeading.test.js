import { describe, it, expect } from 'vitest';
import { ensureCodalArticleHeadingTerminalStop } from '../utils/textUtils';

describe('ensureCodalArticleHeadingTerminalStop', () => {
    it('appends a period when the title has no sentence ending', () => {
        expect(ensureCodalArticleHeadingTerminalStop('Time when Act takes effect')).toBe(
            'Time when Act takes effect.',
        );
    });

    it('leaves strings that already end with . ? ! unchanged', () => {
        expect(ensureCodalArticleHeadingTerminalStop('Definition.')).toBe('Definition.');
        expect(ensureCodalArticleHeadingTerminalStop('Who goes there?')).toBe('Who goes there?');
        expect(ensureCodalArticleHeadingTerminalStop('Stop!')).toBe('Stop!');
    });

    it('returns null and empty string as-is', () => {
        expect(ensureCodalArticleHeadingTerminalStop(null)).toBe(null);
        expect(ensureCodalArticleHeadingTerminalStop('')).toBe('');
    });
});
