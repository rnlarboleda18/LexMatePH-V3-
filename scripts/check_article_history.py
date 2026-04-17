import psycopg2

def check_article(article_num):
    conn = psycopg2.connect('postgres://bar_admin:RABpass021819!@lexmateph-ea-db.postgres.database.azure.com:5432/lexmateph-ea-db?sslmode=require')
    cur = conn.cursor()
    
    # Check article_versions joining with codal_amendments (using id=amendment_id)
    query = """
    SELECT av.version_id, av.article_number, av.valid_from, ca.amendment_law, av.amendment_description
    FROM article_versions av
    LEFT JOIN codal_amendments ca ON av.amendment_id::uuid = ca.id
    WHERE av.article_number = %s
    ORDER BY av.valid_from ASC
    """
    cur.execute(query, (article_num,))
    rows = cur.fetchall()
    
    print(f"\nVersions for Article {article_num}:")
    if not rows:
        print("No versions found in article_versions table.")
    for row in rows:
        print(f"ID: {row[0]}, Num: {row[1]}, Valid From: {row[2]}, Law: {row[3]}, Desc: {row[4]}")
    
    conn.close()

if __name__ == "__main__":
    check_article('134-A')  # Coup d'etat
    check_article('294')    # Robbery (Overlap 7659 & 10951)
