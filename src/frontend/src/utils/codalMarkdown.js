/**
 * IndexedDB / codex cache buster: bump when `/api/codex/versions` article body shape changes
 * so `lexCache.swr('codals', …)` does not keep serving stale `content_md` after deploy.
 */
export const CODAL_LEXCACHE_REVISION = '_codexfmt8';

/**
 * E-Library / bad exports sometimes emit one table header cell per line (`| Name` only has one `|`).
 * `shieldGfmTables` and remark-gfm then skip those lines, so the underscore row becomes the table header.
 * Merge those rows into a single GFM header row (and repair similar 5-column subscriber headers).
 */
export function repairRccBrokenIncorporatorPipeHeaders(md) {
    if (md == null || md === '') return md;
    let t = String(md).replace(/\r\n/g, '\n').replace(/\r/g, '\n');

    // 3-column: one pipe per line
    t = t.replace(
        /(^|\n)\|\s*Name\s*\n\|\s*Nationality\s*\n\|\s*Residence\s*(?=\n\|)/g,
        '$1| Name | Nationality | Residence |',
    );

    // 5-column subscriber block (split cells)
    t = t.replace(
        /(^|\n)\|\s*Name of Subscriber\s*\n\|\s*Nationality\s*\n\|\s*No\.\s*of Shares Subscribed\s*\n\|\s*Amount Subscribed\s*\n\|\s*Amount Paid\s*(?=\n\|)/gi,
        '$1| Name of Subscriber | Nationality | No. of Shares Subscribed | Amount Subscribed | Amount Paid |',
    );

    // Floating labels (no leading pipes) immediately before a 3-column pipe row (not already fixed)
    t = t.replace(
        /(^|\n)Name\s*\n\s*Nationality\s*\n\s*Residence\s*\n\s*(?!\|\s*Name\s*\|)(?=\|[^\n]+\|[^\n]+\|[^\n]+\n\|)/gm,
        '$1| Name | Nationality | Residence |\n| --- | --- | --- |\n',
    );

    // IN WITNESS: year placeholder sometimes rendered as "20 in the" after HTML strip
    t = t.replace(/(IN WITNESS WHEREOF[^\n]+?)(\b20)\s+(in the City\/Municipality)/gi, '$1$2____ $3');

    return t;
}

/**
 * GFM pipe tables must not have blank lines between rows. Ingested sources sometimes insert
 * an extra newline between the header row and the `|---|` row (or between body rows), which
 * breaks remark-gfm table parsing.
 */
export function collapseBlankLinesInPipeTables(md) {
    if (md == null || md === '') return md;
    const lines = String(md).replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
    const isPipeRow = (line) => {
        const t = String(line).trim();
        return t.startsWith('|') && (t.match(/\|/g) || []).length >= 2;
    };
    const out = [];
    let i = 0;
    while (i < lines.length) {
        if (!isPipeRow(lines[i])) {
            out.push(lines[i]);
            i++;
            continue;
        }
        while (i < lines.length && isPipeRow(lines[i])) {
            out.push(lines[i]);
            i++;
        }
        if (i < lines.length && lines[i].trim() === '') {
            let j = i;
            while (j < lines.length && lines[j].trim() === '') j++;
            if (j < lines.length && isPipeRow(lines[j])) {
                i = j;
                continue;
            }
        }
    }
    return out.join('\n');
}

/**
 * GFM pipe tables use single newlines between rows. ArticleNode's enumeration preprocessor
 * inserts `\n\n` before markers like `(a)` or `2.` — that can split a table across "paragraph"
 * segments so remark-gfm never sees a valid table (pipes render as plain text).
 *
 * Replace each contiguous pipe-table block with a one-line placeholder, run preprocessors,
 * then restore placeholders.
 */
