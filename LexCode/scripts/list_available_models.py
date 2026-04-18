from google import genai
import os

print("--- Listing ALL available models ---")
try:
    client = genai.Client(vertexai=True, project="gen-lang-client-0565960161", location="us-central1")
    for m in client.models.list():
        print(f"Model: {m.name}, Display: {m.display_name}")
except Exception as e:
    print(f"FAILED (us-central1): {e}")

try:
    client = genai.Client(vertexai=True, project="gen-lang-client-0565960161", location="asia-southeast1")
    for m in client.models.list():
        print(f"Model: {m.name}, Display: {m.display_name}")
except Exception as e:
    print(f"FAILED (asia-southeast1): {e}")
