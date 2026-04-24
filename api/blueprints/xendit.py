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
from utils.trial import expire_trial_for_user

xendit_bp = func.Blueprint()

# ── Config ────────────────────────────────────────────────────────────────────
# Read XENDIT_API_KEY at request time in _xendit_headers() so cold starts and
# app setting updates are picked up reliably; do not cache at import.
XENDIT_WEBHOOK_TOKEN = os.environ.get("XENDIT_WEBHOOK_TOKEN", "")
XENDIT_BASE_URL     = "https://api.xendit.co"

FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://lexmateph.com")

ADMIN_EMAILS = [
    "rnlarboleda@gmail.com",
    "rnlarboleda18@gmail.com",
]

# ── Bypass mode (same as old PayMongo bypass — skip payment, grant tier) ─────
# Set XENDIT_BYPASS=true in local.settings.json for local dev without real payments.
XENDIT_BYPASS = os.environ.get("XENDIT_BYPASS", "").lower() in ("true", "1", "yes")

# ── Plan definitions ──────────────────────────────────────────────────────────
# amount is in PHP (whole number, not centavos — Xendit PHP uses whole amounts)
PLAN_CONFIGS = {
    "amicus_monthly":    {"amount": 199,  "interval": "MONTH", "interval_count": 1, "tier": "amicus",    "label": "Amicus Monthly"},
    "amicus_yearly":     {"amount": 1990, "interval": "YEAR",  "interval_count": 1, "tier": "amicus",    "label": "Amicus Yearly"},
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

def _xendit_headers() -> dict:
    key = (os.environ.get("XENDIT_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("XENDIT_API_KEY is not set")
    encoded = base64.b64encode(f"{key}:".encode()).decode()
    return {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json",
        "api-version": "2022-07-31",
    }


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


def _get_or_create_xendit_customer(clerk_id: str, email: str) -> str:
    """Return existing Xendit customer_id from DB, or create one via API."""
    first_name = None
    last_name = None
    with _get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT xendit_customer_id, first_name, last_name FROM users WHERE clerk_id = %s",
                (clerk_id,),
            )
            row = cur.fetchone()
            if row and row[0]:
                return row[0]
            if row:
                first_name = row[1]
                last_name = row[2]

    if not first_name:
        first_name = email.split("@")[0].replace(".", " ").replace("_", " ").title() or "User"
    if not last_name:
        last_name = "."

    client_ref = f"lexmate-{clerk_id}"
    # Xendit Customer API with client_reference uses a flat schema (no individual_detail wrapper)
    payload = {
        "client_reference": client_ref,
        "type": "INDIVIDUAL",
        "given_name": first_name,
        "surname": last_name,
        "email": email,
    }
    resp = requests.post(
        f"{XENDIT_BASE_URL}/customers",
        json=payload,
        headers=_xendit_headers(),
        timeout=15,
    )
    if resp.status_code not in (200, 201):
        # Xendit returns 400 DUPLICATE_END_CUSTOMER_ERROR or 409 when client_reference already exists
        is_duplicate = (
            resp.status_code == 409
            or (resp.status_code == 400 and "DUPLICATE_END_CUSTOMER_ERROR" in resp.text)
        )
        if is_duplicate:
            fetch_resp = requests.get(
                f"{XENDIT_BASE_URL}/customers?client_reference={client_ref}",
                headers=_xendit_headers(),
                timeout=15,
            )
            if fetch_resp.status_code == 200:
                data = fetch_resp.json()
                items = data.get("data", data) if isinstance(data, dict) else data
                if isinstance(items, list) and items:
                    customer_id = items[0].get("id") or items[0].get("end_customer_id", "")
                elif isinstance(items, dict):
                    customer_id = items.get("id") or items.get("end_customer_id", "")
                else:
                    raise RuntimeError(f"Xendit customer lookup failed after duplicate: {fetch_resp.text}")
            else:
                raise RuntimeError(f"Xendit customer creation failed: {resp.text}")
        else:
            raise RuntimeError(f"Xendit customer creation failed ({resp.status_code}): {resp.text}")
    else:
        resp_data = resp.json()
        customer_id = resp_data.get("id") or resp_data.get("end_customer_id", "")
        if not customer_id:
            raise RuntimeError(f"Xendit customer creation: no id in response: {resp.text}")

    with _get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET xendit_customer_id = %s WHERE clerk_id = %s",
                (customer_id, clerk_id),
            )
            conn.commit()
    return customer_id


def _create_xendit_recurring_plan(clerk_id: str, customer_id: str, plan_key: str) -> str:
    """Create a Xendit recurring plan for the given customer. Returns plan_id."""
    cfg = PLAN_CONFIGS[plan_key]
    ref_id = f"lm-plan-{int(time.time())}-{uuid.uuid4().hex[:6]}"
    payload = {
        "reference_id": ref_id,
        "customer_id": customer_id,
        "currency": "PHP",
        "amount": cfg["amount"],
        "schedule": {
            "interval": cfg["interval"],
            "interval_count": cfg["interval_count"],
            "anchor_date": _next_anchor_date(cfg["interval"]),
            "retry_interval": "DAY",
            "retry_interval_count": 3,
            "total_retry": 3,
        },
        "immediate_payment": False,  # first payment collected via the PAY session
        "failed_cycle_action": "RESUME",
        "notification_channels": ["EMAIL"],
        "metadata": {
            "clerk_id": clerk_id,
            "plan_key": plan_key,
        },
        "description": f"LexMatePH {cfg['label']} subscription",
    }
    resp = requests.post(
        f"{XENDIT_BASE_URL}/recurring/plans",
        json=payload,
        headers=_xendit_headers(),
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
    try:
        try:
            with _get_db() as conn:
                with conn.cursor() as cur:
                    expire_trial_for_user(cur, clerk_id)
                    expire_founding_promo_for_user(cur, clerk_id)
                    cur.execute(
                        "SELECT is_admin, email FROM users WHERE clerk_id = %s",
                        (clerk_id,),
                    )
                    urow = cur.fetchone()
                    if urow:
                        db_admin, email = urow[0], urow[1]
                        em = (email or "").strip().lower()
                        admin_list = [e.strip().lower() for e in ADMIN_EMAILS]
                        is_admin_flag = bool(db_admin) or (em in admin_list)
                        try_grant_founding_promo(cur, clerk_id, is_admin_flag)
                    conn.commit()
        except Exception as ex:
            logging.warning("trial/founding promo expire/grant: %s", ex)

        with _get_db() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        """
                        SELECT subscription_tier, subscription_status, subscription_expires_at,
                               is_admin, email, founding_promo_slot, subscription_source
                        FROM users WHERE clerk_id = %s
                        """,
                        (clerk_id,),
                    )
                    row = cur.fetchone()
                except Exception as db_err:
                    logging.warning(f"Full user fetch failed: {db_err}")
                    conn.rollback()
                    cur.execute(
                        "SELECT subscription_tier, email FROM users WHERE clerk_id = %s",
                        (clerk_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        tier, email = row
                        row = (tier, "inactive", None, False, email, None, None)

                logging.info(f"[subscription-status] clerk_id={clerk_id}, found={row is not None}")

                if not row:
                    return func.HttpResponse(
                        json.dumps({"tier": "free", "status": "inactive", "expires_at": None,
                                    "is_admin": False, "debug": "User not in DB"}),
                        mimetype="application/json", status_code=200,
                        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
                    )

                tier, status, expires_at, is_admin, email, founding_slot, sub_source = row

                if email and email.strip().lower() in [e.strip().lower() for e in ADMIN_EMAILS]:
                    is_admin = True
                    try:
                        if not row[3]:
                            cur.execute("UPDATE users SET is_admin = TRUE WHERE clerk_id = %s", (clerk_id,))
                            conn.commit()
                    except Exception:
                        conn.rollback()

                return func.HttpResponse(
                    json.dumps({
                        "tier": tier or "free",
                        "status": status or "inactive",
                        "expires_at": expires_at.isoformat() if expires_at else None,
                        "is_admin": is_admin or False,
                        "email": email,
                        "founding_promo_slot": founding_slot,
                        "subscription_source": sub_source,
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

        # Get user email from DB
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT email FROM users WHERE clerk_id = %s", (clerk_id,))
                row = cur.fetchone()
                if not row:
                    return func.HttpResponse(
                        json.dumps({"error": "User not found in database"}),
                        mimetype="application/json", status_code=404,
                    )
                email = row[0]

        # Get/create Xendit customer
        customer_id = _get_or_create_xendit_customer(clerk_id, email)

        # Store pending plan key — the payment_token.activated webhook handler reads this
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET xendit_pending_plan_key = %s WHERE clerk_id = %s",
                    (plan_key, clerk_id),
                )
                conn.commit()

        # Create Xendit payment session:
        # session_type=PAY with allow_save_payment_method=FORCED
        # → charges first period AND saves payment method for future recurring cycles
        session_ref = f"lm-{clerk_id[:20]}-{int(time.time())}"
        payload = {
            "reference_id": session_ref,
            "customer_id": customer_id,
            "session_type": "PAY",
            "allow_save_payment_method": "FORCED",
            "currency": "PHP",
            "amount": cfg["amount"],
            "mode": "PAYMENT_LINK",
            "country": "PH",
            "locale": "en",
            "description": f"LexMatePH — {cfg['label']}",
            "success_return_url": f"{FRONTEND_URL}/?xendit_payment=success&plan={plan_key}",
            "cancel_return_url": f"{FRONTEND_URL}/?xendit_payment=cancelled",
            "metadata": {
                "clerk_id": clerk_id,
                "plan_key": plan_key,
            },
        }
        resp = requests.post(
            f"{XENDIT_BASE_URL}/payment_session",
            json=payload,
            headers=_xendit_headers(),
            timeout=20,
        )
        resp_data = resp.json()

        if resp.status_code not in (200, 201):
            logging.error(f"Xendit session creation failed: {resp_data}")
            return func.HttpResponse(
                json.dumps({"error": "Failed to create checkout session", "detail": resp_data}),
                mimetype="application/json", status_code=502,
            )

        checkout_url = resp_data.get("payment_link_url", "")
        if not checkout_url:
            logging.error(f"Xendit session: no payment_link_url in response: {resp_data}")
            return func.HttpResponse(
                json.dumps({"error": "No checkout URL returned by payment provider"}),
                mimetype="application/json", status_code=502,
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
                json.dumps({"error": "Payment provider is not configured", "detail": str(e)}),
                mimetype="application/json",
                status_code=503,
            )
        return func.HttpResponse(
            json.dumps({"error": str(e) or "Unknown internal error", "trace": detail[-600:]}),
            mimetype="application/json",
            status_code=422,
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
                    "SELECT xendit_plan_id FROM users WHERE clerk_id = %s",
                    (clerk_id,),
                )
                row = cur.fetchone()
                if not row or not row[0]:
                    return func.HttpResponse(
                        json.dumps({"error": "No active subscription found"}),
                        mimetype="application/json", status_code=404,
                    )
                plan_id = row[0]

        # Cancel via Xendit API: POST /recurring/plans/{id}/inactivate
        cancel_resp = requests.post(
            f"{XENDIT_BASE_URL}/recurring/plans/{plan_id}/deactivate",
            headers=_xendit_headers(),
            timeout=15,
        )
        if cancel_resp.status_code not in (200, 201):
            logging.warning(
                f"Xendit cancel returned {cancel_resp.status_code}: {cancel_resp.text}"
            )
            # Still downgrade locally so the user is not stuck on a paid tier

        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE users SET
                           subscription_tier   = 'free',
                           subscription_status = 'cancelled',
                           xendit_plan_id      = NULL
                       WHERE clerk_id = %s""",
                    (clerk_id,),
                )
                conn.commit()

        return func.HttpResponse(
            json.dumps({"message": "Subscription cancelled successfully"}),
            mimetype="application/json", status_code=200,
        )
    except Exception as e:
        logging.error(f"cancel_subscription error: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
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
                        cur.execute(
                            "SELECT pg_advisory_xact_lock(hashtext(%s::text))",
                            (f"{usage_key}|{feature}",),
                        )
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

                        if used >= limit:
                            return func.HttpResponse(
                                json.dumps({"allowed": False, "used": used, "limit": limit,
                                            "tier": "free", "anonymous": True}),
                                mimetype="application/json", status_code=200,
                            )

                        cur.execute(
                            "INSERT INTO usage_logs (clerk_id, feature) VALUES (%s, %s)",
                            (usage_key, feature),
                        )

                return func.HttpResponse(
                    json.dumps({"allowed": True, "used": used + 1, "limit": limit,
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
        logging.error(f"track_usage error: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
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
    return func.HttpResponse(
        json.dumps({
            **plans,
            "bypass_mode": XENDIT_BYPASS,
            "payment_provider": "xendit",
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

        # Idempotency key: use event type + data id when available
        data_id = evt_data.get("id", "") if isinstance(evt_data, dict) else ""
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

        # v3 uses "payment_token.activation"; older docs said "payment_token.activated"
        if evt_type in ("payment_token.activated", "payment_token.activation"):
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

def _handle_payment_token_activated(data: dict):
    """
    payment_token.activated — user saved their payment method.
    We use this to create the recurring subscription plan.
    The pending plan key was stored in DB when checkout was initiated.
    """
    customer_id = data.get("customer_id", "")
    if not customer_id:
        logging.error("payment_token.activated: missing customer_id")
        return

    try:
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT clerk_id, xendit_pending_plan_key FROM users WHERE xendit_customer_id = %s",
                    (customer_id,),
                )
                row = cur.fetchone()
    except Exception as e:
        logging.error(f"payment_token.activated: DB lookup failed: {e}")
        return

    if not row:
        logging.error(f"payment_token.activated: no user found for customer_id={customer_id}")
        return

    clerk_id, plan_key = row[0], row[1]
    if not plan_key or plan_key not in PLAN_CONFIGS:
        logging.warning(
            f"payment_token.activated: clerk_id={clerk_id} has no pending plan_key — "
            "recurring plan creation skipped (token saved for future use)"
        )
        return

    try:
        plan_id = _create_xendit_recurring_plan(clerk_id, customer_id, plan_key)
        logging.info(f"payment_token.activated: created plan {plan_id} for clerk_id={clerk_id}, plan={plan_key}")
    except Exception as e:
        logging.error(f"payment_token.activated: plan creation failed for clerk_id={clerk_id}: {e}")


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
    """recurring.plan.inactivated — plan ended or was cancelled."""
    plan_id = data.get("id", "")
    if not plan_id:
        logging.warning("recurring.plan.inactivated: missing plan id")
        return
    try:
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE users SET
                           subscription_tier   = 'free',
                           subscription_status = 'cancelled',
                           xendit_plan_id      = NULL
                       WHERE xendit_plan_id = %s""",
                    (plan_id,),
                )
                conn.commit()
        logging.info(f"recurring.plan.inactivated: plan_id={plan_id}")
    except Exception as e:
        logging.error(f"recurring.plan.inactivated: DB update failed: {e}")


def _handle_cycle_succeeded(data: dict):
    """recurring.cycle.succeeded — renewal payment successful."""
    plan_id = data.get("recurring_plan_id", "")
    if not plan_id:
        logging.warning("recurring.cycle.succeeded: missing recurring_plan_id")
        return
    try:
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET subscription_status = 'active' WHERE xendit_plan_id = %s",
                    (plan_id,),
                )
                conn.commit()
        logging.info(f"recurring.cycle.succeeded: plan_id={plan_id}")
    except Exception as e:
        logging.error(f"recurring.cycle.succeeded: DB update failed: {e}")


def _handle_cycle_failed(data: dict):
    """recurring.cycle.failed — all retries exhausted."""
    plan_id = data.get("recurring_plan_id", "")
    if not plan_id:
        logging.warning("recurring.cycle.failed: missing recurring_plan_id")
        return
    try:
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET subscription_status = 'past_due' WHERE xendit_plan_id = %s",
                    (plan_id,),
                )
                conn.commit()
        logging.warning(f"recurring.cycle.failed: plan_id={plan_id}")
    except Exception as e:
        logging.error(f"recurring.cycle.failed: DB update failed: {e}")


def _handle_cycle_retrying(data: dict):
    """recurring.cycle.retrying — payment failed, retry scheduled."""
    plan_id = data.get("recurring_plan_id", "")
    if not plan_id:
        logging.warning("recurring.cycle.retrying: missing recurring_plan_id")
        return
    try:
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET subscription_status = 'past_due' WHERE xendit_plan_id = %s",
                    (plan_id,),
                )
                conn.commit()
        logging.info(f"recurring.cycle.retrying: plan_id={plan_id}")
    except Exception as e:
        logging.error(f"recurring.cycle.retrying: DB update failed: {e}")
