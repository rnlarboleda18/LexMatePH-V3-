import psycopg2, json
from pathlib import Path

settings = Path(__file__).resolve().parents[2] / "api" / "local.settings.json"
vals = json.loads(settings.read_text()).get("Values", {})
cs = vals.get("DB_CONNECTION_STRING")

conn = psycopg2.connect(cs)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM rpc_codal")
total = cur.fetchone()[0]
print(f"rpc_codal total rows: {total}")

cur.execute(
    "SELECT COUNT(*) FROM article_versions av "
    "JOIN legal_codes lc ON av.code_id = lc.code_id "
    "WHERE lc.short_name = 'RPC'"
)
av_total = cur.fetchone()[0]
print(f"article_versions (RPC) rows: {av_total}")

cur.execute(
    "SELECT DISTINCT amendment_id FROM article_versions av "
    "JOIN legal_codes lc ON av.code_id = lc.code_id "
    "WHERE lc.short_name = 'RPC' "
    "AND amendment_id IS NOT NULL "
    "AND amendment_id != 'Act No. 3815' "
    "ORDER BY amendment_id"
)
amendments = [r[0] for r in cur.fetchall()]
print(f"Amendments already ingested ({len(amendments)}):")
for a in amendments:
    print(f"  - {a}")

cur.close()
conn.close()
