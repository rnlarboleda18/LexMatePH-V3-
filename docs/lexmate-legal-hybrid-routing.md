# /legal and public pages (DPA, Azure SWA, Clerk)

## Production URL (Clerk)

Set **Terms of Service** and **Privacy Policy** in the Clerk dashboard to:

`https://www.lexmateph.com/legal`

The app route is always **`/legal`**; the `www` host is DNS / deployment.

## Vite SPA (this repo)

Clerk **Edge `middleware` does not run** in Vite. Public access is by **not** gating `PublicLayout` with `SignedIn`. If you add Next.js later, whitelist `^/legal` in Clerk middleware there.

## Azure Static Web Apps

`staticwebapp.config.json` must keep **`navigationFallback` → `index.html`** so refresh on `/legal` is not 404. The copy under `src/frontend/public/` is deployed with the PWA.
