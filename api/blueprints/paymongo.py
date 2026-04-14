import azure.functions as func
import json
import os
import logging
import hashlib
import hmac
import time
import uuid
import psycopg
import requests

from utils.clerk_auth import get_authenticated_user_id
from utils.founding_promo import expire_founding_promo_for_user, try_grant_founding_promo
from utils.trial import expire_trial_for_user

paymongo_bp = func.Blueprint()

PAYMONGO_SECRET_KEY = os.environ.get("PAYMONGO_SECRET_KEY", "")
PAYMONGO_PUBLIC_KEY = os.environ.get("PAYMONGO_PUBLIC_KEY", "")
PAYMONGO_WEBHOOK_SECRET = os.environ.get("PAYMONGO_WEBHOOK_SECRET", "")
PAYMONGO_BASE_URL = "https://api.paymongo.com/v1"

# Maps PayMongo plan IDs back to tier names
PLAN_TIER_MAP = {
    os.environ.get("PAYMONGO_PLAN_AMICUS_MONTHLY", ""): "amicus",
    os.environ.get("PAYMONGO_PLAN_AMICUS_YEARLY", ""): "amicus",
    os.environ.get("PAYMONGO_PLAN_JURIS_MONTHLY", ""): "juris",
    os.environ.get("PAYMONGO_PLAN_JURIS_YEARLY", ""): "juris",
    os.environ.get("PAYMONGO_PLAN_BARRISTER_MONTHLY", ""): "barrister",
    os.environ.get("PAYMONGO_PLAN_BARRISTER_YEARLY", ""): "barrister",
}

# Available plans for frontend to reference
AVAILABLE_PLANS = {
    "amicus_monthly": os.environ.get("PAYMONGO_PLAN_AMICUS_MONTHLY", ""),
    "amicus_yearly": os.environ.get("PAYMONGO_PLAN_AMICUS_YEARLY", ""),
    "juris_monthly": os.environ.get("PAYMONGO_PLAN_JURIS_MONTHLY", ""),
    "juris_yearly": os.environ.get("PAYMONGO_PLAN_JURIS_YEARLY", ""),
    "barrister_monthly": os.environ.get("PAYMONGO_PLAN_BARRISTER_MONTHLY", ""),
    "barrister_yearly": os.environ.get("PAYMONGO_PLAN_BARRISTER_YEARLY", ""),
}

FREE_TIER_DAILY_LIMITS = {
    "case_digest": 5,
    "bar_question": 5,
    "flashcard": 5,
    "case_digest_download": 5,
}


def _request_has_auth_header(req: func.HttpRequest) -> bool:
    h = (req.headers.get("X-Clerk-Authorization") or req.headers.get("Authorization") or "").strip()
    return bool(h)


