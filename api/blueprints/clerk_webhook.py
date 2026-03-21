import azure.functions as func
import json
import os
import logging
import psycopg
from svix.webhooks import Webhook, WebhookVerificationError

clerk_webhook_bp = func.Blueprint()

@clerk_webhook_bp.route(route="clerk-webhook", methods=["POST"])
def clerk_webhook(req: func.HttpRequest) -> func.HttpResponse:
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
        email_addresses = data.get("email_addresses", [])
        email = email_addresses[0].get("email_address") if email_addresses else None
        
        if not clerk_id or not email:
            logging.error(f"Malformed {evt_type} data: {data}")
            return func.HttpResponse("Malformed data", status_code=400)
            
        conn_string = os.environ.get("DB_CONNECTION_STRING")
        try:
            with psycopg.connect(conn_string) as conn:
                with conn.cursor() as cur:
                    # Link by clerk_id if it exists, otherwise link by email
                    cur.execute("""
                        INSERT INTO users (clerk_id, email)
                        VALUES (%s, %s)
                        ON CONFLICT (clerk_id) DO UPDATE SET email = EXCLUDED.email
                        RETURNING id;
                    """, (clerk_id, email))
                    
                    # If the above didn't link (e.g. clerk_id is new but email exists), 
                    # we update the existing row with the same email.
                    cur.execute("""
                        UPDATE users 
                        SET clerk_id = %s 
                        WHERE email = %s AND clerk_id IS NULL;
                    """, (clerk_id, email))
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
