import psycopg2

conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
conn = psycopg2.connect(conn_str)
cur = conn.cursor()

# The properly formatted amended article from Act No. 3999
# Based on the amendment text, with proper line breaks
amended_content = """### Article 329. Other mischiefs.

The mischiefs not included in the next preceding article shall be punished:

1. By arresto mayor in its medium and maximum periods, if the value of the damage caused exceeds 1,000 Pesos;

2. By arresto mayor in its minimum and medium periods, if such value is over 200 pesos but does not exceed 1,000; and

3. By arresto menor or fine of not less than the value of the damage caused and not more than 200 pesos, if the amount involved does not exceed 200 pesos or cannot be estimated."""

# Update the old version (set valid_to)
cur.execute("""
    UPDATE article_versions
    SET valid_to = '1932-12-05'
    WHERE code_id = '570b007a-36b6-4e74-a993-4b8d5d17a4ef'
        AND article_number = '329'
        AND valid_to IS NULL
""")

# Insert the new version
cur.execute("""
    INSERT INTO article_versions
    (code_id, article_number, content, valid_from, valid_to, amendment_id)
    VALUES (%s, %s, %s, %s, NULL, %s)
""", ('570b007a-36b6-4e74-a993-4b8d5d17a4ef', '329', amended_content, '1932-12-05', 'Act No. 3999'))

conn.commit()
print("✓ Article 329 amended successfully with proper formatting!")
print("✓ Old version: valid 1932-01-01 to 1932-12-05")
print("✓ New version: valid 1932-12-05 to NULL (current)")

conn.close()