def _read_json_body(req: func.HttpRequest) -> dict:
    """Parse JSON body; Azure sometimes returns {} from get_json() even when a body exists."""
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
    """Return canonical lowercase UUID string, or None if invalid."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return str(uuid.UUID(s)).lower()
    except (ValueError, AttributeError, TypeError):
        return None


ADMIN_EMAILS = [
    "rnlarboleda@gmail.com",
    "rnlarboleda18@gmail.com"
]

# ── Testing / dev mode ────────────────────────────────────────────────────────
# Set PAYMONGO_BYPASS=true in local.settings.json to skip PayMongo entirely.
# Any subscription button will IMMEDIATELY grant the tier without payment.
PAYMONGO_BYPASS = os.environ.get("PAYMONGO_BYPASS", "").lower() in ("true", "1", "yes")

# Simple plan-key to tier mapping (used in bypass mode)
PLAN_KEY_TO_TIER = {
    "amicus_monthly": "amicus",
    "amicus_yearly": "amicus",
    "juris_monthly": "juris",
    "juris_yearly": "juris",
    "barrister_monthly": "barrister",
    "barrister_yearly": "barrister",
}



def _paymongo_headers():
    import base64
    encoded = base64.b64encode(f"{PAYMONGO_SECRET_KEY}:".encode()).decode()
    return {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _get_db():
    conn_string = os.environ.get("DB_CONNECTION_STRING")
    if not conn_string:
        raise RuntimeError("DB_CONNECTION_STRING not configured")
    return psycopg.connect(conn_string)


def _get_or_create_paymongo_customer(clerk_id: str, email: str) -> str:
    """Get existing PayMongo customer ID from DB or create a new one."""
    first_name = None
    last_name = None
    with _get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT paymongo_customer_id, first_name, last_name FROM users WHERE clerk_id = %s",
                (clerk_id,),
            )
            row = cur.fetchone()
            if row and row[0]:
                return row[0]
            if row:
                first_name = row[1]
                last_name = row[2]

    # Fallback: derive names from email when Clerk didn't provide them
    if not first_name:
        first_name = email.split("@")[0].replace(".", " ").replace("_", " ").title() or "User"
    if not last_name:
        last_name = "."

    # Create new PayMongo customer — first_name, last_name, email, default_device are all required
    payload = {
        "data": {
            "attributes": {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "default_device": "phone",
            }
        }
    }
    response = requests.post(f"{PAYMONGO_BASE_URL}/customers", json=payload, headers=_paymongo_headers(), timeout=15)
    if response.status_code not in (200, 201):
        raise RuntimeError(f"PayMongo customer creation failed: {response.text}")

    customer_id = response.json()["data"]["id"]

    # Store in DB
    with _get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET paymongo_customer_id = %s WHERE clerk_id = %s",
                (customer_id, clerk_id)
            )
            conn.commit()

    return customer_id


def _verify_paymongo_webhook(payload: bytes, signature_header: str) -> bool:
    """Verify PayMongo webhook signature."""
    if not PAYMONGO_WEBHOOK_SECRET or not signature_header:
        return False
    try:
        # signature_header format: "t=timestamp,te=hash_test,li=hash_live"
        parts = dict(p.split("=", 1) for p in signature_header.split(","))
        timestamp = parts.get("t", "")
        te_hash = parts.get("te", "")  # test mode hash
        li_hash = parts.get("li", "")  # live mode hash

        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        computed = hmac.new(
            PAYMONGO_WEBHOOK_SECRET.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        # Accept either test or live hash
        return computed == te_hash or computed == li_hash
    except Exception as e:
        logging.error(f"Webhook signature verification error: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Route: GET /api/subscription-status
# ─────────────────────────────────────────────────────────────────────────────
@paymongo_bp.route(route="subscription-status", methods=["GET"])
def subscription_status(req: func.HttpRequest) -> func.HttpResponse:
    clerk_id, error = get_authenticated_user_id(req)
    if error:
        return func.HttpResponse(
            json.dumps({"error": "Unauthorized", "detail": error}),
            mimetype="application/json", status_code=401
        )
    try:
        # Expire + try grant in its own transaction so a rollback on fallback SELECT cannot undo it.
        # try_grant fixes missed/delayed Clerk webhooks (user gets Barrister on first subscription-status).
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
                # 1. Try fetching everything (assuming migration has run)
                try:
                    cur.execute(
                        """
                        SELECT subscription_tier, subscription_status, subscription_expires_at, is_admin, email,
                               founding_promo_slot, subscription_source
                        FROM users WHERE clerk_id = %s
                        """,
                        (clerk_id,),
                    )
                    row = cur.fetchone()
                except Exception as db_err:
                    logging.warning(f"Full user fetch failed (migration might be missing): {db_err}")
                    conn.rollback() # Important to reset transaction
                    # 2. Fallback to columns we are SURE exist
                    cur.execute(
                        "SELECT subscription_tier, email FROM users WHERE clerk_id = %s",
                        (clerk_id,)
                    )
                    row = cur.fetchone()
                    # Map fallback row back to our expected format
                    if row:
                        tier, email = row
                        status, expires_at, is_admin = "inactive", None, False
                        row = (tier, status, expires_at, is_admin, email, None, None)

                logging.info(f"[subscription-status] clerk_id: {clerk_id}, found: {row is not None}")
                
                if not row:
                    return func.HttpResponse(
                        json.dumps({"tier": "free", "status": "inactive", "expires_at": None, "is_admin": False, "debug": "User not in DB"}),
                        mimetype="application/json", 
                        status_code=200,
                        headers={"Cache-Control": "no-store, no-cache, must-revalidate"}
                    )
                
                tier, status, expires_at, is_admin, email, founding_slot, sub_source = row
                
                # Check for hardcoded admin bypass
                if email and email.strip().lower() in [e.strip().lower() for e in ADMIN_EMAILS]:
                    is_admin = True
                    # Self-heal DB if needed (wrap in try to avoid 500 if col missing)
                    try:
                        if not row[3]: # row[3] is is_admin
                            cur.execute("UPDATE users SET is_admin = TRUE WHERE clerk_id = %s", (clerk_id,))
                            conn.commit()
                    except:
                        conn.rollback()
                        logging.warning("Could not self-heal is_admin column (probably missing)")


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
                    mimetype="application/json", 
                    status_code=200,
                    headers={"Cache-Control": "no-store, no-cache, must-revalidate"}
                )



    except Exception as e:
        logging.error(f"subscription_status error: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            mimetype="application/json", status_code=500
        )


# ─────────────────────────────────────────────────────────────────────────────
# Route: POST /api/create-checkout
# ─────────────────────────────────────────────────────────────────────────────
@paymongo_bp.route(route="create-checkout", methods=["POST"])
def create_checkout(req: func.HttpRequest) -> func.HttpResponse:
    clerk_id, error = get_authenticated_user_id(req)
    if error:
        return func.HttpResponse(
            json.dumps({"error": "Unauthorized", "detail": error}),
            mimetype="application/json", status_code=401
        )
    try:
        body = req.get_json()
        plan_id = body.get("plan_id", "").strip()          # PayMongo plan ID  (normal mode)
        plan_key = body.get("plan_key", "").strip()        # e.g. 'amicus_monthly' (bypass mode)

        # ── BYPASS MODE: skip PayMongo and immediately grant the tier ──────────
        if PAYMONGO_BYPASS:
            tier = PLAN_KEY_TO_TIER.get(plan_key) or PLAN_KEY_TO_TIER.get(plan_id, "free")
            if tier == "free":
                return func.HttpResponse(
                    json.dumps({"error": "Invalid plan key for bypass mode"}),
                    mimetype="application/json", status_code=400
                )
            with _get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE users SET subscription_tier = %s, subscription_status = 'active' WHERE clerk_id = %s",
                        (tier, clerk_id)
                    )
                    conn.commit()
            logging.info(f"[BYPASS] Granted tier '{tier}' to clerk_id={clerk_id}")
            return func.HttpResponse(
                json.dumps({"tier": tier, "bypass": True, "message": f"Bypass: granted {tier} tier."}),
                mimetype="application/json", status_code=200
            )
        # ────────────────────────────────────────────────────────────────────────

        if not plan_id:
            return func.HttpResponse(
                json.dumps({"error": "plan_id is required"}),
                mimetype="application/json", status_code=400
            )

        # Get user email from DB (needed to create/get PayMongo customer)
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT email FROM users WHERE clerk_id = %s", (clerk_id,))
                row = cur.fetchone()
                if not row:
                    return func.HttpResponse(
                        json.dumps({"error": "User not found in database"}),
                        mimetype="application/json", status_code=404
                    )
                email = row[0]

        # Get or create PayMongo customer
        customer_id = _get_or_create_paymongo_customer(clerk_id, email)

        # Determine return URL
        frontend_url = os.environ.get("FRONTEND_URL", "https://lexmateph.com")

        # Create subscription via PayMongo
        payload = {
            "data": {
                "attributes": {
                    "plan_id": plan_id,
                    "customer_id": customer_id,
                    "send_email_receipt": True,
                    "cancel_at_period_end": False,
                }
            }
        }
        response = requests.post(
            f"{PAYMONGO_BASE_URL}/subscriptions",
            json=payload,
            headers=_paymongo_headers(),
            timeout=20
        )
        resp_data = response.json()

        if response.status_code not in (200, 201):
            logging.error(f"PayMongo subscription creation failed: {resp_data}")
            return func.HttpResponse(
                json.dumps({"error": "Failed to create subscription", "detail": resp_data}),
                mimetype="application/json", status_code=502
            )

        sub_id = resp_data["data"]["id"]
        sub_attrs = resp_data["data"]["attributes"]

        # Extract the Payment Intent ID from the first invoice.
        # PayMongo subscriptions use the Payment Intent workflow — there is no
        # single hosted checkout URL. The frontend must create a payment method
        # (card or Maya) and attach it to this PI to complete the first payment.
        pi_id = (
            sub_attrs
            .get("latest_invoice", {})
            .get("payment_intent", {})
            .get("id", "")
        )

        # Retrieve the PI to get the client_key the frontend needs
        client_key = ""
        if pi_id:
            pi_resp = requests.get(
                f"{PAYMONGO_BASE_URL}/payment_intents/{pi_id}",
                headers=_paymongo_headers(),
                timeout=15,
            )
            if pi_resp.status_code == 200:
                client_key = (
                    pi_resp.json()
                    .get("data", {})
                    .get("attributes", {})
                    .get("client_key", "")
                )

        return func.HttpResponse(
            json.dumps({
                "payment_intent_id": pi_id,
                "client_key": client_key,
                "subscription_id": sub_id,
                # checkout_url is intentionally absent — PayMongo subscriptions
                # require a client-side payment method form (card / Maya).
                # See PAYMONGO_INTEGRATION.md §10 for the full checkout flow.
            }),
            mimetype="application/json", status_code=200
        )

    except Exception as e:
        logging.error(f"create_checkout error: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json", status_code=500
        )


# ─────────────────────────────────────────────────────────────────────────────
# Route: POST /api/cancel-subscription
# ─────────────────────────────────────────────────────────────────────────────
@paymongo_bp.route(route="cancel-subscription", methods=["POST"])
def cancel_subscription(req: func.HttpRequest) -> func.HttpResponse:
    clerk_id, error = get_authenticated_user_id(req)
    if error:
        return func.HttpResponse(
            json.dumps({"error": "Unauthorized"}),
            mimetype="application/json", status_code=401
        )
    try:
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT paymongo_subscription_id FROM users WHERE clerk_id = %s",
                    (clerk_id,)
                )
                row = cur.fetchone()
                if not row or not row[0]:
                    return func.HttpResponse(
                        json.dumps({"error": "No active subscription found"}),
                        mimetype="application/json", status_code=404
                    )
                sub_id = row[0]

        # Cancel via PayMongo API: POST /v1/subscriptions/{id}/cancel
        cancel_response = requests.post(
            f"{PAYMONGO_BASE_URL}/subscriptions/{sub_id}/cancel",
            json={"data": {"attributes": {"cancellation_reason": "other"}}},
            headers=_paymongo_headers(),
            timeout=15,
        )
        if cancel_response.status_code not in (200, 201):
            logging.warning(
                f"PayMongo cancel returned {cancel_response.status_code}: {cancel_response.text}"
            )
            # Still downgrade locally so the user isn't stuck on a paid tier
        
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE users SET
                           subscription_tier = 'free',
                           subscription_status = 'cancelled',
                           paymongo_subscription_id = NULL
                       WHERE clerk_id = %s""",
                    (clerk_id,),
                )
                conn.commit()

        return func.HttpResponse(
            json.dumps({"message": "Subscription cancelled successfully"}),
            mimetype="application/json", status_code=200
        )
    except Exception as e:
        logging.error(f"cancel_subscription error: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json", status_code=500
        )


