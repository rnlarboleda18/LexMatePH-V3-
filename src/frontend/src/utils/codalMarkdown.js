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
