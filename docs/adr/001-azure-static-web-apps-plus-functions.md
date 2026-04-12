# ADR 001: Azure Static Web Apps + Azure Functions

**Status:** Accepted  
**Date:** 2024

## Context

LexMatePH is a Philippine bar review PWA. We need hosting that:
- Serves a Vite/React SPA with PWA support and custom cache headers
- Provides a Python API backend with database access
- Handles automatic HTTPS, global CDN, and CI/CD from GitHub
- Keeps infrastructure cost manageable for an early-stage product

## Decision

Use **Azure Static Web Apps (SWA)** for the frontend and **Azure Functions v2 (Python)** as the integrated API.

## Reasons

- SWA provides built-in GitHub Actions CI/CD, custom domains, HTTPS, and CDN with zero server management.
- SWA + Functions share an origin, eliminating CORS for all `/api/*` routes.
- Python Azure Functions supports async, psycopg (PostgreSQL), Redis, Azure Speech, and Blob Storage natively.
- The SWA `navigationFallback` in `staticwebapp.config.json` handles SPA deep-link routing server-side.

## Consequences

- **Positive:** Zero-maintenance SSL, automatic global CDN, integrated preview environments per PR, no containers to manage.
- **Positive:** Free tier covers early usage; cost scales proportionally.
- **Negative:** Python Functions cold-start on the Consumption plan can add 1–3 seconds to the first request after idle periods. Mitigated by the defensive `try/except` import pattern in `function_app.py`.
- **Negative:** API runtime is set to `python:3.10` in `staticwebapp.config.json`; update this when upgrading Python version.
