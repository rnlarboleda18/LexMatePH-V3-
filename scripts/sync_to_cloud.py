import psycopg2
from psycopg2.extras import RealDictCursor
import io

LOCAL_DB = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
CLOUD_DB = "postgresql://bar_admin:RABpass021819!@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"

def ensure_tables_cloud(cur_local, cur_cloud):
    print("\n--- Recreating Schemas on Cloud ---")
    
    # 1. Get exact columns and data types of roc_codal FROM local
    cur_local.execute("""
        SELECT column_name, udt_name, is_nullable
        FROM information_schema.columns 
        WHERE table_name = 'roc_codal'
        ORDER BY ordinal_position
    """)
    cols = cur_local.fetchall()
    if not cols:
         print("Error: roc_codal not found in local database!")
         return

    # 2. Build CREATE TABLE statement
    col_defs = []
    for cname, dtype, isnullable in cols:
         # Map UDT types to standard postgres types
         type_map = {
             'uuid': 'uuid',
             'text': 'text',
             'timestamptz': 'timestamptz',
             'jsonb': 'jsonb',
             'int4': 'integer',
             'varchar': 'varchar'
         }
         ptype = type_map.get(dtype, 'text')
         
         if cname == 'id' and ptype == 'uuid':
              col_defs.append(f"{cname} {ptype} DEFAULT gen_random_uuid() PRIMARY KEY")
         else:
              null_def = "" if isnullable == 'YES' else " NOT NULL"
              col_defs.append(f"{cname} {ptype}{null_def}")

    ddl = f"CREATE TABLE IF NOT EXISTS public.roc_codal (\n    " + ",\n    ".join(col_defs) + "\n);"
    print("Executing public.roc_codal table creator on Cloud...")
    cur_cloud.execute(ddl)
    cur_cloud.connection.commit() # Commit to make visible to bulk streamers

def sync_table(cur_local, cur_cloud, table_name, delete_clause=None, select_clause=None):
    print(f"\n--- Syncing table: {table_name} ---")
    
    # 1. Fetch from Local
    query = f"SELECT * FROM {table_name}"
    if select_clause:
        query += f" WHERE {select_clause}"
    cur_local.execute(query)
    rows = cur_local.fetchall()
    if not rows:
        print(f"No rows found in local {table_name}.")
        return
    cols = [desc[0] for desc in cur_local.description]
    print(f"Found {len(rows)} rows locally. Columns: {cols}")

    # 2. Clear from Cloud
    full_table = f"public.{table_name}"
    if delete_clause:
        print(f"Clearing Cloud {full_table} using: {delete_clause}...")
        cur_cloud.execute(f"DELETE FROM {full_table} WHERE {delete_clause}")
    else:
        print(f"Clearing ALL Cloud {full_table}...")
        cur_cloud.execute(f"DELETE FROM {full_table}")

    # 3. Insert into Cloud
    print(f"Streaming data into Cloud {full_table} via copy_from...")
    values = []
    for r in rows:
        values.append(tuple(r[col] for col in cols))
        
    f_buf = io.StringIO()
    for v in values:
        # Use \N for NULL values inside Postgres COPY streams
        cleaned_values = ["\\N" if x is None else str(x).replace('\t', ' ').replace('\n', ' ') for x in v]
        f_buf.write("\t".join(cleaned_values) + "\n")
    f_buf.seek(0)

    try:
         sql = f"COPY {full_table} ({', '.join(cols)}) FROM STDIN WITH (FORMAT TEXT, DELIMITER '\t')"
         cur_cloud.copy_expert(sql, f_buf)
         print(f"Successfully synced {len(rows)} rows to Cloud.")
    except Exception as e:
         import traceback
         with open("C:/tmp/sync_error.log", "a") as f:
              f.write(f"--- SYNC TABLE ERROR for {table_name} ---\n{traceback.format_exc()}\n")
         print(f"Error executing bulk copy_expert on {full_table}: {e}")

def main():
    try:
        print("Connecting to LOCAL DB...")
        conn_local = psycopg2.connect(LOCAL_DB)
        cur_local = conn_local.cursor(cursor_factory=RealDictCursor)

        print("Connecting to CLOUD DB...")
        conn_cloud = psycopg2.connect(CLOUD_DB)
        cur_cloud = conn_cloud.cursor(cursor_factory=RealDictCursor)

        # 1. Ensure Schema
        ensure_tables_cloud(cur_local, cur_cloud)

        # 2. Sync dataset
        sync_table(cur_local, cur_cloud, "roc_codal")
        sync_table(cur_local, cur_cloud, "codal_case_links", delete_clause="statute_id = 'ROC'", select_clause="statute_id = 'ROC'")

        conn_cloud.commit()
        print("\n🎉 Cloud Sync Complete!")

    except Exception as e:
        print(f"Sync failed: {e}")
    finally:
        if 'conn_local' in locals(): conn_local.close()
        if 'conn_cloud' in locals(): conn_cloud.close()

if __name__ == "__main__":
    main()