# ─────────────────────────────────────────────────────────────────────────────
# Route: POST /api/track-usage
# ─────────────────────────────────────────────────────────────────────────────
@paymongo_bp.route(route="track-usage", methods=["POST"])
def track_usage(req: func.HttpRequest) -> func.HttpResponse:
    """Track free-tier daily usage. Returns {allowed, used, limit}.

    Authenticated: Clerk Bearer in X-Clerk-Authorization or Authorization.
    Anonymous (same free caps): JSON body must include ``anonymousId`` (a UUID).
    Rows are stored with ``clerk_id = 'anon:<uuid>'``.

    If a Bearer header is present but invalid/expired, a valid ``anonymousId`` in
    the body still counts as anonymous (avoids blocking guests with stray headers).
    """
    try:
        body = _read_json_body(req)
        feature = (body.get("feature") or "").strip()

        if feature not in FREE_TIER_DAILY_LIMITS:
            return func.HttpResponse(
                json.dumps({"error": f"Unknown feature: {feature}"}),
                mimetype="application/json", status_code=400
            )

        limit = FREE_TIER_DAILY_LIMITS[feature]

        clerk_id = None
        if _request_has_auth_header(req):
            clerk_id, _auth_error = get_authenticated_user_id(req)

        if clerk_id:
            with _get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT subscription_tier, is_admin FROM users WHERE clerk_id = %s", (clerk_id,))
                    row = cur.fetchone()
                    tier = (row[0] if row else "free") or "free"
                    is_admin = (row[1] if row else False) or False

                    if is_admin or tier != "free":
                        return func.HttpResponse(
                            json.dumps(
                                {"allowed": True, "used": 0, "limit": -1, "tier": tier, "is_admin": is_admin}
                            ),
                            mimetype="application/json", status_code=200,
                        )

                # Free tier: serialize per (clerk_id, feature) so rapid parallel opens cannot exceed the daily cap.
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
                                json.dumps(
                                    {
                                        "allowed": False,
                                        "used": used,
                                        "limit": limit,
                                        "tier": "free",
                                        "anonymous": True,
                                    }
                                ),
                                mimetype="application/json", status_code=200,
                            )

                        cur.execute(
                            "INSERT INTO usage_logs (clerk_id, feature) VALUES (%s, %s)",
                            (usage_key, feature),
                        )

                return func.HttpResponse(
                    json.dumps(
                        {
                            "allowed": True,
                            "used": used + 1,
                            "limit": limit,
                            "tier": "free",
                            "anonymous": True,
                        }
                    ),
                    mimetype="application/json", status_code=200,
                )

        if _request_has_auth_header(req):
            return func.HttpResponse(
                json.dumps({"error": "Unauthorized"}),
                mimetype="application/json", status_code=401,
            )

        return func.HttpResponse(
            json.dumps(
                {
                    "error": "anonymousId (UUID) required in JSON body when not signed in",
                }
            ),
            mimetype="application/json", status_code=400,
        )

    except Exception as e:
        logging.error(f"track_usage error: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json", status_code=500
        )


