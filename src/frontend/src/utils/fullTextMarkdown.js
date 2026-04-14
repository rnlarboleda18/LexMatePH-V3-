/**
 * Normalize Supreme Court full-text markdown before GFM rendering (react-markdown + remark-gfm).
 * Fixes common E-Library / conversion artifacts so tables, footnotes, and headings display correctly.
 */

/**
 * UTF-8 punctuation decoded as Windows-1252 (each byte → one BMP char): â + € + third.
 * Third-byte map from `new TextDecoder('windows-1252').decode(Uint8Array.from(utf8Bytes))`.
 */
export function repairFullTextMojibake(mdText) {
    if (!mdText) return mdText;
    return (
        mdText
            .replace(/\u00e2\u20ac\u201d/g, '\u2014') // — em dash (E2 80 94)
            .replace(/\u00e2\u20ac\u0022/g, '\u2014') // em dash when third byte misread as ASCII "
            .replace(/\u00e2\u20ac\u201c/g, '\u2013') // – en dash (E2 80 93)
            .replace(/\u00e2\u20ac\u2122/g, '\u2019') // ’ right single (E2 80 99)
            .replace(/\u00e2\u20ac\u0153/g, '\u201c') // “ left double (E2 80 9c → œ)
            .replace(/\u00e2\u20ac\u009d/g, '\u201d') // ” right double (E2 80 9d → raw 0x9d)
            .replace(/\u00e2\u20ac\u00a2/g, '\u2022') // • bullet (E2 80 A2 → ¢)
            .replace(/\u00e2\u20ac\u00a6/g, '\u2026') // … ellipsis (E2 80 A6 → U+00A6 as cp1252)
            // Rules / headings: ". â' When" → em dash before new sentence (SECTION …).
            .replace(/([.!?])\s*\u00e2(?:\u20ac)?['\u2019]\s+([A-Z])/g, '$1\u2014 $2')
            // Possessive: "plaintiffâ' cause" / "accountsâ€' inclusion" → correct apostrophe (+ s when needed).
            .replace(/(\w+)\u00e2(?:\u20ac)?['\u2019](\s+)([a-z])/g, (m, word, sp, next) => {
                const w = String(word);
                const apos = '\u2019';
                if (/s$/i.test(w)) return `${w}${apos}${sp}${next}`;
                return `${w}${apos}s${sp}${next}`;
            })
            // Truncated UTF-8 for ’ (E2 80 99) not caught above: â + € + ASCII '.
            .replace(/\u00e2\u20ac'/g, '\u2019')
            // Remaining â + ASCII/curly apostrophe → typographic apostrophe.
            .replace(/\u00e2['\u2019]/g, '\u2019')
            // Lone â between word chars (lost € and third byte) → em dash, e.g. "confusionsâbench".
            .replace(/(\w)\u00e2(?=\w)/g, '$1\u2014')
            // "reiteratingâ in the" → em dash before continuation.
            .replace(/(\w)\u00e2\s+([a-z])/g, '$1\u2014 $2')
    );
}

/** Common PDF / OCR glitches in Philippine full text. */
export function repairFullTextBracketGlitches(mdText) {
    if (!mdText) return mdText;
    return mdText.replace(/an\[g\]/g, 'ang').replace(/ling\[g\]o/gi, 'linggo');
}

/**
 * SC party captions use `NAME,*` / `NAME,**` for footnote markers; GFM treats `**` as bold.
 * Escape asterisks after a comma when followed by space + capital letter (next name / "JJ.").
 */
export function escapeLegalCaptionCommaAsterisks(mdText) {
    if (!mdText) return mdText;
    return mdText.replace(/,(\*+)(?=\s*[\p{Lu}\p{Lt}])/gu, (match, stars) => {
        const escaped = [...stars].map(() => '\\*').join('');
        return `,${escaped}`;
    });
}

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
    let s = repairFullTextMojibake(mdText);
    s = repairFullTextBracketGlitches(s);
    s = escapeLegalCaptionCommaAsterisks(s);
    s = splitSpacedHeadingFromCaseTitleLines(s);
    s = splitInlineLetterSpacedHeadings(s);
    s = normalizeLooseFootnoteCarets(s);
    return s;
}
