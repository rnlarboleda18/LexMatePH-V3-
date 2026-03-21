import psycopg2
import os

DB_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def main():
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor()

        # Assumption: ~3000 chars per page. 50 pages = 150,000 chars.
        # We'll use LENGTH(full_text_md) to approximate.
        min_length = 150000 
        
        print(f"Searching for cases with > {min_length} characters (approx 50+ pages)...")
        
        query = """
            SELECT id, case_number, title, date, LENGTH(full_text_md) as char_len
            FROM sc_decided_cases 
            WHERE LENGTH(full_text_md) > %s
            ORDER BY char_len DESC
            LIMIT 20
        """
        
        cur.execute(query, (min_length,))
        rows = cur.fetchall()
        
        if not rows:
            print("No cases found exceeding that length.")
            return

        print(f"\nFound {len(rows)} very long cases (showing top 20):\n")
        print(f"{'ID':<8} | {'Est. Pages':<12} | {'Chars':<10} | {'Date':<12} | {'Title'}")
        print("-" * 120)
        
        output_file = 'long_cases_list.txt'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Long Cases (>50 estimated pages / {min_length} chars)\n")
            f.write("-" * 80 + "\n\n")
            
            for row in rows:
                case_id = row[0]
                case_no = row[1]
                title = row[2]
                date = row[3]
                length = row[4]
                est_pages = int(length / 3000)
                
                # Console Output
                title_short = (title[:50] + '..') if title and len(title) > 50 else title
                print(f"{case_id:<8} | {est_pages:<12} | {length:<10} | {str(date):<12} | {title_short}")
                
                # File Output
                f.write(f"ID: {case_id}\n")
                f.write(f"Case No: {case_no}\n")
                f.write(f"Title: {title}\n")
                f.write(f"Date: {date}\n")
                f.write(f"Length: {length} chars (~{est_pages} pages)\n")
                f.write("-" * 80 + "\n")
        
        print("-" * 120)
        print(f"\nFull list saved to: {output_file}")
        
        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
