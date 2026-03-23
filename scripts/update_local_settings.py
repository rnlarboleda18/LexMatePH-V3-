import json
import os

SETTINGS_PATH = 'api/local.settings.json'

def update_settings():
    if not os.path.exists(SETTINGS_PATH):
        print(f"Error: {SETTINGS_PATH} not found")
        return

    try:
        with open(SETTINGS_PATH, 'r') as f:
            data = json.load(f)
        
        # Add new settings
        data['Values']['LOCAL_DB_CONNECTION_STRING'] = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
        data['Values']['ENVIRONMENT'] = "local"
        data['Values']['REDIS_ENABLED'] = "true"
        
        with open(SETTINGS_PATH, 'w') as f:
            json.dump(data, f, indent=4)
            
        print("Successfully updated local.settings.json")
        
    except Exception as e:
        print(f"Error updating settings: {e}")

if __name__ == "__main__":
    update_settings()