# ─────────────────────────────────────────────────────────────────────────────
# Route: GET /api/available-plans
# ─────────────────────────────────────────────────────────────────────────────
@paymongo_bp.route(route="available-plans", methods=["GET"])
def available_plans(req: func.HttpRequest) -> func.HttpResponse:
    """Return available plan IDs and public key for the frontend to use."""
    return func.HttpResponse(
        json.dumps({
            **AVAILABLE_PLANS,
            "bypass_mode": PAYMONGO_BYPASS,
            "public_key": PAYMONGO_PUBLIC_KEY,
        }),
        mimetype="application/json", status_code=200
    )


# ─────────────────────────────────────────────────────────────────────────────
# Route: POST /api/attach-payment-method
# ─────────────────────────────────────────────────────────────────────────────
@paymongo_bp.route(route="attach-payment-method", methods=["POST"])
def attach_payment_method(req: func.HttpRequest) -> func.HttpResponse:
    """
    Attach a PaymentMethod to a PaymentIntent to complete a subscription's
    first payment.  Called by the frontend after collecting card details.

    Request body:
      {
        "payment_intent_id": "pi_...",
        "payment_method_id": "pm_...",   # created client-side via public key
        "return_url":        "https://..."  # where to land after 3DS
      }

    Responses:
      200 { "status": "succeeded" }                         — payment done
      200 { "status": "awaiting_next_action",               — 3DS required
             "redirect_url": "https://..." }
      502 { "error": "...", "detail": {...} }               — PayMongo error
    """
    clerk_id, error = get_authenticated_user_id(req)
    if error:
        return func.HttpResponse(
            json.dumps({"error": "Unauthorized", "detail": error}),
            mimetype="application/json", status_code=401,
        )
    try:
        body = req.get_json()
        payment_intent_id = (body.get("payment_intent_id") or "").strip()
        payment_method_id = (body.get("payment_method_id") or "").strip()
        return_url = (
            body.get("return_url")
            or os.environ.get("FRONTEND_URL", "https://lexmateph.com")
        )

        if not payment_intent_id or not payment_method_id:
            return func.HttpResponse(
                json.dumps({"error": "payment_intent_id and payment_method_id are required"}),
                mimetype="application/json", status_code=400,
            )

        # Attach the payment method to the payment intent
        response = requests.post(
            f"{PAYMONGO_BASE_URL}/payment_intents/{payment_intent_id}/attach",
            json={
                "data": {
                    "attributes": {
                        "payment_method": payment_method_id,
                        "return_url": return_url,
                    }
                }
            },
            headers=_paymongo_headers(),
            timeout=20,
        )
        resp_data = response.json()

        if response.status_code not in (200, 201):
            logging.error(f"attach_payment_method PayMongo error: {resp_data}")
            return func.HttpResponse(
                json.dumps({"error": "PayMongo attach failed", "detail": resp_data}),
                mimetype="application/json", status_code=502,
            )

        attrs = resp_data.get("data", {}).get("attributes", {})
        status = attrs.get("status", "")

        if status == "succeeded":
            logging.info(
                f"attach_payment_method: succeeded pi={payment_intent_id} clerk_id={clerk_id}"
            )
            return func.HttpResponse(
                json.dumps({"status": "succeeded"}),
                mimetype="application/json", status_code=200,
            )

        if status in ("awaiting_next_action", "processing"):
            next_action = attrs.get("next_action") or {}
            redirect_url = next_action.get("redirect", {}).get("url", "")
            logging.info(
                f"attach_payment_method: {status} — 3DS redirect pi={payment_intent_id}"
            )
            return func.HttpResponse(
                json.dumps({"status": status, "redirect_url": redirect_url}),
                mimetype="application/json", status_code=200,
            )

        # Unexpected status (e.g. 'awaiting_payment_method', 'cancelled')
        logging.warning(
            f"attach_payment_method: unexpected status={status} pi={payment_intent_id}"
        )
        return func.HttpResponse(
            json.dumps({"status": status, "error": f"Unexpected payment status: {status}"}),
            mimetype="application/json", status_code=200,
        )

    except Exception as e:
        logging.error(f"attach_payment_method error: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json", status_code=500,
        )

