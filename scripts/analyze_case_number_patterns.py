"""
Summarize sc_decided_cases.case_number prefix patterns (counts + short description).

Usage (from repo root, cloud DB per project rules):
  python scripts/analyze_case_number_patterns.py

Connection: DB_CONNECTION_STRING env, else api/local.settings.json Values.DB_CONNECTION_STRING.
Requires: psycopg2 (no secrets committed; do not paste URLs into issues).
"""

from __future__ import annotations

import json
import os
import sys

try:
    import psycopg2
except ImportError:
    print("Install psycopg2: pip install psycopg2-binary", file=sys.stderr)
    sys.exit(1)


def load_conn_str() -> str | None:
    s = os.environ.get("DB_CONNECTION_STRING")
    if s:
        return s
    for path in ("api/local.settings.json", "local.settings.json"):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)["Values"]["DB_CONNECTION_STRING"]
        except OSError:
            continue
    return None


SQL = r"""
WITH tagged AS (
  SELECT
    case_number,
    CASE
      WHEN case_number IS NULL OR btrim(case_number) = '' THEN
        '00_NULL_OR_BLANK'
      WHEN case_number ~* '^\s*G\.?\s*R\.?\s*U\.?\s*J\.?\s*No\.?\s' THEN
        '01_GR_UJ'
      WHEN case_number ~* '^\s*G\.?\s*R\.?\s*Nos\.?\s' THEN
        '02_GR'
      WHEN case_number ~* '^\s*G\.?\s*R\.?\s*No\.?\s' THEN
        '02_GR'
      WHEN case_number ~* '^\s*Adm\.?\s*Matter' THEN
        '03_AM'
      WHEN case_number ~* '^\s*A\.?\s*M\.?\s*No\.?\s' THEN
        '03_AM'
      WHEN case_number ~* '^\s*A\.?\s*C\.?\s*No\.?\s' THEN
        '04_AC'
      WHEN case_number ~* '^\s*B\.?\s*M\.?\s*No\.?\s' THEN
        '05_BM'
      WHEN case_number ~* '^\s*U\.?\s*D\.?\s*K\.?\s*No\.?\s' THEN
        '06_UDK'
      WHEN case_number ~* '^\s*I\.?\s*P\.?\s*C\.?\s*No\.?\s' OR case_number ~* '^\s*IPC\s' THEN
        '07_IPC'
      WHEN case_number ~* 'OCA\s+IPI' THEN
        '08_OCA_IPI'
      WHEN case_number ~* '^\s*L-\s*[0-9]' THEN
        '09_L_NUMBER'
      WHEN case_number ~* '^\s*A\.?\s*M\.?\s*P\.?\s*No\.?\s' THEN
        '10_AMP'
      WHEN case_number ~* '^\s*A\.?\s*M\.?\s*T\.?\s*O\.?\s*No\.?\s' THEN
        '11_AMTO'
      WHEN case_number ~* '^\s*A\.?\s*M\.?\s*O\.?\s*No\.?\s' THEN
        '12_AMO'
      WHEN case_number ~* '^\s*A\.?\s*M\.?\s*R\.?\s*T\.?\s*J\.?\s*No\.?\s' THEN
        '13_AMRTJ'
      WHEN case_number ~* '^\s*A\.?\s*M\.?\s*R\.?\s*T\.?\s*No\.?\s' THEN
        '14_AMRT'
      WHEN case_number ~* '^\s*A\.?\s*M\.?\s*T\.?\s*C\.?\s*No\.?\s' THEN
        '15_AMTC'
      WHEN case_number ~* '^\s*A\.?\s*M\.?\s*R\.?\s*S\.?\s*No\.?\s' THEN
        '16_AMRS'
      WHEN case_number ~* '^\s*A\.?\s*M\.?\s*R\.?\s*S\.?\s*P\.?\s*No\.?\s' THEN
        '17_AMRSP'
      WHEN case_number ~* '^\s*A\.?\s*M\.?\s*R\.?\s*T\.?\s*I\.?\s*No\.?\s' THEN
        '18_AMRTI'
      WHEN case_number ~* '^\s*A\.?\s*M\.?\s*R\.?\s*T\.?\s*I\.?\s*P\.?\s*No\.?\s' THEN
        '19_AMRTIP'
      WHEN case_number ~* '^\s*A\.?\s*M\.?\s*R\.?\s*T\.?\s*I\.?\s*P\.?\s*P\.?\s*No\.?\s' THEN
        '20_AMRTIPP'
      ELSE
        '99_OTHER'
    END AS pattern_key
  FROM sc_decided_cases
)
SELECT pattern_key, COUNT(*) AS row_count
FROM tagged
GROUP BY pattern_key
ORDER BY pattern_key;
"""

