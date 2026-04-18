import json
import os

files = ["api/local.settings.json", "local.settings.json"]

for fpath in files:
    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        data["Values"]["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
        # Optional: ensure we stay on 2.5 flash which we verified works on Vertex
        
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"Enabled Vertex AI in {fpath}")
