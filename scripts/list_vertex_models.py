import sys
import os
from pathlib import Path
from google import genai

# Load local settings for DB and API config
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from load_local_settings_env import load_api_local_settings_into_environ
load_api_local_settings_into_environ(_SCRIPTS.parent)

PROJECT = "gen-lang-client-0813708151"
LOCATION = "us-central1"

# Strip any AI Studio env vars to prevent SDK from silently rerouting
for var in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_GENAI_USE_VERTEXAI"):
    os.environ.pop(var, None)

print(f"Initializing Vertex AI client (project={PROJECT}, location={LOCATION})...")
client = genai.Client(
    vertexai=True,
    project=PROJECT,
    location=LOCATION
)

print("Fetching available models from Vertex AI...\n")
try:
    models = list(client.models.list())
    print(f"Found {len(models)} models available:")
    print("=" * 60)
    for model in sorted(models, key=lambda m: m.name):
        print(f"Model ID: {model.name}")
    print("=" * 60)
except Exception as e:
    print(f"Error listing Vertex AI models: {e}")
