"""
Write GOOGLE_API_KEY / GEMINI_API_KEY into local.settings.json from the environment.

Never hardcode keys. Run from a shell that has the key set, e.g.:

  set GOOGLE_API_KEY=...   (Windows)
  python LexCode/scripts/update_tokens.py
"""

import json
import os
import sys

def main() -> None:
    token = (
        (os.environ.get("GOOGLE_API_KEY") or "").strip()
        or (os.environ.get("GEMINI_API_KEY") or "").strip()
    )
    if not token:
        print(
            "Set GOOGLE_API_KEY or GEMINI_API_KEY in the environment (do not commit keys).",
            file=sys.stderr,
        )
        sys.exit(1)

    files = ["api/local.settings.json", "local.settings.json"]

    for fpath in files:
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            data.setdefault("Values", {})
            data["Values"]["GOOGLE_API_KEY"] = token
            data["Values"]["GEMINI_API_KEY"] = token
            data["Values"]["GOOGLE_GENAI_USE_VERTEXAI"] = "false"
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            print(f"Updated {fpath}")
        else:
            print(f"Not found: {fpath}")


if __name__ == "__main__":
    main()
