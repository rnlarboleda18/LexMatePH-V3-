import psycopg2
import os

BASE_URI = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:{}/postgres?sslmode=require"

def check_port(port):
    print(f"\n--- Checking Port {port} ---")
    try:
        uri = BASE_URI.format(port)
        conn = psycopg2.connect(uri)
        cur = conn.cursor()
        
        cur.execute("SHOW max_connections")
        max_conn = cur.fetchone()[0]
        print(f"Max Connections: {max_conn}")
        
        cur.execute("SELECT count(*) FROM pg_stat_activity")
        active = cur.fetchone()[0]
        print(f"Active: {active}")
        
        conn.close()
    except Exception as e:
        print(f"Error checking port {port}: {e}")

if __name__ == "__main__":
    check_port(5432) # Direct
    check_port(6432) # PgBouncer
