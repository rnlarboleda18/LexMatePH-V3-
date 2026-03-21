import os
import time

DOWNLOADS_DIR = "downloads"

print(f"Checking {os.path.abspath(DOWNLOADS_DIR)}...")
start = time.time()
count = 0
for root, dirs, files in os.walk(DOWNLOADS_DIR):
    for file in files:
        if file.endswith(".html"):
            print(f"Found: {os.path.join(root, file)}")
            count += 1
            if count >= 5:
                break
    if count >= 5:
        break
        
print(f"Time to find 5 files: {time.time() - start:.4f}s")
