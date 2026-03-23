import psycopg2

DB_CONNECTION = "dbname=lexmateph-ea-db user=postgres password=b66398241bfe483ba5b20ca5356a87be host=localhost port=5432"
conn = psycopg2.connect(DB_CONNECTION)
cur = conn.cursor()
cur.execute("SELECT article_num, section_label, group_header FROM const_codal WHERE article_label = 'ARTICLE II' ORDER BY list_order;")
for row in cur.fetchall():
    print(row)
cur.close()
conn.close()
