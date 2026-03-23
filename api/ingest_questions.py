"""
ingest_questions.py
Re-ingests all Q&A from the ai_md source files into the local database.
Groups sub-parts (Q4a, Q4b, Q4c → A4a, A4b, A4c) into a single record.
"""
import os
import re
import psycopg2
from psycopg2.extras import execute_values

# ── Config ─────────────────────────────────────────────────────────────────────

CONN_STR = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@127.0.0.1:5432/lexmateph-ea-db"

SOURCE_FILES = {
    r"Quamto 2023 Civil Law_AI.md":       "Civil Law",
    r"2_Criminal_Law_QUAMTO_AI.md":       "Criminal Law",
    r"3_Labor_Law_QUAMTO_AI.md":          "Labor and Social Legislation",
    r"4_Legal_Ethics_QUAMTO_AI.md":       "Legal and Judicial Ethics",
    r"5_Political_Law_QUAMTO_AI.md":      "Political Law",
    r"6_Commercial_Law_QQUAMTOL_AI.md":   "Commercial Law",
    r"7_Remedial_Law_QUAMTOL_AI.md":      "Remedial Law",
    r"8_Taxation_Law_QUAMTO_AI.md":       "Taxation Law",
}

AI_MD_DIR = r"C:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3\pdf quamto\ai_md"

# ── Regex Patterns ─────────────────────────────────────────────────────────────

# Matches: Q1: | Q4a: | Q30-1: | Q4b:
Q_MARKER = re.compile(r'^(Q([\d]+(?:-[\d]+)?[a-z]?)):?\s*$', re.IGNORECASE)
# Matches: A1: | A4a: | A30-1: | A4b:
A_MARKER = re.compile(r'^(A([\d]+(?:-[\d]+)?[a-z]?)):?\s*$', re.IGNORECASE)
# Matches: Question (2022 BAR) | Question (2012, 2008 BAR)
YEAR_HEADER = re.compile(r'Question\s*\(.*?(\d{4}).*?BAR\)', re.IGNORECASE)

def base_key(marker):
    """
    Extract the base group key from a Q/A marker.
    Q4a → '4', Q30-1 → '30-1', Q4b → '4'
    """
    # Strip leading Q or A, then strip trailing letter(s)
    raw = marker[1:].rstrip('abcdefghijklmnopqrstuvwxyz')
    return raw

# ── Parser ─────────────────────────────────────────────────────────────────────

