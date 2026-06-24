import azure.functions as func
import json
import os
import logging
import psycopg
from svix.webhooks import Webhook, WebhookVerificationError

from utils.founding_promo import try_grant_founding_promo
from utils.trial import try_grant_trial
from utils.email import send_new_signup_notification

clerk_webhook_bp = func.Blueprint()


def _unsafe_metadata_from_clerk_user(data: dict) -> dict:
    """Clerk user payloads include optional unsafe_metadata (dict)."""
    meta = data.get("unsafe_metadata")
    return meta if isinstance(meta, dict) else {}


def _clerk_primary_email(data: dict):
    """Prefer primary_email_address_id; avoids empty/wrong order in email_addresses."""
    emails = data.get("email_addresses") or []
    primary_id = data.get("primary_email_address_id")
    if primary_id and isinstance(emails, list):
        for e in emails:
            if isinstance(e, dict) and e.get("id") == primary_id:
                addr = e.get("email_address")
                if addr:
                    return addr.strip() if isinstance(addr, str) else addr
    if emails and isinstance(emails[0], dict):
        addr = emails[0].get("email_address")
        if addr:
            return addr.strip() if isinstance(addr, str) else addr
    return None


def _svix_header_dict(req: func.HttpRequest) -> dict:
    """Build Svix header dict for verification (case-insensitive; proxies may vary)."""
    lower = {k.lower(): v for k, v in req.headers.items()}
    return {
        "svix-id": lower.get("svix-id", ""),
        "svix-timestamp": lower.get("svix-timestamp", ""),
        "svix-signature": lower.get("svix-signature", ""),
    }


@clerk_webhook_bp.route(route="clerk-webhook", methods=["POST"])
def clerk_webhook_hyphen(req: func.HttpRequest) -> func.HttpResponse:
    return clerk_webhook_core(req)

@clerk_webhook_bp.route(route="clerk_webhook", methods=["POST"])
def clerk_webhook_underscore(req: func.HttpRequest) -> func.HttpResponse:
    return clerk_webhook_core(req)

