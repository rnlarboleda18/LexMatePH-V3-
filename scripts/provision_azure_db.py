
import subprocess
import secrets
import string
import json
import time

def run_command(command, shell=False):
    """Runs a shell command and returns the output."""
    print(f"Running: {command}")
    try:
        result = subprocess.run(command, shell=shell, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        raise e

def generate_password(length=20):
    """Generates a secure password."""
    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for i in range(length))
    return password

def main():
    RESOURCE_GROUP = "rg-bar-project-v2"
    LOCATION = "southeastasia"
    SERVER_NAME = f"bar-db-server-gen-{secrets.token_hex(4)}"
    ADMIN_USER = "bar_admin"
    ADMIN_PASS = generate_password()

    print("--- Azure Provisioning Started ---")
    
    # 1. Create Resource Group
    print(f"\n1. Creating Resource Group: {RESOURCE_GROUP}...")
    try:
        run_command(f"az group create --name {RESOURCE_GROUP} --location {LOCATION}", shell=True)
        print("Resource Group created.")
    except Exception as e:
        print("Failed to create resource group. Ensure you are logged in (az login).")
        return

    # 2. Create PostgreSQL Flexible Server
    print(f"\n2. Creating PostgreSQL Flexible Server: {SERVER_NAME}...")
    print("(This usually takes 3-5 minutes. Please wait...)")
    try:
        cmd = (
            f"az postgres flexible-server create "
            f"--resource-group {RESOURCE_GROUP} "
            f"--name {SERVER_NAME} "
            f"--location {LOCATION} "
            f"--admin-user {ADMIN_USER} "
            f"--admin-password {ADMIN_PASS} "
            f"--sku-name Standard_B1ms "
            f"--tier Burstable "
            f"--public-access all "  # Allow public access (simplifies migration)
            f"--storage-size 32 "
            f"--yes"
        )
        run_command(cmd, shell=True)
        print("Database Server created.")
    except Exception as e:
        print("Failed to create database server.")
        return

    # 3. Construct Connection String
    conn_string = f"postgresql://{ADMIN_USER}:{ADMIN_PASS}@{SERVER_NAME}.postgres.database.azure.com:5432/postgres?sslmode=require"
    
    # 4. Save Credentials
    with open("azure_db_credentials.txt", "w") as f:
        f.write(f"Resource Group: {RESOURCE_GROUP}\n")
        f.write(f"Server Name: {SERVER_NAME}\n")
        f.write(f"Admin User: {ADMIN_USER}\n")
        f.write(f"Admin Password: {ADMIN_PASS}\n")
        f.write(f"Connection String: {conn_string}\n")
    
    print("\n--- Provisioning Complete ---")
    print(f"Credentials saved to: azure_db_credentials.txt")
    print("\nPlease verify the server in Azure Portal.")

if __name__ == "__main__":
    main()
