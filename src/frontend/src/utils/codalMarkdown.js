/**
 * IndexedDB / codex cache buster: bump when `/api/codex/versions` article body shape changes
 * so `lexCache.swr('codals', …)` does not keep serving stale `content_md` after deploy.
 */
export const CODAL_LEXCACHE_REVISION = '_codexfmt3';

/**
 * Legacy `/api/codex/versions` rows embedded "## Book…" / "## Title…" plus `Article N.`
 * on the same line as body text. LexCodeStream already hoists book/title from row fields and
 * ArticleNode renders "Article N." — strip the duplicate run-in (works offline against old API/cache).
 */
export function stripLegacyCodexArticleRunIn(contentMd, articleNum) {
    if (contentMd == null || contentMd === '') return contentMd;
    if (articleNum == null || String(articleNum).trim() === '') return contentMd;

    let md = String(contentMd).replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    const escapedNum = String(articleNum).trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

    const leadBlock = new RegExp(
        '^\\s*Article\\s+' +
            escapedNum +
            '\\.\\s*' +
            '(?:\\*\\*[^*]+?\\*\\*\\s*-\\s*)?' +
            '(?:##[^\\n]+\\n(?:\\s*\\n)?)*',
        'i'
    );
    let out = md.replace(leadBlock, '').trimStart();

    const dupLead = new RegExp('^\\s*Article\\s+' + escapedNum + '\\.\\s+', 'i');
    for (let i = 0; i < 4 && dupLead.test(out); i++) {
        out = out.replace(dupLead, '').trimStart();
    }
    return out;
}

/**
 * RCC articles open with a short title in emphasis, then a dash (ASCII or em/en) before the body.
 * Shapes include `_Title. -_`, `_Title._ -`, `_Title —_`, `_Title._ —` (and *…* variants).
 * E-library / RA 11232 also uses a leading word outside emphasis, e.g.
 * `Form _of Articles of Incorporation._ - Unless otherwise…` (Section/Article 14 under Title II).
 * Pull the title for inline display with "Article N." and drop the dash before the body.
 */
export function extractRccLeadingShortTitle(md) {
    if (md == null || md === '') return { lead: null, body: md };
    const full = String(md).replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    const s = full.trimStart();
    const prefixLen = full.length - s.length;

    const normalizeLead = (inner) =>
        inner
            .replace(/\n/g, ' ')
            .trim()
            .replace(/\s*[–—]\s*$/u, '')
            .replace(/\s+-\s*$/u, '')
            .trim();

    const finish = (m, innerFn) => {
        const lead = normalizeLead(innerFn(m));
        const body = full.slice(0, prefixLen) + s.slice(m[0].length);
        return lead ? { lead, body } : { lead: null, body: md };
    };

    // Word + partial emphasis + dash (Article 14 style from SC E-Library markdown)
    const splitWordEmUnd = s.match(/^([A-Za-z][A-Za-z']{0,47})\s+_(.+?)_\s*(?:-\s+|[–—]\s+)/);
    if (splitWordEmUnd) {
        const combined = `${splitWordEmUnd[1]} ${splitWordEmUnd[2]}`.replace(/\n/g, ' ');
        return finish(splitWordEmUnd, () => combined);
    }
    const splitWordEmStar = s.match(/^([A-Za-z][A-Za-z']{0,47})\s+\*(.+?)\*\s*(?:-\s+|[–—]\s+)/);
    if (splitWordEmStar) {
        const combined = `${splitWordEmStar[1]} ${splitWordEmStar[2]}`.replace(/\n/g, ' ');
        return finish(splitWordEmStar, () => combined);
    }

    const und = [
        /^_(.+?)\s*—\s*_\s+/u,
        /^_(.+?)_\s*[–—]\s+/u,
        /^_(.+?)\s*-\s*_\s+/,
        /^_(.+?)_\s*-\s+/,
    ];
    for (const re of und) {
        const m = s.match(re);
        if (m) return finish(m, (x) => x[1]);
    }
    const star = [/^\*(.+?)\s*—\s*\*\s+/u, /^\*(.+?)\*\s*[–—]\s+/u, /^\*(.+?)\s*-\s*\*\s+/, /^\*(.+?)\*\s*-\s+/];
    for (const re of star) {
        const m = s.match(re);
        if (m) return finish(m, (x) => x[1]);
    }
    return { lead: null, body: md };
}

/**
 * RCC markdown occasionally wraps a single lettered item across a blank line (e.g. Art. 6 (g)
 * "...with this" then "Code; and"). Merge so one list item is not split into two segments.
 */
export function repairRccListMidItemLineBreaks(md) {
    if (md == null || md === '') return md;
    let t = String(md).replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    t = t.replace(/(\(\s*[a-z]\)[^\n]*\bthis)\s*\n\s*\n(Code;\s*and)\b/gi, '$1 $2');
    return t;
}

/**
 * Mirrors api/codal_text.fix_stray_quotation_artifacts for display-time cleanup.
 * Keeps paragraph boundaries (\n) intact.
 */
export function fixStrayQuotationArtifacts(text) {
    if (!text) return text;
    const lines = text.split('\n');
    const out = [];
    for (const line of lines) {
        const stripped = line.trim();
        if (stripped === '"' || stripped === "'" || stripped === '\u201c' || stripped === '\u201d') {
            continue;
        }
        let s = line;
        s = s.replace(/^\s*"\s*/, '');
        s = s.replace(/\s*"\s*$/, '');
        s = s.replace(/^\s*\u201c\s*/, '');
        s = s.replace(/\s*\u201d\s*$/, '');
        out.push(s);
    }
    let joined = out.join('\n');
    joined = joined.replace(/\.(\s*")(\s+[A-Za-z])/g, '.$2');
    joined = joined.replace(/\.(\s*\u201d)(\s+[A-Za-z])/g, '.$2');
    return joined;
}
