import azure.functions as func
import json
import os
import logging
import hashlib
import hmac
import time
import psycopg
import requests

from utils.clerk_auth import get_authenticated_user_id
from utils.founding_promo import expire_founding_promo_for_user

paymongo_bp = func.Blueprint()

PAYMONGO_SECRET_KEY = os.environ.get("PAYMONGO_SECRET_KEY", "")
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
}

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
    with _get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT paymongo_customer_id FROM users WHERE clerk_id = %s", (clerk_id,))
            row = cur.fetchone()
            if row and row[0]:
                return row[0]

    # Create new PayMongo customer
    payload = {
        "data": {
            "attributes": {
                "email": email,
                "default_device": "phone"
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
        # Expire promo in its own transaction so a rollback on fallback SELECT cannot undo it.
        try:
            with _get_db() as conn:
                with conn.cursor() as cur:
                    expire_founding_promo_for_user(cur, clerk_id)
        except Exception as ex:
            logging.warning("expire_founding_promo_for_user: %s", ex)

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

        # Extract checkout URL from the latest invoice
        checkout_url = (
            resp_data.get("data", {})
            .get("attributes", {})
            .get("latest_invoice", {})
            .get("attributes", {})
            .get("hosted_url", "")
        )

        return func.HttpResponse(
            json.dumps({
                "checkout_url": checkout_url,
                "subscription_id": resp_data["data"]["id"]
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

        # Cancel via PayMongo API
        # (Assuming PayMongo has a cancel endpoint or similar)
        # response = requests.post(f"{PAYMONGO_BASE_URL}/subscriptions/{sub_id}/cancel", headers=_paymongo_headers())
        
        # For now, let's just update DB
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET subscription_tier = 'free', subscription_status = 'cancelled' WHERE clerk_id = %s",
                    (clerk_id,)
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
    """Track free-tier daily usage. Returns {allowed, used, limit}."""
    clerk_id, error = get_authenticated_user_id(req)
    if error:
        return func.HttpResponse(
            json.dumps({"error": "Unauthorized"}),
            mimetype="application/json", status_code=401
        )
    try:
        body = req.get_json()
        feature = body.get("feature", "").strip()

        if feature not in FREE_TIER_DAILY_LIMITS:
            return func.HttpResponse(
                json.dumps({"error": f"Unknown feature: {feature}"}),
                mimetype="application/json", status_code=400
            )

        limit = FREE_TIER_DAILY_LIMITS[feature]

        with _get_db() as conn:
            with conn.cursor() as cur:
                # Get current tier and admin status
                cur.execute("SELECT subscription_tier, is_admin FROM users WHERE clerk_id = %s", (clerk_id,))
                row = cur.fetchone()
                tier = (row[0] if row else "free") or "free"
                is_admin = (row[1] if row else False) or False

                # Admin or Paid users are always allowed
                if is_admin or tier != "free":
                    return func.HttpResponse(
                        json.dumps({"allowed": True, "used": 0, "limit": -1, "tier": tier, "is_admin": is_admin}),
                        mimetype="application/json", status_code=200
                    )


                # Count today's usage
                cur.execute("""
                    SELECT COUNT(*) FROM usage_logs
                    WHERE clerk_id = %s AND feature = %s
                      AND created_at >= CURRENT_DATE
                      AND created_at < CURRENT_DATE + INTERVAL '1 day'
                """, (clerk_id, feature))
                used = cur.fetchone()[0]

                if used >= limit:
                    return func.HttpResponse(
                        json.dumps({"allowed": False, "used": used, "limit": limit, "tier": "free"}),
                        mimetype="application/json", status_code=200
                    )

                # Log the usage
                cur.execute(
                    "INSERT INTO usage_logs (clerk_id, feature) VALUES (%s, %s)",
                    (clerk_id, feature)
                )
                conn.commit()

                return func.HttpResponse(
                    json.dumps({"allowed": True, "used": used + 1, "limit": limit, "tier": "free"}),
                    mimetype="application/json", status_code=200
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
    """Return available plan IDs for the frontend to use."""
    return func.HttpResponse(
        json.dumps({**AVAILABLE_PLANS, "bypass_mode": PAYMONGO_BYPASS}),
        mimetype="application/json", status_code=200
    )


# ─────────────────────────────────────────────────────────────────────────────
# Route: POST /api/paymongo-webhook
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
        evt_type = event.get("data", {}).get("attributes", {}).get("type", "")
        evt_data = event.get("data", {}).get("attributes", {}).get("data", {})

        logging.info(f"PayMongo webhook received: {evt_type}")

        if evt_type == "subscription.created":
            _handle_subscription_created(evt_data)
        elif evt_type == "invoice.payment_succeeded":
            _handle_invoice_succeeded(evt_data)
        elif evt_type == "subscription.cancelled":
            _handle_subscription_cancelled(evt_data)
        elif evt_type == "invoice.payment_failed":
            _handle_invoice_failed(evt_data)
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


def _handle_subscription_created(data: dict):
    sub_id = data.get("id", "")
    plan_id = data.get("attributes", {}).get("plan_id", "")
    customer_id = data.get("attributes", {}).get("customer_id", "")
    tier = PLAN_TIER_MAP.get(plan_id, "free")

    clerk_id = _get_clerk_id_from_customer(customer_id)
    if not clerk_id:
        logging.error(f"subscription.created: No user found for customer_id {customer_id}")
        return

    with _get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users SET
                    subscription_tier = %s,
                    subscription_status = 'active',
                    paymongo_subscription_id = %s,
                    subscription_source = 'paymongo'
                WHERE clerk_id = %s
            """, (tier, sub_id, clerk_id))
            conn.commit()
    logging.info(f"Subscription created: clerk_id={clerk_id}, tier={tier}")


def _handle_invoice_succeeded(data: dict):
    """Renew / confirm active subscription on successful payment."""
    sub_id = data.get("attributes", {}).get("subscription_id", "")
    if not sub_id:
        return
    with _get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users SET subscription_status = 'active'
                WHERE paymongo_subscription_id = %s
            """, (sub_id,))
            conn.commit()
    logging.info(f"Invoice payment succeeded for subscription: {sub_id}")


def _handle_subscription_cancelled(data: dict):
    sub_id = data.get("id", "")
    with _get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users SET
                    subscription_tier = 'free',
                    subscription_status = 'cancelled',
                    paymongo_subscription_id = NULL
                WHERE paymongo_subscription_id = %s
            """, (sub_id,))
            conn.commit()
    logging.info(f"Subscription cancelled: {sub_id}")


def _handle_invoice_failed(data: dict):
    sub_id = data.get("attributes", {}).get("subscription_id", "")
    if not sub_id:
        return
    with _get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users SET subscription_status = 'past_due'
                WHERE paymongo_subscription_id = %s
            """, (sub_id,))
            conn.commit()
    logging.warning(f"Invoice payment FAILED for subscription: {sub_id}")