export function shieldGfmTables(md) {
    if (md == null || md === '') {
        return { protectedText: md, restore: (s) => s };
    }
    const text = collapseBlankLinesInPipeTables(String(md).replace(/\r\n/g, '\n').replace(/\r/g, '\n'));
    const lines = text.split('\n');
    const tables = [];
    const out = [];
    let i = 0;
    /** Lenient: many DB rows omit the trailing `|`; still treat as a GFM table row. */
    const isPipeTableLine = (line) => {
        const t = line.trim();
        if (!t.startsWith('|')) return false;
        const pipes = (t.match(/\|/g) || []).length;
        if (pipes >= 2) return true;
        // One leading pipe, rest is cell text (e.g. "| Name" from broken SC exports)
        return pipes === 1 && /\|\s*\S/.test(t);
    };
    while (i < lines.length) {
        const raw = lines[i];
        if (isPipeTableLine(raw)) {
            const block = [];
            let j = i;
            while (j < lines.length) {
                const L = lines[j];
                if (L.trim() === '') {
                    let k = j + 1;
                    while (k < lines.length && lines[k].trim() === '') k++;
                    if (k < lines.length && isPipeTableLine(lines[k])) {
                        j = k;
                        continue;
                    }
                    break;
                }
                if (!isPipeTableLine(L)) break;
                block.push(L);
                j++;
            }
            if (block.length >= 2) {
                tables.push(block.join('\n'));
                out.push(`\uFFF1GFMTBL${tables.length - 1}\uFFF2`);
                i = j;
                continue;
            }
        }
        out.push(raw);
        i++;
    }
    const protectedText = out.join('\n');
    const restore = (s) => {
        if (s == null) return s;
        let t = String(s);
        for (let idx = 0; idx < tables.length; idx++) {
            const ph = `\uFFF1GFMTBL${idx}\uFFF2`;
            t = t.split(ph).join(tables[idx]);
        }
        return t;
    };
    return { protectedText, restore };
}

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
        '^\\s*(?:Article|Section)\\s+' +
            escapedNum +
            '\\.\\s*' +
            '(?:\\*\\*[^*]+?\\*\\*\\s*-\\s*)?' +
            '(?:##[^\\n]+\\n(?:\\s*\\n)?)*',
        'i'
    );
    let out = md.replace(leadBlock, '').trimStart();

    const dupLead = new RegExp('^\\s*(?:Article|Section)\\s+' + escapedNum + '\\.\\s+', 'i');
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
 * Pull the title for inline display with "Section N" chrome and drop the dash before the body.
 */
/** Numeric part when `article_num` is stored as "Section 32" (API / markdown). */
export function rccSectionNumberFromArticleNum(articleNum) {
    const s = String(articleNum ?? '').trim();
    const m = s.match(/^section\s+(.+)$/i);
    const token = (m ? m[1] : s).trim();
    return token.replace(/\.$/, '').trim();
}

/** Same token as DB chrome, with trailing period (e.g. `32.`). Not used for preliminary rows. */
export function rccSectionNumberDisplayWithPeriod(articleNum) {
    const n = rccSectionNumberFromArticleNum(articleNum);
    return n ? `${n}.` : '';
}

export function extractRccLeadingShortTitle(md) {
    if (md == null || md === '') return { lead: null, body: md };
    const full = String(md).replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    let s = full.trimStart();
    const prefixLen = full.length - s.length;
    // Drop duplicate "### Section N" line (do not add removed chars to prefixLen — that would put
    // the heading back into `body` when rebuilding with full.slice(0, prefixLen) + s.slice(…)).
    s = s.replace(/^#{1,6}\s*section\s+[^\n]+\n+/i, '').replace(/^\n+/, '');

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
    // Bold then dash — before single-* patterns so `**Title.** -` is not parsed as `*Title*`.
    const boldDash = s.match(/^\*\*([^*]+)\*\*\s*[-–—]\s+/);
    if (boldDash) return finish(boldDash, (x) => x[1]);
    // Plain sentence + dash or em dash (RCC Section 32 style: "Contracts…. — Except…")
    const plainDotDash = s.match(/^([A-Za-z0-9][^.]{0,220}\.)\s*-\s+/);
    if (plainDotDash && plainDotDash[1].trim().length >= 3) {
        return finish(plainDotDash, (x) => x[1].trim());
    }
    const plainDotEm = s.match(/^([A-Za-z0-9][^.]{0,220}\.)\s*[–—]\s+/);
    if (plainDotEm && plainDotEm[1].trim().length >= 3) {
        return finish(plainDotEm, (x) => x[1].trim());
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
