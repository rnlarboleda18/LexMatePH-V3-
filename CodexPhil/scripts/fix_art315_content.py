
import psycopg2
import os

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "bar_db")
DB_USER = os.getenv("DB_USER", "postgres")
# Use the known correct password or fetch from env if set correctly elsewhere
DB_PASSWORD = os.getenv("DB_PASSWORD", "b66398241bfe483ba5b20ca5356a87be")

# Full text of Article 315 as amended by RA 10951
CORRECT_CONTENT = """Article 315. Swindling (estafa). - Any person who shall defraud another by any of the means mentioned hereinbelow shall be punished by:

1st. The penalty of prisión correccional in its maximum period to prisión mayor in its minimum period, if the amount of the fraud is over Two million four hundred thousand pesos (P2,400,000) but does not exceed Four million four hundred thousand pesos (P4,400,000), and if such amount exceeds the latter sum, the penalty provided in this paragraph shall be imposed in its maximum period, adding one year for each additional Two million pesos (P2,000,000); but the total penalty which may be imposed shall not exceed twenty years. In such cases, and in connection with the accessory penalties which may be imposed and for the purpose of the other provisions of this Code, the penalty shall be termed prisión mayor or reclusion temporal, as the case may be.

2nd. The penalty of prisión correccional in its minimum and medium periods, if the amount of the fraud is over One million two hundred thousand pesos (P1,200,000) but does not exceed Two million four hundred thousand pesos (P2,400,000).

3rd. The penalty of arresto mayor in its maximum period to prisión correccional in its minimum period, if such amount is over Forty thousand pesos (P40,000) but does not exceed One million two hundred thousand pesos (P1,200,000).

4th. By arresto mayor in its medium and maximum periods, if such amount does not exceed Forty thousand pesos (P40,000): Provided, That in the four cases mentioned, the fraud be committed by any of the following means:

1. With unfaithfulness or abuse of confidence, namely:

(a) altering the substance, quantity, or quality of anything of value which the offender shall deliver by virtue of an obligation to do so, even though such obligation be based on an immoral or illegal consideration.

(b) By misappropriating or converting, to the prejudice of another, money, goods, or any other personal property received by the offender in trust or on commission, or for administration, or under any other obligation involving the duty to make delivery of or to return the same, even though such obligation be totally or partially guaranteed by a bond; or by denying having received such money, goods, or other property.

(c) By taking undue advantage of the signature of the offended party in blank, and by writing any document above such signature in blank, to the prejudice of the offended party or any third person.

2. By means of any of the following false pretenses or fraudulent acts executed prior to or simultaneously with the commission of the fraud:

(a) By using fictitious name, or falsely pretending to possess power, influence, qualifications, property, credit, agency, business or imaginary transactions, or by means of other similar deceits.

(b) By altering the quality, fineness or weight of anything pertaining to his art or business.

(c) By pretending to have bribed any Government employee, without prejudice to the action for calumny which the offended party may deem proper to bring against the offender. In this case, the offender shall be punished by the maximum period of the penalty.

(d) By postdating a check, or issuing a check in payment of an obligation when the offender had no funds in the bank, or his funds deposited therein were not sufficient to cover the amount of the check. The failure of the drawer of the check to deposit the amount necessary to cover his check within three (3) clays from receipt of notice from the bank and/or the payee or holder that said check has been dishonored for lack or insufficiency of funds shall be prime facie evidence of deceit constituting false pretense or fraudulent act.

Any person who shall defraud another by means of false pretenses or fraudulent acts as defined in paragraph 2(d) hereof shall be punished by:

1st. The penalty of reclusion temporal in its maximum period, if the amount of fraud is over Four million four hundred thousand pesos (P4,400,000) but does not exceed Eight million eight hundred thousand pesos (P8,800,000). If the amount exceeds the latter, the penalty shall be reclusion perpetua.

2nd. The penalty of reclusion temporal in its minimum and medium periods, if the amount of the fraud is over Two million four hundred thousand pesos (P2,400,000) but does not exceed Four million four hundred thousand pesos (P4,400,000).

3rd. The penalty of prisión mayor in its maximum period, if the amount of the fraud is over One million two hundred thousand pesos (P1,200,000) but does not exceed Two million four hundred thousand pesos (P2,400,000).

4th. The penalty of prisión mayor in its medium period, if such amount is over Forty thousand pesos (P40,000) but does not exceed One million two hundred thousand pesos (P1,200,000).

5th. By prisión mayor in its minimum period, if such amount does not exceed Forty thousand pesos (P40,000).

3. Through any of the following fraudulent means:

(a) By inducing another, by means of deceit, to sign any document.

(b) By resorting to some fraudulent practice to insure success in a gambling game.

(c) By removing, concealing or destroying, in whole or in part, any court record, office files, document or any other papers."""

def fix_article_315():
    try:
        conn = psycopg2.connect("postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local")
        cur = conn.cursor()

        print("Updating Article 315 content...")
        cur.execute("""
            UPDATE article_versions
            SET content = %s
            WHERE article_number = '315' AND amendment_id = 'Republic Act No. 10951';
        """, (CORRECT_CONTENT,))
        
        conn.commit()
        print(f"Update successful. Rows affected: {cur.rowcount}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_article_315()
