import sys

def trim_logs():
    try:
        with open("run_log.txt", "r", encoding="utf-16le") as f:
            content = f.read()
            
        print(f"Total size: {len(content)} chars")
        
        # Save last 30000 characters (most relevant usually at the end)
        trimmed = content[-40000:]
        with open("run_log_trimmed.txt", "w", encoding="utf-8") as f_out:
            f_out.write(trimmed)
            
        print("Trimmed logs saved to run_log_trimmed.txt")
        
    except Exception as e:
         print("Error:", e)

trim_logs()