# Same CASE as in SQL (for samples query); keep in sync when editing patterns above.
_PATTERN_CASE = r"""
      WHEN case_number IS NULL OR btrim(case_number) = '' THEN
        '00_NULL_OR_BLANK'
      WHEN case_number ~* '^\s*G\.?\s*R\.?\s*U\.?\s*J\.?\s*No\.?\s' THEN
        '01_GR_UJ'
      WHEN case_number ~* '^\s*G\.?\s*R\.?\s*Nos\.?\s' THEN
        '02_GR'
      WHEN case_number ~* '^\s*G\.?\s*R\.?\s*No\.?\s' THEN
        '02_GR'
      WHEN case_number ~* '^\s*Adm\.?\s*Matter' THEN
        '03_AM'
      WHEN case_number ~* '^\s*A\.?\s*M\.?\s*No\.?\s' THEN
        '03_AM'
      WHEN case_number ~* '^\s*A\.?\s*C\.?\s*No\.?\s' THEN
        '04_AC'
      WHEN case_number ~* '^\s*B\.?\s*M\.?\s*No\.?\s' THEN
        '05_BM'
      WHEN case_number ~* '^\s*U\.?\s*D\.?\s*K\.?\s*No\.?\s' THEN
        '06_UDK'
      WHEN case_number ~* '^\s*I\.?\s*P\.?\s*C\.?\s*No\.?\s' OR case_number ~* '^\s*IPC\s' THEN
        '07_IPC'
      WHEN case_number ~* 'OCA\s+IPI' THEN
        '08_OCA_IPI'
      WHEN case_number ~* '^\s*L-\s*[0-9]' THEN
        '09_L_NUMBER'
      WHEN case_number ~* '^\s*A\.?\s*M\.?\s*P\.?\s*No\.?\s' THEN
        '10_AMP'
      WHEN case_number ~* '^\s*A\.?\s*M\.?\s*T\.?\s*O\.?\s*No\.?\s' THEN
        '11_AMTO'
      WHEN case_number ~* '^\s*A\.?\s*M\.?\s*O\.?\s*No\.?\s' THEN
        '12_AMO'
      WHEN case_number ~* '^\s*A\.?\s*M\.?\s*R\.?\s*T\.?\s*J\.?\s*No\.?\s' THEN
        '13_AMRTJ'
      WHEN case_number ~* '^\s*A\.?\s*M\.?\s*R\.?\s*T\.?\s*No\.?\s' THEN
        '14_AMRT'
      WHEN case_number ~* '^\s*A\.?\s*M\.?\s*T\.?\s*C\.?\s*No\.?\s' THEN
        '15_AMTC'
      WHEN case_number ~* '^\s*A\.?\s*M\.?\s*R\.?\s*S\.?\s*No\.?\s' THEN
        '16_AMRS'
      WHEN case_number ~* '^\s*A\.?\s*M\.?\s*R\.?\s*S\.?\s*P\.?\s*No\.?\s' THEN
        '17_AMRSP'
      WHEN case_number ~* '^\s*A\.?\s*M\.?\s*R\.?\s*T\.?\s*I\.?\s*No\.?\s' THEN
        '18_AMRTI'
      WHEN case_number ~* '^\s*A\.?\s*M\.?\s*R\.?\s*T\.?\s*I\.?\s*P\.?\s*No\.?\s' THEN
        '19_AMRTIP'
      WHEN case_number ~* '^\s*A\.?\s*M\.?\s*R\.?\s*T\.?\s*I\.?\s*P\.?\s*P\.?\s*No\.?\s' THEN
        '20_AMRTIPP'
      ELSE
        '99_OTHER'
"""

