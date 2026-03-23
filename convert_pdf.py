import os
import fitz
import re
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
    # Ignore Q: and A:
    if re.match(r'^(Q|Q\.|Question|A|A\.|Answer)\s*:', line, re.IGNORECASE):
        return False
    # Check for all-caps syllabus headers: I. TOPIC, a) TOPIC, etc.
    pattern = r'^([A-Za-z0-9IVX]+[\.\)])?\s*[A-Z0-9\s,\.\-\(\)&/]{5,}$'
    if re.match(pattern, line):
        if any(c.isalpha() for c in line):
            return True
    return False

def parse_subquestions(q_idx, raw_q, raw_a):
    q_body = re.sub(r'^(Q|Q\.|Question)\s*:', '', raw_q, flags=re.IGNORECASE).strip()
    a_body = re.sub(r'^(A|A\.|Answer)\s*:', '', raw_a, flags=re.IGNORECASE).strip()
    
    # Robust sub-marker: (a), a., (b), b.
    # We exclude numbers 1. 2. 3.
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
            
    # ONLY split into sub-blocks if BOTH question and answer have sub-markers
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
        # For MCQs or simple lists, keep them integrated in the main block
        output = [f"Q{q_idx}: {q_body}", f"A{q_idx}: {a_body}"]
        return "\n\n".join(output) + "\n"


def extract_qa(pdf_path, out_md_path):
    print(f"Processing {pdf_path}...")
    doc = fitz.open(pdf_path)
    qa_pairs = []
    
    current_q = []
    current_a = []
    state = "SEARCHING"
    
    for page in doc:
        blocks = page.get_text("blocks")
        page_height = page.rect.height
        page_width = page.rect.width
        mid_x = page_width / 2
        
        # Filter headers and footers (top 6%, bottom 6%)
        body_blocks = [b for b in blocks if b[1] > page_height*0.06 and b[3] < page_height*0.94]
        
        # Two columns: left (x0 < mid_x), right (x0 >= mid_x)
        left_col = sorted([b for b in body_blocks if b[0] < mid_x], key=lambda b: b[1])
        right_col = sorted([b for b in body_blocks if b[0] >= mid_x], key=lambda b: b[1])
        
        sorted_blocks = left_col + right_col
        
        for block in sorted_blocks:
            text = block[4].strip()
            
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if not line: continue
                if "GOLDEN NOTES" in line or "UNIVERSITY OF SANTO TOMAS" in line or "FACULTY OF CIVIL LAW" in line:
                    continue
                if is_topic_header(line):
                    continue
                
                is_q = re.match(r'^(Q|Q\.|Question)\s*:', line, re.IGNORECASE)
                is_a = re.match(r'^(A|A\.|Answer)\s*:', line, re.IGNORECASE)
                
                # Special check for Choice answers: "Q6d: rebellion (Ibid)" -> This is likely an Answer
                if is_q and "(Ibid)" in line:
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
                    
                    if state == "READING_Q":
                        if current_q:
                            print(f"[Warning] Question without answer: {current_q[0][:50]}...")
                        current_q = []
                        
                    state = "READING_Q"
                    current_q.append(line)
                elif is_a:
                    state = "READING_A"
                    current_a.append(line)
                else:
                    if state == "READING_Q":
                        current_q.append(line)
                    elif state == "READING_A":
                        current_a.append(line)
                        
    # Append the last one
    if current_q and current_a:
         qa_pairs.append({
             "question": clean_text(' '.join(current_q)),
             "answer": clean_text(' '.join(current_a))
         })
         
    doc.close()
    
    # Write to MD
    os.makedirs(os.path.dirname(out_md_path), exist_ok=True)
    with open(out_md_path, 'w', encoding='utf-8') as f:
        f.write(f"# Extracted Q&A from {os.path.basename(pdf_path)}\n\n")
        f.write(f"Total Main Q&A pairs: {len(qa_pairs)}\n\n")
        f.write("---\n\n")
        for i, pair in enumerate(qa_pairs, 1):
            formatted_block = parse_subquestions(i, pair['question'], pair['answer'])
            f.write(formatted_block)
            f.write("---\n\n")
            
    print(f"Done. Extracted {len(qa_pairs)} main Q&A pairs to {out_md_path}")
    return len(qa_pairs)

if __name__ == "__main__":
    pdf_dir = r"C:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3\pdf quamto"
    out_dir = os.path.join(pdf_dir, "md")
    
    total = 0
    try:
        files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
        for f in files:
            pdf_path = os.path.join(pdf_dir, f)
            md_name = f.replace('.pdf', '.md')
            out_md_path = os.path.join(out_dir, md_name)
            total += extract_qa(pdf_path, out_md_path)
            
        print(f"\nProcessing complete! Total main Q&A pairs extracted across all files: {total}")
    except Exception as e:
        traceback.print_exc()
