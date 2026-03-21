import os
import json
import psycopg2
from psycopg2 import pool
import time
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import queue
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURATION ---
DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING")
if not DB_CONNECTION_STRING:
    settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'api', 'local.settings.json')
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r') as f:
                data = json.load(f)
                DB_CONNECTION_STRING = data.get('Values', {}).get('DB_CONNECTION_STRING')
        except: pass

if not DB_CONNECTION_STRING:
    # Use the connection string found in previous files
    DB_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

# Email Config
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")
EMAIL_RECIPIENT = "rnlarboleda18@gmail.com"

# Gemini Config
GEMINI_API_KEY = "REDACTED_API_KEY_HIDDEN"
genai.configure(api_key=GEMINI_API_KEY)

MODEL_NAME = 'gemini-2.5-flash-lite'

# Statistics
stats_lock = threading.Lock()
stats = {
    'processed': 0,
    'failed': 0,
    'skipped': 0, # For locked items
    'start_time': time.time(),
}

# Connection Pool
db_pool = None

def init_db_pool(max_workers):
    global db_pool
    try:
        db_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=2,
            maxconn=max_workers + 2,
            dsn=DB_CONNECTION_STRING
        )
        print("DB Connection Pool Initialized.")
    except Exception as e:
        print(f"Error creating connection pool: {e}")
        raise

def get_db_connection():
    global db_pool
    if db_pool is None:
        raise Exception("DB Pool not initialized!")
    return db_pool.getconn()

def return_db_connection(conn):
    global db_pool
    if db_pool and conn:
        db_pool.putconn(conn)

def send_email_update(processed, failed, skipped, speed, eta):
    if not EMAIL_USER or not EMAIL_PASS:
        # Suppress repeated warnings, maybe just print once or debug logs
        # print("[EMAIL] Skipped: Missing credentials.") 
        return

    try:
        subject = f"Backfill Update: {processed} Processed"
        body = f"""
        <h3>Backfill Status Update</h3>
        <p><b>Model:</b> {MODEL_NAME}</p>
        <p><b>Processed:</b> {processed}</p>
        <p><b>Failed:</b> {failed}</p>
        <p><b>Skipped:</b> {skipped}</p>
        <p><b>Current Speed:</b> {speed:.2f} cases/sec</p>
        <p><b>Estimated Time Remaining:</b> {eta}</p>
        <br>
        <p><i>Sent automatically by Backfill Script</i></p>
        """

        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_RECIPIENT
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        
        print(f"[EMAIL] Sent update to {EMAIL_RECIPIENT}")

    except Exception as e:
        print(f"[EMAIL] Failed to send: {e}")

def generate_html(raw_text):
    if not raw_text or not raw_text.strip():
        return None

    cleaning_prompt = f"""
    You are a Senior Legal Editor. Transform this raw legal text into pristine HTML.
    
    RULES:
    1. Fix Casing (Title Case -> Sentence Case).
    2. Add <div style="text-align: center; font-weight: bold; margin-bottom: 20px;"> HEADER </div> for the case title/header info.
    3. Use <p style="margin-bottom: 10px; text-align: justify;"> for paragraphs.
    4. Use <h3 style="margin-top: 20px; font-weight: bold;"> for headers.
    5. Fix encoding errors like 'Ï¿½' or mojibake.
    6. RETURN ONLY HTML. Do not wrap in markdown blocks like ```html. Just raw HTML.

    INPUT TEXT:
    {raw_text}
    """

    max_retries = 10
    base_delay = 2
    model = genai.GenerativeModel(MODEL_NAME)

    for attempt in range(max_retries):
        try:
            # print(f"DEBUG: Generating for... (Attempt {attempt})")
            response = model.generate_content(
                cleaning_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                ),
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                },
                request_options={'timeout': 120}
            )
            
            content = response.text
            if content.startswith("```html"): content = content[7:]
            if content.startswith("```"): content = content[3:]
            if content.endswith("```"): content = content[:-3]
            return content.strip()
        except Exception as e:
            if "429" in str(e):
                time.sleep(base_delay * (2 ** attempt))
            else:
                print(f"  [AI Error Non-Retriable]: {e}")
                return None
    return None

