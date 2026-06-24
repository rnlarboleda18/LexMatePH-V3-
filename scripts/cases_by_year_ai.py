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
    
    # Query to group by year and model
    cur.execute("""
        SELECT 
            COALESCE(EXTRACT(YEAR FROM date)::integer, 0) AS yr,
            ai_model,
            COUNT(*)
        FROM sc_decided_cases
        WHERE date >= '1987-01-01' AND date <= '2026-12-31'
        GROUP BY yr, ai_model
        ORDER BY yr, ai_model
    """)
    
    rows = cur.fetchall()
    
    # Structure of data: year -> model -> count
    year_model_counts = defaultdict(lambda: defaultdict(int))
    all_models = set()
    years = set()
    
    for yr, model, count in rows:
        if yr < 1987 or yr > 2026:
            continue
        m_name = model or "None (Undigested)"
        year_model_counts[yr][m_name] = count
        all_models.add(m_name)
        years.add(yr)
        
    cur.close()
    conn.close()
    
    sorted_years = sorted(list(years))
    sorted_models = sorted(list(all_models))
    
    print("## Yearly Distribution of AI Models (1987-2026)\n")
    
    header = "| Year | " + " | ".join(sorted_models) + " | Total |"
    divider = "|---|" + "|".join(["---" for _ in sorted_models]) + "|---|"
    print(header)
    print(divider)
    
    model_totals = defaultdict(int)
    grand_total = 0
    
    for yr in sorted_years:
        row_vals = []
        row_total = 0
        for model in sorted_models:
            cnt = year_model_counts[yr][model]
            row_vals.append(f"{cnt:,d}" if cnt > 0 else "0")
            row_total += cnt
            model_totals[model] += cnt
        grand_total += row_total
        print(f"| {yr} | " + " | ".join(row_vals) + f" | {row_total:,d} |")
        
    print(divider)
    total_vals = []
    for model in sorted_models:
        total_vals.append(f"**{model_totals[model]:,d}**")
    print(f"| **TOTAL** | " + " | ".join(total_vals) + f" | **{grand_total:,d}** |")

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
