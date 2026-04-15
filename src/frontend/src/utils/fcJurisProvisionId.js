/**
 * Provision id for Family Code jurisprudence queries.
 * `/api/fc/all` sets `key_id` to raw fc_codal.article_num (e.g. FC-I-1) while codal_case_links
 * for statute FAM use the display segment (e.g. 1), matching attach_fam_link_counts in const.py.
 *
 * @param {{ article_num?: string, article_number?: string, key_id?: string }} article
 * @param {string|number|undefined} stableId fallback when no segment can be derived
 * @returns {string}
 */
export function fcJurisProvisionIdFromArticle(article, stableId) {
  const n = String(article?.article_num || article?.article_number || '').trim();
  if (n) return n;
  const k = String(article?.key_id || '').trim();
  if (k.includes('-')) return k.split('-').pop().trim();
  return k || String(stableId ?? '');
}
