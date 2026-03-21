import psycopg2
import json
import os
from datetime import datetime

def get_db_connection():
    try:
        with open('local.settings.json', 'r') as f:
            settings = json.load(f)
        return psycopg2.connect(settings['Values']['DB_CONNECTION_STRING'])
    except:
        return psycopg2.connect("postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local")

def run_audit():
    conn = get_db_connection()
    cur = conn.cursor()

    eras = [
        ("Legacy Era (1901-1986)", 1901, 1986),
        ("Modern Era (1987-2052)", 1987, 2052)
    ]

    report = {}

    for label, start, end in eras:
        # Ghost Cases
        cur.execute("""
            SELECT COUNT(*) FROM sc_decided_cases 
            WHERE EXTRACT(YEAR FROM date) BETWEEN %s AND %s 
              AND ai_model IS NULL
        """, (start, end))
        ghosts = cur.fetchone()[0]

        # Total Cases
        cur.execute("""
            SELECT COUNT(*) FROM sc_decided_cases 
            WHERE EXTRACT(YEAR FROM date) BETWEEN %s AND %s
        """, (start, end))
        total = cur.fetchone()[0]

        # Backfill Stats (Only for cases that HAVE an ai_model)
        fields = [
            ("digest_facts", "text"), ("digest_issues", "text"), ("digest_ruling", "text"), 
            ("digest_significance", "text"), ("digest_ratio", "text"), ("keywords", "json"), 
            ("legal_concepts", "json"), ("flashcards", "json"), ("spoken_script", "text")
        ]
        
        backfill_needs = {}
        for field, ftype in fields:
            if ftype == "text":
                cur.execute(f"""
                    SELECT COUNT(*) FROM sc_decided_cases 
                    WHERE EXTRACT(YEAR FROM date) BETWEEN %s AND %s 
                      AND ai_model IS NOT NULL 
                      AND ({field} IS NULL OR {field} = '')
                """, (start, end))
            else:
                cur.execute(f"""
                    SELECT COUNT(*) FROM sc_decided_cases 
                    WHERE EXTRACT(YEAR FROM date) BETWEEN %s AND %s 
                      AND ai_model IS NOT NULL 
                      AND ({field} IS NULL OR {field}::text = '[]' OR {field}::text = '{{}}')
                """, (start, end))
            backfill_needs[field] = cur.fetchone()[0]

        report[label] = {
            "ghosts": ghosts,
            "total": total,
            "digested": total - ghosts,
            "backfill_needs": backfill_needs
        }

    conn.close()
    return report

if __name__ == "__main__":
    results = run_audit()
    print(json.dumps(results, indent=2))
