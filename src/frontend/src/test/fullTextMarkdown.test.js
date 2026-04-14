import { describe, it, expect } from 'vitest';
import {
    escapeLegalCaptionCommaAsterisks,
    normalizeFullTextMarkdownForGfm,
    normalizeLooseFootnoteCarets,
    repairFullTextBracketGlitches,
    repairFullTextMojibake,
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

describe('repairFullTextMojibake', () => {
    it('repairs UTF-8 punctuation mis-decoded as Windows-1252 (â€… triplets)', () => {
        // Hardcode the exact Unicode sequences produced by cp1252 decoding of UTF-8 bytes —
        // avoids relying on TextDecoder('windows-1252') ICU availability in CI.
        // Byte E2 80 94 → â (U+00E2) + € (U+20AC) + " (U+201D) in cp1252
        expect(repairFullTextMojibake('thusly\u00e2\u20ac\u201dend')).toBe('thusly\u2014end');
        // Byte E2 80 93 → â (U+00E2) + € (U+20AC) + " (U+201C) in cp1252
        expect(repairFullTextMojibake('range\u00e2\u20ac\u201chere')).toBe('range\u2013here');
        // Byte E2 80 99 → â (U+00E2) + € (U+20AC) + ™ (U+2122) in cp1252
        expect(repairFullTextMojibake('don\u00e2\u20ac\u2122t')).toBe('don\u2019t');
        // em-dash when third byte arrives as ASCII "
        expect(repairFullTextMojibake('thusly\u00e2\u20ac"end')).toBe('thusly\u2014end');
    });

    it('repairs truncated mojibake (â + apostrophe, lone â)', () => {
        expect(repairFullTextMojibake('accounts\u00e2\u20ac\' inclusion')).toBe('accounts\u2019 inclusion');
        expect(repairFullTextMojibake('plaintiff\u00e2\' cause')).toBe('plaintiff\u2019s cause');
        expect(repairFullTextMojibake('confusions\u00e2bench')).toBe('confusions\u2014bench');
        expect(repairFullTextMojibake('reiterating\u00e2 in the')).toBe('reiterating\u2014 in the');
        expect(repairFullTextMojibake('certiorari.\u00e2\' When')).toBe('certiorari.\u2014 When');
    });
});

describe('repairFullTextBracketGlitches', () => {
    it('fixes common PDF bracket artifacts in Tagalog snippets', () => {
        expect(repairFullTextBracketGlitches('homes an[g] na-expose')).toBe('homes ang na-expose');
        expect(repairFullTextBracketGlitches('nakaraang ling[g]o')).toBe('nakaraang linggo');
    });
});

describe('escapeLegalCaptionCommaAsterisks', () => {
    it('escapes comma-footnote asterisks before capitalized names or JJ.', () => {
        const line = 'ROSARIO,** JJ., concur.';
        expect(escapeLegalCaptionCommaAsterisks(line)).toBe('ROSARIO,\\*\\* JJ., concur.');
        expect(escapeLegalCaptionCommaAsterisks('NAME,* JUNRI')).toBe('NAME,\\* JUNRI');
        expect(escapeLegalCaptionCommaAsterisks('LEONEN,* ACTING C.J.')).toBe('LEONEN,\\* ACTING C.J.');
    });
});