# ─────────────────────────────────────────────────────────────────────────────
@paymongo_bp.route(route="paymongo-webhook", methods=["POST"])
def paymongo_webhook(req: func.HttpRequest) -> func.HttpResponse:
    raw_body = req.get_body()
    signature_header = req.headers.get("Paymongo-Signature", "")

    # Verify signature
    if not _verify_paymongo_webhook(raw_body, signature_header):
        logging.warning("PayMongo webhook: invalid signature")
        return func.HttpResponse("Invalid signature", status_code=400)

    try:
        event = json.loads(raw_body)
        evt_id = event.get("data", {}).get("id", "")
        evt_type = event.get("data", {}).get("attributes", {}).get("type", "")
        evt_data = event.get("data", {}).get("attributes", {}).get("data", {})

        # Idempotency: skip duplicate deliveries for the same event ID.
        # The webhook_events table must have: id TEXT PRIMARY KEY, received_at TIMESTAMPTZ.
        # Create with: CREATE TABLE IF NOT EXISTS webhook_events (id TEXT PRIMARY KEY, received_at TIMESTAMPTZ DEFAULT NOW());
        if evt_id:
            try:
                with _get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO webhook_events (id) VALUES (%s) ON CONFLICT (id) DO NOTHING",
                            (evt_id,),
                        )
                        inserted = cur.rowcount
                        conn.commit()
                if inserted == 0:
                    logging.info(f"PayMongo webhook: duplicate event {evt_id} ({evt_type}) — skipping")
                    return func.HttpResponse("OK", status_code=200)
            except Exception as idem_err:
                # If the table doesn't exist yet, log a warning and proceed (don't block webhooks).
                logging.warning(f"PayMongo webhook idempotency check skipped (table missing?): {idem_err}")

        logging.info(f"PayMongo webhook received: {evt_type} (id={evt_id})")

        # Actual PayMongo event names (corrected from original implementation)
        if evt_type == "subscription.activated":
            _handle_subscription_activated(evt_data)
        elif evt_type == "subscription.updated":
            # Covers both 'cancelled' and 'incomplete_cancelled' status changes
            _handle_subscription_updated(evt_data)
        elif evt_type == "subscription.past_due":
            _handle_subscription_past_due(evt_data)
        elif evt_type == "subscription.unpaid":
            _handle_subscription_unpaid(evt_data)
        elif evt_type == "subscription.invoice.paid":
            _handle_invoice_paid(evt_data)
        elif evt_type == "subscription.invoice.payment_failed":
            _handle_invoice_payment_failed(evt_data)
        else:
            logging.info(f"PayMongo webhook: unhandled event type: {evt_type}")

        return func.HttpResponse("OK", status_code=200)

    except Exception as e:
        logging.error(f"paymongo_webhook error: {e}")
        return func.HttpResponse("Internal error", status_code=500)


