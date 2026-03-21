import json
import psycopg2
import os

# --- CONFIGURATION ---
BATCH_OUTPUT_FILE = "batch_output_random_10.jsonl"
settings = json.load(open('api/local.settings.json'))
DB_CONNECTION_STRING = settings['Values']['DB_CONNECTION_STRING']

def transform_digest_data(data):
    """Transforms AI output keys to match DB/UI expectations."""
    # 1. Transform Legal Concepts (concept->term, definition->definition)
    if 'legal_concepts' in data and isinstance(data['legal_concepts'], list):
        new_concepts = []
        for item in data['legal_concepts']:
            if isinstance(item, dict):
                new_item = {
                    'term': item.get('concept', item.get('term', item.get('title'))),
                    'definition': item.get('definition', item.get('content'))
                }
                if 'citation' in item:
                    new_item['definition'] = f"{new_item['definition']} (Cit: {item['citation']})"
                new_concepts.append(new_item)
        data['legal_concepts'] = new_concepts

    # 2. Transform Flashcards (front->q, back->a)
    if 'flashcards' in data and isinstance(data['flashcards'], list):
        new_flashcards = []
        for item in data['flashcards']:
            if isinstance(item, dict):
                new_flashcards.append({
                    'q': item.get('front', item.get('question', item.get('q'))),
                    'a': item.get('back', item.get('answer', item.get('a'))),
                    'type': item.get('type', 'Concept') 
                })
        data['flashcards'] = new_flashcards

    # 3. Transform Secondary Rulings (list of strings -> list of objects)
    if 'secondary_rulings' in data and isinstance(data['secondary_rulings'], list):
        new_rulings = []
        for item in data['secondary_rulings']:
            if isinstance(item, str):
                topic = "Additional Ruling" # Default
                # Smart extraction: Check if any keyword appears in the ruling
                if 'keywords' in data and isinstance(data['keywords'], list):
                    # Sort keywords by length desc to match specific terms first
                    sorted_kws = sorted(data['keywords'], key=len, reverse=True)
                    for kw in sorted_kws:
                        if kw.lower() in item.lower():
                            topic = kw # Use the matched keyword as topic
                            break
                
                new_rulings.append({
                    'topic': topic, 
                    'ruling': item
                })
            elif isinstance(item, dict):
                new_rulings.append(item)
        data['secondary_rulings'] = new_rulings
        
    # 4. Transform Digest Facts (Ensure paragraphs)
    if 'digest_facts' in data and isinstance(data['digest_facts'], str):
        # basic check, if no double newlines, try to split? 
        # For now, trust the AI but maybe replace single \n with \n\n if mostly single?
        # Actually safer not to touch unless confirmed broken.
        pass

    return data

