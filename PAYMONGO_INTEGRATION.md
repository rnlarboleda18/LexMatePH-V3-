# PayMongo Subscription Integration — LexMatePH v3
### Full Technical Documentation

---

## Table of Contents
1. [Overview](#1-overview)
2. [Subscription Tiers](#2-subscription-tiers)
3. [Architecture](#3-architecture)
4. [Database Schema](#4-database-schema)
5. [Backend API Reference](#5-backend-api-reference)
6. [Webhook Event Handling](#6-webhook-event-handling)
7. [Frontend Components](#7-frontend-components)
8. [Feature Gating Reference](#8-feature-gating-reference)
9. [Environment Variables](#9-environment-variables)
10. [Setup Guide (First-Time)](#10-setup-guide-first-time)
11. [Local Development with Webhooks](#11-local-development-with-webhooks)
12. [Security Model](#12-security-model)
13. [Error Reference](#13-error-reference)
14. [Pending Work](#14-pending-work)
15. [Test & Bypass Mode](#15-test--bypass-mode)
16. [Admin Bypass Mechanism](#16-admin-bypass-mechanism)

---

## 1. Overview

LexMatePH v3 uses **PayMongo** for Philippine-native recurring billing (GCash, Maya, card, GrabPay) and **Clerk** for user identity. The two systems are bridged by the backend PostgreSQL `users` table.

```
User signs in (Clerk)
      │
      ▼
Backend reads subscription_tier from users table
      │
      ▼
Frontend canAccess(feature) → Allow or UpgradeWall
      │                              │
      ▼                              ▼
Feature renders              SubscriptionModal opens
                                     │
                                     ▼
                           POST /api/create-checkout
                                     │
                                     ▼
                           PayMongo Hosted Checkout
                                     │
                                     ▼
                           PayMongo fires webhook
                                     │
                                     ▼
                           POST /api/paymongo-webhook
                                     │
                                     ▼
                           DB updated → tier = 'amicus'|'juris'|'barrister'
```

> [!IMPORTANT]
> All subscription enforcement MUST be done **server-side**. Frontend gating is UI-only and can be bypassed by a technically skilled user. Always verify `subscription_tier` from the DB in any backend route that serves gated content.

---

## 2. Subscription Tiers

| Internal Key | Display Name | Price | Description |
|---|---|---|---|
| `free` | Free | ₱0 | Default for all new users |
| `amicus` | Amicus | ₱199/mo · ₱1,990/yr | Unlimited core legal content, limited LexPlay |
| `juris` | Juris | ₱499/mo · ₱4,990/yr | Unlimited everything except Lexify |
| `barrister` | Barrister | ₱999/mo · ₱9,990/yr | All features including Lexify AI grading |
| `admin` | Administrator | N/A | Bypasses all restrictions (Hardcoded emails) |

### Feature Matrix

| Feature | Free | Amicus | Juris | Barrister | Administrator |
|---|---|---|---|---|---|
| Case Digests (SC Decisions) | 5/day | Unlimited | Unlimited | Unlimited | Unlimited |
| Bar Questions (detail view) | 5/day | Unlimited | Unlimited | Unlimited | Unlimited |
| Flashcards | 5/day | Unlimited | Unlimited | Unlimited | Unlimited |
| LexCode / CodexPhil (read-only) | ✅ | ✅ | ✅ | ✅ | ✅ |
| LexCode Linked Jurisprudence | ❌ | ✅ | ✅ | ✅ | ✅ |
| Case Digest Sidebar in LexCode | ❌ | ✅ | ✅ | ✅ | ✅ |
| LexPlay (audio/video) | 5 min/day | 5 min/day | Unlimited | Unlimited | Unlimited |
| LexPlaylist | Add only | Add only | Full | Full | Full |
| Lexify Bar Simulator + AI Grading | ❌ | ❌ | ❌ | ✅ | ✅ |


---

## 3. Architecture

### Tech Stack

| Layer | Technology |
|---|---|
| Identity / Auth | Clerk (JWT via RS256 / HS256) |
| Payment Processing | PayMongo (Subscriptions API) |
| Backend | Python, Azure Functions (Blueprint pattern) |
| Database | PostgreSQL via `psycopg` |
| Frontend | React + Vite + Tailwind CSS |

### Key Design Decisions

**1. Clerk owns identity. PayMongo owns billing. PostgreSQL bridges them.**

- Clerk fires a webhook on user creation → stored in `users(clerk_id, email)`
- PayMongo fires webhooks on subscription events → updates `users(subscription_tier, subscription_status)`
- Every authenticated backend request validates the Clerk JWT from `X-Clerk-Authorization` header
- There is NO cross-dependency between Clerk and PayMongo at the API level

**2. Webhooks are the single source of truth.**

The frontend NEVER upgrades a user's tier directly. Only verified PayMongo webhook events may change `subscription_tier` in the database. This prevents tampering.

**3. Free tier limits are tracked server-side.**

Daily usage is recorded in the `usage_logs` table via `POST /api/track-usage`. The backend counts today's rows per `clerk_id + feature` and enforces the limit atomically.

---

## 4. Database Schema

### Migration Script
**File:** `sql/paymongo_migration.sql`

```sql
-- Run once against your PostgreSQL database
ALTER TABLE users ADD COLUMN IF NOT EXISTS paymongo_customer_id TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_tier TEXT NOT NULL DEFAULT 'free';
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_status TEXT NOT NULL DEFAULT 'inactive';
ALTER TABLE users ADD COLUMN IF NOT EXISTS paymongo_subscription_id TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_expires_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;

-- Set admin status for specific emails
UPDATE users SET is_admin = TRUE WHERE email IN ('rnlarboleda@gmail.com', 'rnlarboleda18@gmail.com');

CREATE TABLE IF NOT EXISTS usage_logs (

    id SERIAL PRIMARY KEY,
    clerk_id TEXT NOT NULL,
    feature TEXT NOT NULL,  -- 'case_digest' | 'bar_question' | 'flashcard'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usage_logs_clerk_date
    ON usage_logs(clerk_id, feature, created_at);
```

### `users` Table — New Columns

| Column | Type | Description |
|---|---|---|
| `subscription_tier` | `TEXT` (default: `'free'`) | Active tier: `free`, `amicus`, `juris`, `barrister` |
| `subscription_status` | `TEXT` (default: `'inactive'`) | `active`, `inactive`, `cancelled`, `past_due` |
| `paymongo_customer_id` | `TEXT` | PayMongo Customer ID (`cus_...`) |
| `paymongo_subscription_id` | `TEXT` | PayMongo Subscription ID (`sub_...`) |
| `subscription_expires_at` | `TIMESTAMPTZ` | When the current billing period ends |

### `usage_logs` Table

| Column | Type | Description |
|---|---|---|
| `id` | `SERIAL` | Auto-incrementing PK |
| `clerk_id` | `TEXT` | References `users.clerk_id` |
| `feature` | `TEXT` | `case_digest`, `bar_question`, or `flashcard` |
| `created_at` | `TIMESTAMPTZ` | Auto-set to `NOW()` |

---

## 5. Backend API Reference

**File:** `api/blueprints/paymongo.py`
**Registered in:** `api/function_app.py`

All authenticated routes require the Clerk JWT in the request header:
```
X-Clerk-Authorization: Bearer <clerk_jwt>
```

---

### `GET /api/subscription-status`

Returns the subscription tier and status for the authenticated user.

**Auth:** Required (Clerk JWT)

**Response `200`:**
```json
{
  "tier": "amicus",
  "status": "active",
  "expires_at": "2026-04-25T00:00:00+00:00"
}
```

**Response if user not in DB:**
```json
{ "tier": "free", "status": "inactive", "expires_at": null }
```

---

### `GET /api/available-plans`

Returns the PayMongo Plan IDs currently configured in environment variables. Used by the frontend `SubscriptionModal` to map tier selection to the correct `plan_id` for checkout.

**Auth:** None required

**Response `200`:**
```json
{
  "amicus_monthly": "plan_xxxxxxxx",
  "amicus_yearly": "plan_xxxxxxxx",
  "juris_monthly": "plan_xxxxxxxx",
  "juris_yearly": "plan_xxxxxxxx",
  "barrister_monthly": "plan_xxxxxxxx",
  "barrister_yearly": "plan_xxxxxxxx"
}
```

---

### `POST /api/create-checkout`

Creates a PayMongo Customer (or reuses an existing one) and initiates a Subscription, returning the hosted checkout URL.

**Auth:** Required (Clerk JWT)

**Request Body:**
```json
{ "plan_id": "plan_xxxxxxxx" }
```

**Response `200`:**
```json
{
  "checkout_url": "https://checkout.paymongo.com/cs_...",
  "subscription_id": "sub_xxxxxxxx"
}
```

**Response `400`** — Missing `plan_id`:
```json
{ "error": "plan_id is required" }
```

**Response `404`** — User not in DB (Clerk webhook not yet fired):
```json
{ "error": "User not found in database" }
```

**Response `502`** — PayMongo API error:
```json
{ "error": "Failed to create subscription", "detail": { ... } }
```

**Flow:**
1. Validate Clerk JWT → get `clerk_id`
2. Look up `email` from `users` table
3. Check `paymongo_customer_id` — if none, call `POST /v1/customers` on PayMongo API and store the result
4. Call `POST /v1/subscriptions` with `plan_id` + `customer_id`
5. Extract `latest_invoice.attributes.hosted_url` and return as `checkout_url`

---

### `POST /api/cancel-subscription`

Cancels the user's active PayMongo subscription and resets their tier to `free`.

**Auth:** Required (Clerk JWT)

**Response `200`:**
```json
{ "message": "Subscription cancelled successfully" }
```

**Response `404`** — No active subscription:
```json
{ "error": "No active subscription found" }
```

---

### `POST /api/track-usage`

Logs a usage event for Free tier daily limit enforcement. Returns whether the action is allowed.

**Auth:** Required (Clerk JWT)

**Request Body:**
```json
{ "feature": "case_digest" }
```

Valid `feature` values: `case_digest`, `bar_question`, `flashcard`

**Response `200` — Allowed (remaining quota):**
```json
{ "allowed": true, "used": 3, "limit": 5, "tier": "free" }
```

**Response `200` — Blocked (limit reached):**
```json
{ "allowed": false, "used": 5, "limit": 5, "tier": "free" }
```

**Response `200` — Paid user (always allowed):**
```json
{ "allowed": true, "used": 0, "limit": -1, "tier": "amicus" }
```

> [!NOTE]
> Limit is checked and logged atomically in a single DB transaction. Paid users bypass the check entirely and the usage is not logged.

---

### `POST /api/lexify_grade` *(Modified)*

**File:** `api/blueprints/lexify.py`

Now requires **Barrister** tier. If the user is authenticated but not a Barrister subscriber, returns `403`.

**Response `403` — Non-Barrister user:**
```json
{
  "error": "Lexify requires a Barrister subscription.",
  "upgrade": true,
  "required_tier": "barrister",
  "current_tier": "amicus"
}
```

> [!IMPORTANT]
> The `"upgrade": true` field is used by the frontend to distinguish a subscription gate from a general server error, allowing it to show the UpgradeWall instead of an error toast.

---

### `POST /api/paymongo-webhook`

Receives and processes PayMongo webhook events. **Does not require Clerk auth** — uses PayMongo's HMAC-SHA256 signature instead.

See [Section 6](#6-webhook-event-handling) for full details.

---

## 6. Webhook Event Handling

### Signature Verification

PayMongo signs every webhook request with an HMAC-SHA256 signature using `PAYMONGO_WEBHOOK_SECRET`. The signature is in the `Paymongo-Signature` header:

```
Paymongo-Signature: t=1743000000,te=<sha256_hash>,li=<sha256_hash>
```

The verification algorithm:
```python
signed_payload = f"{timestamp}.{raw_body}"
computed = hmac.new(
    PAYMONGO_WEBHOOK_SECRET.encode(),
    signed_payload.encode(),
    hashlib.sha256
).hexdigest()

# Accept if computed matches te (test) or li (live)
is_valid = computed == te_hash or computed == li_hash
```

If verification fails → `400 Bad Request`.

### Handled Events

| PayMongo Event | Action |
|---|---|
| `subscription.created` | Set `subscription_tier`, `subscription_status = 'active'`, store `paymongo_subscription_id` |
| `invoice.payment_succeeded` | Set `subscription_status = 'active'` (renewal confirmation) |
| `subscription.cancelled` | Reset `subscription_tier = 'free'`, `subscription_status = 'cancelled'`, clear `paymongo_subscription_id` |
| `invoice.payment_failed` | Set `subscription_status = 'past_due'` |

### How `subscription.created` Maps to a Tier

The backend uses a `PLAN_TIER_MAP` dictionary that maps each Plan ID env var to its tier name:

```python
PLAN_TIER_MAP = {
    os.environ.get("PAYMONGO_PLAN_AMICUS_MONTHLY"):   "amicus",
    os.environ.get("PAYMONGO_PLAN_AMICUS_YEARLY"):    "amicus",
    os.environ.get("PAYMONGO_PLAN_JURIS_MONTHLY"):    "juris",
    os.environ.get("PAYMONGO_PLAN_JURIS_YEARLY"):     "juris",
    os.environ.get("PAYMONGO_PLAN_BARRISTER_MONTHLY"):"barrister",
    os.environ.get("PAYMONGO_PLAN_BARRISTER_YEARLY"): "barrister",
}
```

The event's `plan_id` is looked up in this map to determine which tier to assign.

### Subscribe to These Events in PayMongo Dashboard

When creating your webhook, subscribe to:
- `subscription.created`
- `invoice.payment_succeeded`
- `subscription.cancelled`
- `invoice.payment_failed`

---

## 7. Frontend Components

### `SubscriptionContext.jsx`

**Path:** `src/frontend/src/context/SubscriptionContext.jsx`
**Provided via:** `<SubscriptionProvider>` in `main.jsx`

#### Context Values

| Value | Type | Description |
|---|---|---|
| `tier` | `string` | Current tier: `'free'`, `'amicus'`, `'juris'`, `'barrister'` |
| `status` | `string` | `'active'`, `'inactive'`, `'cancelled'`, `'past_due'` |
| `tierLabel` | `string` | Human display name: `'Free'`, `'Amicus'`, `'Juris'`, `'Barrister'` |
| `canAccess(feature)` | `function` | Returns `true` if current tier meets the feature requirement |
| `requireAccess(feature)` | `function` | Returns `true` if allowed, or triggers the upgrade modal and returns `false` |
| `openUpgradeModal(feature?)` | `function` | Opens the SubscriptionModal, optionally pre-targeting a feature |
| `closeUpgradeModal()` | `function` | Closes the SubscriptionModal |
| `showUpgradeModal` | `boolean` | Whether the upgrade modal is open |
| `upgradeContext` | `object \| null` | `{ feature, requiredTier }` for the current upgrade prompt |
| `refreshStatus()` | `function` | Re-fetches subscription status from the backend |

#### Tier Order & Feature Requirements

```js
const TIER_ORDER = ['free', 'amicus', 'juris', 'barrister'];

const FEATURE_REQUIREMENTS = {
  case_digest_unlimited: 'amicus',
  bar_question_unlimited: 'amicus',
  flashcard_unlimited: 'amicus',
  codex_linked_cases: 'amicus',
  lexplay_unlimited: 'juris',
  lexify: 'barrister',
};
```

`canAccess(feature)` returns `true` if `TIER_ORDER.indexOf(tier) >= TIER_ORDER.indexOf(required)`.

#### Usage Example

```jsx
import { useSubscription } from '../context/SubscriptionContext';

function MyComponent() {
  const { canAccess, openUpgradeModal } = useSubscription();

  const handleAction = () => {
    if (!canAccess('codex_linked_cases')) {
      openUpgradeModal('codex_linked_cases');
      return;
    }
    // proceed with action
  };
}
```

---

### `UpgradeWall.jsx`

**Path:** `src/frontend/src/components/UpgradeWall.jsx`

A reusable upgrade prompt that appears when a user hits a feature gate.

#### Props

| Prop | Type | Default | Description |
|---|---|---|---|
| `feature` | `string` | required | Key from `FEATURE_REQUIREMENTS` (e.g. `'lexify'`, `'codex_linked_cases'`) |
| `variant` | `'inline' \| 'compact' \| 'modal'` | `'inline'` | Display style |
| `onClose` | `function` | optional | For `'modal'` variant — triggered by "Maybe later" |

#### Variants

- **`inline`** — Full-page centered lock screen with icon, description, CTA button. Used when replacing an entire feature view (e.g., Lexify).
- **`compact`** — Small horizontal bar with lock icon, tier price, and Upgrade button. Used inline within existing UI.
- **`modal`** — Same as `inline` but includes a "Maybe later" dismiss button.

#### Usage

```jsx
// Block entire feature view
<UpgradeWall feature="lexify" variant="inline" />

// Show compact prompt inside a sidebar or panel
<UpgradeWall feature="codex_linked_cases" variant="compact" />
```

---

### `SubscriptionModal.jsx`

**Path:** `src/frontend/src/components/SubscriptionModal.jsx`

Full-screen pricing modal with 4 plan cards and PayMongo checkout integration.

#### Behavior
- Fetches live Plan IDs from `GET /api/available-plans` on mount
- Monthly/Yearly billing toggle (Yearly shows "SAVE 17%" badge)
- Current plan shown with "Current Plan" badge — subscribe button disabled
- "Get [Tier]" button calls `POST /api/create-checkout` → `window.location.href = checkout_url`
- Payment processed on PayMongo's hosted page (supports GCash, Maya, Card, GrabPay)

#### Triggered By
- `openUpgradeModal()` from the Subscription Context (any component can call this)
- `UpgradeWall` "Upgrade" button
- Sidebar "Upgrade" button

---

## 8. Feature Gating Reference

### Where Each Gate Is Enforced

| Feature | Frontend Gate Location | Backend Gate Location |
|---|---|---|
| **Lexify AI Grading** | `App.jsx` — `canAccess('lexify')` renders `<UpgradeWall>` instead of `<LexifyApp>` | `api/blueprints/lexify.py` — checks Barrister tier before calling Gemini API |
| **LexCode Linked Jurisprudence** | `CodexViewer.jsx` — `handleJurisprudenceClick` calls `openUpgradeModal` for Free users | *(none — sidebar data is public, link click is the gate)* |
| **Case Digest Daily Limit** | *(pending: `SupremeDecisions.jsx`)* | `POST /api/track-usage` with `feature: "case_digest"` |
| **Bar Question Daily Limit** | *(pending: `QuestionDetailModal.jsx`)* | `POST /api/track-usage` with `feature: "bar_question"` |
| **Flashcard Daily Limit** | *(pending: `FlashcardSetup.jsx`)* | `POST /api/track-usage` with `feature: "flashcard"` |
| **LexPlay Time Limit** | *(pending: `useLexPlay.jsx`)* | *(client-side — localStorage timer)* |

> [!NOTE]
> Items marked *(pending)* have the backend route fully implemented — only the frontend call to `/api/track-usage` and the UI response (showing UpgradeWall when `allowed: false`) remain to be wired.

---

## 9. Environment Variables

Add these to `api/local.settings.json` for local development, and to Azure App Settings for production:

```json
{
  "Values": {
    "PAYMONGO_SECRET_KEY": "sk_test_...",
    "PAYMONGO_WEBHOOK_SECRET": "whsk_...",
    "PAYMONGO_PLAN_AMICUS_MONTHLY":   "plan_xxxxxxxx",
    "PAYMONGO_PLAN_AMICUS_YEARLY":    "plan_xxxxxxxx",
    "PAYMONGO_PLAN_JURIS_MONTHLY":    "plan_xxxxxxxx",
    "PAYMONGO_PLAN_JURIS_YEARLY":     "plan_xxxxxxxx",
    "PAYMONGO_PLAN_BARRISTER_MONTHLY":"plan_xxxxxxxx",
    "PAYMONGO_PLAN_BARRISTER_YEARLY": "plan_xxxxxxxx",
    "PAYMONGO_BYPASS": "true",
    "FRONTEND_URL": "https://lexmateph.com"
  }
}
```

| Variable | Source | Notes |
|---|---|---|
| `PAYMONGO_SECRET_KEY` | Dashboard → API Keys | Use `sk_test_` prefix for sandbox |
| `PAYMONGO_WEBHOOK_SECRET` | Dashboard → Webhooks → Signing Secret | Generated when you create a webhook endpoint |
| `PAYMONGO_PLAN_*` | Dashboard → Products → Plans | Created manually per plan |
| `PAYMONGO_BYPASS` | Manual | Set to `true` to skip PayMongo and grant tiers instantly |
| `FRONTEND_URL` | Your deployment URL | Used for redirect URLs after checkout |

---

## 10. Setup Guide (First-Time)

### Step 1 — Create a PayMongo Account
1. Register at [paymongo.com](https://paymongo.com)
2. Complete basic business info (Test Mode works without full KYC)

### Step 2 — Get API Keys
1. Dashboard → **Developers → API Keys**
2. Copy **Secret Key** (Test Mode): `sk_test_...`
3. Paste into `local.settings.json` as `PAYMONGO_SECRET_KEY`

### Step 3 — Create the 6 Plans
1. Dashboard → **Products → Plans → Create Plan**
2. Create each plan with these settings:

| Plan Name | Amount (centavos) | Interval | Result |
|---|---|---|---|
| LexMatePH Amicus Monthly | `19900` | `month` | ₱199/mo |
| LexMatePH Amicus Yearly | `199000` | `year` | ₱1,990/yr |
| LexMatePH Juris Monthly | `49900` | `month` | ₱499/mo |
| LexMatePH Juris Yearly | `499000` | `year` | ₱4,990/yr |
| LexMatePH Barrister Monthly | `99900` | `month` | ₱999/mo |
| LexMatePH Barrister Yearly | `999000` | `year` | ₱9,990/yr |

3. Copy each Plan ID (`plan_xxxxxxxx`) and add to env vars

### Step 4 — Run the SQL Migration
```sql
-- Connect to your PostgreSQL DB and run:
-- File: sql/paymongo_migration.sql
```
Or copy the SQL from [Section 4](#4-database-schema) and execute it.

### Step 5 — Create the Webhook
1. Dashboard → **Developers → Webhooks → Add Endpoint**
2. URL: `https://your-api-domain/api/paymongo-webhook`
3. Subscribe to: `subscription.created`, `invoice.payment_succeeded`, `subscription.cancelled`, `invoice.payment_failed`
4. Copy **Signing Secret** → `PAYMONGO_WEBHOOK_SECRET`

### Step 6 — Verify
Start the backend and test:
```bash
curl https://your-api-domain/api/subscription-status \
  -H "X-Clerk-Authorization: Bearer <your_clerk_token>"
# Should return: {"tier": "free", "status": "inactive", "expires_at": null}
```

---

## 11. Local Development with Webhooks

PayMongo webhooks require a publicly reachable URL. For local testing, use **ngrok**.

### Setup ngrok
```powershell
# Install (if not already installed)
winget install ngrok

# Authenticate (get token from ngrok.com)
ngrok config add-authtoken YOUR_TOKEN

# Expose Azure Functions local port
ngrok http 7071
```

ngrok will print something like:
```
Forwarding    https://abc123.ngrok-free.app -> http://localhost:7071
```

### Register with PayMongo
1. Dashboard → **Developers → Webhooks → Add Endpoint**
2. URL: `https://abc123.ngrok-free.app/api/paymongo-webhook`
3. Copy **Signing Secret** → `PAYMONGO_WEBHOOK_SECRET` in `local.settings.json`

### Test Checkout Flow
```powershell
# 1. Start Azure Functions
cd api
func start

# 2. Start React frontend (separate terminal)
cd src/frontend
npm run dev

# 3. Sign in, open pricing modal, pick a plan
# 4. Complete checkout with test card:
#    Card: 4343 4343 4343 4343
#    Expiry: Any future date
#    CVV: Any 3 digits
#    OTP: 111111

# 5. Check DB to confirm tier was updated:
#    SELECT subscription_tier, subscription_status FROM users WHERE clerk_id = '<your_id>';
```

---

## 12. Security Model

### Authentication Chain

```
Browser → X-Clerk-Authorization: Bearer <jwt>
              │
              ▼
         clerk_auth.py::get_authenticated_user_id()
              │
              ├── Validates JWT signature (RS256 via JWKS or HS256 via secret)
              ├── Checks token expiry
              └── Returns clerk_id (sub claim)
```

### Webhook Security

```
PayMongo → POST /api/paymongo-webhook
              │
              ▼
         _verify_paymongo_webhook(raw_body, signature_header)
              │
              ├── Parses t= timestamp from header
              ├── Constructs signed_payload = f"{timestamp}.{raw_body}"
              ├── Computes HMAC-SHA256 with PAYMONGO_WEBHOOK_SECRET
              └── Compares with te= (test) or li= (live) hash
                  │
                  ├── Match → Process event
                  └── No match → 400 Bad Request (request rejected)
```

### Tier Enforcement Layers

| Layer | How |
|---|---|
| **Frontend** | `canAccess(feature)` in `SubscriptionContext` — UI only, cosmetic lock |
| **Backend API** | `lexify_grade` checks `subscription_tier == 'barrister'` from DB |
| **Webhook idempotency** | `subscription_status` updates use `paymongo_subscription_id` as the key — safe to receive the same event multiple times |
| **SQL defaults** | `subscription_tier DEFAULT 'free'` — new users always start free, never accidentally get paid access |

> [!CAUTION]
> Never trust the `tier` value from the frontend or from the Clerk session token. Always read from `users.subscription_tier` in the PostgreSQL database. Only the PayMongo webhook handler writes to this column.

---

## 13. Error Reference

### Backend HTTP Errors

| Status | Occurs When | Response Body |
|---|---|---|
| `400` | Missing required field, invalid webhook signature | `{ "error": "..." }` |
| `401` | Missing or invalid Clerk JWT | `{ "error": "Unauthorized", "detail": "..." }` |
| `403` | Feature requires higher tier | `{ "error": "...", "upgrade": true, "required_tier": "barrister", "current_tier": "amicus" }` |
| `404` | User or subscription not found | `{ "error": "..." }` |
| `500` | DB error or internal failure | `{ "error": "Internal server error" }` |
| `502` | PayMongo API error | `{ "error": "...", "detail": { PayMongo response } }` |

### Frontend Handling

The `SubscriptionModal.jsx` catches checkout errors and displays them inline:
```jsx
const data = await res.json();
if (data.checkout_url) {
  window.location.href = data.checkout_url;
} else {
  setErrorMsg(data.error || 'Failed to create checkout session.');
}
```

When `lexify_grade` returns `403` with `"upgrade": true`, the Lexify frontend should redirect to the UpgradeWall instead of showing a generic error.

---

## 14. Pending Work

The following items have been planned and backend routes are fully ready, but the frontend wiring is incomplete:

### 14.1 Free Tier Daily Limit UI (Frontend)

**Files to modify:** `SupremeDecisions.jsx`, `QuestionDetailModal.jsx`, `FlashcardSetup.jsx` / `Flashcard.jsx`

**Pattern to implement in each:**
```jsx
const { tier } = useSubscription();
const { getToken } = useAuth();

const checkAndTrackUsage = async (feature) => {
  if (tier !== 'free') return true; // paid users skip
  const token = await getToken();
  const res = await fetch('/api/track-usage', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Clerk-Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ feature }),
  });
  const data = await res.json();
  return data.allowed;
};

// On case digest open:
const handleOpen = async (decision) => {
  const allowed = await checkAndTrackUsage('case_digest');
  if (!allowed) {
    openUpgradeModal('case_digest_unlimited');
    return;
  }
  // proceed to open
};
```

### 14.2 LexPlay 5-Minute Timer (Frontend)

**File to modify:** `src/features/lexplay/useLexPlay.jsx`

Track cumulative playback duration in `localStorage`, reset at midnight (Philippine Time). After 5 minutes (300 seconds) for Free and Amicus users, pause playback and call `openUpgradeModal('lexplay_unlimited')`.

```js
// Key: `lexplay_usage_${clerkId}_${todayDate}`
// Value: seconds played today
```

### 14.3 Production Webhook URL

When deploying to Azure, update the PayMongo webhook endpoint from the ngrok URL to:
```
https://<your-azure-function-app>.azurewebsites.net/api/paymongo-webhook
```

Also update `FRONTEND_URL` in Azure App Settings to your production domain.

### 14.4 Subscription Management Page

Consider adding a "Manage Subscription" section to the user profile where subscribers can:
- View current plan and renewal date
- Cancel subscription (calls `POST /api/cancel-subscription`)
- Upgrade/downgrade plan
- Allow users to download invoices (stored in PayMongo)

---

## 15. Test & Bypass Mode

To test subscription gating without setting up PayMongo or using a real card, you can use **Bypass Mode**.

### 15.1 Backend Bypass (Recommended)
This mode allows you to use the UI's subscription buttons to instantly grant a tier.

1.  In `api/local.settings.json`, set `"PAYMONGO_BYPASS": "true"`.
2.  Restart the Azure Functions host.
3.  Refresh the frontend.
4.  In the `SubscriptionModal`, buttons will now show as **⚡ Activate [Tier]**.
5.  Clicking a button will immediately update your tier in the database and unlock features.

### 15.2 Frontend Console Bypass
You can also force a specific tier purely in your browser session using the console:

```js
// Set temporary tier
localStorage.setItem('lexmate_test_tier', 'barrister'); // 'amicus' | 'juris' | 'barrister'

// Clear override
localStorage.removeItem('lexmate_test_tier');
```
*Note: This only affects your current browser and does not save to the database.*

---

## 16. Admin Bypass Mechanism

Designated administrators bypass all subscription restrictions and usage limits.

### 16.1 Admin Emails
The following emails are hardcoded as administrators:
- `rnlarboleda@gmail.com`
- `rnlarboleda18@gmail.com`

### 16.2 How it Works
1.  **Frontend Sync**: The `SubscriptionContext` checks the Clerk user object directly. If the email matches, `isAdmin` is set to `true` and the tier is set to `barrister` locally.
2.  **Backend Sync**: The `subscription-status` route performs the same check. If the email matches, it returns `is_admin: true` and automatically updates the `is_admin` column in the database (Self-Healing).
3.  **Webhook Sync**: The Clerk webhook automatically flags these emails as admins during the first user creation or any update.

### 16.3 Usage
Admins see an **Administrator** badge in the Sidebar and have unlimited access to all features, including Lexify AI grading, regardless of their PayMongo status.

---

*Last updated: 2026-03-25 · LexMatePH v3 · PayMongo Integration v1.0*
