import azure.functions as func
import json
import os
import logging
import time
import uuid
import base64
import psycopg
import requests
from datetime import datetime, timezone, timedelta

from utils.clerk_auth import get_authenticated_user_id
from utils.founding_promo import expire_founding_promo_for_user, try_grant_founding_promo
from utils.trial import (
    expire_trial_for_user,
    expire_cancelled_xendit_sub,
    expire_past_due_xendit_sub,
    trial_duration_hours,
    past_due_grace_days,
    claim_trial_ending_reminder,
    trial_reminder_hours_before_end,
)
from utils.email import (
    send_cancellation_email,
    send_subscription_payment_past_due_email,
    send_trial_ending_reminder_email,
)

xendit_bp = func.Blueprint()

# ── Config ────────────────────────────────────────────────────────────────────
# Read XENDIT_API_KEY at request time in _xendit_headers() so cold starts and
# app setting updates are picked up reliably; do not cache at import.
XENDIT_WEBHOOK_TOKEN = os.environ.get("XENDIT_WEBHOOK_TOKEN", "")
XENDIT_BASE_URL     = "https://api.xendit.co"

FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://lexmateph.com").rstrip("/")

# ── Bypass mode (same as old PayMongo bypass — skip payment, grant tier) ─────
# Set XENDIT_BYPASS=true in local.settings.json for local dev without real payments.
XENDIT_BYPASS = os.environ.get("XENDIT_BYPASS", "").lower() in ("true", "1", "yes")

# ── Plan definitions ──────────────────────────────────────────────────────────
# amount is in PHP (whole number, not centavos — Xendit PHP uses whole amounts)
PLAN_CONFIGS = {
    "amicus_monthly":    {"amount": 299,  "interval": "MONTH", "interval_count": 1, "tier": "amicus",    "label": "Amicus Monthly"},
    "amicus_yearly":     {"amount": 2990, "interval": "YEAR",  "interval_count": 1, "tier": "amicus",    "label": "Amicus Yearly"},
    "juris_monthly":     {"amount": 499,  "interval": "MONTH", "interval_count": 1, "tier": "juris",     "label": "Juris Monthly"},
    "juris_yearly":      {"amount": 4990, "interval": "YEAR",  "interval_count": 1, "tier": "juris",     "label": "Juris Yearly"},
    "barrister_monthly": {"amount": 999,  "interval": "MONTH", "interval_count": 1, "tier": "barrister", "label": "Barrister Monthly"},
    "barrister_yearly":  {"amount": 9990, "interval": "YEAR",  "interval_count": 1, "tier": "barrister", "label": "Barrister Yearly"},
}

PLAN_KEY_TO_TIER = {k: v["tier"] for k, v in PLAN_CONFIGS.items()}

