import os
import psycopg2
import sys
from pathlib import Path
from collections import defaultdict

# Setup paths
_SCRIPTS = Path(__file__).resolve().parent
_WORKSPACE = _SCRIPTS.parent
sys.path.append(str(_WORKSPACE))
sys.path.append(str(_WORKSPACE / "api"))

import load_local_settings_env

def get_db_connection():
    db_url = os.environ.get("DB_CONNECTION_STRING_AZURE") or os.environ.get("DB_CONNECTION_STRING")
    if not db_url:
        raise ValueError("No database connection string found in environment.")
    return psycopg2.connect(db_url)

def main():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Group by eras: 1987-1999, 2000-2009, 2010-2019, 2020-2026
    eras = [
        ("1987-1999", "1987-01-01", "1999-12-31"),
        ("2000-2009", "2000-01-01", "2009-12-31"),
        ("2010-2019", "2010-01-01", "2019-12-31"),
        ("2020-2026", "2020-01-01", "2026-12-31"),
    ]
    
    era_model_counts = defaultdict(lambda: defaultdict(int))
    all_models = set()
    
    for era_name, start_date, end_date in eras:
        cur.execute("""
            SELECT ai_model, COUNT(*) 
            FROM sc_decided_cases 
            WHERE date >= %s AND date <= %s
            GROUP BY ai_model
        """, (start_date, end_date))
        for model, count in cur.fetchall():
            m_name = model or "None (Undigested)"
            era_model_counts[era_name][m_name] = count
            all_models.add(m_name)
            
    # Print the markdown table for eras
    print("## Distribution of AI Models by Eras (1987-2026)\n")
    sorted_models = sorted(list(all_models))
    
    header = "| Era | " + " | ".join(sorted_models) + " | Total |"
    divider = "|---|" + "|".join(["---" for _ in sorted_models]) + "|---|"
    print(header)
    print(divider)
    
    # We will also accumulate totals for each model
    model_totals = defaultdict(int)
    grand_total = 0
    
    for era_name, _, _ in eras:
        row_vals = []
        row_total = 0
        for model in sorted_models:
            cnt = era_model_counts[era_name][model]
            row_vals.append(f"{cnt:,d}" if cnt > 0 else "0")
            row_total += cnt
            model_totals[model] += cnt
        grand_total += row_total
        print(f"| {era_name} | " + " | ".join(row_vals) + f" | {row_total:,d} |")
        
    # Print Totals row
    total_vals = []
    for model in sorted_models:
        total_vals.append(f"**{model_totals[model]:,d}**")
    print(divider)
    print(f"| **TOTAL** | " + " | ".join(total_vals) + f" | **{grand_total:,d}** |")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
