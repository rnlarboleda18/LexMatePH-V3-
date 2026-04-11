/**
 * Canonical Art. 266 body (RA No. 10951, Sec. 61). Used when DB row still holds a 266-A fragment.
 */
export const RPC_ARTICLE_266_BODY_MD = `The crime of slight physical injuries shall be punished:

1. By *arresto menor* when the offender has inflicted physical injuries which shall incapacitate the offended party for labor from one (1) days to nine (9) days, or shall require medical attendance during the same period.

2. By *arresto menor* or a fine not exceeding Forty thousand pesos (₱40,000) and censure when the offender has caused physical injuries which do not prevent the offended party from engaging in his habitual work nor require medical assistance.

3. By *arresto menor* in its minimum period or a fine not exceeding Five thousand pesos (₱5,000) when the offender shall ill-treat another by deed without causing any injury.
`;

export function isCorruptedRpcArticle266Body(md) {
    if (!md || typeof md !== 'string') return false;
    const t = md.trim();
    const hasSlight = /the crime of slight physical injuries/i.test(md);
    if (hasSlight) return false;
    if (/As used in this Act,?\s*non-abusive shall mean/i.test(md)) return true;
    if (/carnal knowledge of another person/i.test(md)) return true;
    if (/^\s*1\)\s*By\s+a\s+person\s+who\s+shall\s+have\s+carnal\s+knowledge/i.test(t)) return true;
    if (/\bx\s+x\s+x\b/i.test(md) && /\(16\)\s*years?\s+of\s+age/i.test(md)) return true;
    return false;
}
