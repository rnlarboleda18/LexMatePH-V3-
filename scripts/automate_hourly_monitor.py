
import time
import os
import sys
from openai import OpenAI
from datetime import datetime

# Configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") or "REDACTED_OPENAI_KEY" 
ID_FILE = "last_batch_id.txt"

def get_client():
    return OpenAI(api_key=OPENAI_API_KEY)

def monitor_loop():
    print("Starting Hourly Batch Monitor...")
    
    # Wait for ID file if not present (script might start before submission finishes)
    while not os.path.exists(ID_FILE):
        print(f"Waiting for {ID_FILE} to be created...")
        time.sleep(10)
        
    with open(ID_FILE, 'r') as f:
        batch_id = f.read().strip()
        
    print(f"Monitoring Batch ID: {batch_id}")
    client = get_client()

    while True:
        try:
            batch = client.batches.retrieve(batch_id)
            status = batch.status
            
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now}] Status: {status} | Completed: {batch.request_counts.completed} | Failed: {batch.request_counts.failed}")
            
            if status in ['completed', 'failed', 'cancelled']:
                print(f"Batch {status}. Exiting monitor.")
                break
                
            # Wait 1 hour
            print("Next check in 60 minutes...")
            time.sleep(3600)
            
        except Exception as e:
            print(f"Error checking status: {e}")
            time.sleep(60)

if __name__ == "__main__":
    monitor_loop()