FREE_TIER_DAILY_LIMITS = {
    "case_digest": 5,
    "bar_question": 5,
    "flashcard": 5,
    "case_digest_download": 5,
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _xendit_headers(api_version: str | None = None) -> dict:
    key = (os.environ.get("XENDIT_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("XENDIT_API_KEY is not set")
    encoded = base64.b64encode(f"{key}:".encode()).decode()
    headers = {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json",
    }
    if api_version:
        headers["api-version"] = api_version
    return headers


def _get_db():
    conn_string = os.environ.get("DB_CONNECTION_STRING")
    if not conn_string:
        raise RuntimeError("DB_CONNECTION_STRING not configured")
    return psycopg.connect(conn_string)


def _request_has_auth_header(req: func.HttpRequest) -> bool:
    h = (req.headers.get("X-Clerk-Authorization") or req.headers.get("Authorization") or "").strip()
    return bool(h)


def _read_json_body(req: func.HttpRequest) -> dict:
    body = None
    try:
        body = req.get_json()
    except Exception:
        body = None
    if isinstance(body, dict) and body:
        return body
    raw = req.get_body()
    if raw:
        try:
            text = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else str(raw)
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return body if isinstance(body, dict) else {}


def _normalize_anonymous_usage_id(raw) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return str(uuid.UUID(s)).lower()
    except (ValueError, AttributeError, TypeError):
        return None


def _next_anchor_date(interval: str) -> str:
    """Return ISO-8601 UTC anchor date for the next billing cycle."""
    now = datetime.now(timezone.utc)
    if interval == "MONTH":
        # Add ~30 days; cap day at 28 (Xendit requirement)
        target = now + timedelta(days=30)
    else:  # YEAR
        target = now + timedelta(days=365)
    if target.day > 28:
        target = target.replace(day=28)
    return target.strftime("%Y-%m-%dT%H:%M:%SZ")




def _subscription_tier_label(tier: str | None) -> str:
    return {
        "amicus": "Amicus",
        "juris": "Juris",
        "barrister": "Barrister",
    }.get((tier or "").strip().lower(), "Paid plan")


def _notify_subscription_payment_grace(plan_id: str, grace_fallback: datetime, *, final_failure: bool) -> None:
    """Load user by Xendit plan id and email them about grace / downgrade (non-blocking)."""
    if not plan_id:
        return
    try:
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT email, subscription_tier, subscription_expires_at
                       FROM users WHERE xendit_plan_id = %s""",
                    (plan_id,),
                )
                row = cur.fetchone()
        if not row or not (row[0] or "").strip():
            return
        raw_email, stier, exp_at = row[0], row[1], row[2]
        deadline = exp_at if exp_at is not None else grace_fallback
        send_subscription_payment_past_due_email(
            raw_email.strip(),
            _subscription_tier_label(stier),
            deadline,
            final_failure=final_failure,
        )
    except Exception as e:
        logging.warning("_notify_subscription_payment_grace: %s", e)


def _ensure_user_exists(clerk_id: str, req: func.HttpRequest):
    """Create a DB row for this Clerk user if one doesn't exist yet.

    Fallback for when the Clerk webhook failed to deliver. Fetches user details
    from the Clerk API using the Bearer token already in the request headers.
    """
    with _get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM users WHERE clerk_id = %s", (clerk_id,))
            if cur.fetchone():
                return  # already exists

    # User missing — fetch details from Clerk API
    try:
        clerk_secret = os.environ.get("CLERK_SECRET_KEY", "")
        if not clerk_secret:
            logging.warning("_ensure_user_exists: CLERK_SECRET_KEY not set, cannot auto-create user")
            return
        clerk_resp = requests.get(
            f"https://api.clerk.com/v1/users/{clerk_id}",
            headers={"Authorization": f"Bearer {clerk_secret}"},
            timeout=10,
        )
        if clerk_resp.status_code != 200:
            logging.warning(f"_ensure_user_exists: Clerk API returned {clerk_resp.status_code}")
            return
        u = clerk_resp.json()
        emails = u.get("email_addresses") or []
        primary_id = u.get("primary_email_address_id")
        email = None
        for e in emails:
            if e.get("id") == primary_id:
                email = e.get("email_address")
                break
        if not email and emails:
            email = emails[0].get("email_address")
        if not email:
            logging.warning(f"_ensure_user_exists: no email for clerk_id={clerk_id}")
            return
        first_name = (u.get("first_name") or "").strip() or None
        last_name  = (u.get("last_name")  or "").strip() or None
        ADMIN_EMAILS = ["rnlarboleda@gmail.com", "rnlarboleda18@gmail.com"]
        is_admin = email.lower() in [e.lower() for e in ADMIN_EMAILS]

        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (clerk_id, email, first_name, last_name, is_admin, founding_promo_eligible)
                    VALUES (%s, %s, %s, %s, %s, TRUE)
                    ON CONFLICT (clerk_id) DO NOTHING
                """, (clerk_id, email, first_name, last_name, is_admin))
                # Also link if the email row exists with no clerk_id (or stale one)
                cur.execute("""
                    UPDATE users SET clerk_id = %s,
                        first_name = COALESCE(%s, first_name),
                        last_name  = COALESCE(%s, last_name)
                    WHERE LOWER(email) = LOWER(%s) AND (clerk_id IS NULL OR clerk_id != %s)
                """, (clerk_id, first_name, last_name, email, clerk_id))
                conn.commit()
        logging.info(f"_ensure_user_exists: auto-created user {clerk_id} ({email})")
    except Exception as e:
        logging.error(f"_ensure_user_exists: failed for clerk_id={clerk_id}: {e}")


def _create_xendit_recurring_plan(clerk_id: str, customer_id: str, payment_token_id: str, plan_key: str) -> str:
    """Create a Xendit recurring plan for the given customer. Returns plan_id."""
    cfg = PLAN_CONFIGS[plan_key]
    ref_id = f"lm-plan-{int(time.time())}-{uuid.uuid4().hex[:6]}"
    payload = {
        "reference_id": ref_id,
        "customer_id": customer_id,
        "currency": "PHP",
        "amount": cfg["amount"],
        # payment_tokens is REQUIRED — without it Xendit has no card to charge on future cycles
        "payment_tokens": [{"payment_token_id": payment_token_id, "rank": 1}],
        "schedule": {
            "interval": cfg["interval"],
            "interval_count": cfg["interval_count"],
            "anchor_date": _next_anchor_date(cfg["interval"]),
            "retry_interval": "DAY",
            "retry_interval_count": 3,
            "total_retry": 3,
            "failed_attempt_notifications": [1, 2, 3],
        },
        "immediate_payment": False,  # first payment already collected via the PAY session
        "failed_cycle_action": "RESUME",
        "notification_channels": ["EMAIL"],
        "payment_link_for_failed_attempt": True,
        "locale": "en",
        "metadata": {
            "clerk_id": clerk_id,
            "plan_key": plan_key,
        },
        "description": f"LexMatePH {cfg['label']} subscription",
    }
    # Recurring plans API requires api-version: 2026-01-01
    recurring_headers = _xendit_headers(api_version="2026-01-01")
    resp = requests.post(
        f"{XENDIT_BASE_URL}/recurring/plans",
        json=payload,
        headers=recurring_headers,
        timeout=20,
    )
    if resp.status_code not in (200, 201, 202):
        raise RuntimeError(f"Xendit recurring plan creation failed ({resp.status_code}): {resp.text}")

    plan_id = resp.json().get("id", "")
    if not plan_id:
        raise RuntimeError(f"Xendit recurring plan: no id in response: {resp.text}")

    # Store plan_id and clear pending plan key
    with _get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE users
                   SET xendit_plan_id = %s, xendit_pending_plan_key = NULL
                   WHERE clerk_id = %s""",
                (plan_id, clerk_id),
            )
            conn.commit()
    return plan_id


# ─────────────────────────────────────────────────────────────────────────────
# Route: GET /api/subscription-status
# ─────────────────────────────────────────────────────────────────────────────
@xendit_bp.route(route="subscription-status", methods=["GET"])
def subscription_status(req: func.HttpRequest) -> func.HttpResponse:
    clerk_id, error = get_authenticated_user_id(req)
    if error:
        return func.HttpResponse(
            json.dumps({"error": "Unauthorized", "detail": error}),
            mimetype="application/json", status_code=401,
        )
    # Auto-create DB row if Clerk webhook missed this user
    _ensure_user_exists(clerk_id, req)
    try:
        trial_reminder_claim = None
        try:
            with _get_db() as conn:
                with conn.cursor() as cur:
                    expire_trial_for_user(cur, clerk_id)
                    expire_cancelled_xendit_sub(cur, clerk_id)
                    expire_past_due_xendit_sub(cur, clerk_id)
                    expire_founding_promo_for_user(cur, clerk_id)
                    cur.execute(
                        "SELECT is_admin, email FROM users WHERE clerk_id = %s",
                        (clerk_id,),
                    )
                    urow = cur.fetchone()
                    if urow:
                        db_admin, email = urow[0], urow[1]
                        is_admin_flag = bool(db_admin)
                        try_grant_founding_promo(cur, clerk_id, is_admin_flag)
                    trial_reminder_claim = claim_trial_ending_reminder(cur, clerk_id)
                    conn.commit()
        except Exception as ex:
            logging.warning("trial/founding promo expire/grant: %s", ex)

        if trial_reminder_claim:
            rem_email, rem_tier, rem_exp = trial_reminder_claim
            send_trial_ending_reminder_email(
                rem_email,
                _subscription_tier_label(str(rem_tier)),
                rem_exp,
                trial_reminder_hours_before_end(),
            )

        with _get_db() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        """
                        SELECT subscription_tier, subscription_status, subscription_expires_at,
                               is_admin, email, founding_promo_slot, subscription_source,
                               xendit_plan_id, founding_promo_granted_at
                        FROM users WHERE clerk_id = %s
                        """,
                        (clerk_id,),
                    )
                    row = cur.fetchone()
                except Exception as db_err:
                    logging.warning(f"Full user fetch failed: {db_err}")
                    conn.rollback()
                    cur.execute(
                        "SELECT subscription_tier, email, xendit_plan_id FROM users WHERE clerk_id = %s",
                        (clerk_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        tier, email, plan_id = row
                        row = (tier, "inactive", None, False, email, None, None, plan_id, None)

                logging.info(f"[subscription-status] clerk_id={clerk_id}, found={row is not None}")

                if not row:
                    return func.HttpResponse(
                        json.dumps({
                            "tier": "free",
                            "status": "inactive",
                            "expires_at": None,
                            "is_admin": False,
                            "debug": "User not in DB",
                            "can_cancel_xendit": False,
                        }),
                        mimetype="application/json", status_code=200,
                        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
                    )

                tier, status, expires_at, is_admin, email, founding_slot, sub_source, xendit_plan_id, founding_granted_at = row

                # Founding promo stores expiry via founding_promo_granted_at + N days.
                # Back-fill expires_at for users granted before this fix was deployed.
                if not expires_at and (sub_source or "").strip().lower() == "founding_promo" and founding_granted_at:
                    from datetime import timedelta
                    from utils.founding_promo import get_promo_duration_days
                    expires_at = founding_granted_at + timedelta(days=get_promo_duration_days())

                is_admin_eff = bool(is_admin)
                tier_norm = (tier or "free")
                sub_low = (sub_source or "").strip().lower()
                # Paid Xendit users may lack xendit_plan_id if payment_token.activation
                # webhooks were delayed or missed after payment_session.completed granted tier.
                can_cancel_xendit = (not is_admin_eff) and (
                    bool(xendit_plan_id)
                    or (sub_low == "xendit" and tier_norm != "free")
                )

                return func.HttpResponse(
                    json.dumps({
                        "tier": tier or "free",
                        "status": status or "inactive",
                        "expires_at": expires_at.isoformat() if expires_at else None,
                        "is_admin": is_admin_eff,
                        "email": email,
                        "founding_promo_slot": founding_slot,
                        "subscription_source": sub_source,
                        "can_cancel_xendit": can_cancel_xendit,
                        "past_due_grace_days": past_due_grace_days(),
                    }),
                    mimetype="application/json", status_code=200,
                    headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
                )

    except Exception as e:
        logging.error(f"subscription_status error: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            mimetype="application/json", status_code=500,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Route: POST /api/create-checkout
# Creates a Xendit payment session and returns a hosted checkout URL.
# Flow: user is redirected to Xendit's page → pays → webhook fires → DB updated.
# ─────────────────────────────────────────────────────────────────────────────
@xendit_bp.route(route="create-checkout", methods=["POST"])
def create_checkout(req: func.HttpRequest) -> func.HttpResponse:
    clerk_id, error = get_authenticated_user_id(req)
    if error:
        return func.HttpResponse(
            json.dumps({"error": "Unauthorized", "detail": error}),
            mimetype="application/json", status_code=401,
        )
    try:
        body = _read_json_body(req)
        plan_key = (body.get("plan_key") or "").strip()

        if not plan_key or plan_key not in PLAN_CONFIGS:
            return func.HttpResponse(
                json.dumps({"error": "Invalid or missing plan_key"}),
                mimetype="application/json", status_code=400,
            )

        # ── BYPASS MODE: skip Xendit and immediately grant the tier ──────────
        if XENDIT_BYPASS:
            tier = PLAN_KEY_TO_TIER.get(plan_key, "free")
            if tier == "free":
                return func.HttpResponse(
                    json.dumps({"error": "Invalid plan_key for bypass mode"}),
                    mimetype="application/json", status_code=400,
                )
            with _get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE users
                           SET subscription_tier = %s, subscription_status = 'active',
                               subscription_source = 'xendit'
                           WHERE clerk_id = %s""",
                        (tier, clerk_id),
                    )
                    conn.commit()
            logging.info(f"[BYPASS] Granted tier '{tier}' to clerk_id={clerk_id}")
            return func.HttpResponse(
                json.dumps({"tier": tier, "bypass": True,
                            "message": f"Bypass: granted {tier} tier."}),
                mimetype="application/json", status_code=200,
            )
        # ─────────────────────────────────────────────────────────────────────

        if not (os.environ.get("XENDIT_API_KEY") or "").strip():
            logging.error("create-checkout: XENDIT_API_KEY is empty in app settings")
            return func.HttpResponse(
                json.dumps({
                    "error": "Payment provider is not configured",
                    "detail": "XENDIT_API_KEY is missing. Add the Xendit secret key to Azure "
                    "Static Web App → Environment variables, or to api/local.settings.json locally.",
                }),
                mimetype="application/json",
                status_code=503,
            )

        cfg = PLAN_CONFIGS[plan_key]

        # Auto-create DB row if Clerk webhook missed this user
        _ensure_user_exists(clerk_id, req)

        # Get user info and any stored Xendit customer ID from DB
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT email, first_name, last_name, xendit_customer_id FROM users WHERE clerk_id = %s",
                    (clerk_id,),
                )
                row = cur.fetchone()
                if not row:
                    return func.HttpResponse(
                        json.dumps({"error": "User not found in database"}),
                        mimetype="application/json", status_code=404,
                    )
                email, first_name, last_name, stored_customer_id = row

        if not first_name:
            first_name = email.split("@")[0].replace(".", " ").replace("_", " ").title() or "User"

        # Determine how to identify the customer in the session:
        # - If we have a valid cust-xxx ID from a previous session, pass it as customer_id.
        # - Otherwise, pass an inline customer object. Use a UUID reference_id so it
        #   never conflicts with previous attempts.
        valid_stored = (stored_customer_id or "").strip()
        has_valid_customer = valid_stored.startswith("cust-") and len(valid_stored) == 41

        # Store pending plan key — the payment_token.activated webhook handler reads this
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET xendit_pending_plan_key = %s WHERE clerk_id = %s",
                    (plan_key, clerk_id),
                )
                conn.commit()

        # Encode full clerk_id in reference_id (no truncation) so the webhook
        # handler can parse it as a reliable fallback if metadata/customer_id lookup fails.
        session_ref = f"lm-{clerk_id}-{int(time.time())}"
        payload = {
            "reference_id": session_ref,
            "session_type": "PAY",
            "allow_save_payment_method": "FORCED",
            "currency": "PHP",
            "amount": cfg["amount"],
            "mode": "PAYMENT_LINK",
            "country": "PH",
            "locale": "en",
            "description": f"LexMatePH — {cfg['label']}",
            # Return to the main app (Case Digest), not marketing `/`, so paid users are not dropped on the landing page.
            "success_return_url": f"{FRONTEND_URL}/decisions?xendit_payment=success&plan={plan_key}",
            "cancel_return_url": f"{FRONTEND_URL}/decisions?xendit_payment=cancelled",
            "metadata": {
                "clerk_id": clerk_id,
                "plan_key": plan_key,
            },
        }

        if has_valid_customer:
            # Reuse existing customer — avoids any duplicate reference_id issue
            payload["customer_id"] = valid_stored
        else:
            # First checkout: create customer inline with a unique reference_id.
            # The session response will contain customer_id which we save to DB.
            payload["customer"] = {
                "reference_id": f"lm-{uuid.uuid4().hex}",
                "type": "INDIVIDUAL",
                "email": email,
                "individual_detail": {
                    "given_names": (first_name or "User")[:50],
                    "surname": (last_name or ".")[:50],
                },
            }
        resp = requests.post(
            f"{XENDIT_BASE_URL}/sessions",
            json=payload,
            headers=_xendit_headers(),
            timeout=20,
        )
        resp_data = resp.json()

        if resp.status_code not in (200, 201):
            logging.error(f"Xendit session creation failed ({resp.status_code}): {resp_data}")
            return func.HttpResponse(
                json.dumps({"error": "Failed to create checkout session", "detail": resp_data}),
                mimetype="application/json", status_code=503,
            )

        checkout_url = resp_data.get("payment_link_url", "")
        if not checkout_url:
            logging.error(f"Xendit session: no payment_link_url in response: {resp_data}")
            return func.HttpResponse(
                json.dumps({"error": "No checkout URL returned by payment provider", "detail": resp_data}),
                mimetype="application/json", status_code=503,
            )

        return func.HttpResponse(
            json.dumps({
                "checkout_url": checkout_url,
                "session_id": resp_data.get("payment_session_id", ""),
                "plan_key": plan_key,
            }),
            mimetype="application/json", status_code=200,
        )

    except Exception as e:
        import traceback
        detail = traceback.format_exc()
        logging.error(f"create_checkout error: {e}\n{detail}")
        if "XENDIT_API_KEY" in str(e):
            return func.HttpResponse(
                json.dumps({"error": "Payment provider is not configured"}),
                mimetype="application/json",
                status_code=503,
            )
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            mimetype="application/json",
            status_code=500,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Route: POST /api/cancel-subscription
