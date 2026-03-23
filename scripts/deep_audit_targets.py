import psycopg2
import re
from datetime import datetime, timedelta

DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

def deep_audit():
    try:
        # Read original target IDs
        with open("target_fix_facts.txt", "r") as f:
            target_ids = [int(line.strip()) for line in f if line.strip()]
        
        print(f"Deep Audit of {len(target_ids)} Targeted Cases")
        print("="*60)
        
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor()
        
        compliant = []
        non_compliant = []
        not_updated = []
        
        # Check each target case
        for case_id in target_ids:
            cur.execute("""
                SELECT digest_facts, updated_at 
                FROM sc_decided_cases 
                WHERE id = %s
            """, (case_id,))
            
            row = cur.fetchone()
            if not row or not row[0]:
                not_updated.append(case_id)
                continue
            
            facts = row[0]
            updated_at = row[1]
            
            # Check if updated in last 3 hours (since fleet launched)
            if updated_at < datetime.now() - timedelta(hours=3):
                not_updated.append(case_id)
                continue
            
            # Header checks
            ant_match = re.search(r"\*\*(?:The\s*)?Antecedents(?:\s*(?:of the Case)?)?\s*:?\*\*", facts, re.IGNORECASE)
            proc_match = re.search(r"\*\*(?:The\s*)?(?:Procedural\s*History|Proceedings(?:.*)?)?\s*:?\*\*", facts, re.IGNORECASE)
            pet_match = re.search(r"\*\*(?:The\s*)?(?:Petition|Appeal|Present(?:.*)?)?\s*:?\*\*", facts, re.IGNORECASE)
            
            # Paragraph count
            paragraphs = [p for p in re.split(r'\n\s*\n', facts.strip()) if p.strip()]
            para_count = len(paragraphs)
            
            if ant_match and proc_match and pet_match and para_count == 3:
                compliant.append(case_id)
            else:
                reasons = []
                if not ant_match: reasons.append("Missing Antecedents")
                if not proc_match: reasons.append("Missing Procedural")
                if not pet_match: reasons.append("Missing Petition")
                if para_count != 3: reasons.append(f"Para Count: {para_count}")
                
                non_compliant.append((case_id, ", ".join(reasons)))
        
        # Results
        print(f"\nRESULTS FOR TARGETED 25,293 CASES:")
        print(f"  Compliant:       {len(compliant)} ({len(compliant)/len(target_ids)*100:.2f}%)")
        print(f"  Non-Compliant:   {len(non_compliant)} ({len(non_compliant)/len(target_ids)*100:.2f}%)")
        print(f"  Not Updated:     {len(not_updated)} ({len(not_updated)/len(target_ids)*100:.2f}%)")
        print(f"  Total Checked:   {len(target_ids)}")
        
        if non_compliant:
            print(f"\nFirst 20 Non-Compliant Cases:")
            for case_id, reason in non_compliant[:20]:
                print(f"  Case {case_id}: {reason}")
        
        if not_updated:
            print(f"\nFirst 20 Not Updated Cases:")
            for case_id in not_updated[:20]:
                print(f"  Case {case_id}")
        
        # Save full lists
        with open("audit_compliant.txt", "w") as f:
            f.write("\n".join(map(str, compliant)))
        
        with open("audit_non_compliant.txt", "w") as f:
            for case_id, reason in non_compliant:
                f.write(f"{case_id}: {reason}\n")
        
        with open("audit_not_updated.txt", "w") as f:
            f.write("\n".join(map(str, not_updated)))
        
        print(f"\nFull lists saved to:")
        print(f"  audit_compliant.txt")
        print(f"  audit_non_compliant.txt") 
        print(f"  audit_not_updated.txt")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    deep_audit()