def save_digest_result(case_id, data, conn, model_name):
    """Updates the sc_decided_cases table with the AI-generated digest."""
    
    # --- TRANSFORM DATA ---
    data = transform_digest_data(data)
    
    cur = conn.cursor()
    
    classification = data.get('classification') or data.get('significance_category', 'REITERATION')
    reasoning = data.get('classification_reasoning', '')
    narrative = data.get('significance_narrative', '')
    rel_doctrine = data.get('relevant_doctrine', '') # Field from AI
    
    # Merge narrative and reasoning into significance_text
    significance_text = f"[{classification}]\n\n**Reasoning:** {reasoning}\n\n{narrative}"
    if rel_doctrine:
        significance_text += f"\n\n**Relevant Doctrine:** {rel_doctrine}"

    def to_str(val):
        if val is None: return None
        if isinstance(val, (dict, list)): return json.dumps(val, indent=2)
        return str(val)

    try:
        cur.execute("""
            UPDATE sc_decided_cases SET
                short_title = %s,
                significance_category = %s,
                ponente = %s,
                subject = %s,
                keywords = %s,
                statutes_involved = %s,
                main_doctrine = %s,
                cited_cases = %s,
                timeline = %s,
                digest_facts = %s,
                digest_issues = %s,
                digest_ruling = %s,
                digest_ratio = %s,
                legal_concepts = %s,
                flashcards = %s,
                spoken_script = %s,
                separate_opinions = %s,
                secondary_rulings = %s,
                ai_model = %s,
                updated_at = CURRENT_TIMESTAMP,
                digest_significance = %s
            WHERE id = %s
        """, (
            to_str(data.get('short_title')),
            to_str(classification),
            to_str(data.get('ponente')),
            to_str(data.get('subject')),
            json.dumps(data.get('keywords', [])),
            json.dumps(data.get('statutes_involved', [])),
            to_str(data.get('main_doctrine') or rel_doctrine),
            json.dumps(data.get('cited_cases', [])),
            json.dumps(data.get('timeline', [])),
            to_str(data.get('digest_facts')),
            to_str(data.get('digest_issues')),
            to_str(data.get('digest_ruling')),
            to_str(data.get('digest_ratio')),
            json.dumps(data.get('legal_concepts', [])),
            json.dumps(data.get('flashcards', [])),
            to_str(data.get('spoken_script')),
            json.dumps(data.get('separate_opinions', [])),
            json.dumps(data.get('secondary_rulings', [])),
            model_name,
            to_str(significance_text),
            case_id
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating case {case_id}: {e}")
        conn.rollback()
        return False

def repair_truncated_json(json_str):
    """Attempt to repair truncated JSON by closing open brackets/braces."""
    json_str = json_str.strip()
    
    # Simple stack-based closer
    stack = []
    is_string = False
    escaped = False
    
    for char in json_str:
        if escaped:
            escaped = False
            continue
        if char == '\\':
            escaped = True
            continue
        if char == '"':
            is_string = not is_string
            continue
        
        if not is_string:
            if char == '{':
                stack.append('}')
            elif char == '[':
                stack.append(']')
            elif char == '}' or char == ']':
                # Attempt to pop. If stack empty or mismatch, ignore
                if stack:
                    if stack[-1] == char:
                        stack.pop()
    
    # Output is truncated. 
    # If inside string, close it.
    if is_string:
        json_str += '"'
    
    # Remove trailing comma if present (whitespace safe)
    json_str = json_str.rstrip()
    if json_str.endswith(','):
        json_str = json_str[:-1]

    # Close remaining structures
    while stack:
        closer = stack.pop()
        json_str += closer
        
    return json_str

def main():
    if not os.path.exists(BATCH_OUTPUT_FILE):
        print(f"Error: {BATCH_OUTPUT_FILE} not found.")
        return

    conn = psycopg2.connect(DB_CONNECTION_STRING)
    
    print(f"Ingesting results from {BATCH_OUTPUT_FILE}...")
    
    # Track stats
    success_count = 0
    fail_count = 0
    total_count = 0
    
    with open(BATCH_OUTPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            total_count += 1
            line = line.strip()
            if not line: continue
            
            try:
                batch_obj = json.loads(line)
                custom_id = batch_obj.get('custom_id')
                if not custom_id: continue
                
                case_id = custom_id.replace('req-', '')
                
                # Check for error
                if 'error' in batch_obj:
                    print(f"Case {case_id}: API Error - {batch_obj['error']}")
                    fail_count += 1
                    continue
                
                # Extract content
                response = batch_obj.get('response', {})
                candidates = response.get('candidates', [])
                if not candidates:
                    print(f"Case {case_id}: No candidates returned.")
                    fail_count += 1
                    continue
                    
                raw_text = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                if not raw_text:
                    print(f"Case {case_id}: No text content in candidate.")
                    fail_count += 1
                    continue

                # Clean markdown
                clean_text = raw_text.replace('```json', '').replace('```', '').strip()
                
                data = {} # Initialize data
                try:
                    data = json.loads(clean_text)
                except json.JSONDecodeError:
                    # Attempt Repair
                    print(f"Case {case_id}: JSON parsing failed. Attempting repair...")
                    repaired_text = repair_truncated_json(clean_text)
                    try:
                        data = json.loads(repaired_text)
                        print(f"Case {case_id}: Repair SUCCESS.")
                    except json.JSONDecodeError:
                        print(f"Case {case_id}: Repair FAILED. Original error: {e}")
                        fail_count += 1
                        continue
                
                if save_digest_result(case_id, data, conn, "gemini-3-flash-preview-batch"):
                    success_count += 1
                    print(f"Case {case_id}: SUCCESS")
                else:
                    fail_count += 1
                    print(f"Case {case_id}: FAILED (DB update error)")

            except Exception as e:
                print(f"Error processing line: {e}")

    conn.close()
    print("-" * 30)
    print(f"INGESTION COMPLETE: {success_count}/{total_count} cases updated.")

if __name__ == "__main__":
    main()
