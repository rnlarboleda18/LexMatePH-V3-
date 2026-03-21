import time
import os

LOG_ASC = "logs/backfill_fleet_asc.log"
LOG_DESC = "logs/backfill_fleet_desc.log"

def tail_files():
    print("Starting Live Dual Fleet Monitor...")
    print("------------------------------------------------")
    
    files = {}
    if os.path.exists(LOG_ASC):
        f = open(LOG_ASC, 'r')
        f.seek(0, os.SEEK_END)
        files['ASC'] = f
    
    if os.path.exists(LOG_DESC):
        f = open(LOG_DESC, 'r')
        f.seek(0, os.SEEK_END)
        files['DESC'] = f
        
    if not files:
        print("No log files found yet. Waiting...")
        
    try:
        while True:
            data_found = False
            for name, f in files.items():
                line = f.readline()
                if line:
                    data_found = True
                    print(f"[{name}] {line.strip()}")
            
            if not data_found:
                # check for new files if not open
                if 'ASC' not in files and os.path.exists(LOG_ASC):
                     f = open(LOG_ASC, 'r')
                     files['ASC'] = f
                if 'DESC' not in files and os.path.exists(LOG_DESC):
                     f = open(LOG_DESC, 'r')
                     files['DESC'] = f
                     
                time.sleep(0.1)
                
    except KeyboardInterrupt:
        print("\nMonitor stopped.")

if __name__ == "__main__":
    tail_files()
