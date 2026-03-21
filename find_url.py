import subprocess

def find_url():
    try:
        # Run gh run view and capture output
        # databaseId is correct based on previous tests
        result = subprocess.run(["gh", "run", "view", "23134226937", "--log"], capture_output=True, text=True, encoding='utf-8')
        logs = result.stdout
        
        # Search for SWA URL patterns
        for line in logs.splitlines():
            if "https://" in line and ".azurestaticapps.net" in line:
                print(f"FOUND: {line.strip()}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_url()
