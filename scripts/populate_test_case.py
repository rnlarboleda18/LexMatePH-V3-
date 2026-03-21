import psycopg2
import os

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

def update_case():
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor()
        
        # Update ID 39842
        full_title = "JOSEPH E. ESTRADA vs. ANIANO DESIERTO, in his capacity as Ombudsman, RAMON GONZALEZ, VOLUNTEERS AGAINST CRIME AND CORRUPTION, GRAFT FREE PHILIPPINES FOUNDATION, INC., RAYMOND FORTUN, PEOPLE OF THE PHILIPPINES"
        
        cur.execute("UPDATE sc_decided_cases SET full_title = %s WHERE id = 39842", (full_title,))
        conn.commit()
        
        print("Updated ID 39842 with Full Title.")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_case()
