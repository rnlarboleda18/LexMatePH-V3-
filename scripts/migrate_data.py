import os
import subprocess
import time

# Configuration
REMOTE_HOST = "bar-reviewer-app-db.postgres.database.azure.com"
REMOTE_PORT = "6432"  # Note: Azure often uses 6432 for pgbouncer, or 5432 direct
REMOTE_USER = "barappadmin"
REMOTE_PASS = "BRApass021819!"
REMOTE_DB = "postgres"

LOCAL_HOST = "localhost"
LOCAL_PORT = "5432"
LOCAL_USER = "postgres"
LOCAL_PASS = "postgres"
LOCAL_DB = "lexmateph-ea-db"

DUMP_FILE = "bar_reviewer_backup.sql"

def run_command(cmd, env=None):
    try:
        subprocess.run(cmd, check=True, shell=True, env=env)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        return False

def migrate():
    print("=== Starting Data Migration ===")
    
    # Add PostgreSQL bin to PATH
    pg_bin_path = r"C:\Program Files\PostgreSQL\16\bin"
    if os.path.exists(pg_bin_path):
        os.environ["PATH"] += os.pathsep + pg_bin_path
        print(f"Added {pg_bin_path} to PATH")

    # Check if tools exist
    try:
        subprocess.run(["pg_dump", "--version"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["psql", "--version"], check=True, stdout=subprocess.DEVNULL)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Error: PostgreSQL tools (pg_dump, psql) not found.")
        print("Please install PostgreSQL and ensure bin directory is in PATH.")
        return

    # Set environment variables for password
    env = os.environ.copy()
    env["PGPASSWORD"] = REMOTE_PASS
    
    # 1. Dump remote database
    print(f"\n1. Dumping remote database '{REMOTE_DB}' from {REMOTE_HOST}...")
    # Use -Fc for custom format (compressed, allowing parallel restore)
    # Azure requires sslmode=require usually.
    dump_cmd = (
        f'pg_dump -h {REMOTE_HOST} -p {REMOTE_PORT} -U {REMOTE_USER} '
        f'-d {REMOTE_DB} -F c -b -v -f "{DUMP_FILE}"'
    )
    env["PGSSLMODE"] = "require"
    
    if run_command(dump_cmd, env):
        print("Dump successful.")
    else:
        print("Dump failed. Check network connection and credentials.")
        return

    # 2. Create local database
    print(f"\n2. Creating local database '{LOCAL_DB}'...")
    env["PGPASSWORD"] = LOCAL_PASS
    del env["PGSSLMODE"] # Local usually doesn't need ssl
    
    create_db_cmd = (
        f'psql -h {LOCAL_HOST} -p {LOCAL_PORT} -U {LOCAL_USER} -d postgres '
        f'-c "DROP DATABASE IF EXISTS {LOCAL_DB}; CREATE DATABASE {LOCAL_DB};"'
    )
    
    if run_command(create_db_cmd, env):
        print("Database created.")
    else:
        print("Failed to create database. Is local PostgreSQL running?")
        return

    # 3. Restore to local database
    print(f"\n3. Restoring to '{LOCAL_DB}'...")
    restore_cmd = (
        f'pg_restore -h {LOCAL_HOST} -p {LOCAL_PORT} -U {LOCAL_USER} '
        f'-d {LOCAL_DB} -v "{DUMP_FILE}"'
    )
    
    if run_command(restore_cmd, env):
        print("\n=== Migration Completed Successfully ===")
        print(f"Update your local.settings.json to use: postgres://{LOCAL_USER}:{LOCAL_PASS}@{LOCAL_HOST}:{LOCAL_PORT}/{LOCAL_DB}")
    else:
        print("Restore failed.")

if __name__ == "__main__":
    migrate()