SQL_SAMPLES = (
    "SELECT case_number FROM sc_decided_cases WHERE (CASE "
    + _PATTERN_CASE.strip()
    + " END) = '99_OTHER' ORDER BY length(case_number) DESC NULLS LAST LIMIT 25;"
)


DESCRIPTIONS = {
    "00_NULL_OR_BLANK": "Missing or empty case_number",
    "01_GR_UJ": "G.R. U.J. No. - urgent / special G.R. docket (SC)",
    "02_GR": "G.R. No. / G.R. Nos. - Supreme Court docket (single or plural / consolidated)",
    "03_AM": "A.M. No. - Administrative Matter (SC)",
    "04_AC": "A.C. No. - Administrative Case",
    "05_BM": "B.M. No. - Bar Matter",
    "06_UDK": "U.D.K. No. - disciplinary / rare admin docket",
    "07_IPC": "I.P.C. / IPC - Integrated Bar / practice docket",
    "08_OCA_IPI": "OCA IPI - Office of the Court Administrator internal investigation",
    "09_L_NUMBER": "L-xxxxx - legacy Court of Appeals numbered docket",
    "10_AMP": "A.M.P. No. - administrative docket variant",
    "11_AMTO": "A.M. T.O. No. - administrative (T.O.)",
    "12_AMO": "A.M.O. No. - administrative office order",
    "13_AMRTJ": "A.M. RTJ No. - re complaint vs judge (RTJ)",
    "14_AMRT": "A.M. RT No. - administrative (RT)",
    "15_AMTC": "A.M. TC No. - administrative (TC)",
    "16_AMRS": "A.M. RS No. - administrative (RS)",
    "17_AMRSP": "A.M. RSP No. - administrative (RSP)",
    "18_AMRTI": "A.M. RTI No. - administrative (RTI)",
    "19_AMRTIP": "A.M. RTIP No.",
    "20_AMRTIPP": "A.M. RTIPP No.",
    "99_OTHER": "Other / compound / nonstandard prefix (see samples)",
}


def main() -> None:
    conn_s = load_conn_str()
    if not conn_s:
        print("Set DB_CONNECTION_STRING or add it to api/local.settings.json and re-run.", file=sys.stderr)
        sys.exit(2)

    conn = psycopg2.connect(conn_s)
    cur = conn.cursor()
    samples: list[str] = []
    try:
        cur.execute("SELECT COUNT(*) FROM sc_decided_cases")
        (total,) = cur.fetchone()
        cur.execute(SQL)
        rows = cur.fetchall()
        cur.execute(SQL_SAMPLES)
        samples = [r[0] for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()

    print(f"sc_decided_cases total rows: {total}\n")
    print(f"{'Pattern key':<14} {'Rows':>10}  Short description")
    print("-" * 78)
    subtotal = 0
    for key, cnt in rows:
        subtotal += cnt
        desc = DESCRIPTIONS.get(key, key)
        print(f"{key:<14} {cnt:>10}  {desc}")
    print("-" * 78)
    print(f"{'SUM':<14} {subtotal:>10}")

    if samples:
        print("\nSample case_number values classified as 99_OTHER (up to 25):")
        for s in samples:
            print(f"  - {s!r}")


if __name__ == "__main__":
    main()