# ─────────────────────────────────────────────────────────────────────────────
@xendit_bp.route(route="cancel-subscription", methods=["POST"])
def cancel_subscription(req: func.HttpRequest) -> func.HttpResponse:
    clerk_id, error = get_authenticated_user_id(req)
    if error:
        return func.HttpResponse(
            json.dumps({"error": "Unauthorized"}),
            mimetype="application/json", status_code=401,
        )
    try:
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT xendit_plan_id, subscription_source, subscription_tier, email
                       FROM users WHERE clerk_id = %s""",
                    (clerk_id,),
                )
                row = cur.fetchone()

        if not row:
            return func.HttpResponse(
                json.dumps({"error": "User not found"}),
                mimetype="application/json", status_code=404,
            )

        plan_id, sub_source, sub_tier, user_email = row[0], row[1] or "", row[2] or "free", row[3] or ""
        sub_low = sub_source.strip().lower() if sub_source else ""
        paid = (sub_tier or "free") != "free"
        xendit_deactivated = False

        if plan_id:
            # Step 1: deactivate at Xendit — this stops all future billing cycles.
            cancel_resp = requests.post(
                f"{XENDIT_BASE_URL}/recurring/plans/{plan_id}/deactivate",
                headers=_xendit_headers(api_version="2026-01-01"),
                timeout=15,
            )
            if cancel_resp.status_code in (200, 201):
                xendit_deactivated = True
                logging.info(
                    "cancel_subscription: Xendit plan %s deactivated for clerk_id=%s",
                    plan_id, clerk_id,
                )
            else:
                logging.warning(
                    "cancel_subscription: Xendit deactivate returned %s for plan %s — "
                    "proceeding with local cancellation; review plan in Xendit dashboard",
                    cancel_resp.status_code, plan_id,
                )
        elif sub_low == "xendit" and paid:
            logging.warning(
                "cancel_subscription: paid xendit user clerk_id=%s has no xendit_plan_id; "
                "local cancellation only (recurring plan may never have been linked)",
                clerk_id,
            )
        else:
            return func.HttpResponse(
                json.dumps({"error": "No active subscription found"}),
                mimetype="application/json", status_code=404,
            )

        # Step 2: determine end of current paid period so we can keep access until then.
        # Stored expires_at (from the last cycle.succeeded) is the most accurate.
        # Fallback: query Xendit for the plan schedule; last resort: +30 or +365 days.
        expires_at_value = None
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT subscription_expires_at FROM users WHERE clerk_id = %s",
                    (clerk_id,),
                )
                ea_row = cur.fetchone()
                if ea_row and ea_row[0]:
                    expires_at_value = ea_row[0]

        if expires_at_value is None and plan_id:
            # Query Xendit for the plan to find its schedule anchor / interval.
            try:
                plan_resp = requests.get(
                    f"{XENDIT_BASE_URL}/recurring/plans/{plan_id}",
                    headers=_xendit_headers(api_version="2026-01-01"),
                    timeout=10,
                )
                if plan_resp.status_code == 200:
                    plan_data = plan_resp.json()
                    # Xendit returns next_action_time or schedule.anchor_date
                    schedule = plan_data.get("schedule") or {}
                    next_action = plan_data.get("next_action_time") or schedule.get("next_action_time", "")
                    if next_action:
                        expires_at_value = datetime.fromisoformat(next_action.replace("Z", "+00:00"))
                    else:
                        # Derive from anchor_date + 1 interval
                        anchor = schedule.get("anchor_date", "")
                        interval = (schedule.get("interval") or "MONTH").upper()
                        if anchor:
                            anchor_dt = datetime.fromisoformat(anchor.replace("Z", "+00:00"))
                            delta = timedelta(days=365 if interval == "YEAR" else 30)
                            expires_at_value = anchor_dt + delta
            except Exception as ex:
                logging.warning("cancel_subscription: could not query Xendit plan: %s", ex)

        if expires_at_value is None:
            # Last resort: grant 30 days from now (covers one monthly cycle)
            expires_at_value = datetime.now(timezone.utc) + timedelta(days=30)
            logging.info(
                "cancel_subscription: expires_at fallback to +30d for clerk_id=%s", clerk_id
            )

        # Step 3: mark as cancelled in DB but keep tier until expires_at.
        # The existing expire_cancelled_xendit_sub() called on every subscription-status
        # request will downgrade to Free once NOW() > expires_at.
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE users SET
                           subscription_status     = 'cancelled',
                           subscription_expires_at = %s,
                           xendit_plan_id          = NULL
                       WHERE clerk_id = %s""",
                    (expires_at_value, clerk_id),
                )
                conn.commit()

        logging.info(
            "cancel_subscription: clerk_id=%s tier kept until %s, xendit_deactivated=%s",
            clerk_id, expires_at_value, xendit_deactivated,
        )

        # Send cancellation confirmation email (non-blocking — failure is logged, not raised).
        if user_email:
            _TIER_LABELS = {
                "amicus": "Amicus", "juris": "Juris", "barrister": "Barrister",
            }
            tier_label = _TIER_LABELS.get(sub_tier.lower(), sub_tier.capitalize())
            access_until_str = (
                expires_at_value.strftime("%B %d, %Y")
                if hasattr(expires_at_value, "strftime")
                else str(expires_at_value)
            )
            send_cancellation_email(user_email, tier_label, access_until_str)

        return func.HttpResponse(
            json.dumps({
                "message": "Subscription cancelled. You keep access until the end of your paid period.",
                "access_until": expires_at_value.isoformat() if hasattr(expires_at_value, "isoformat") else str(expires_at_value),
                "xendit_deactivated": xendit_deactivated,
            }),
            mimetype="application/json", status_code=200,
        )
    except Exception as e:
        logging.error(f"cancel_subscription error: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            mimetype="application/json", status_code=500,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Route: POST /api/track-usage
# ─────────────────────────────────────────────────────────────────────────────
@xendit_bp.route(route="track-usage", methods=["POST"])
def track_usage(req: func.HttpRequest) -> func.HttpResponse:
    """Track free-tier daily usage. Returns {allowed, used, limit}.

    Authenticated users on paid tiers are always allowed (no metering).
    Anonymous users get the same free caps via an anonymousId UUID.
    """
    try:
        body = _read_json_body(req)
        feature = (body.get("feature") or "").strip()

        if feature not in FREE_TIER_DAILY_LIMITS:
            return func.HttpResponse(
                json.dumps({"error": f"Unknown feature: {feature}"}),
                mimetype="application/json", status_code=400,
            )

        limit = FREE_TIER_DAILY_LIMITS[feature]

        clerk_id = None
        if _request_has_auth_header(req):
            clerk_id, _auth_error = get_authenticated_user_id(req)

        if clerk_id:
            with _get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT subscription_tier, is_admin FROM users WHERE clerk_id = %s",
                        (clerk_id,),
                    )
                    row = cur.fetchone()
                    tier = (row[0] if row else "free") or "free"
                    is_admin = (row[1] if row else False) or False

                    if is_admin or tier != "free":
                        return func.HttpResponse(
                            json.dumps({"allowed": True, "used": 0, "limit": -1,
                                        "tier": tier, "is_admin": is_admin}),
                            mimetype="application/json", status_code=200,
                        )

                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT pg_advisory_xact_lock(hashtext(%s::text))",
                            (f"{clerk_id}|{feature}",),
                        )
                        cur.execute(
                            """
                            SELECT COUNT(*) FROM usage_logs
                            WHERE clerk_id = %s AND feature = %s
                              AND created_at >= CURRENT_DATE
                              AND created_at < CURRENT_DATE + INTERVAL '1 day'
                            """,
                            (clerk_id, feature),
                        )
                        used = cur.fetchone()[0]

                        if used >= limit:
                            return func.HttpResponse(
                                json.dumps({"allowed": False, "used": used, "limit": limit, "tier": "free"}),
                                mimetype="application/json", status_code=200,
                            )

                        cur.execute(
                            "INSERT INTO usage_logs (clerk_id, feature) VALUES (%s, %s)",
                            (clerk_id, feature),
                        )

                return func.HttpResponse(
                    json.dumps({"allowed": True, "used": used + 1, "limit": limit, "tier": "free"}),
                    mimetype="application/json", status_code=200,
                )

        anon = _normalize_anonymous_usage_id(body.get("anonymousId") or body.get("anonymous_id"))
        if anon:
            usage_key = f"anon:{anon}"
            with _get_db() as conn:
                with conn.transaction():
                    with conn.cursor() as cur:
                        # Check when this anonymous ID was first seen (any feature).
                        # If within 24 hours, grant full unlimited access — no metering.
                        cur.execute(
                            """
                            SELECT MIN(created_at) FROM usage_logs
                            WHERE clerk_id = %s
                            """,
                            (usage_key,),
                        )
                        first_row = cur.fetchone()
                        first_seen = first_row[0] if first_row else None

                        # Determine if the 24-hour guest window is still active
                        guest_window_hours = int(os.environ.get("GUEST_FULL_ACCESS_HOURS", "24"))
                        in_guest_window = False
                        if first_seen is None:
                            # First ever request — window starts now
                            in_guest_window = True
                        else:
                            # Make first_seen offset-aware for comparison
                            if first_seen.tzinfo is None:
                                from datetime import timezone as _tz
                                first_seen = first_seen.replace(tzinfo=_tz.utc)
                            elapsed = datetime.now(timezone.utc) - first_seen
                            in_guest_window = elapsed.total_seconds() < guest_window_hours * 3600

                        # Always record a usage log entry (so we can track first_seen)
                        cur.execute(
                            "INSERT INTO usage_logs (clerk_id, feature) VALUES (%s, %s)",
                            (usage_key, feature),
                        )

                        if in_guest_window:
                            return func.HttpResponse(
                                json.dumps({"allowed": True, "used": 1, "limit": -1,
                                            "tier": "free", "anonymous": True,
                                            "guest_window": True}),
                                mimetype="application/json", status_code=200,
                            )

                        # 24-hour window expired — fall back to daily cap metering
                        cur.execute(
                            """
                            SELECT COUNT(*) FROM usage_logs
                            WHERE clerk_id = %s AND feature = %s
                              AND created_at >= CURRENT_DATE
                              AND created_at < CURRENT_DATE + INTERVAL '1 day'
                            """,
                            (usage_key, feature),
                        )
                        used = cur.fetchone()[0]

                        if used > limit:
                            return func.HttpResponse(
                                json.dumps({"allowed": False, "used": used, "limit": limit,
                                            "tier": "free", "anonymous": True}),
                                mimetype="application/json", status_code=200,
                            )

                return func.HttpResponse(
                    json.dumps({"allowed": True, "used": used, "limit": limit,
                                "tier": "free", "anonymous": True}),
                    mimetype="application/json", status_code=200,
                )

        if _request_has_auth_header(req):
            return func.HttpResponse(
                json.dumps({"error": "Unauthorized"}),
                mimetype="application/json", status_code=401,
            )

        return func.HttpResponse(
            json.dumps({"error": "anonymousId (UUID) required in JSON body when not signed in"}),
            mimetype="application/json", status_code=400,
        )

    except Exception as e:
        logging.error(f"track_usage error: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            mimetype="application/json", status_code=500,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Route: GET /api/available-plans
# ─────────────────────────────────────────────────────────────────────────────
@xendit_bp.route(route="available-plans", methods=["GET"])
def available_plans(req: func.HttpRequest) -> func.HttpResponse:
    """Return available plan configs for the frontend SubscriptionModal."""
    plans = {
        key: {"amount": cfg["amount"], "tier": cfg["tier"], "label": cfg["label"]}
        for key, cfg in PLAN_CONFIGS.items()
    }

    # Check if founding promo slots are still available (best-effort; public endpoint).
    from utils.founding_promo import get_promo_slot_limit, get_promo_duration_days
    founding_promo_available = False
    founding_promo_slots_remaining = 0
    try:
        limit = get_promo_slot_limit()
        if limit > 0:
            with _get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT claimed_count FROM founding_promo_state WHERE id = 1")
                    row = cur.fetchone()
                    if row is None:
                        founding_promo_available = True
                        founding_promo_slots_remaining = limit
                    else:
                        remaining = max(0, limit - row[0])
                        founding_promo_available = remaining > 0
                        founding_promo_slots_remaining = remaining
    except Exception:
        pass  # Default to unavailable on any DB error

    return func.HttpResponse(
        json.dumps({
            **plans,
            "bypass_mode": XENDIT_BYPASS,
            "payment_provider": "xendit",
            "founding_promo_available": founding_promo_available,
            "founding_promo_slots_remaining": founding_promo_slots_remaining,
            "founding_promo_duration_days": get_promo_duration_days(),
            "trial_duration_hours": trial_duration_hours(),
            "past_due_grace_days": past_due_grace_days(),
        }),
        mimetype="application/json", status_code=200,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Route: POST /api/xendit-webhook
# Receives Xendit webhook events.
# Auth: x-callback-token header (set in Xendit Dashboard → Webhooks).
# ─────────────────────────────────────────────────────────────────────────────
@xendit_bp.route(route="xendit-webhook", methods=["POST"])
def xendit_webhook(req: func.HttpRequest) -> func.HttpResponse:
    # Verify token
    callback_token = req.headers.get("x-callback-token", "")
    if XENDIT_WEBHOOK_TOKEN and callback_token != XENDIT_WEBHOOK_TOKEN:
        logging.warning("Xendit webhook: invalid callback token")
        return func.HttpResponse("Invalid token", status_code=401)

    try:
        raw_body = req.get_body()
        event = json.loads(raw_body)

        evt_type = event.get("event", "")
        evt_data = event.get("data", {})

        # Idempotency key: payment_token events use payment_token_id, others use id
        if isinstance(evt_data, dict):
            data_id = (evt_data.get("payment_token_id") or evt_data.get("id", ""))
        else:
            data_id = ""
        idempotency_key = f"xendit-{evt_type}-{data_id}" if data_id else None

        if idempotency_key:
            try:
                with _get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO webhook_events (id) VALUES (%s) ON CONFLICT (id) DO NOTHING",
                            (idempotency_key,),
                        )
                        inserted = cur.rowcount
                        conn.commit()
                if inserted == 0:
                    logging.info(f"Xendit webhook: duplicate {evt_type}/{data_id} — skipping")
                    return func.HttpResponse("OK", status_code=200)
            except Exception as idem_err:
                logging.warning(f"Xendit webhook idempotency check skipped: {idem_err}")

        logging.info(f"Xendit webhook received: {evt_type} (id={data_id})")

        # Grant tier immediately when initial payment succeeds (before plan is created)
        if evt_type in ("payment.capture", "payment.succeeded", "payment_session.completed"):
            _handle_payment_succeeded(evt_data)
        # v3 uses "payment_token.activation"; older docs said "payment_token.activated"
        elif evt_type in ("payment_token.activated", "payment_token.activation"):
            _handle_payment_token_activated(evt_data)
        elif evt_type in ("recurring.plan.activated", "recurring_plan.activated"):
            _handle_plan_activated(evt_data)
        elif evt_type in ("recurring.plan.inactivated", "recurring_plan.inactivated"):
            _handle_plan_inactivated(evt_data)
        elif evt_type in ("recurring.cycle.succeeded", "recurring_cycle.succeeded"):
            _handle_cycle_succeeded(evt_data)
        elif evt_type in ("recurring.cycle.failed", "recurring_cycle.failed"):
            _handle_cycle_failed(evt_data)
        elif evt_type in ("recurring.cycle.retrying", "recurring_cycle.retrying"):
            _handle_cycle_retrying(evt_data)
        else:
            logging.info(f"Xendit webhook: unhandled event type: {evt_type}")

        return func.HttpResponse("OK", status_code=200)

    except Exception as e:
        logging.error(f"xendit_webhook error: {e}")
        return func.HttpResponse("Internal error", status_code=500)


# ── Webhook handlers ──────────────────────────────────────────────────────────

def _handle_payment_succeeded(data: dict):
    """
    payment_session.completed / payment.capture / payment.succeeded

    1. Grants the subscription tier immediately.
    2. Stores xendit_customer_id so future sessions reuse the same customer.
    3. If payment_token_id is present in the payload (always true for PAY sessions
       with allow_save_payment_method=FORCED), creates the Xendit recurring plan
       right here — no need to wait for the separate payment_token.activation event.
       payment_token.activation remains a reliable backup if this step fails.

    Lookup priority for clerk_id:
    1. metadata.clerk_id (always present in our session metadata)
    2. customer_id → xendit_customer_id in DB
    3. reference_id prefix → parse clerk_id from lm-{clerk_id}-{ts}
    """
    clerk_id = None
    plan_key = None

    # payment_token_id and customer_id are top-level in payment_session.completed
    payment_token_id = (
        data.get("payment_token_id")
        or data.get("payment", {}).get("payment_token_id", "")
        or ""
    )
    customer_id = (
        data.get("customer_id")
        or data.get("payment", {}).get("customer_id", "")
        or ""
    )

    # Priority 1: metadata.clerk_id (most reliable — we always embed it at checkout)
    metadata = data.get("metadata") or data.get("payment", {}).get("metadata") or {}
    clerk_id = metadata.get("clerk_id", "")
    plan_key_meta = metadata.get("plan_key", "")
    if clerk_id:
        try:
            with _get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT xendit_pending_plan_key FROM users WHERE clerk_id = %s",
                        (clerk_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        plan_key = row[0] or plan_key_meta
                    else:
                        plan_key = plan_key_meta
        except Exception as e:
            logging.warning(f"payment.succeeded: metadata clerk_id lookup failed: {e}")
            plan_key = plan_key_meta

    # Priority 2: customer_id → xendit_customer_id column
    if not clerk_id and customer_id:
        try:
            with _get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT clerk_id, xendit_pending_plan_key FROM users WHERE xendit_customer_id = %s",
                        (customer_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        clerk_id, plan_key = row[0], row[1]
        except Exception as e:
            logging.warning(f"payment.succeeded: customer_id lookup failed: {e}")

    # Priority 3: parse clerk_id from our reference_id pattern lm-{clerk_id}-{timestamp}
    if not clerk_id:
        import re
        ref_id = data.get("reference_id", "")
        m = re.match(r'^lm-(.+)-\d+$', ref_id)
        if m:
            parsed_clerk = m.group(1)
            try:
                with _get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT xendit_pending_plan_key FROM users WHERE clerk_id = %s",
                            (parsed_clerk,),
                        )
                        row = cur.fetchone()
                        if row:
                            clerk_id = parsed_clerk
                            plan_key = row[0]
                            logging.info(f"payment.succeeded: found user via reference_id parse: {clerk_id}")
            except Exception as e:
                logging.warning(f"payment.succeeded: reference_id parse lookup failed: {e}")

    if not clerk_id:
        logging.warning(f"payment.succeeded: cannot identify user (customer_id={customer_id}, data keys={list(data.keys())})")
        return

    # Fall back to metadata plan_key if pending key was already cleared
    if not plan_key:
        plan_key = plan_key_meta

    if not plan_key or plan_key not in PLAN_CONFIGS:
        logging.warning(f"payment.succeeded: no valid plan_key for clerk_id={clerk_id} (plan_key={plan_key!r})")
        return

    tier = PLAN_KEY_TO_TIER.get(plan_key, "free")
    if tier == "free":
        return

    # Step 1: grant tier and store xendit_customer_id
    try:
        with _get_db() as conn:
            with conn.cursor() as cur:
                if customer_id:
                    cur.execute(
                        """UPDATE users SET
                               subscription_tier   = %s,
                               subscription_status = 'active',
                               subscription_source = 'xendit',
                               xendit_customer_id  = COALESCE(xendit_customer_id, %s)
                           WHERE clerk_id = %s""",
                        (tier, customer_id, clerk_id),
                    )
                else:
                    cur.execute(
                        """UPDATE users SET
                               subscription_tier   = %s,
                               subscription_status = 'active',
                               subscription_source = 'xendit'
                           WHERE clerk_id = %s""",
                        (tier, clerk_id),
                    )
                conn.commit()
        logging.info(f"payment.succeeded: granted tier '{tier}' to clerk_id={clerk_id}")
    except Exception as e:
        logging.error(f"payment.succeeded handler error: {e}")
        return

    # Step 2: create the Xendit recurring plan immediately using the payment token
    # from this same event. This eliminates the dependency on payment_token.activation.
    # On upgrade, the old plan is deactivated first so the user isn't double-billed.
    if payment_token_id and customer_id:
        try:
            with _get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT xendit_plan_id FROM users WHERE clerk_id = %s",
                        (clerk_id,),
                    )
                    existing = cur.fetchone()
            existing_plan_id = existing[0] if existing else None

            if existing_plan_id:
                # Upgrade path: deactivate the old recurring plan so the user
                # isn't charged at the old rate on the next billing cycle.
                try:
                    deact_resp = requests.post(
                        f"{XENDIT_BASE_URL}/recurring/plans/{existing_plan_id}/deactivate",
                        headers=_xendit_headers(api_version="2026-01-01"),
                        timeout=15,
                    )
                    if deact_resp.status_code in (200, 201):
                        logging.info(
                            "payment.succeeded: deactivated old plan %s for upgrade (clerk_id=%s)",
                            existing_plan_id, clerk_id,
                        )
                    else:
                        logging.warning(
                            "payment.succeeded: deactivate old plan %s returned %s — proceeding",
                            existing_plan_id, deact_resp.status_code,
                        )
                except Exception as deact_err:
                    logging.warning(
                        "payment.succeeded: could not deactivate old plan %s: %s — proceeding",
                        existing_plan_id, deact_err,
                    )
                # Clear old plan_id so _create_xendit_recurring_plan can write the new one.
                try:
                    with _get_db() as conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                "UPDATE users SET xendit_plan_id = NULL WHERE clerk_id = %s",
                                (clerk_id,),
                            )
                            conn.commit()
                except Exception as clear_err:
                    logging.warning(
                        "payment.succeeded: could not clear old xendit_plan_id for clerk_id=%s: %s",
                        clerk_id, clear_err,
                    )

            plan_id = _create_xendit_recurring_plan(
                clerk_id, customer_id, payment_token_id, plan_key
            )
            logging.info(
                "payment.succeeded: created recurring plan %s for clerk_id=%s plan=%s%s",
                plan_id, clerk_id, plan_key,
                " (upgrade — old plan deactivated)" if existing_plan_id else "",
            )
        except Exception as e:
            logging.warning(
                "payment.succeeded: recurring plan creation failed for clerk_id=%s: %s — "
                "payment_token.activation webhook will retry",
                clerk_id, e,
            )
    else:
        logging.info(
            "payment.succeeded: no payment_token_id in payload for clerk_id=%s — "
            "waiting for payment_token.activation webhook",
            clerk_id,
        )


