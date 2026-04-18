import os

files = [
    "LexCode/scripts/lexcode_genai_client.py",
    "LexCode/scripts/batch_ingest_rpc.py"
]

for fpath in files:
    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        
        content = content.replace("gemini-2.5-pro", "gemini-3-flash-preview")
        
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {fpath}")