def _get_clerk_id_from_customer(customer_id: str) -> str | None:
    try:
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT clerk_id FROM users WHERE paymongo_customer_id = %s",
                    (customer_id,)
                )
                row = cur.fetchone()
                return row[0] if row else None
    except Exception as e:
        logging.error(f"Error looking up clerk_id for customer {customer_id}: {e}")
        return None


def _handle_subscription_activated(data: dict):
    """subscription.activated — first payment succeeded, subscription is now active."""
    sub_id = data.get("id", "")
    attrs = data.get("attributes", {})
    plan_id = attrs.get("plan_id", "")
    customer_id = attrs.get("customer_id", "")
    tier = PLAN_TIER_MAP.get(plan_id, "free")

    clerk_id = _get_clerk_id_from_customer(customer_id)
    if not clerk_id:
        logging.error(f"subscription.activated: No user found for customer_id={customer_id}")
        return

    with _get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users SET
                    subscription_tier        = %s,
                    subscription_status      = 'active',
                    paymongo_subscription_id = %s,
                    subscription_source      = 'paymongo',
                    subscription_expires_at  = NULL
                WHERE clerk_id = %s
                """,
                (tier, sub_id, clerk_id),
            )
            conn.commit()
    logging.info(f"subscription.activated: clerk_id={clerk_id}, tier={tier}")


def _handle_subscription_updated(data: dict):
    """subscription.updated — catches 'cancelled' and 'incomplete_cancelled' status changes."""
    sub_id = data.get("id", "")
    status = data.get("attributes", {}).get("status", "")

    if status in ("cancelled", "incomplete_cancelled"):
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users SET
                        subscription_tier        = 'free',
                        subscription_status      = 'cancelled',
                        paymongo_subscription_id = NULL
                    WHERE paymongo_subscription_id = %s
                    """,
                    (sub_id,),
                )
                conn.commit()
        logging.info(f"subscription.updated → cancelled: sub_id={sub_id}")
    else:
        logging.info(f"subscription.updated: sub_id={sub_id}, status={status} (no action taken)")


