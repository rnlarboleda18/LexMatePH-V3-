import { normalizeBarSubject } from './subjectNormalize';

/**
 * Canonical Bar subject for a flashcard concept — mirrors api/utils/flashcard_legal_concepts.get_primary_subject:
 * modal count of `digest_primary` on sources (digest Primary only), else legacy modal of normalized case
 * `subject`, else `card.primary_subject`. Never prefers top-level primary before digest so the deck filter
 * matches how the API buckets concepts from legal_concepts JSON.
 */
export function getFlashcardConceptPrimarySubject(card) {
  if (!card || typeof card !== 'object') return null;
  const sources = Array.isArray(card.sources) ? card.sources : [];
  const dpFreq = {};
  const legFreq = {};
  for (const s of sources) {
    if (!s || typeof s !== 'object') continue;
    const dp = String(s.digest_primary || '').trim();
    if (dp) {
      const lab = normalizeBarSubject(dp);
      if (lab) dpFreq[lab] = (dpFreq[lab] || 0) + 1;
      continue;
    }
    const sub = String(s.subject || '').trim();
    if (sub) {
      const lab = normalizeBarSubject(sub);
      if (lab) legFreq[lab] = (legFreq[lab] || 0) + 1;
    }
  }
  const pickModal = (freq) => {
    const keys = Object.keys(freq);
    if (!keys.length) return null;
    return keys.reduce((a, b) => (freq[b] > freq[a] ? b : a));
  };
  const fromDigest = pickModal(dpFreq);
  if (fromDigest) return fromDigest;
  const fromLegacy = pickModal(legFreq);
  if (fromLegacy) return fromLegacy;
  if (card.primary_subject) return normalizeBarSubject(String(card.primary_subject).trim());
  return null;
}
