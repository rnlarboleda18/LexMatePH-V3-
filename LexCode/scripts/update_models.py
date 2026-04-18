import os

files = ["LexCode/scripts/lexcode_genai_client.py", "LexCode/scripts/process_amendment.py"]

for fpath in files:
    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        
        content = content.replace("gemini-1.5-flash-002", "gemini-2.5-flash")
        content = content.replace("gemini-1.5-flash", "gemini-2.5-flash")
        content = content.replace("gemini-1.5-pro-002", "gemini-2.5-pro")
        content = content.replace("gemini-1.5-pro", "gemini-2.5-pro")
        
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {fpath}")
