import json
import os

token = "AIzaSyBgYSw6BGJo7YbaBbLqjRMs5uCZ9ty1Cr8"

files = ["api/local.settings.json", "local.settings.json"]

for fpath in files:
    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["Values"]["GOOGLE_API_KEY"] = token
        data["Values"]["GEMINI_API_KEY"] = token
        data["Values"]["GOOGLE_GENAI_USE_VERTEXAI"] = "false"
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"Updated {fpath}")
    else:
        print(f"Not found: {fpath}")
