import psycopg2

DB_CONNECTION = "dbname=bar_reviewer_local user=postgres password=b66398241bfe483ba5b20ca5356a87be host=localhost port=5432"

try:
    conn = psycopg2.connect(DB_CONNECTION)
    cur = conn.cursor()
    cur.execute("SELECT article_num, section_label, group_header, article_title, content_md FROM const_codal WHERE article_label = 'ARTICLE II' ORDER BY list_order;")
    for row in cur.fetchall():
        print(f"num: {row[0]}, sec: {row[1]}, grp: {row[2]}, title: {row[3]}, content_len: {len(row[4]) if row[4] else 0}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