def parse_file(filepath, subject):
    """
    Parse a single ai_md file. Returns a list of grouped records:
    [{'year': int, 'subject': str, 'question': str, 'answer': str}]
    """
    with open(filepath, encoding='utf-8') as f:
        lines = f.readlines()

    # We'll process line by line, tracking state
    groups = {}        # key: (year, base_number) → {'question': [...], 'answer': [...]}
    order = []         # preserves insertion order

    current_year = None
    current_q_key = None
    current_a_key = None
    mode = None        # 'q' | 'a' | None
    buffer = []

    def flush_buffer():
        nonlocal buffer
        text = '\n'.join(buffer).strip()
        buffer = []
        return text

    def get_or_create(year, base):
        key = (year, base)
        if key not in groups:
            groups[key] = {'year': year, 'subject': subject, 'question': [], 'answer': []}
            order.append(key)
        return groups[key]

    for raw_line in lines:
        line = raw_line.rstrip('\r\n')
        stripped = line.strip()

        # Year header
        ym = YEAR_HEADER.search(stripped)
        if ym:
            # Flush whatever we were collecting
            if mode == 'q' and current_q_key:
                text = flush_buffer()
                if text:
                    grp = get_or_create(current_year, current_q_key)
                    grp['question'].append(text)
            elif mode == 'a' and current_a_key:
                text = flush_buffer()
                if text:
                    grp = get_or_create(current_year, current_a_key)
                    grp['answer'].append(text)
            mode = None
            current_q_key = None
            current_a_key = None
            current_year = int(ym.group(1))
            continue

        # Q marker
        qm = Q_MARKER.match(stripped)
        if qm:
            if mode == 'q' and current_q_key:
                text = flush_buffer()
                if text:
                    grp = get_or_create(current_year, current_q_key)
                    grp['question'].append(text)
            elif mode == 'a' and current_a_key:
                text = flush_buffer()
                if text:
                    grp = get_or_create(current_year, current_a_key)
                    grp['answer'].append(text)
            mode = 'q'
            current_q_key = base_key(qm.group(1))
            buffer = []
            continue

        # A marker
        am = A_MARKER.match(stripped)
        if am:
            if mode == 'q' and current_q_key:
                text = flush_buffer()
                if text:
                    grp = get_or_create(current_year, current_q_key)
                    grp['question'].append(text)
            elif mode == 'a' and current_a_key:
                text = flush_buffer()
                if text:
                    grp = get_or_create(current_year, current_a_key)
                    grp['answer'].append(text)
            mode = 'a'
            current_a_key = base_key(am.group(1))
            buffer = []
            continue

        # Skip section headers like "Suggested Answer"
        if stripped.lower() in ('suggested answer', 'alternative answer:', 'alternative answer'):
            continue

        # Accumulate content
        if mode in ('q', 'a'):
            buffer.append(line)

    # Final flush
    if mode == 'q' and current_q_key:
        text = flush_buffer()
        if text:
            grp = get_or_create(current_year, current_q_key)
            grp['question'].append(text)
    elif mode == 'a' and current_a_key:
        text = flush_buffer()
        if text:
            grp = get_or_create(current_year, current_a_key)
            grp['answer'].append(text)

    # Convert groups to flat records
    records = []
    for key in order:
        g = groups[key]
        q_text = '\n\n'.join(p.strip() for p in g['question'] if p.strip())
        a_text = '\n\n'.join(p.strip() for p in g['answer'] if p.strip())
        if q_text:  # skip empty
            records.append({
                'year': g['year'],
                'subject': g['subject'],
                'question': q_text,
                'answer': a_text or None,
            })

    return records

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    all_records = []

    for filename, subject in SOURCE_FILES.items():
        filepath = os.path.join(AI_MD_DIR, filename)
        if not os.path.exists(filepath):
            print(f"  MISSING: {filename}")
            continue
        records = parse_file(filepath, subject)
        print(f"  {subject}: {len(records)} groups parsed from {filename}")
        all_records.extend(records)

    print(f"\nTotal grouped records: {len(all_records)}")

    # Preview first 3
    print("\n=== Sample Records ===")
    for r in all_records[:3]:
        print(f"\n[{r['year']} | {r['subject']}]")
        print(f"Q: {r['question'][:120]}...")
        print(f"A: {(r['answer'] or '')[:120]}...")

    confirm = input("\nProceed with DB insert? This will TRUNCATE questions + answers. (yes/no): ")
    if confirm.strip().lower() != 'yes':
        print("Aborted.")
        return

    conn = psycopg2.connect(CONN_STR)
    cur = conn.cursor()

    print("\nTruncating tables...")
    cur.execute("TRUNCATE TABLE answers, questions RESTART IDENTITY CASCADE")

    print("Inserting questions...")
    q_values = [
        (r['year'], r['subject'], r['question'], 'AI Extracted QUAMTO')
        for r in all_records
    ]
    execute_values(
        cur,
        "INSERT INTO questions (year, subject, text, source_label) VALUES %s RETURNING id",
        q_values
    )
    inserted_ids = [row[0] for row in cur.fetchall()]

    print("Inserting answers...")
    a_values = [
        (inserted_ids[i], all_records[i]['answer'], 'UPLC / Bar Q&A')
        for i in range(len(all_records))
        if all_records[i]['answer']
    ]
    execute_values(
        cur,
        "INSERT INTO answers (question_id, text, source_url) VALUES %s",
        a_values
    )

    conn.commit()
    cur.close()
    conn.close()

    print(f"\n✓ Done. {len(inserted_ids)} questions inserted, {len(a_values)} answers inserted.")

if __name__ == "__main__":
    main()
