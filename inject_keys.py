import subprocess
import json
import os

def run(cmd):
    return subprocess.check_output(cmd, shell=True, text=True).strip()

print("Fetching Storage Account Name...")
storage_acc = run("az storage account list --resource-group bar-reviewer --query \"[?contains(name, 'lexmatestorage')].name | [0]\" -o tsv")
print(f"Got: {storage_acc}")

print("Fetching Storage Connection String...")
storage_conn = run(f"az storage account show-connection-string --name {storage_acc} --resource-group bar-reviewer --query connectionString -o tsv")

print("Fetching Speech Key...")
speech_key = run("az cognitiveservices account keys list --name lexmate-speech --resource-group bar-reviewer --query key1 -o tsv")

settings_path = "api/local.settings.json"
print("Updating local.settings.json...")

with open(settings_path, "r") as f:
    settings = json.load(f)

settings["Values"]["AZURE_STORAGE_CONNECTION_STRING"] = storage_conn
settings["Values"]["SPEECH_KEY"] = speech_key
settings["Values"]["SPEECH_REGION"] = "japaneast"

with open(settings_path, "w") as f:
    json.dump(settings, f, indent=2)

print("SUCCESS")
