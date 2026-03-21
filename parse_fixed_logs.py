import re

def parse_logs():
    try:
        # Read with UTF-16LE encoding
        with open("run_log.txt", "r", encoding="utf-16le") as f:
            lines = f.readlines()
            
        print(f"Total lines in log: {len(lines)}")
        
        # Search for key terms relating to building and uploading
        target_patterns = [
            r"Starting submodules",
            r"Failed to find",
            r"Skipping",
            r"Uploading",
            r"Vite",
            r"Done building",
            r"Visit your site"
        ]
        
        for i, line in enumerate(lines):
             # Check if any pattern matches
             for pattern in target_patterns:
                  if re.search(pattern, line, re.IGNORECASE):
                       # Print the line and a few context lines around it
                       print(f"\n--- MATCH at line {i+1} ---")
                       for j in range(max(0, i-2), min(len(lines), i+5)):
                            print(lines[j].strip())
                       break # matches only once per line
                       
    except Exception as e:
        print("Error reading log:", e)

parse_logs()