def _handle_payment_token_activated(data: dict):
    """
    payment_token.activation — user saved their payment method during checkout.
    We use payment_token_id + customer_id to create the recurring subscription plan.
    The pending plan key was stored in DB when checkout was initiated.

    Note: Xendit test events may omit customer_id; fall back to metadata.clerk_id.
    """
    customer_id = data.get("customer_id", "")
    payment_token_id = data.get("payment_token_id", "")

    if not payment_token_id:
        logging.error("payment_token.activation: missing payment_token_id")
        return

    clerk_id = None
    plan_key = None

    if customer_id:
        try:
            with _get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT clerk_id, xendit_pending_plan_key FROM users WHERE xendit_customer_id = %s",
                        (customer_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        clerk_id, plan_key = row[0], row[1]
        except Exception as e:
            logging.error(f"payment_token.activation: DB lookup failed: {e}")

    if not clerk_id:
        metadata = data.get("metadata") or {}
        clerk_id = metadata.get("clerk_id", "")
        if clerk_id:
            try:
                with _get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT xendit_customer_id, xendit_pending_plan_key FROM users WHERE clerk_id = %s",
                            (clerk_id,),
                        )
                        row = cur.fetchone()
                        if row:
                            if not customer_id:
                                customer_id = row[0] or ""
                            plan_key = row[1]
            except Exception as e:
                logging.error(f"payment_token.activation: metadata clerk_id lookup failed: {e}")

    if not clerk_id:
        logging.error(f"payment_token.activation: cannot identify user (customer_id={customer_id})")
        return
    if not plan_key or plan_key not in PLAN_CONFIGS:
        logging.warning(
            f"payment_token.activation: clerk_id={clerk_id} has no pending plan_key — "
            "recurring plan creation skipped"
        )
        return

    try:
        plan_id = _create_xendit_recurring_plan(clerk_id, customer_id, payment_token_id, plan_key)
        logging.info(f"payment_token.activation: created plan {plan_id} for clerk_id={clerk_id}, plan={plan_key}")
    except Exception as e:
        logging.error(f"payment_token.activation: plan creation failed for clerk_id={clerk_id}: {e}")


