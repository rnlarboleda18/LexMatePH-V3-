import glob
import os
import time
import sys
from datetime import datetime

# Enable ANSI colors in Windows terminal
os.system('color')

def parse_log_line(line):
    try:
        parts = line.split(' - ')
        timestamp_str = parts[0].split(',')[0]
        message = parts[-1].strip()
        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        return timestamp, message
    except:
        return None, line.strip()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    log_dir = "logs/finite_fleet"
    
    print("Starting Live Monitor... Press Ctrl+C to stop.")
    time.sleep(1)
    
    try:
        while True:
            log_files = glob.glob(os.path.join(log_dir, "worker_*.log"))
            log_files.sort(key=lambda x: int(os.path.basename(x).split('_')[1].split('.')[0]))
            
            # buffer output to print all at once to reduce flickering
            output = []
            output.append("=========================================================================================")
            output.append(f"  LIVE FLEET MONITOR (50 Workers) | {datetime.now().strftime('%H:%M:%S')}")
            output.append("=========================================================================================")
            output.append(f"{'WORKER':<8} | {'LAST ACT':<10} | {'STATUS'}")
            output.append("-" * 85)
            
            for log_file in log_files:
                worker_id = os.path.basename(log_file).replace('.log', '').replace('worker_', '#')
                
                try:
                    with open(log_file, 'r') as f:
                        f.seek(0, os.SEEK_END)
                        pos = f.tell() - 250
                        if pos < 0: pos = 0
                        f.seek(pos)
                        lines = f.readlines()
                        
                        if not lines:
                            output.append(f"{worker_id:<8} | {'WAITING':<10} | -")
                            continue
                            
                        last_line = lines[-1].strip()
                        ts, msg = parse_log_line(last_line)
                        
                        if ts:
                            time_str = ts.strftime('%H:%M:%S')
                            # Truncate msg
                            if len(msg) > 55: msg = msg[:52] + "..."
                            
                            row = f"{worker_id:<8} | {time_str:<10} | {msg}"
                            
                            # Highlight Success
                            if "Successfully" in msg:
                                row += " [DONE]" 
                            
                            output.append(row)
                        else:
                             output.append(f"{worker_id:<8} | {'UNKNOWN':<10} | {last_line[-50:]}")
                             
                except Exception:
                     output.append(f"{worker_id:<8} | {'ERROR':<10} | Read Fail")

            clear_screen()
            print("\n".join(output))
            print("-" * 85)
            print("Updates every 1.0s. Ctrl+C to quit.")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nMonitor Stopped.")

if __name__ == "__main__":
    main()
