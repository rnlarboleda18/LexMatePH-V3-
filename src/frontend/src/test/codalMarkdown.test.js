import { describe, it, expect } from 'vitest';
import {
    collapseBlankLinesInPipeTables,
    extractRccLeadingShortTitle,
    repairRccBrokenIncorporatorPipeHeaders,
    repairRccListMidItemLineBreaks,
    rccSectionNumberFromArticleNum,
    rccSectionNumberDisplayWithPeriod,
    shieldGfmTables,
    stripLegacyCodexArticleRunIn,
} from '../utils/codalMarkdown';

describe('repairRccBrokenIncorporatorPipeHeaders', () => {
    it('merges split single-pipe Name/Nationality/Residence lines before the separator row', () => {
        const raw =
            'Fifth: … follows:\n\n' +
            '| Name\n' +
            '| Nationality\n' +
            '| Residence\n' +
            '| ___ | ___ | ___ |\n' +
            '| --- | --- | --- |\n' +
            '| a | b | c |\n';
        const out = repairRccBrokenIncorporatorPipeHeaders(raw);
        expect(out).toContain('| Name | Nationality | Residence |');
        expect(out).not.toMatch(/\|\s*Name\s*\n\|\s*Nationality/s);
    });

    it('restores year placeholder when stripped to "20 in the City"', () => {
        const raw =
            'IN WITNESS WHEREOF, we have hereunto signed these Articles, this ______ day of ________, 20 in the City/Municipality of ________.';
        const out = repairRccBrokenIncorporatorPipeHeaders(raw);
        expect(out).toContain('20____ in the City/Municipality');
    });
});

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

    it('removes Section 3 run-in when legacy cache used Section label', () => {
        const raw =
            'Section 3. Classes of Corporations. - Corporations formed or organized under this Code may be stock or nonstock corporations.';
        const out = stripLegacyCodexArticleRunIn(raw, '3');
        expect(out).not.toMatch(/^Section\s+3\./i);
        expect(out).toContain('Classes of Corporations');
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

    it('parses **Title.** - body (bold short title, no inner emphasis)', () => {
        const raw =
            '**Title of the Code.** - This Code shall be known as the "Revised Corporation Code of the Philippines".';
        const { lead, body } = extractRccLeadingShortTitle(raw);
        expect(lead).toBe('Title of the Code.');
        expect(body).toBe('This Code shall be known as the "Revised Corporation Code of the Philippines".');
    });

    it('parses plain "Sentence. -" before body (Section 1 E-Library style)', () => {
        const raw = 'Title of the Code. - This Code shall be known as the "RCC".';
        const { lead, body } = extractRccLeadingShortTitle(raw);
        expect(lead).toBe('Title of the Code.');
        expect(body).toBe('This Code shall be known as the "RCC".');
    });

    it('parses plain "Sentence. —" em dash before body (Section 32 style)', () => {
        const raw =
            'Contracts Between Corporations with Interlocking Directors. — Except in cases of fraud';
        const { lead, body } = extractRccLeadingShortTitle(raw);
        expect(lead).toBe('Contracts Between Corporations with Interlocking Directors.');
        expect(body).toBe('Except in cases of fraud');
    });

    it('strips leading ### Section N before extracting lead', () => {
        const raw =
            '### Section 32\n\nContracts Between Corporations with Interlocking Directors. — Except in cases';
        const { lead, body } = extractRccLeadingShortTitle(raw);
        expect(lead).toBe('Contracts Between Corporations with Interlocking Directors.');
        expect(body).not.toMatch(/###\s*Section/i);
        expect(body).toContain('Except in cases');
    });
});

describe('rccSectionNumberFromArticleNum', () => {
    it('returns digits when article_num is Section N', () => {
        expect(rccSectionNumberFromArticleNum('Section 32')).toBe('32');
    });
    it('returns raw when numeric only', () => {
        expect(rccSectionNumberFromArticleNum('32')).toBe('32');
    });
    it('strips a trailing period from the token', () => {
        expect(rccSectionNumberFromArticleNum('Section 32.')).toBe('32');
        expect(rccSectionNumberFromArticleNum('32.')).toBe('32');
    });
});

describe('rccSectionNumberDisplayWithPeriod', () => {
    it('returns number plus period', () => {
        expect(rccSectionNumberDisplayWithPeriod('Section 32')).toBe('32.');
    });
});

describe('collapseBlankLinesInPipeTables', () => {
    it('removes blank lines between pipe rows so GFM stays one table block', () => {
        const md = '| A | B |\n\n| --- | --- |\n| x | y |';
        expect(collapseBlankLinesInPipeTables(md)).toBe('| A | B |\n| --- | --- |\n| x | y |');
    });

    it('keeps blank lines after the table (before prose)', () => {
        const md = '| A | B |\n| --- | --- |\n\nNext paragraph.';
        expect(collapseBlankLinesInPipeTables(md)).toBe('| A | B |\n| --- | --- |\n\nNext paragraph.');
    });
});

describe('shieldGfmTables', () => {
    const articleNodeEnumerationPreprocess = (s) =>
        String(s)
            .replace(/([a-zA-Z0-9.,;:!?])\s+(\[\s*\([a-zA-Z0-9]{1,3}\)\s*)/g, '$1\n\n$2')
            .replace(/([a-zA-Z0-9.,;:!?])\s*\n\s*(\([a-zA-Z0-9]{1,3}\)\s+)/g, '$1\n\n$2')
            .replace(/([.;:])\s+(\([a-zA-Z0-9]{1,3}\)\s+)/g, '$1\n\n$2')
            .replace(/([.;:])\s+(\d{1,3}\.\s+)/g, '$1\n\n$2')
            .replace(
                /([a-zA-Z0-9.,;:!?])\s*\n?\s*((?:First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)\.\s+)/gi,
                '$1\n\n$2',
            );

    it('keeps GFM tables intact through ArticleNode enumeration preprocessing', () => {
        const md =
            'Fifth: follow.\n\n' +
            '| Name | Nationality | Residence |\n' +
            '| --- | --- | --- |\n' +
            '| a | b | c |\n\n' +
            'Sixth: next.';
        const { protectedText, restore } = shieldGfmTables(md);
        expect(restore(articleNodeEnumerationPreprocess(protectedText))).toBe(md);
    });

    it('round-trips RCC Article 14 style multi-row table block', () => {
        const table =
            '| Name of Subscriber | Nationality | No. of Shares Subscribed | Amount Subscribed | Amount Paid |\n' +
            '| --- | --- | --- | --- | --- |\n' +
            '|  |  |  |  |  |\n' +
            '|  |  |  |  |  |';
        const md = `Intro line.\n\n${table}\n\nAfter table.`;
        const { protectedText, restore } = shieldGfmTables(md);
        expect(restore(protectedText)).toBe(md);
    });

    it('shields tables that had a blank line between header and separator (invalid GFM until collapsed)', () => {
        const md = '| Name | Nat |\n\n| --- | --- |\n| a | b |';
        const collapsed = collapseBlankLinesInPipeTables(md);
        const { protectedText, restore } = shieldGfmTables(collapsed);
        expect(restore(articleNodeEnumerationPreprocess(protectedText))).toBe(collapsed);
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
