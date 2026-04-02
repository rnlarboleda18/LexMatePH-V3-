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
