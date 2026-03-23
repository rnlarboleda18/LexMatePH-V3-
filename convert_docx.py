import os
import re
import docx
import traceback

def clean_text(text):
    text = re.sub(r'202\d GOLDEN NOTES', '', text)
    # Remove trailing syllabus headers: e.g. "a) TOPIC"
    text = re.sub(r'\s+[a-z]\)\s+[A-Z\s]{5,}$', '', text)
    # Remove trailing BAR year lists: e.g. "(2022, 2019 BAR)" or truncated "(2022, 2019, "
    text = re.sub(r'\s+\((19|20)\d{2}[^)]*?(BAR)?\)?$', '', text)
    text = text.replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def is_topic_header(line):
    line = line.strip()
    if not line: return False
    if re.match(r'^(Q|Q\.|Question|A|A\.|Answer)\s*:', line, re.IGNORECASE):
        return False
    pattern = r'^([A-Za-z0-9IVX]+[\.\)])?\s*[A-Z0-9\s,\.\-\(\)&/]{5,}$'
    if re.match(pattern, line):
        if any(c.isalpha() for c in line):
            return True
    return False

def parse_subquestions(q_idx, raw_q, raw_a):
    q_body = re.sub(r'^(Q|Q\.|Question)\s*:', '', raw_q, flags=re.IGNORECASE).strip()
    a_body = re.sub(r'^(A|A\.|Answer)\s*:', '', raw_a, flags=re.IGNORECASE).strip()
    
    marker_regex = r'(\([a-g]\)|(?<=\s)[a-g]\.|^[a-g]\.)'
    
    q_parts = re.split(marker_regex, q_body)
    sub_qs = {}
    main_q = q_parts[0].strip()
    if len(q_parts) > 1:
        for i in range(1, len(q_parts), 2):
            label = q_parts[i].strip('().').lower()
            if i+1 < len(q_parts):
                sub_qs[label] = q_parts[i+1].strip()
            
    a_parts = re.split(marker_regex, a_body)
    sub_as = {}
    main_a = a_parts[0].strip()
    if len(a_parts) > 1:
        for i in range(1, len(a_parts), 2):
            label = a_parts[i].strip('().').lower()
            if i+1 < len(a_parts):
                sub_as[label] = a_parts[i+1].strip()
            
    if len(sub_qs) > 0 and len(sub_as) > 0:
        all_keys = sorted(list(set(sub_qs.keys()).union(sub_as.keys())))
        
        output = [f"Q{q_idx}: {main_q}"]
        for k in all_keys:
            output.append(f"Q{q_idx}{k}: {sub_qs.get(k, '')}")
            
        if main_a and len(main_a) > 10:
             output.append(f"A{q_idx}: {main_a}")
             
        for k in all_keys:
            output.append(f"A{q_idx}{k}: {sub_as.get(k, '')}")
            
        return "\n\n".join(output) + "\n"
    else:
        output = [f"Q{q_idx}: {q_body}", f"A{q_idx}: {a_body}"]
        return "\n\n".join(output) + "\n"

def extract_qa_docx(docx_path, out_md_path):
    print(f"Processing {docx_path}...")
    doc = docx.Document(docx_path)
    qa_pairs = []
    
    current_q = []
    current_a = []
    state = "SEARCHING"
    
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text: continue
        
        # Remove intrusive headers
        if "GOLDEN NOTES" in text or "UNIVERSITY OF SANTO TOMAS" in text or "FACULTY OF CIVIL LAW" in text or "CIVIL LAW" in text:
            if len(text) < 50:
                continue
        if is_topic_header(text):
            continue
                
        is_q = re.match(r'^(Q|Q\.|Question)\s*:', text, re.IGNORECASE)
        is_a = re.match(r'^(A|A\.|Answer)\s*:', text, re.IGNORECASE)
        
        if is_q and "(Ibid)" in text:
            is_q = None
            is_a = True

        if is_q:
            if state == "READING_A":
                qa_pairs.append({
                    "question": clean_text(' '.join(current_q)),
                    "answer": clean_text(' '.join(current_a))
                })
                current_q = []
                current_a = []
            state = "READING_Q"
            current_q.append(text)
        elif is_a:
            state = "READING_A"
            current_a.append(text)
        else:
            if state == "READING_Q":
                current_q.append(text)
            elif state == "READING_A":
                current_a.append(text)
                
    if current_q and current_a:
        qa_pairs.append({
            "question": clean_text(' '.join(current_q)),
            "answer": clean_text(' '.join(current_a))
        })
         
    os.makedirs(os.path.dirname(out_md_path), exist_ok=True)
    with open(out_md_path, 'w', encoding='utf-8') as f:
        f.write(f"# Extracted Q&A from {os.path.basename(docx_path)}\n\n")
        f.write(f"Total Main Q&A pairs: {len(qa_pairs)}\n\n")
        f.write("---\n\n")
        for i, pair in enumerate(qa_pairs, 1):
            formatted_block = parse_subquestions(i, pair['question'], pair['answer'])
            f.write(formatted_block)
            f.write("---\n\n")
            
    print(f"Done. Extracted {len(qa_pairs)} main Q&A pairs to {out_md_path}")
    return len(qa_pairs)

if __name__ == "__main__":
    docx_path = r"C:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3\pdf quamto\Quamto 2023 Civil Law.docx"
    out_dir = r"C:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3\pdf quamto\md"
    out_md_path = os.path.join(out_dir, "Quamto_2023_Civil_Law.md")
    extract_qa_docx(docx_path, out_md_path)
