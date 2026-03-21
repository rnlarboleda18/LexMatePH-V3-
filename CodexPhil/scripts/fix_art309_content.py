
import psycopg2
import os

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "bar_db")
DB_USER = os.getenv("DB_USER", "postgres")
# Use the known correct password or fetch from env if set correctly elsewhere
DB_PASSWORD = os.getenv("DB_PASSWORD", "b66398241bfe483ba5b20ca5356a87be")

# Full text of Article 309 as amended by RA 10951
CORRECT_CONTENT = """Article 309. Penalties. - Any person guilty of theft shall be punished by:

1. The penalty of prision mayor in its minimum and medium periods, if the value of the thing stolen is more than One million two hundred thousand pesos (P1,200,000) but does not exceed Two million two hundred thousand pesos (P2,200,000); but if the value of the thing stolen exceeds the latter amount, the penalty shall be the maximum period of the one prescribed in this paragraph, and one year for each additional One million pesos (P1,000,000), but the total of the penalty which may be imposed shall not exceed twenty years. In such cases, and in connection with the accessory penalties which may be imposed and for the purpose of the other provisions of this Code, the penalty shall be termed prision mayor or reclusion temporal, as the case may be.

2. The penalty of prision correccional in its medium and maximum periods, if the value of the thing stolen is more than Six hundred thousand pesos (P600,000) but does not exceed One million two hundred thousand pesos (P1,200,000).

3. The penalty of prision correccional in its minimum and medium periods, if the value of the property stolen is more than Twenty thousand pesos (P20,000) but does not exceed Six hundred thousand pesos (P600,000).

4. Arresto mayor in its medium period to prision correccional in its minimum period, if the value of the property stolen is over Five thousand pesos (P5,000) but does not exceed Twenty thousand pesos (P20,000).

5. Arresto mayor to its full extent, if such value is over Five hundred pesos (P500) but does not exceed Five thousand pesos (P5,000).

6. Arresto mayor in its minimum and medium periods, if such value does not exceed Five hundred pesos (P500).

7. Arresto menor or a fine not exceeding Twenty thousand pesos (P20,000), if the theft is committed under the circumstances enumerated in paragraph 3 of the next preceding article and the value of the thing stolen does not exceed Five hundred pesos (P500). If such value exceeds said amount, the provisions of any of the five preceding subdivisions shall be made applicable.

8. Arresto menor in its minimum period or a fine of not exceeding Five thousand pesos (P5,000), when the value of the thing stolen is not over Five hundred pesos (P500), and the offender shall have acted under the impulse of hunger, poverty, or the difficulty of earning a livelihood for the support of himself or his family."""

def fix_article_309():
    try:
        conn = psycopg2.connect("postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local")
        cur = conn.cursor()

        print("Updating Article 309 content...")
        cur.execute("""
            UPDATE article_versions
            SET content = %s
            WHERE article_number = '309' AND amendment_id = 'Republic Act No. 10951';
        """, (CORRECT_CONTENT,))
        
        conn.commit()
        print(f"Update successful. Rows affected: {cur.rowcount}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_article_309()
