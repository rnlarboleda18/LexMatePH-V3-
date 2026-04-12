# ADR 004: PayMongo for Subscription Payments

**Status:** Accepted  
**Date:** 2024

## Context

LexMatePH offers tiered subscriptions (Amicus, Juris, Barrister) that must be purchased in PHP. We need a payment gateway that supports Philippine payment methods and provides reliable webhook delivery.

## Decision

Use **PayMongo** as the subscription payment processor.

## Reasons

- PayMongo supports GCash, Maya, cards, and bank transfers — the dominant payment methods in the Philippines.
- PayMongo's webhook system delivers subscription lifecycle events (`payment.paid`, `subscription.created`, etc.) with HMAC-SHA256 signature verification.
- Plan IDs are stored as environment variables (`PAYMONGO_PLAN_*`) rather than hardcoded, making tier pricing updates a config-only change.
- A `PAYMONGO_BYPASS=true` flag allows local development without real payment flows.

## Consequences

- **Positive:** Native PH payment method support without custom integrations.
- **Positive:** Subscription status is persisted in PostgreSQL via webhooks, decoupled from the PayMongo API being reachable at read time.
- **Negative:** PayMongo webhooks must be verified (HMAC signature) and handled idempotently. See `api/blueprints/paymongo.py` for the verification implementation and the `webhook_events` idempotency table.
- **Negative:** Currency is PHP only; international subscriptions are not directly supported.
- **Negative:** Test mode (`te=` hash) and live mode (`li=` hash) webhooks use different signature fields. The verification function accepts either.
