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
    
    # Query count by year and model
    cur.execute("""
        SELECT EXTRACT(YEAR FROM date) as year, ai_model, COUNT(*) 
        FROM sc_decided_cases 
        WHERE date >= '1987-01-01' AND date <= '2026-12-31'
        GROUP BY year, ai_model
        ORDER BY year ASC, ai_model ASC
    """)
    rows = cur.fetchall()
    
    year_model_counts = defaultdict(lambda: defaultdict(int))
    all_models = set()
    years = set()
    
    for yr, model, count in rows:
        if yr is not None:
            yr_int = int(yr)
            m_name = model or "None (Undigested)"
            year_model_counts[yr_int][m_name] = count
            all_models.add(m_name)
            years.add(yr_int)
            
    sorted_years = sorted(list(years))
    sorted_models = sorted(list(all_models))
    
    # Helper to print a sub-table for a range of years
    def print_sub_table(title, start_yr, end_yr):
        print(f"### {title}\n")
        
        # We only include models that actually have non-zero counts in this era to keep tables thin
        active_models = []
        for model in sorted_models:
            model_has_data = False
            for yr in range(start_yr, end_yr + 1):
                if year_model_counts[yr][model] > 0:
                    model_has_data = True
                    break
            if model_has_data:
                active_models.append(model)
                
        header = "| Year | " + " | ".join(active_models) + " | Total |"
        divider = "|:---:| " + " | ".join([":---:" for _ in active_models]) + " | :---:|"
        print(header)
        print(divider)
        
        era_total = 0
        for yr in range(start_yr, end_yr + 1):
            if yr not in year_model_counts:
                continue
            row_vals = []
            row_total = 0
            for model in active_models:
                cnt = year_model_counts[yr][model]
                row_vals.append(f"{cnt:,d}" if cnt > 0 else "-")
                row_total += cnt
            era_total += row_total
            print(f"| **{yr}** | " + " | ".join(row_vals) + f" | **{row_total:,d}** |")
            
        print("\n" + "="*50 + "\n")

    print_sub_table("Era 1987 – 1999", 1987, 1999)
    print_sub_table("Era 2000 – 2009", 2000, 2009)
    print_sub_table("Era 2010 – 2019", 2010, 2019)
    print_sub_table("Era 2020 – 2026", 2020, 2026)

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
