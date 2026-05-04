/**
 * Normalize Supreme Court full-text markdown before GFM rendering (react-markdown + remark-gfm).
 * Fixes common E-Library / conversion artifacts so tables, footnotes, and headings display correctly.
 */

const UTF8_LATIN1_MOJIBAKE_RE = /[ÃÂ][-ÿ]|Ã.|Â.|â€|â€™|â€œ|â€/;

function mojibakeScore(text) {
    if (!text) return 0;
    const hits = text.match(/[ÃÂ][-ÿ]|Ã.|Â.|â€|â€™|â€œ|â€|�/g);
    return hits ? hits.length : 0;
}

/**
 * Targeted fix for double-UTF-8 mojibake: U+00C2 ("Â") or U+00C3 ("Ã")
 * followed by a valid UTF-8 continuation byte (U+0080-U+00BF).  These pairs appear
 * when UTF-8 bytes are misread as Latin-1 and re-encoded, turning N-tilde into
 * "Ã", n-tilde into "Ã±", e-acute into "Ã©", etc.
 * The decode formula is exact -- no heuristic score comparison needed.
 */
export function repairDoubleUtf8Latin1(text) {
    if (!text) return text;
    return text.replace(/[ÂÃ][-¿]/g, (m) =>
        String.fromCodePoint(((m.charCodeAt(0) & 0x1f) << 6) | (m.charCodeAt(1) & 0x3f))
    );
}

/**
 * Repair UTF-8 that was accidentally decoded as Latin-1 / CP1252.
 * Example: "EspaÃ±a" -> "España".
 */
export function repairUtf8Latin1Mojibake(text) {
    if (!text || !UTF8_LATIN1_MOJIBAKE_RE.test(text)) return text;
    try {
        const bytes = Uint8Array.from([...text].map((ch) => ch.charCodeAt(0) & 0xff));
        const decoded = new TextDecoder('utf-8', { fatal: false }).decode(bytes);
        return mojibakeScore(decoded) < mojibakeScore(text) ? decoded : text;
    } catch {
        return text;
    }
}

/**
 * UTF-8 punctuation decoded as Windows-1252 (each byte -> one BMP char): a-hat + euro + third.
 * Third-byte map from `new TextDecoder('windows-1252').decode(Uint8Array.from(utf8Bytes))`.
 */
export function repairFullTextMojibake(mdText) {
    if (!mdText) return mdText;
    return (
        mdText
            // ISO-8859-1 decoded 3-byte UTF-8: requests uses ISO-8859-1 when the HTTP
            // Content-Type header has no charset (eLib).  Bytes 0x80-0xBF map to
            // U+0080-U+00BF in Latin-1, so [E2][80][94] → â + U+0080 + U+0094 (two
            // invisible C1 controls).  Decode the trio back to the proper Unicode char.
            .replace(/â([\x80-\x9f])([\x80-\xbf])/g, (m, c1, c2) => {
                try {
                    return new TextDecoder('utf-8', { fatal: true }).decode(
                        new Uint8Array([0xe2, c1.charCodeAt(0), c2.charCodeAt(0)])
                    );
                } catch { return m; }
            })
            .replace(/â€”/g, '—') // em dash (E2 80 94)
            .replace(/â€"/g, '—') // em dash when third byte misread as ASCII "
            .replace(/â€“/g, '–') // en dash (E2 80 93)
            .replace(/â€™/g, '’') // right single quote (E2 80 99)
            .replace(/â€œ/g, '“') // left double quote (E2 80 9c -> oe-ligature)
            .replace(/â€/g, '”') // right double quote (E2 80 9d -> raw 0x9d)
            .replace(/â€¢/g, '•') // bullet (E2 80 A2 -> cent)
            .replace(/â€¦/g, '…') // ellipsis (E2 80 A6 -> broken bar as cp1252)
            // Rules / headings: ". a-hat' When" -> em dash before new sentence (SECTION ...).
            .replace(/([.!?])\s*â(?:€)?['’]\s+([A-Z])/g, '$1— $2')
            // Possessive: "plaintiffa-hat' cause" / "accountsa-hateuro' inclusion" -> correct apostrophe (+ s when needed).
            .replace(/(\w+)â(?:€)?['’](\s+)([a-z])/g, (m, word, sp, next) => {
                const w = String(word);
                const apos = '’';
                if (/s$/i.test(w)) return `${w}${apos}${sp}${next}`;
                return `${w}${apos}s${sp}${next}`;
            })
            // Truncated UTF-8 for right-single-quote (E2 80 99) not caught above: a-hat + euro + ASCII '.
            .replace(/â€'/g, '’')
            // Remaining a-hat + ASCII/curly apostrophe -> typographic apostrophe.
            .replace(/â['’]/g, '’')
            // Lone U+00E2 between letters (lost € + third UTF-8 byte) -> em dash, e.g. "confusionsa-hatbench".
            .replace(/([\w)])â(?=\w)/g, '$1—')
            // Sentence / rule-number ends where dash introduced mid-line: "Rules. â These …"
            // (Must run before generic ([\w)])â rule — word char does not precede â here.)
            .replace(/([.!?])\s*â\s+(?=[A-Z\u00C0-\u024F])/g, '$1— ')
            // Truncated em dash when only â remains (Euro + 3rd byte stripped from pipeline).
            // Line-start cites: â Malcolm X / â Our ruling (allow markdown blockquote prefixes)
            .replace(/^((?:>\s*)*)(\s*)â(\s+)(?=[A-Z""„«»\u00C0-\u024F])/gm, '$1$2—$3')
            // â + whitespace + lowercase (clause continues)
            .replace(/(\w)â(\s+)(?=[a-z])/g, '$1—$2')
            // â + whitespace + uppercase (new sentence / name after word-boundary punctuation)
            .replace(/([\w)])â(\s+)(?=[A-Z])/g, '$1—$2')
            // â directly preceded by whitespace or ] (mid-text citations, footnote bodies like
            // "[^1]: â Malcolm X" where ^ is not at true line-start relative to the preceding token).
            .replace(/([ \t\]])â(\s+)(?=[A-ZÀ-ɏ])/g, '$1—$2')
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
 * Split `### ... D E C I S I O N` / `### ... R E S O L U T I O N` into caption line + `### Decision` / `### Resolution`.
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
    // CP1252 patterns (â€" → —) must be fixed before the byte-level Latin-1 decoder
    // runs, otherwise mixed-encoding documents get partially decoded in a way that
    // corrupts the CP1252 sequences before repairFullTextMojibake can match them.
    let s = repairFullTextMojibake(mdText);
    s = repairDoubleUtf8Latin1(s);
    s = repairUtf8Latin1Mojibake(s);
    s = repairFullTextBracketGlitches(s);
    s = escapeLegalCaptionCommaAsterisks(s);
    s = splitSpacedHeadingFromCaseTitleLines(s);
    s = splitInlineLetterSpacedHeadings(s);
    s = normalizeLooseFootnoteCarets(s);
    return s;
}
