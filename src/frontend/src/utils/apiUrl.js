/**
 * Build an API URL. In dev, relative `/api/...` uses the Vite proxy.
 * Set VITE_API_BASE_URL (e.g. https://your-app.azurewebsites.net) if the SPA is not served with /api on the same origin.
 */
export function apiUrl(path) {
  const base = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
  const p = path.startsWith('/') ? path : `/${path}`;
  if (base) return `${base}${p}`;
  return p;
}

/**
 * `GET /api/sc_decisions/{id}` is registered with an integer route param.
 * Normalize ids from JSON/Postgres (number, decimal string) for a valid path segment.
 * @param {unknown} caseId
 * @returns {string|null} integer string, or null if not usable
 */
export function normalizeScDecisionsRouteId(caseId) {
  if (caseId == null) return null;
  if (typeof caseId === 'number' && Number.isInteger(caseId) && caseId > 0) return String(caseId);
  const s = String(caseId).trim();
  if (!/^\d+$/.test(s)) return null;
  if (/^0+$/.test(s)) return null;
  return s;
}
