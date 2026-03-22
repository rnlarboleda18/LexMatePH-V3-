import psycopg2

LOCAL_DB = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
CLOUD_DB = "postgresql://bar_admin:[DB_PASSWORD]@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"

def main():
    try:
        print("Connecting to LOCAL DB...")
        conn_local = psycopg2.connect(LOCAL_DB)
        cur_local = conn_local.cursor()

        print("Connecting to CLOUD DB...")
        conn_cloud = psycopg2.connect(CLOUD_DB)
        cur_cloud = conn_cloud.cursor()

        # 1. Get exact columns and data types
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
             ptype = type_map.get(dtype, 'text') # Default to text for safety
             
             # Handle constraints (simplified assuming PK has index)
             if cname == 'id' and ptype == 'uuid':
                  col_defs.append(f"{cname} {ptype} DEFAULT gen_random_uuid() PRIMARY KEY")
             else:
                  null_def = "" if isnullable == 'YES' else " NOT NULL"
                  col_defs.append(f"{cname} {ptype}{null_def}")

        ddl = f"CREATE TABLE IF NOT EXISTS roc_codal (\n    " + ",\n    ".join(col_defs) + "\n);"
        print(f"\n--- TO EXECUTE DDL ---\n{ddl}\n-----------------------")

        # 3. Execute against Cloud
        print("Creating table roc_codal on cloud...")
        cur_cloud.execute(ddl)
        conn_cloud.commit()
        print("Table roc_codal ensured on Cloud DB!")

    except Exception as e:
        print(f"Failed to create cloud schema: {e}")
    finally:
        if 'conn_local' in locals(): conn_local.close()
        if 'conn_cloud' in locals(): conn_cloud.close()

if __name__ == "__main__":
    main()
