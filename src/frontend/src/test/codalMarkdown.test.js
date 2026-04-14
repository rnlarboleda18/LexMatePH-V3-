import { describe, it, expect } from 'vitest';
import { extractRccLeadingShortTitle, repairRccListMidItemLineBreaks, stripLegacyCodexArticleRunIn } from '../utils/codalMarkdown';

describe('stripLegacyCodexArticleRunIn', () => {
    it('removes Article 1 run-in with embedded ## Book / ## Title blocks', () => {
        const raw =
            'Article 1. ## Book 1 - REVISED CORPORATION CODE OF THE PHILIPPINES\n\n' +
            '## Title I - GENERAL PROVISIONS DEFINITIONS AND CLASSIFICATIONS\n\n' +
            '_Title of the Code. -_ This Code shall be known as the "Revised Corporation Code of the Philippines".';
        const out = stripLegacyCodexArticleRunIn(raw, '1');
        expect(out).not.toContain('##');
        expect(out).not.toMatch(/^Article\s+1\./i);
        expect(out).toContain('Title of the Code');
    });

    it('removes duplicate Article 2. lead when body repeats the label', () => {
        const raw =
            'Article 2. Corporation Defined. - A corporation is an artificial being created by operation of law.';
        const out = stripLegacyCodexArticleRunIn(raw, '2');
        expect(out).not.toMatch(/^Article\s+2\./i);
        expect(out).toContain('Corporation Defined');
    });

    it('is a no-op for normal RCC body (no leading Article line)', () => {
        const raw = '_Title of the Code. -_ This Code shall be known as the "RCC".';
        expect(stripLegacyCodexArticleRunIn(raw, '1')).toBe(raw);
    });
});

describe('extractRccLeadingShortTitle', () => {
    it('parses _Lead. -_ body (Article 1 style)', () => {
        const raw =
            '_Title of the Code. -_ This Code shall be known as the "Revised Corporation Code of the Philippines".';
        const { lead, body } = extractRccLeadingShortTitle(raw);
        expect(lead).toBe('Title of the Code.');
        expect(body).toBe('This Code shall be known as the "Revised Corporation Code of the Philippines".');
    });

    it('parses _Lead._ - body (Article 2 style)', () => {
        const raw =
            '_Corporation Defined._ - A corporation is an artificial being created by operation of law.';
        const { lead, body } = extractRccLeadingShortTitle(raw);
        expect(lead).toBe('Corporation Defined.');
        expect(body).toBe('A corporation is an artificial being created by operation of law.');
    });

    it('returns null lead when pattern missing', () => {
        expect(extractRccLeadingShortTitle('Plain paragraph.').lead).toBeNull();
    });

    it('parses _Lead. —_ body (em dash before closing underscore, Article 16 style)', () => {
        const raw =
            '_Grounds When Articles of Incorporation or Amendment May be Disapproved. —_ The Commission may disapprove';
        const { lead, body } = extractRccLeadingShortTitle(raw);
        expect(lead).toBe('Grounds When Articles of Incorporation or Amendment May be Disapproved.');
        expect(body).toBe('The Commission may disapprove');
    });

    it('parses _Lead._ — body (closed underscore then em dash)', () => {
        const raw =
            '_Violation of Duty to Maintain Records._ — The unjustified failure or refusal by the corporation';
        const { lead, body } = extractRccLeadingShortTitle(raw);
        expect(lead).toBe('Violation of Duty to Maintain Records.');
        expect(body).toBe('The unjustified failure or refusal by the corporation');
    });

    it('parses Word _…_ - body (Article 14 / Title II, SC E-Library style)', () => {
        const raw =
            'Form _of Articles of Incorporation._ - Unless otherwise prescribed by special law, the articles of incorporation';
        const { lead, body } = extractRccLeadingShortTitle(raw);
        expect(lead).toBe('Form of Articles of Incorporation.');
        expect(body).toBe('Unless otherwise prescribed by special law, the articles of incorporation');
    });
});

describe('repairRccListMidItemLineBreaks', () => {
    it('merges Art. 6 (g) wrap across blank line before Code; and', () => {
        const raw =
            '(g) Investment of corporate funds in another corporation or business in accordance with this\n\nCode; and\n\n(h) Dissolution';
        const out = repairRccListMidItemLineBreaks(raw);
        expect(out).toContain('this Code; and');
        expect(out).not.toMatch(/this\s*\n\s*\nCode;\s*and/);
    });
});
