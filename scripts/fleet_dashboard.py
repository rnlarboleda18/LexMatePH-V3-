import glob
import os
import time
from datetime import datetime

def parse_log_line(line):
    # Expected: 2025-12-08 10:55:19,688 - INFO - Processing content for Case ID 24384...
    try:
        parts = line.split(' - ')
        timestamp_str = parts[0].split(',')[0]
        message = parts[-1].strip()
        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        return timestamp, message
    except:
        return None, line.strip()

def main():
    log_dir = "logs/finite_fleet"
    log_files = glob.glob(os.path.join(log_dir, "worker_*.log"))
    
    # Sort by worker ID
    log_files.sort(key=lambda x: int(os.path.basename(x).split('_')[1].split('.')[0]))
    
    print(f"\n{'WORKER':<10} | {'LAST UPDATE':<20} | {'STATUS MESSAGE'}")
    print("-" * 80)
    
    active_count = 0
    now = datetime.now()
    
    for log_file in log_files:
        worker_name = os.path.basename(log_file).replace('.log', '').replace('worker_', 'W#')
        
        try:
            with open(log_file, 'r') as f:
                # Efficiently read last line (approximately)
                f.seek(0, os.SEEK_END)
                pos = f.tell() - 200 # Go back 200 chars
                if pos < 0: pos = 0
                f.seek(pos)
                last_lines = f.readlines()
                if not last_lines:
                    print(f"{worker_name:<10} | {'Empty Log':<20} | -")
                    continue
                    
                last_line = last_lines[-1]
                ts, msg = parse_log_line(last_line)
                
                if ts:
                    # Check if "Active" (update within last 60s)
                    # Note: We can't easily compare log time (server time) with system time if they drift,
                    # but we can just show the time.
                    time_display = ts.strftime('%H:%M:%S')
                    
                    # Truncate msg
                    if len(msg) > 45:
                        msg = msg[:42] + "..."
                        
                    print(f"{worker_name:<10} | {time_display:<20} | {msg}")
                    active_count += 1
                else:
                    print(f"{worker_name:<10} | {'Unknown':<20} | {last_line[:40]}")
                    
        except Exception as e:
            print(f"{worker_name:<10} | {'Error':<20} | {str(e)}")

    print("-" * 80)
    print(f"Total Workers Logged: {len(log_files)}")

if __name__ == "__main__":
    main()
