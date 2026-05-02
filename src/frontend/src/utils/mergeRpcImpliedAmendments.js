import RPC_IMPLIED_AMENDMENTS from '../data/rpcImpliedAmendments.json';

/**
 * Merge supplementary “implied” RPC amendment blurbs (special laws that affect an article
 * without a codal row in `rpc_codal.amendments`) into each article for LexCode display.
 *
 * Entries are tagged with `implied: true` so the UI can use the red info affordance.
 */
function normalizeArticleNumKey(art) {
    const n = art?.article_num ?? art?.article_number ?? art?.key_id;
    if (n == null || n === '') return '';
    return String(n).trim();
}

function amendmentAlreadyCoversLaw(existingId, lawLabel) {
    const id = String(existingId || '').toLowerCase();
    const law = String(lawLabel || '').toLowerCase();
    if (!id || !law) return false;
    if (law.includes(id.slice(0, 12)) || id.includes(law.slice(0, 12))) return true;
    const ra = (s) => {
        const m = s.match(/\bra\s*\.?\s*(\d+)/i);
        return m ? m[1] : null;
    };
    const idRa = ra(id);
    const lawRa = ra(law);
    if (idRa && lawRa && idRa === lawRa) return true;
    return false;
}

export function mergeRpcImpliedAmendmentsIntoArticles(articles) {
    if (!Array.isArray(articles) || articles.length === 0) return articles;
    const manifest = RPC_IMPLIED_AMENDMENTS;
    if (!manifest || typeof manifest !== 'object') return articles;

    return articles.map((art) => {
        const key = normalizeArticleNumKey(art);
        if (!key) return art;

        const impliedList = manifest[key];
        if (!impliedList || !Array.isArray(impliedList) || impliedList.length === 0) return art;

        let am = art.amendments;
        if (typeof am === 'string') {
            try {
                am = JSON.parse(am);
            } catch {
                am = [];
            }
        }
        if (!Array.isArray(am)) am = [];

        const next = [...am];
        let changed = false;

        for (const row of impliedList) {
            const law = row?.law;
            const desc = row?.legal_effect;
            if (!law || !desc) continue;

            const dup = next.some((x) => amendmentAlreadyCoversLaw(x.id || x.law, law));
            if (dup) continue;

            next.push({
                id: law,
                date: '',
                description: desc,
                implied: true,
            });
            changed = true;
        }

        if (!changed) return art;
        return { ...art, amendments: next };
    });
}