def _handle_plan_activated(data: dict):
    """
    recurring.plan.activated — the subscription plan is now active.
    clerk_id and plan_key are stored in plan metadata.
    """
    plan_id = data.get("id", "")
    metadata = data.get("metadata") or {}
    clerk_id = metadata.get("clerk_id", "")
    plan_key = metadata.get("plan_key", "")

    if not clerk_id:
        # Fallback: look up by xendit_plan_id if metadata is missing
        if plan_id:
            try:
                with _get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT clerk_id, xendit_pending_plan_key FROM users WHERE xendit_plan_id = %s",
                            (plan_id,),
                        )
                        row = cur.fetchone()
                        if row:
                            clerk_id = row[0]
                            plan_key = row[1] or plan_key
            except Exception as e:
                logging.error(f"plan_activated: fallback lookup failed: {e}")

    if not clerk_id:
        logging.error(f"recurring.plan.activated: cannot resolve clerk_id (plan_id={plan_id})")
        return

    tier = PLAN_KEY_TO_TIER.get(plan_key, "free")
    if tier == "free":
        logging.error(f"recurring.plan.activated: unknown plan_key '{plan_key}' for clerk_id={clerk_id}")
        return

    try:
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE users SET
                           subscription_tier        = %s,
                           subscription_status      = 'active',
                           xendit_plan_id           = %s,
                           subscription_source      = 'xendit',
                           subscription_expires_at  = NULL,
                           xendit_pending_plan_key  = NULL
                       WHERE clerk_id = %s""",
                    (tier, plan_id, clerk_id),
                )
                conn.commit()
        logging.info(f"recurring.plan.activated: clerk_id={clerk_id}, tier={tier}, plan_id={plan_id}")
    except Exception as e:
        logging.error(f"recurring.plan.activated: DB update failed: {e}")


def _handle_plan_inactivated(data: dict):
    """recurring.plan.inactivated — Xendit confirms plan is cancelled / ended.

    If the user still has paid days remaining (subscription_expires_at > NOW()),
    keep their tier and let the normal expiry path downgrade them at period end.
    If no expiry is set (edge case) downgrade immediately.
    """
    plan_id = data.get("id", "")
    if not plan_id:
        logging.warning("recurring.plan.inactivated: missing plan id")
        return
    try:
        with _get_db() as conn:
            with conn.cursor() as cur:
                # Always clear plan_id and mark cancelled.
                # Only drop tier immediately when no unexpired period remains.
                cur.execute(
                    """UPDATE users SET
                           subscription_status = 'cancelled',
                           xendit_plan_id      = NULL,
                           subscription_tier   = CASE
                               WHEN subscription_expires_at IS NOT NULL
                                AND subscription_expires_at > NOW()
                               THEN subscription_tier   -- keep until period ends
                               ELSE 'free'
                           END
                       WHERE xendit_plan_id = %s""",
                    (plan_id,),
                )
                conn.commit()
        logging.info(f"recurring.plan.inactivated: plan_id={plan_id} — tier kept if expires_at in future")
    except Exception as e:
        logging.error(f"recurring.plan.inactivated: DB update failed: {e}")


def _handle_cycle_succeeded(data: dict):
    """recurring.cycle.succeeded — renewal payment successful.

    Updates subscription_status to 'active' and records the next billing date
    in subscription_expires_at. Knowing the next date lets cancel_subscription
    keep the user on their paid tier until that date rather than cutting them
    off immediately.
    """
    plan_id = data.get("recurring_plan_id", "")
    if not plan_id:
        logging.warning("recurring.cycle.succeeded: missing recurring_plan_id")
        return

    # Xendit puts the next scheduled date in scheduled_timestamp / next_action_time
    next_billing_raw = (
        data.get("next_action_time")
        or data.get("scheduled_timestamp")
        or data.get("next_billing_date")
        or ""
    )
    next_billing_dt = None
    if next_billing_raw:
        try:
            next_billing_dt = datetime.fromisoformat(
                str(next_billing_raw).replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            pass

    try:
        with _get_db() as conn:
            with conn.cursor() as cur:
                if next_billing_dt:
                    cur.execute(
                        """UPDATE users
                           SET subscription_status     = 'active',
                               subscription_expires_at = %s
                           WHERE xendit_plan_id = %s""",
                        (next_billing_dt, plan_id),
                    )
                else:
                    cur.execute(
                        "UPDATE users SET subscription_status = 'active' WHERE xendit_plan_id = %s",
                        (plan_id,),
                    )
                conn.commit()
        logging.info(
            "recurring.cycle.succeeded: plan_id=%s next_billing=%s",
            plan_id, next_billing_dt,
        )
    except Exception as e:
        logging.error(f"recurring.cycle.succeeded: DB update failed: {e}")


def _handle_cycle_failed(data: dict):
    """recurring.cycle.failed — all retries exhausted.

    Sets status to past_due and records a grace period (PAST_DUE_GRACE_DAYS) in
    subscription_expires_at. If the payment is not resolved by then,
    expire_past_due_xendit_sub() will downgrade the user to Free on their
    next subscription-status request (or nightly batch).
    """
    plan_id = data.get("recurring_plan_id", "")
    if not plan_id:
        logging.warning("recurring.cycle.failed: missing recurring_plan_id")
        return
    grace_days = past_due_grace_days()
    grace_until = datetime.now(timezone.utc) + timedelta(days=grace_days)
    try:
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE users SET
                           subscription_status     = 'past_due',
                           subscription_expires_at = %s
                       WHERE xendit_plan_id = %s
                         AND (subscription_expires_at IS NULL
                              OR subscription_expires_at < %s)""",
                    (grace_until, plan_id, grace_until),
                )
                conn.commit()
        logging.warning(
            "recurring.cycle.failed: plan_id=%s — grace period until %s",
            plan_id, grace_until,
        )
        _notify_subscription_payment_grace(plan_id, grace_until, final_failure=True)
    except Exception as e:
        logging.error(f"recurring.cycle.failed: DB update failed: {e}")


def _handle_cycle_retrying(data: dict):
    """recurring.cycle.retrying — payment failed, Xendit is scheduling a retry.

    Sets past_due but does NOT overwrite an existing grace period expiry
    (that was already set by cycle.failed or a previous retrying event).
    """
    plan_id = data.get("recurring_plan_id", "")
    if not plan_id:
        logging.warning("recurring.cycle.retrying: missing recurring_plan_id")
        return
    grace_days = past_due_grace_days()
    grace_until = datetime.now(timezone.utc) + timedelta(days=grace_days)
    try:
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE users SET
                           subscription_status     = 'past_due',
                           subscription_expires_at = COALESCE(subscription_expires_at, %s)
                       WHERE xendit_plan_id = %s""",
                    (grace_until, plan_id),
                )
                conn.commit()
        logging.info(f"recurring.cycle.retrying: plan_id={plan_id}")
        _notify_subscription_payment_grace(plan_id, grace_until, final_failure=False)
    except Exception as e:
        logging.error(f"recurring.cycle.retrying: DB update failed: {e}")