def _handle_subscription_past_due(data: dict):
    """subscription.past_due — payment failed, grace period started."""
    sub_id = data.get("id", "")
    with _get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET subscription_status = 'past_due' WHERE paymongo_subscription_id = %s",
                (sub_id,),
            )
            conn.commit()
    logging.warning(f"subscription.past_due: sub_id={sub_id}")


def _handle_subscription_unpaid(data: dict):
    """subscription.unpaid — all retries exhausted, subscription is unpaid."""
    sub_id = data.get("id", "")
    with _get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET subscription_status = 'unpaid' WHERE paymongo_subscription_id = %s",
                (sub_id,),
            )
            conn.commit()
    logging.warning(f"subscription.unpaid: sub_id={sub_id}")


def _handle_invoice_paid(data: dict):
    """subscription.invoice.paid — renewal payment succeeded."""
    # Invoice resource: subscription ID is at data.attributes.resource_id
    attrs = data.get("attributes", {})
    sub_id = attrs.get("resource_id", "")
    if not sub_id:
        logging.warning("subscription.invoice.paid: missing resource_id")
        return
    with _get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET subscription_status = 'active' WHERE paymongo_subscription_id = %s",
                (sub_id,),
            )
            conn.commit()
    logging.info(f"subscription.invoice.paid: sub_id={sub_id}")


def _handle_invoice_payment_failed(data: dict):
    """subscription.invoice.payment_failed — renewal payment failed."""
    attrs = data.get("attributes", {})
    sub_id = attrs.get("resource_id", "")
    if not sub_id:
        logging.warning("subscription.invoice.payment_failed: missing resource_id")
        return
    with _get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET subscription_status = 'past_due' WHERE paymongo_subscription_id = %s",
                (sub_id,),
            )
            conn.commit()
    logging.warning(f"subscription.invoice.payment_failed: sub_id={sub_id}")
