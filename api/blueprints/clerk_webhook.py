import azure.functions as func
import json
import os
import logging
import psycopg
from psycopg import errors as pg_errors
from svix.webhooks import Webhook, WebhookVerificationError

from utils.founding_promo import try_grant_founding_promo
clerk_webhook_bp = func.Blueprint()


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

@clerk_webhook_bp.route(route="clerk-webhook", methods=["POST"])
def clerk_webhook_hyphen(req: func.HttpRequest) -> func.HttpResponse:
    return clerk_webhook_core(req)

@clerk_webhook_bp.route(route="clerk_webhook", methods=["POST"])
def clerk_webhook_underscore(req: func.HttpRequest) -> func.HttpResponse:
    return clerk_webhook_core(req)

def clerk_webhook_core(req: func.HttpRequest) -> func.HttpResponse:
    # 1. Get headers for verification
    svix_id = req.headers.get("svix-id")
    svix_timestamp = req.headers.get("svix-timestamp")
    svix_signature = req.headers.get("svix-signature")
    
    if not svix_id or not svix_timestamp or not svix_signature:
        logging.error("Missing Svix headers")
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
        evt = wh.verify(payload, {
            "svix-id": svix_id,
            "svix-timestamp": svix_timestamp,
            "svix-signature": svix_signature,
        })
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

        ADMIN_EMAILS = ["rnlarboleda@gmail.com", "rnlarboleda18@gmail.com"]
        is_admin = email.lower() in [e.lower() for e in ADMIN_EMAILS] if email else False

        conn_string = os.environ.get("DB_CONNECTION_STRING")
        try:
            with psycopg.connect(conn_string) as conn:
                with conn.cursor() as cur:
                    # 1. Link an existing email-only row (no clerk_id yet)
                    cur.execute("""
                        UPDATE users
                        SET clerk_id = %s,
                            first_name = COALESCE(%s, first_name),
                            last_name  = COALESCE(%s, last_name),
                            founding_promo_eligible = TRUE
                        WHERE LOWER(email) = LOWER(%s) AND clerk_id IS NULL;
                    """, (clerk_id, first_name, last_name, email))

                    if cur.rowcount == 0:
                        # 2. Upsert by clerk_id (normal path)
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
                    elif evt_type == "user.created":
                        # Founding promo only — no automatic tier trial on sign-up (trials start when user chooses a plan).
                        try:
                            try_grant_founding_promo(cur, clerk_id, is_admin)
                        except Exception as promo_err:
                            logging.warning("founding promo grant error: %s", promo_err)

                    conn.commit()
            logging.info(f"Successfully synced Clerk user ({evt_type}): {clerk_id}")
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
