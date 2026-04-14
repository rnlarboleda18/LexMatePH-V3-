/**
 * Client helpers for Supreme Court WordPress RSS bundles (`/api/sc_judiciary_feed`).
 * Bar detection mirrors `api/blueprints/supreme.py` `_bar_related_post`.
 */

export function isBarRelatedPost(item) {
  const t = (item?.title || '').toLowerCase();
  const cats = (item?.categories || []).join(' ').toLowerCase();
  const blob = `${t} ${cats}`;
  const keys = [
    'bar examination',
    'bar exam',
    'bar 202',
    'barista',
    'bar bulletin',
    'philippine bar',
    'bar matters',
    'candidate',
  ];
  return keys.some((k) => blob.includes(k));
}

export function parseFeedDateMs(pub) {
  if (!pub || typeof pub !== 'string') return 0;
  const ms = Date.parse(pub);
  return Number.isFinite(ms) ? ms : 0;
}

/**
 * Merge main `items` and `bar_items` from the same RSS fetch: dedupe by `link`,
 * sort newest first, tag Bar-related rows for UI filters.
 */
export function buildUnifiedFeed(items, barItems) {
  const barLinkSet = new Set((barItems || []).map((b) => b.link).filter(Boolean));
  const merged = new Map();

  for (const it of [...(items || []), ...(barItems || [])]) {
    if (!it?.link) continue;
    const barHighlight = barLinkSet.has(it.link) || isBarRelatedPost(it);
    const next = { ...it, _barHighlight: barHighlight };
    const prev = merged.get(it.link);
    if (!prev) {
      merged.set(it.link, next);
      continue;
    }
    const nextMs = parseFeedDateMs(next.pub_date);
    const prevMs = parseFeedDateMs(prev.pub_date);
    const chosen = nextMs >= prevMs ? next : prev;
    chosen._barHighlight = Boolean(prev._barHighlight || next._barHighlight);
    merged.set(it.link, chosen);
  }

  return Array.from(merged.values()).sort((a, b) => parseFeedDateMs(b.pub_date) - parseFeedDateMs(a.pub_date));
}
