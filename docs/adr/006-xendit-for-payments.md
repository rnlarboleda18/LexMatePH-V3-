# ADR 006: Xendit for Subscription Payments

**Status:** Accepted  
**Date:** 2026  
**Supersedes:** [ADR 004 — PayMongo](004-paymongo-for-payments.md)

## Context

PayMongo was the original payment processor but was replaced because Xendit became the preferred PHP payment platform. The PayMongo blueprint was removed entirely (commit `ad0ec96`). Requirements remain the same: PHP subscriptions, GCash/Maya/card support, webhook-based lifecycle events.

## Decision

Use **Xendit** as the subscription payment processor with:

1. **`api/utils/xendit_client.py`** — HTTP abstraction layer with retry + exponential backoff, centralising all Xendit API calls.
2. **Recurring plan model** — recurring plans are created inside the `payment_session.completed` webhook handler (`api/blueprints/xendit.py`), not at checkout time. This decouples plan creation from the redirect flow.
3. **`XENDIT_WEBHOOK_TOKEN`** for callback token verification (not HMAC — Xendit uses a shared token).
4. **`XENDIT_BYPASS=true`** flag for local development without real payment flows.

## Reasons

- Xendit supports GCash, Maya, cards, OTC — dominant payment methods in the Philippines.
- HTTP abstraction (`xendit_client.py`) isolates retry/backoff logic from blueprint handlers.
- Webhook-first subscription model keeps subscription state in PostgreSQL, independent of Xendit API availability at read time.
- Plan IDs stored as `XENDIT_PLAN_*` env vars — pricing updates require no code change.

## Consequences

- **Positive:** Retry/backoff centralised in `xendit_client.py`; blueprint code is thin.
- **Positive:** Recurring plans created on webhook event — idempotent re-delivery is safe.
- **Positive:** `XENDIT_BYPASS=true` enables local development without real credentials.
- **Negative:** `XENDIT_WEBHOOK_TOKEN` is a shared token, not HMAC-signed — must be rotated if leaked. Set in Azure Application Settings.
- **Negative:** Subscription state can lag by one webhook delivery window after payment.
- **Negative:** PHP-only; international subscriptions not supported.

## Key files

| File | Role |
|------|------|
| `api/blueprints/xendit.py` | All Xendit HTTP routes (checkout, webhook, cancel, status) |
| `api/utils/xendit_client.py` | HTTP abstraction with retry + backoff |
| `api/config.py` | `XENDIT_API_KEY`, `XENDIT_WEBHOOK_TOKEN`, `XENDIT_BYPASS`, `XENDIT_PLAN_*` |
