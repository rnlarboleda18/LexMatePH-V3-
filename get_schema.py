import psycopg2

try:
    conn = psycopg2.connect('postgresql://bar_admin:RABpass021819!@lexmateph-ea-db.postgres.database.azure.com:5432/lexmateph-ea-db?sslmode=require')
    cur = conn.cursor()
    
    cur.execute("SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_name IN ('questions', 'answers')")
    rows = cur.fetchall()
    
    schema = {}
    for table_name, column_name, data_type in rows:
        if table_name not in schema:
            schema[table_name] = []
        schema[table_name].append(f"{column_name} ({data_type})")
        
    for table, columns in schema.items():
        print(f"Table: {table}")
        for col in columns:
            print(f"  - {col}")
            
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