def worker_task(worker_id, task_queue):
    print(f"Worker {worker_id} started.", flush=True)
    conn = None
    try:
        conn = get_db_connection()
        while True:
            try:
                # Get ID from queue (Expected: just case_id)
                try:
                    case_id = task_queue.get(timeout=3)
                except queue.Empty:
                    break # All tasks done

                raw_text = None
                
                # Fetch Row with Lock
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT raw_content 
                        FROM supreme_decisions 
                        WHERE id = %s 
                        FOR UPDATE NOWAIT
                    """, (case_id,))
                    row = cursor.fetchone()
                    
                    if not row:
                        task_queue.task_done()
                        cursor.close()
                        continue
                    
                    raw_text = row[0]
                    # Lock is held now.
                    
                except psycopg2.errors.LockNotAvailable:
                    conn.rollback()
                    with stats_lock:
                        stats['skipped'] += 1
                        # print(f"[{time.strftime('%H:%M:%S')}] Worker {worker_id} -> Case {case_id}: SKIPPED (Locked)", flush=True)
                    task_queue.task_done()
                    continue
                except Exception as e:
                    print(f"Worker {worker_id} DB Error fetching {case_id}: {e}")
                    if conn: conn.rollback()
                    task_queue.task_done()
                    time.sleep(1)
                    continue

                # Process
                try:
                    clean_html = generate_html(raw_text)
                    
                    if clean_html:
                        cursor.execute("UPDATE supreme_decisions SET full_text_html = %s WHERE id = %s", (clean_html, case_id))
                        conn.commit() 
                        
                        with stats_lock:
                            stats['processed'] += 1
                        
                        print(f"[{time.strftime('%H:%M:%S')}] Worker {worker_id} -> Case {case_id}: DONE", flush=True)
                    else:
                        conn.rollback() 
                        with stats_lock:
                            stats['failed'] += 1
                        print(f"[{time.strftime('%H:%M:%S')}] Worker {worker_id} -> Case {case_id}: FAILED (AI)", flush=True)
                        
                except Exception as e:
                    print(f"Worker {worker_id} Error processing {case_id}: {e}")
                    if conn: conn.rollback()
                    with stats_lock:
                        stats['failed'] += 1
                finally:
                    if cursor: cursor.close()
                    task_queue.task_done()

            except Exception as e:
                print(f"Worker {worker_id} outer loop error: {e}")
                
    except Exception as e:
        print(f"Worker {worker_id} connection error: {e}")
    finally:
        return_db_connection(conn)

def monitoring_loop(total_count):
    print(f"Monitor started. Queue size: {total_count}")
    last_email_time = time.time()
    
    while True:
        time.sleep(10) # Update console often, email hourly
        with stats_lock:
            processed = stats['processed']
            failed = stats['failed']
            skipped = stats['skipped']
            start_t = stats['start_time']
        
        elapsed = time.time() - start_t
        avg_speed = processed / elapsed if elapsed > 0 else 0
        
        remaining = total_count - processed - failed - skipped # roughly
        eta_seconds = remaining / avg_speed if avg_speed > 0 else 0
        eta_str = time.strftime("%H:%M:%S", time.gmtime(eta_seconds))
        
        print(f"[{time.strftime('%H:%M:%S')}] P:{processed} F:{failed} S:{skipped} | Speed: {avg_speed:.2f} c/s | ETF: {eta_str}")

        # Check for email hour
        if time.time() - last_email_time >= 3600: # 1 hour
            send_email_update(processed, failed, skipped, avg_speed, eta_str)
            last_email_time = time.time()

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=30, help="Number of workers")
    parser.add_argument("--model", type=str, default="gemini-2.5-flash-lite", help="Gemini Model Name")
    parser.add_argument("--skip-existing", action="store_true", help="Skip cases that already have HTML content")
    parser.add_argument("--order", type=str, choices=['ASC', 'DESC'], default='DESC', help="Processing order (ASC or DESC)")
    parser.add_argument("--start-id", type=int, help="Start from a specific case ID")
    args = parser.parse_args()
    
    WORKERS = args.workers
    global MODEL_NAME
    MODEL_NAME = args.model
    ORDER = args.order
    
    print(f"Starting RE-BACKFILL using {MODEL_NAME} with {WORKERS} workers...")
    
    if not EMAIL_USER or not EMAIL_PASS:
        print("[WARNING] EMAIL_USER or EMAIL_PASS not set. Email alerts DISABLED.")
    else:
        print(f"[INFO] Email alerts enabled for {EMAIL_RECIPIENT}")

    if args.skip_existing:
        print(f"Mode: SKIP EXISTING | Order: {ORDER}")
    else:
        print(f"Mode: OVERWRITE ALL | Order: {ORDER}")
    
    if args.start_id:
        print(f"Start ID: {args.start_id}")
    
    # Init Pool
    init_db_pool(WORKERS)
    
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cursor = conn.cursor()
    
    print("Fetching case IDs...")
    
    # Build query with optional start_id filter
    if args.skip_existing:
        base_query = "SELECT id FROM supreme_decisions WHERE full_text_html IS NULL"
    else:
        base_query = "SELECT id FROM supreme_decisions WHERE 1=1"
    
    if args.start_id:
        if ORDER == 'ASC':
            base_query += f" AND id >= {args.start_id}"
        else:
            base_query += f" AND id <= {args.start_id}"
    
    base_query += f" ORDER BY id {ORDER}"
    cursor.execute(base_query)
        
    rows = cursor.fetchall()
    cursor.close() 
    conn.close()
    
    total_cases = len(rows)
    print(f"Found {total_cases} cases to process.")
    
    if total_cases == 0:
        return

    # Fill Queue
    task_queue = queue.Queue()
    for r in rows:
        task_queue.put(r[0])

    # Start Monitor
    monitor_thread = threading.Thread(target=monitoring_loop, args=(total_cases,), daemon=True)
    monitor_thread.start()
    
    # Initial Email
    send_email_update(0, 0, 0, 0, "Calculating...")

    # Start Workers
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = [executor.submit(worker_task, i, task_queue) for i in range(WORKERS)]
        
        # Wait for all to complete
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Worker thread exception: {e}")

    # Final Email
    total_elapsed = time.time() - stats['start_time']
    final_speed = stats['processed'] / total_elapsed if total_elapsed > 0 else 0
    send_email_update(stats['processed'], stats['failed'], stats['skipped'], final_speed, "DONE")
    
    print("\n" + "="*50)
    print("MIGRATION COMPLETE")
    print(f"Total Processed: {stats['processed']}")
    print("="*50)

if __name__ == "__main__":
    main()