def clerk_webhook_core(req: func.HttpRequest) -> func.HttpResponse:
    # 1. Get headers for verification (case-insensitive — some CDNs vary casing)
    h = _svix_header_dict(req)
    svix_id = h["svix-id"]
    svix_timestamp = h["svix-timestamp"]
    svix_signature = h["svix-signature"]

    if not svix_id or not svix_timestamp or not svix_signature:
        logging.error("Missing Svix headers (have keys: %s)", list((req.headers or {}).keys())[:20])
        return func.HttpResponse("Missing headers", status_code=400)
    
    # 2. Get the signing secret
    webhook_secret = os.environ.get("CLERK_WEBHOOK_SECRET")
    if not webhook_secret:
        logging.error("CLERK_WEBHOOK_SECRET not configured")
        return func.HttpResponse("Internal error", status_code=500)
    
    # 3. Verify the payload
    payload = req.get_body().decode('utf-8')
    wh = Webhook(webhook_secret)
    
    try:
        evt = wh.verify(
            payload,
            {
                "svix-id": svix_id,
                "svix-timestamp": svix_timestamp,
                "svix-signature": svix_signature,
            },
        )
    except WebhookVerificationError as e:
        logging.error(f"Webhook verification failed: {e}")
        return func.HttpResponse("Invalid signature", status_code=400)
    
    # 4. Handle events
    data = evt.get("data")
    evt_type = evt.get("type")
    
    logging.info(f"Received Clerk Webhook event: {evt_type}")
    
    if evt_type == "user.created" or evt_type == "user.updated":
        clerk_id = data.get("id")
        email = _clerk_primary_email(data)
        first_name = (data.get("first_name") or "").strip() or None
        last_name  = (data.get("last_name")  or "").strip() or None
        unsafe_meta = _unsafe_metadata_from_clerk_user(data)
        signup_intent = (unsafe_meta.get("signup_intent") or "").strip().lower()
        clerk_trial_tier = unsafe_meta.get("trial_tier")

        if not email:
            logging.warning(
                "Clerk webhook %s: no email in payload for user %s; skipping DB sync",
                evt_type,
                clerk_id,
            )
            return func.HttpResponse("OK", status_code=200)

        raw = os.environ.get("ADMIN_EMAILS", "rnlarboleda@gmail.com,rnlarboleda18@gmail.com")
        ADMIN_EMAILS = [e.strip().lower() for e in raw.split(",") if e.strip()]
        is_admin = email.lower() in ADMIN_EMAILS if email else False

        granted_promo = False
        granted_trial = False
        promo_slot = None
        conn_string = os.environ.get("DB_CONNECTION_STRING")
        try:
            with psycopg.connect(conn_string) as conn:
                with conn.cursor() as cur:
                    # Check if user existed in DB before this event
                    cur.execute(
                        "SELECT 1 FROM users WHERE clerk_id = %s OR LOWER(email) = LOWER(%s)",
                        (clerk_id, email),
                    )
                    exists_before = bool(cur.fetchone())

                    # 1. Link or re-link any existing row for this email (covers both
                    #    email-only rows AND re-registrations where the clerk_id changed)
                    cur.execute("""
                        UPDATE users
                        SET clerk_id = %s,
                            first_name = COALESCE(%s, first_name),
                            last_name  = COALESCE(%s, last_name),
                            founding_promo_eligible = TRUE
                        WHERE LOWER(email) = LOWER(%s) AND (clerk_id IS NULL OR clerk_id != %s);
                    """, (clerk_id, first_name, last_name, email, clerk_id))

                    if cur.rowcount == 0:
                        # 2. Upsert by clerk_id (normal new-user path)
                        cur.execute("""
                            INSERT INTO users (clerk_id, email, first_name, last_name, is_admin, founding_promo_eligible)
                            VALUES (%s, %s, %s, %s, %s, TRUE)
                            ON CONFLICT (clerk_id) DO UPDATE SET
                                email      = EXCLUDED.email,
                                first_name = COALESCE(EXCLUDED.first_name, users.first_name),
                                last_name  = COALESCE(EXCLUDED.last_name,  users.last_name),
                                is_admin   = EXCLUDED.is_admin;
                        """, (clerk_id, email, first_name, last_name, is_admin))

                    if is_admin:
                        cur.execute("""
                            UPDATE users SET
                                subscription_tier   = 'barrister',
                                subscription_status = 'active',
                                subscription_source = 'admin_override'
                            WHERE clerk_id = %s;
                        """, (clerk_id,))
                    else:
                        # Determine if we should attempt the promo or trial grant (fallback healer on user.updated).
                        attempt_grant = (evt_type == "user.created")
                        if not attempt_grant:
                            if not exists_before:
                                # This user.updated is acting as the user's initial registration (e.g. user.created was missed)
                                attempt_grant = True
                                logging.info("Fallback healing: clerk_id=%s did not exist prior to this user.updated event. Attempting grant.", clerk_id)
                            else:
                                # They existed before. Let's see if they qualify for healing (registered recently, still on free with no source)
                                cur.execute(
                                    """
                                    SELECT EXISTS (
                                        SELECT 1 FROM users 
                                        WHERE clerk_id = %s 
                                          AND (subscription_tier = 'free' OR subscription_tier IS NULL)
                                          AND (subscription_source IS NULL OR subscription_source = '')
                                          AND founding_promo_slot IS NULL
                                          AND created_at >= NOW() - INTERVAL '1 hour'
                                    )
                                    """,
                                    (clerk_id,),
                                )
                                attempt_grant = cur.fetchone()[0]
                                if attempt_grant:
                                    logging.info("Fallback healing: clerk_id=%s is on free and was created within the last hour. Attempting grant.", clerk_id)

                        if attempt_grant:
                            # Explicit "free only" sign-up from pricing modal: skip founding slot + paid trial.
                            explicit_free = signup_intent == "free"
                            if not explicit_free:
                                try:
                                    try_grant_founding_promo(cur, clerk_id, is_admin)
                                    cur.execute(
                                        "SELECT subscription_source, founding_promo_slot FROM users WHERE clerk_id = %s",
                                        (clerk_id,),
                                    )
                                    src_row = cur.fetchone()
                                    granted_promo = bool(src_row and src_row[0] == "founding_promo")
                                    promo_slot = src_row[1] if granted_promo else None
                                except Exception as promo_err:
                                    logging.warning("founding promo grant error: %s", promo_err)

                            if not granted_promo and not explicit_free:
                                granted_trial = try_grant_trial(cur, clerk_id, clerk_trial_tier)

                    conn.commit()
            logging.info(f"Successfully synced Clerk user ({evt_type}): {clerk_id}")
            if (evt_type == "user.created" or (evt_type == "user.updated" and (granted_promo or granted_trial))) and not is_admin:
                user_display = f"{first_name or ''} {last_name or ''}".strip() or email
                signup_source = (
                    "founding_promo" if granted_promo
                    else "trial" if granted_trial
                    else None
                )
                send_new_signup_notification(
                    user_name=user_display,
                    user_email=email,
                    source=signup_source,
                    slot=promo_slot,
                )
        except Exception as e:
            logging.error(f"Database error syncing user: {e}")
            return func.HttpResponse("Database error", status_code=500)

    elif evt_type == "user.deleted":
        clerk_id = data.get("id")
        if not clerk_id:
            return func.HttpResponse("Missing ID", status_code=400)
            
        conn_string = os.environ.get("DB_CONNECTION_STRING")
        try:
            with psycopg.connect(conn_string) as conn:
                with conn.cursor() as cur:
                    # Delete user and cascading data (if defined in schema)
                    cur.execute("DELETE FROM users WHERE clerk_id = %s", (clerk_id,))
                    conn.commit()
            logging.info(f"Successfully deleted Clerk user locally: {clerk_id}")
        except Exception as e:
            logging.error(f"Database error deleting user: {e}")
            return func.HttpResponse("Database error", status_code=500)
            
    return func.HttpResponse("OK", status_code=200)
