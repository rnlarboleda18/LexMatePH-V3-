/**
 * Normalize Supreme Court full-text markdown before GFM rendering (react-markdown + remark-gfm).
 * Fixes common E-Library / conversion artifacts so tables, footnotes, and headings display correctly.
 */

const SPACED_HEADING_SUFFIXES = [
    { re: /D\s*E\s*C\s*I\s*S\s*I\s*O\s*N\s*$/i, heading: '### Decision' },
    { re: /R\s+E\s+S\s+O\s+L\s+U\s+T\s+I\s+O\s+N\s*$/i, heading: '### Resolution' },
];

/**
 * Split `### … D E C I S I O N` / `### … R E S O L U T I O N` into caption line + `### Decision` / `### Resolution`.
 */
export function splitSpacedHeadingFromCaseTitleLines(mdText) {
    if (!mdText) return mdText;
    const lines = mdText.split('\n');
    const out = [];
    for (const line of lines) {
        if (line.startsWith('### ')) {
            let matched = false;
            for (const { re, heading } of SPACED_HEADING_SUFFIXES) {
                const m = re.exec(line);
                if (m) {
                    const prefix = line.slice(0, m.index).trimEnd();
                    if (prefix.startsWith('### ') && prefix.length > 4) {
                        out.push(prefix, '', heading);
                        matched = true;
                        break;
                    }
                }
            }
            if (matched) continue;
        }
        out.push(line);
    }
    return out.join('\n');
}

/**
 * Letter-spaced RESOLUTION / DECISION glued after a sentence end (not only on `###` lines).
 */
export function splitInlineLetterSpacedHeadings(mdText) {
    if (!mdText) return mdText;
    let s = mdText.replace(
        /([.!?])(\s*)((?:R\s+E\s+S\s+O\s+L\s+U\s+T\s+I\s+O\s+N))\b/gi,
        '$1\n\n### Resolution\n\n',
    );
    s = s.replace(
        /([.!?])(\s*)((?:D\s+E\s+C\s+I\s+S\s+I\s+O\s+N))\b/gi,
        '$1\n\n### Decision\n\n',
    );
    return s;
}

/**
 * Turn orphan `^12` (not already `[^12]`) into GFM footnote references `[^12]`.
 */
export function normalizeLooseFootnoteCarets(mdText) {
    if (!mdText) return mdText;
    return mdText.replace(/(?<!\[)\^(\d+)\b/g, '[^$1]');
}

export function normalizeFullTextMarkdownForGfm(mdText) {
    if (!mdText) return mdText;
    let s = splitSpacedHeadingFromCaseTitleLines(mdText);
    s = splitInlineLetterSpacedHeadings(s);
    s = normalizeLooseFootnoteCarets(s);
    return s;
}
