import { apiUrl } from './apiUrl';

/** Same-origin `/api/...` in dev, or `VITE_API_BASE_URL` + path when set (see `.env.example`). */
export function adminApiUrl(path) {
  const p = path.startsWith('/') ? path : `/${path}`;
  return apiUrl(p);
}

/**
 * Turn failed admin /api/ops responses into a clear message (HTTP 404 is common when
 * `func start` is stale: only @app.route handlers exist, blueprints never registered).
 */
export function formatAdminApiError(res, bodyError) {
  if (res.status === 404) {
    return (
      'Admin API returned 404 (no route). Stop and restart Azure Functions from the api folder '
      + '(func start). An old process often answers /api/ping but not /api/ops/* because blueprints '
      + 'failed to load at startup — check the Functions terminal for import errors.'
    );
  }
  return bodyError || res.statusText || `Request failed (${res.status})`;
}
