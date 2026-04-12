# ADR 002: Clerk for Authentication

**Status:** Accepted  
**Date:** 2024

## Context

LexMatePH needs user authentication for subscription gating, personalized playlists, and webhook-based user lifecycle events.

## Decision

Use **Clerk** as the authentication provider.

## Reasons

- Clerk provides pre-built, accessible React components (`<ClerkProvider>`, `<SignInButton>`, etc.) with minimal setup.
- JWT-based session tokens are verifiable server-side via `CLERK_JWKS_URL` without a database round-trip.
- Clerk webhooks (via Svix) provide reliable `user.created` / `user.updated` / `user.deleted` events with HMAC signature verification.
- Clerk's publishable key is safe to embed in the frontend bundle; the secret key stays server-side only.

## Consequences

- **Positive:** No custom session management; no password storage; MFA and social login available.
- **Positive:** Clerk `clerk_id` is the canonical user identifier in our PostgreSQL `users` table.
- **Negative:** Dependency on Clerk's availability and pricing. A Clerk outage prevents sign-in (not data access).
- **Negative:** `VITE_CLERK_PUBLISHABLE_KEY` must be set in GitHub Actions secrets for production builds. See `.github/workflows/azure-static-web-apps-*.yml`.
- **Negative:** Local dev requires a Clerk application (test key from Clerk dashboard → `.env.local`).
