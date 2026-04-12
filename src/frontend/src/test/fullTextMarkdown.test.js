import { describe, it, expect } from 'vitest';
import {
    normalizeFullTextMarkdownForGfm,
    normalizeLooseFootnoteCarets,
    splitInlineLetterSpacedHeadings,
    splitSpacedHeadingFromCaseTitleLines,
} from '../utils/fullTextMarkdown';

describe('splitSpacedHeadingFromCaseTitleLines', () => {
    it('splits ### caption ending with letter-spaced DECISION', () => {
        const input = '### PARTY VS. OTHER, RESPONDENT.D E C I S I O N\n\nBody';
        const out = splitSpacedHeadingFromCaseTitleLines(input);
        expect(out).toContain('### PARTY VS. OTHER, RESPONDENT.');
        expect(out).toContain('### Decision');
        expect(out).not.toContain('D E C I S I O N');
    });

    it('splits ### caption ending with letter-spaced RESOLUTION', () => {
        const input = '### PARTY VS. OTHER, RESPONDENTS. R E S O L U T I O N\n\nBody';
        const out = splitSpacedHeadingFromCaseTitleLines(input);
        expect(out).toContain('### PARTY VS. OTHER, RESPONDENTS.');
        expect(out).toContain('### Resolution');
        expect(out).not.toContain('R E S O L U T I O N');
    });
});

describe('splitInlineLetterSpacedHeadings', () => {
    it('inserts ### Resolution after period when RESOLUTION is glued in a paragraph', () => {
        const input = 'foo RESPONDENTS. R E S O L U T I O N\n\nREYES, J.:';
        const out = splitInlineLetterSpacedHeadings(input);
        expect(out).toContain('### Resolution');
        expect(out).not.toMatch(/RESPONDENTS\.\s*R E S/);
    });
});

describe('normalizeLooseFootnoteCarets', () => {
    it('converts orphan ^n to [^n] without touching existing [^n]', () => {
        expect(normalizeLooseFootnoteCarets('text^12 end')).toBe('text[^12] end');
        expect(normalizeLooseFootnoteCarets('already[^34] ok')).toBe('already[^34] ok');
    });
});

describe('normalizeFullTextMarkdownForGfm', () => {
    it('applies heading splits then carets', () => {
        const input = '### A VS. B. R E S O L U T I O N\n\nHeld^1.';
        const out = normalizeFullTextMarkdownForGfm(input);
        expect(out).toContain('### Resolution');
        expect(out).toContain('Held[^1].');
    });
});
