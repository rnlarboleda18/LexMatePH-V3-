import psycopg2
import os

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def seed():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    # Create statutes table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS statutes (
            id SERIAL PRIMARY KEY,
            law_name TEXT NOT NULL,
            provision TEXT NOT NULL, -- e.g. 'Article 36', 'Rule 65, Sec 1'
            content TEXT NOT NULL,
            tags TEXT[],
            UNIQUE(law_name, provision)
        )
    """)
    
    # Common Bar Provisions
    seeds = [
        ("Family Code", "Article 36", "A marriage contracted by any party who, at the time of the celebration, was psychologically incapacitated to comply with the essential marital obligations of marriage, shall likewise be void even if such incapacity becomes manifest only after its solemnization."),
        ("Revised Penal Code", "Article 248", "Murder. — Any person who, not falling within the provisions of Article 246 shall kill another, shall be guilty of murder and shall be punished by reclusion perpetua to death, if committed with any of the following attendant circumstances: 1. With treachery..."),
        ("Rules of Court", "Rule 65, Section 1", "Petition for certiorari. — When any tribunal, board or officer exercising judicial or quasi-judicial functions has acted without or in excess of its or his jurisdiction, or with grave abuse of discretion amounting to lack or excess of jurisdiction..."),
        ("1987 Constitution", "Article III, Section 1", "No person shall be deprived of life, liberty, or property without due process of law, nor shall any person be denied the equal protection of the laws."),
        ("Civil Code", "Article 2", "Laws shall take effect after fifteen days following the completion of their publication in the Official Gazette, unless it is otherwise provided. This Code shall take effect one year after such publication.")
    ]
    
    for law, prov, content in seeds:
        cur.execute("""
            INSERT INTO statutes (law_name, provision, content)
            VALUES (%s, %s, %s)
            ON CONFLICT (law_name, provision) DO UPDATE SET content = EXCLUDED.content
        """, (law, prov, content))
        
    conn.commit()
    cur.close()
    conn.close()
    print("Statutes seeded successfully.")

if __name__ == "__main__":
    seed()
