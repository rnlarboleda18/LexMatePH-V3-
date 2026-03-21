
import os
import sys
import psycopg2

# Import connection from neighbor script
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from process_amendment import get_db_connection

def reset_amendments():
    amendment_ids_to_wipe = [
        "Act No. 4117",
        "Commonwealth Act No. 99",
        "Commonwealth Act No. 235",
        "Republic Act No. 12",
        "Republic Act No. 18"
    ]
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        print("Resetting RPC Database for re-ingestion...")
        
        # 1. Identify affected articles (for logging)
        cur.execute("""
            SELECT DISTINCT article_number FROM article_versions 
            WHERE amendment_id = ANY(%s)
        """, (amendment_ids_to_wipe,))
        affected_articles = [row[0] for row in cur.fetchall()]
        print(f"Affected Articles: {affected_articles}")
        
        # 2. Delete the amended versions
        print(f"Deleting versions for amendments: {amendment_ids_to_wipe}")
        cur.execute("""
            DELETE FROM article_versions 
            WHERE amendment_id = ANY(%s)
        """, (amendment_ids_to_wipe,))
        deleted_count = cur.rowcount
        print(f"Deleted {deleted_count} rows.")
        
        # 3. Heal the base versions (Set valid_to = NULL for the remaining latest versions)
        # Strategy: For the affected articles, find the version that is now 'latest' (highest valid_from) 
        # and set its valid_to to NULL.
        # Actually, simpler: If we deleted the branching, the previous version has valid_to set to the amendment date.
        # We just need to NULL that out.
        # We can select for versions where valid_to matches ANY of the dates of the erased amendments?
        # A safer generic heal:
        # "For every RPC article, set valid_to=NULL for the record with the MAX valid_from."
        
        # Get RPC Code ID
        cur.execute("SELECT code_id FROM legal_codes WHERE short_name = 'RPC'")
        rpc_id = cur.fetchone()[0]
        
        print("Healing valid_to dates for base versions...")
        # Update set valid_to = NULL where it is the latest version for that article
        # We use a subquery to find the latest valid_from for each article
        query = """
            UPDATE article_versions av
            SET valid_to = NULL
            WHERE code_id = %s
            AND article_number = ANY(%s)
            AND valid_from = (
                SELECT MAX(valid_from) 
                FROM article_versions av2 
                WHERE av2.code_id = av.code_id 
                AND av2.article_number = av.article_number
            )
        """
        cur.execute(query, (rpc_id, affected_articles))
        updated_count = cur.rowcount
        print(f"Healed {updated_count} base versions.")
        
        conn.commit()
        print("Reset Complete.")
        
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    reset_amendments()
