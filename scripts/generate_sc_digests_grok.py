import os
import json
import psycopg2
from openai import OpenAI
import time
import logging
import sys
from psycopg2.extras import RealDictCursor, register_default_jsonb, Json

# Configuration
# Default to XAI API Key if present, otherwise use generic or fail
API_KEY = os.getenv("XAI_API_KEY") 
DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

# Client Configuration
# Initialize with default, can be overridden in main
if API_KEY:
    client = OpenAI(api_key=API_KEY, base_url="https://api.x.ai/v1")
else:
    client = None # Will init in main or error

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("grok_fleet_debug.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

def get_db_connection():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    # Register global JSONB adapter for this connection
    register_default_jsonb(conn_or_curs=conn, globally=True)
    return conn

def fetch_and_claim_case(worker_id, conn, year=None, force=False, target_ids=None, en_banc_only=False, start_year=None, end_year=None, ascending=False, exclude_ids=None, model_name=None, fix_gemini_3=False, start_date=None, end_date=None, smart_backfill=False, max_pages=None, metadata_backfill=False, retry_blocked=False, seek_and_fill=False, fill_empty=False, doctrinal_only=False):

    """
    Phase 1: Connect, Fetch, Claim (Mark as PROCESSING), Disconnect.
    Returns: (case_id, content, case_number) or None
    """
    # conn passed from argument
    cur = conn.cursor()
    
    try:
        # Build Query
        query = """
            SELECT id, full_text_md, case_number 
            FROM sc_decided_cases 
            WHERE full_text_md IS NOT NULL 
              AND full_text_md != '' 
        """
        
        params = []

        # --- NEW: Fill Empty Mode (Strict) ---
        conditions = []
        if fill_empty:
             # Target: BLOCKED_SAFETY OR (Digested but missing Facts)
             conditions.append("(digest_significance = 'BLOCKED_SAFETY' OR (ai_model IS NOT NULL AND digest_facts IS NULL))")
             
        # ... logic continues below ...

        if start_date and end_date:
             query += " AND date >= %s AND date <= %s"
             params.append(start_date)
             params.append(end_date)
        
        if max_pages:
            # Approx 3000 chars per page
            max_chars = max_pages * 3000
            query += " AND LENGTH(full_text_md) <= %s"
            params.append(max_chars)

        if force:
            pass # No extra constraint
        elif smart_backfill:
             query += """
               AND (
                   digest_facts IS NULL OR digest_facts = '' OR
                   digest_issues IS NULL OR digest_issues = '' OR
                   digest_ruling IS NULL OR digest_ruling = '' OR
                   digest_significance IS NULL OR digest_significance = '' OR
                   digest_significance = 'Unknown' OR
                   
                   digest_ratio IS NULL OR digest_ratio = '' OR
                   keywords IS NULL OR 
                   legal_concepts IS NULL OR 
                   flashcards IS NULL OR 
                   spoken_script IS NULL OR spoken_script = '' OR
                   cited_cases IS NULL OR 
                   statutes_involved IS NULL
               )
             """
        
        elif fix_gemini_3:
             # Check for cases processed by Gemini 3 if needed
             query += " AND ai_model LIKE %s"
             params.append('gemini-3%')
             pass
        elif metadata_backfill:
             # METADATA REPAIR MODE
             query += """
               AND (
                 short_title IS NULL OR short_title = '' OR
                 date IS NULL OR
                 division IS NULL OR division = '' OR
                 document_type IS NULL OR document_type = ''
               )
             """
        elif seek_and_fill:
             # SEEK AND FILL STRATEGY (SIMPLIFIED)
             query += """
               AND (
                   digest_facts IS NULL OR digest_facts = '' OR
                   digest_issues IS NULL OR digest_issues = '' OR
                   digest_ruling IS NULL OR digest_ruling = '' OR
                   digest_significance IS NULL OR digest_significance = '' OR
                   
                   digest_ratio IS NULL OR digest_ratio = '' OR
                   keywords IS NULL OR 
                   legal_concepts IS NULL OR 
                   flashcards IS NULL OR 
                   spoken_script IS NULL OR spoken_script = '' OR
                   cited_cases IS NULL OR 
                   statutes_involved IS NULL
               )
             """

        elif not force:
             # Standard "Fill Empty" mode
             query += """
                AND (
                  digest_facts IS NULL OR digest_facts = '' OR
                  digest_issues IS NULL OR digest_issues = '' OR
                  digest_ruling IS NULL OR digest_ruling = '' OR
                  digest_significance IS NULL OR digest_significance = '' OR
                  digest_significance = 'Unknown'
                )
              """

        # Exclude cases currently being processed by other workers or blocked
        if target_ids:
             pass 
        elif retry_blocked:
             query += " AND digest_significance = 'BLOCKED_SAFETY'"
        else:
             query += " AND (digest_significance IS NULL OR (digest_significance NOT LIKE '%%PROCESSING%%' AND digest_significance != 'BLOCKED_SAFETY'))"
        
        if target_ids:
            logging.info(f"DEBUG: target_ids received: {target_ids}")
            # Targeted Mode: Only process these IDs
            # Convert list of string IDs to integers for safety
            safe_ids = [int(x) for x in target_ids if x.isdigit()]
            if safe_ids:
                placeholders = ','.join(['%s'] * len(safe_ids))
                query += f" AND id IN ({placeholders})"
                params.extend(safe_ids)
            else:
                 return None
        
        if exclude_ids:
             safe_exclude = [int(x) for x in exclude_ids if isinstance(x, (int, str)) and str(x).isdigit()]
             if safe_exclude:
                 placeholders_ex = ','.join(['%s'] * len(safe_exclude))
                 query += f" AND id NOT IN ({placeholders_ex})"
                 params.extend(safe_exclude)

        if doctrinal_only:
            query += " AND is_doctrinal = TRUE"
            
        if year:
            query += " AND EXTRACT(YEAR FROM date) = %s"
            params.append(year)
            
        if en_banc_only:
            query += " AND substring(full_text_md from 1 for 2000) ILIKE '%%EN BANC%%'"
            
        if start_year:
            query += " AND EXTRACT(YEAR FROM date) >= %s"
            params.append(start_year)
            
        if end_year:
            query += " AND EXTRACT(YEAR FROM date) <= %s"
            params.append(end_year)
            
        # Determine Sort Order
        if ascending:
             query += " ORDER BY date ASC LIMIT 1 FOR UPDATE SKIP LOCKED"
        else:
             query += " ORDER BY is_doctrinal DESC, date DESC LIMIT 1 FOR UPDATE SKIP LOCKED"

        cur.execute(query, tuple(params))
        case = cur.fetchone()
        
        if not case:
            # conn.close() # Managed externally
            return None
            
        case_id = case[0]
        logging.info(f"Claiming Case ID {case_id}...")
        
        # CLAIM THE CASE: Mark as PROCESSING
        cur.execute("UPDATE sc_decided_cases SET digest_significance = 'PROCESSING' WHERE id = %s", (case_id,))
        conn.commit()
        
        return case
        
    except Exception as e:
        logging.error(f"Error fetching case: {e}")
        conn.rollback()
        return None
    finally:
        pass

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
                if stack:
                    if stack[-1] == char:
                        stack.pop()
    
    if is_string:
        json_str += '"'
    
    json_str = json_str.rstrip()
    if json_str.endswith(','):
        json_str = json_str[:-1]

    while stack:
        closer = stack.pop()
        json_str += closer
        
    return json_str

def normalize_ponente(ponente):
    """
    Normalize ponente name to standard format: "LASTNAME, J.:"
    """
    if not ponente or not isinstance(ponente, str):
        return None
    
    ponente = ponente.strip()
    if not ponente:
        return None
    
    if ponente.isupper() and ', J.:' in ponente:
        return ponente
    
    lastname = None
    
    if ', J' in ponente.upper():
        lastname = ponente.split(',')[0].strip()
    elif ' ' in ponente and ',' not in ponente:
        parts = ponente.split()
        lastname = parts[-1]
    else:
        lastname = ponente
    
    if lastname:
        lastname = lastname.rstrip('.:').strip()
        return f"{lastname.upper()}, J.:"
    
    return None

def save_digest_result(case_id, full_text, data, significance, conn, model_name=None, smart_backfill=False):
    cur = conn.cursor()
    try:
        do_overwrite = True
        
        def ensure_json(obj):
            if isinstance(obj, (dict, list)):
                return json.dumps(obj)
            return obj if obj else None

        if smart_backfill:
             do_overwrite = False
             logging.info(f"Smart Backfill: Preserving existing data (Partial Update) for Case {case_id}")

        reasoning = data.get('classification_reasoning') or ""
        narrative = data.get('significance_narrative') or data.get('digest_significance') or ""
        
        full_significance = ""
        if reasoning:
            full_significance += f"**Reasoning:**\n{reasoning}\n\n"
        if narrative:
            full_significance += f"{narrative}"
            
        if not full_significance.strip():
            full_significance = significance 
        else:
            full_significance = full_significance.strip()
            
        significance = full_significance

        raw_ponente = data.get('ponente')
        normalized_ponente = normalize_ponente(raw_ponente) if raw_ponente else None

        if not do_overwrite:
            # CONDITIONAL UPDATE
            cur.execute("""
                UPDATE sc_decided_cases 
                SET 
                    case_number = COALESCE(case_number, %s),
                    date = COALESCE(date, %s),
                    short_title = COALESCE(short_title, %s),
                    division = COALESCE(division, %s),
                    ponente = COALESCE(ponente, %s),
                    document_type = COALESCE(document_type, %s),
                    subject = COALESCE(subject, %s),
                    
                    digest_facts = COALESCE(digest_facts, %s),
                    digest_issues = COALESCE(digest_issues, %s),
                    digest_ruling = COALESCE(digest_ruling, %s),
                    digest_ratio = COALESCE(digest_ratio, %s),
                    digest_significance = COALESCE(NULLIF(digest_significance, 'PROCESSING'), %s),
                    significance_category = COALESCE(significance_category, %s),
                    keywords = COALESCE(keywords, %s),
                    timeline = COALESCE(timeline, %s),
                    legal_concepts = COALESCE(legal_concepts, %s),
                    flashcards = COALESCE(flashcards, %s),
                    spoken_script = COALESCE(spoken_script, %s),
                    main_doctrine = COALESCE(main_doctrine, %s),
                    secondary_rulings = COALESCE(secondary_rulings, %s),
                    cited_cases = COALESCE(cited_cases, %s),
                    statutes_involved = COALESCE(statutes_involved, %s),
                    separate_opinions = COALESCE(separate_opinions, %s),

                    updated_at = NOW()
                WHERE id = %s
            """, (
                ensure_json(data.get('case_number')),
                data.get('date'),
                data.get('short_title').strip().strip('*').strip('_').strip() if data.get('short_title') else None,
                ensure_json(data.get('court_division')),
                ensure_json(normalized_ponente),
                ensure_json(data.get('document_type')),
                ensure_json(data.get('subject')),

                ensure_json(data.get('digest_facts') or data.get('facts')),
                ensure_json(data.get('digest_issues') or data.get('issue')),
                ensure_json(data.get('digest_ruling') or data.get('ruling')),
                ensure_json(data.get('digest_ratio') or data.get('ratio')),
                significance, 
                ensure_json(data.get('classification')),
                ensure_json(data.get('keywords', [])),
                ensure_json(data.get('timeline', [])),
                ensure_json(data.get('legal_concepts', [])),
                ensure_json(data.get('flashcards', [])),
                ensure_json(data.get('spoken_script', '')),
                ensure_json(data.get('main_doctrine')),
                ensure_json(data.get('secondary_rulings', [])),
                ensure_json(data.get('cited_cases', [])),
                ensure_json(data.get('statutes_involved', [])),
                ensure_json(data.get('separate_opinions', [])),
                
                case_id
            ))
        else:
            # STANDARD OVERWRITE
            cur.execute("""
                UPDATE sc_decided_cases 
                SET digest_facts = %s, 
                    digest_issues = %s, 
                    digest_ruling = %s, 
                    digest_ratio = %s, 
                    digest_significance = %s, 
                    significance_category = %s,
                    keywords = %s,
                    timeline = %s,
                    legal_concepts = %s,
                    flashcards = %s,
                    spoken_script = %s,
                    subject = %s,
                    main_doctrine = %s,
                    secondary_rulings = %s,
                    cited_cases = %s,
                    statutes_involved = %s,
                    separate_opinions = %s,
                    document_type = %s,
                    case_number = %s,
                    date = %s,
                    short_title = %s,
                    division = %s,
                    ponente = %s,
                    ai_model = %s,
                    is_doctrinal = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (
                ensure_json(data.get('digest_facts') or data.get('facts')),
                ensure_json(data.get('digest_issues') or data.get('issue')),
                ensure_json(data.get('digest_ruling') or data.get('ruling')),
                ensure_json(data.get('digest_ratio') or data.get('ratio')),
                significance,
                ensure_json(data.get('significance_category')),
                ensure_json(data.get('keywords', [])),
                ensure_json(data.get('timeline', [])),
                ensure_json(data.get('legal_concepts', [])),
                ensure_json(data.get('flashcards', [])),
                ensure_json(data.get('spoken_script', '')),
                ensure_json(data.get('subject')),
                ensure_json(data.get('main_doctrine')),
                ensure_json(data.get('secondary_rulings', [])),
                ensure_json(data.get('cited_cases', [])),
                ensure_json(data.get('statutes_involved', [])),
                ensure_json(data.get('separate_opinions', [])),
                ensure_json(data.get('document_type')),
                ensure_json(data.get('case_number')),
                data.get('date'),
                data.get('short_title').strip().strip('*').strip('_').strip() if data.get('short_title') else None,
                ensure_json(data.get('court_division')),
                ensure_json(normalized_ponente),
                model_name,
                data.get('is_doctrinal', False),
                case_id
            ))

        if significance and significance != 'PROCESSING':
             logging.info(f"debug: aggressively forcing update of digest_significance for {case_id}")
             cur.execute("UPDATE sc_decided_cases SET digest_significance = %s WHERE id = %s", (significance, case_id))

        conn.commit()
    except Exception as e:
        logging.error(f"Error saving digest: {e}")
        with open(f"save_error_{case_id}.txt", "w") as f:
            f.write(str(e))
        conn.rollback()
    finally:
        pass

def generate_digest_batch(limit=10, doctrinal_only=False, year=None, force=False, target_ids=None, en_banc_only=False, start_year=None, end_year=None, ascending=False, exclude_ids=None, model_name=None, fix_gemini_3=False, start_date=None, end_date=None, smart_backfill=False, max_pages=None, metadata_backfill=False, retry_blocked=False, seek_and_fill=False, fill_empty=False):
    
    conn = get_db_connection()

    processed_count = 0
    if exclude_ids is None:
        exclude_ids = []
    
    for _ in range(limit):
        case = fetch_and_claim_case(
            worker_id=os.getpid(),
            conn=conn,
            doctrinal_only=doctrinal_only,
            year=year,
            force=force,
            target_ids=target_ids,
            en_banc_only=en_banc_only,
            start_year=start_year,
            end_year=end_year,
            ascending=ascending,
            exclude_ids=exclude_ids,
            model_name=model_name,
            fix_gemini_3=fix_gemini_3,
            start_date=start_date,
            end_date=end_date,
            smart_backfill=smart_backfill,
            max_pages=max_pages,
            metadata_backfill=metadata_backfill,
            retry_blocked=retry_blocked,
            seek_and_fill=seek_and_fill,
            fill_empty=fill_empty
        )

        if not case:
            logging.info("No more cases found.")
            break
            
        case_id = case[0]
        content = case[1]
        
        try:
            logging.info(f"Processing content for Case ID {case_id} using {model_name} (Grok API)...")
            
            safe_content = content
            
            # --- PROMPT (UPDATED FOR GROK: FORCE ELABORATION) ---
            sys_instruction = """ROLE: You are an Expert Legal Analyst and Senior Bar Reviewer for Philippine Jurisprudence.
YOUR GOAL: Create valid JSON digests that are EXHAUSTIVE, DETAILED, AND ACADEMICALLY RIGOROUS. 
CRITICAL INSTRUCTION: DO NOT SUMMARIZE for brevity. Summarize for DEPTH. Conciseness is NOT the goal. The goal is complete legal analysis sufficient for a Bar Exam top-notcher study material.
TONE: Formal, clinical, authoritative. Use standard legal terminology."""

            prompt = f"""
            **CRITICAL RULE: ELABORATE, DO NOT CONDENSE.**
            - **Grok Specific Instruction:** You tend to be too concise. FORCE yourself to write detailed paragraphs.
            - **Facts:** Must be detailed enough to tell the full story (Antecedents -> Procedure -> Arguments).
            - **Issues:** Extract the specific legal questions raised, derived from the assignment of errors or the Court's statement of issues. Format as a bulleted list.
            - **Ruling/Ratio:** Must explain the "WHY" in depth. Avoid one-sentence answers.
            - **Doctrines/Main Doctrine:** Summarize the core jurisprudence in a minimum of 5 sentences. Focus on the rule and its application, but avoid excessive verbosity.
            - **Separate Opinions:** DO NOT read or summarize the text of separate opinions. Only extract the VOTE (concur/dissent) from the signatories section of the main decision.

            **SIGNIFICANCE CLASSIFICATION HIERARCHY & CONSTRAINTS**

            **REITERATION**: The Court applies settled SC doctrine.
            *CRITICAL: Reversing a Court of Appeals or Trial Court decision based on established SC precedent is a REITERATION, not a Reversal of doctrine.*

            **NEW DOCTRINE**: The Court establishes a novel rule, principle, or interpretation for a "case of first impression" where no prior SC precedent existed.

            **MODIFICATION**: The SC explicitly adjusts, narrows, or expands an EXISTING SC DOCTRINE.
            *WARNING: Modifying a criminal penalty (e.g., from Reclusion Perpetua to 12 years) or adjusting monetary damages is REITERATION, not Modification of doctrine.*

            **ABANDONMENT**: The SC explicitly overturns or departs from an EXISTING SC DOCTRINE.
            The SC explicitly overturns an existing doctrine in a new and different case (e.g., Carpio-Morales abandoning the Condonation Doctrine). This sets a new precedent for the entire legal system.
            *LOGIC: This requires the Court to state that a previous SC ruling is no longer "good law."*

            **REVERSAL (via Resolution)**: The SC reverses its own prior decision in the same case via a Motion for Reconsideration (MR).

            **THOUGHT PROCESS (INTERNAL MONOLOGUE)**
            Before providing the output, you must:
            1. Identify the Ratio Decidendi.
            2. Check if the Court cites a "Lead Case."
            3. Determine if the Court is "Clarifying" (Modification) or "Following" (Reiteration).
            4. Check for False Positives: Did the Court merely reverse the CA? If yes, classify as REITERATION.

            **PRECISION GUARDRAILS**
            - **Outcome vs. Doctrine**: If the SC reverses its own decision on MR, classify as REVERSAL. If the SC tells the public "the old rule from 1990 is no longer good law," classify as ABANDONMENT.
            - **Lower Court Reversals**: If the SC reverses the Court of Appeals, this is usually REITERATION unless they state they are creating a new rule.
            - **Penalty/Award Changes**: Changing "Death" to "Life Imprisonment" based on existing law is REITERATION.

            **INPUT TEXT:**
            {safe_content}

            **OUTPUT FORMAT (JSON):**
            Return ONLY valid JSON with this structure:
            {{
                "full_title": "...",
                "short_title": "...",
                "significance_category": "REITERATION | NEW DOCTRINE | MODIFICATION | ABANDONMENT | REVERSAL", 
                "classification": "REITERATION | NEW DOCTRINE | MODIFICATION | ABANDONMENT | REVERSAL",
                "classification_reasoning": "Evidence and quote from the text justifying the classification...",
                "significance_narrative": "Explain the nuances and significance to Bar examinees. Avoid the word 'trap'. Use phrases like 'examinees may misappreciate'. Do not just repeat the ruling.",
                "relevant_doctrine": "...",
                "statutes_involved": [
                    {{"law": "Family Code", "provision": "Article 36"}},
                    {{"law": "Rules of Court", "provision": "Rule 65, Sec. 1"}}
                ],
                "main_doctrine": "[Summary of the Doctrine - Minimum 5 sentences.] ...",
                "keywords": ["Keyword1", "Keyword2"],
                "court_division": "En Banc | Third Division",
                "ponente": "...",
                "document_type": "Decision | Resolution",
                "subject": "Political Law | Labor Law | Civil Law | Taxation Law | Commercial Law | Criminal Law | Remedial Law | Legal Ethics. (Pick ONLY from these 8. Do NOT invent subtitles like 'Constitutional Law'.)",
                "date": "YYYY-MM-DD",
                "case_number": "...",
                
                "digest_facts": "1. **The Antecedents:** [DETAILED NARRATIVE OF EVENTS - Min. 5 sentences] ... \\n\\n 2. **Procedural History:** [DETAILED LOWER COURT ACTION] ... \\n\\n 3. **The Petition:** [ARGUMENTS] ...",
                "issue": "* Issue 1\\n* Issue 2",
                "ruling": "...",
                "ratio": "* **On Issue 1:** [EXTENSIVE REASONING - Minimum 5-7 sentences. Citing specific laws and precedents...]\\n* **On Issue 2:** [EXTENSIVE REASONING...]",
                
                "timeline": [
                    {{"date": "2020-01-01", "event": "Incident occurred..."}},
                    {{"date": null, "event": "Complaint filed..."}}
                ],
                "cited_cases": [
                    {{"title": "Short Title (G.R. No. 000000)", "relationship": "Applied", "elaboration": "2-3 sentences explaining the application..."}},
                    {{"title": "Short Title (G.R. No. 111111)", "relationship": "Distinguished", "elaboration": "2-3 sentences explaining the distinction..."}}
                ],
                "legal_concepts": [
                    {{"term": "Political Question", "definition": "those questions which... [citing Article X, Section Y]"}},
                    {{"term": "Buyer in Good Faith", "definition": "... [citing Case Title]"}}
                ],
                "flashcards": [
                    {{"type": "Concept", "q": "...", "a": "..."}},
                    {{"type": "Distinction", "q": "...", "a": "..."}},
                    {{"type": "Scenario", "q": "...", "a": "..."}}
                ],
                "spoken_script": "A 1-minute script: 'Hi! Today we are discussing [Case]. The main takeaway is...'",
                "separate_opinions": [
                    "Justice Carpio dissents",
                    "Justice Leonen concurs"
                ],
                "secondary_rulings": [
                    {{"topic": "Quantum of Proof", "ruling": "..."}}
                ]
            }}
            """
            
            response = None
            used_model = model_name
            
            logging.info(f"Attempting digest with {model_name} (XAI/Grok)...")
            try:
                # USING OPENAI CLIENT FOR GROK
                chat_completion = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": sys_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                )
                
                response_text = chat_completion.choices[0].message.content
                
            except Exception as e:
                logging.error(f"Model {model_name} Error: {e}")
                continue
            
            if not response_text:
                 logging.error(f"Empty response for Case {case_id}.")
                 continue
            
            # Parse JSON
            try:
                clean_text = response_text.replace('```json', '').replace('```', '').strip()
                data = json.loads(clean_text)
            except ValueError:
                logging.warning(f"JSON Parsing failed. Attempting repair for Case {case_id}...")
                try:
                     repaired_text = repair_truncated_json(clean_text)
                     data = json.loads(repaired_text)
                     logging.info(f"JSON Repair SUCCESS for Case {case_id}")
                except Exception as repair_err:
                     logging.error(f"JSON Repair FAILED for Case {case_id}: {repair_err}")
                     with open(f"failed_digest_{case_id}.txt", "w", encoding="utf-8") as f:
                        f.write(response_text)
                     continue
            
            if isinstance(data, list):
                if len(data) > 0:
                    data = data[0]
                else:
                    continue
            
            # Construction
            classification = data.get('classification') or data.get('significance_category', 'REITERATION')
            narrative = data.get('significance_narrative', '') 
            rel_doctrine = data.get('relevant_doctrine', '')
            reasoning = data.get('classification_reasoning', '')
            
            data['significance_category'] = classification 
            
            significance_text = f"[{classification}]\n\n**Reasoning:** {reasoning}\n\n{narrative}"
            if rel_doctrine:
                significance_text += f"\n\n**Relevant Doctrine:** {rel_doctrine}"

            effective_smart_backfill = smart_backfill or seek_and_fill
            
            save_digest_result(case_id, content, data, significance_text, conn=conn, model_name=used_model, smart_backfill=effective_smart_backfill)
            
            processed_count += 1
            exclude_ids.append(case_id)
            time.sleep(1)
            
        except Exception as e:
            logging.error(f"Failed to process Case ID {case_id}: {e}")
            if "429" in str(e) or "quota" in str(e).lower():
                logging.warning("Hit Rate Limit/Quota. Sleeping for 90s...")
                time.sleep(90)
            
            try:
                conn.rollback() # Rollback any pending trans
                cur = conn.cursor()
                cur.execute("UPDATE sc_decided_cases SET digest_significance = NULL WHERE id = %s AND digest_significance = 'PROCESSING'", (case_id,))
                conn.commit()
                logging.info(f"Reset lock for Case ID {case_id}")
            except Exception as reset_error:
                logging.error(f"Failed to reset lock for Case ID {case_id}: {reset_error}")

    conn.close()
    return processed_count

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10, help="Number of cases per batch")
    parser.add_argument("--continuous", action="store_true", help="Run continuously until no cases left")
    parser.add_argument("--doctrinal-only", action="store_true", help="Only digest cases marked as doctrinal")
    parser.add_argument("--year", type=int, help="Filter by year (e.g. 2024)")
    parser.add_argument("--exit-on-finish", action="store_true", help="Exit if no cases found in batch")
    parser.add_argument("--force", action="store_true", help="Force re-digest even if already processed")
    parser.add_argument("--target-ids", type=str, help="Comma-separated list of IDs to target specifically")
    parser.add_argument("--target-ids-file", type=str, help="Path to text file containing comma-separated IDs")
    parser.add_argument("--en-banc-only", action="store_true", help="Only process EN BANC cases")
    parser.add_argument("--start-year", type=int, help="Start year filter (inclusive)")
    parser.add_argument("--end-year", type=int, help="End year filter (inclusive)")
    parser.add_argument("--start-date", type=str, help="Start date filter (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date filter (YYYY-MM-DD)")
    parser.add_argument("--model", type=str, default="grok-beta", help="Grok Model to use")
    parser.add_argument("--ascending", action="store_true", help="Process from oldest to newest")
    parser.add_argument("--fix-gemini-3", action="store_true", help="Backfill mode for Gemini 3 cases")
    parser.add_argument("--smart-backfill", action="store_true", help="Smart Backfill")
    parser.add_argument("--metadata-backfill", action="store_true", help="Metadata Backfill")
    parser.add_argument("--seek-and-fill", action="store_true", help="Seek any empty fields")
    parser.add_argument("--retry-blocked", action="store_true", help="Target BLOCKED_SAFETY cases")
    parser.add_argument("--max-pages", type=int, help="Max length in pages")
    parser.add_argument("--fill-empty", action="store_true", help="Target only cases with empty digest fields")
    parser.add_argument("--api-key", type=str, help="Custom XAI API key")

    args = parser.parse_args()
    
    # Configure Client from Args if provided
    if args.api_key:
        logging.info(f"Using Custom API Key for this run.")
        client = OpenAI(api_key=args.api_key, base_url="https://api.x.ai/v1")
    elif not client:
        logging.error("No API Key provided (env XAI_API_KEY or --api-key). Exiting.")
        sys.exit(1)
    
    logging.info(f"Using Model: {args.model}")
    
    target_ids_list = None
    if args.target_ids:
        target_ids_list = [x.strip() for x in args.target_ids.split(',')]
        
    if args.target_ids_file:
        if not target_ids_list:
            target_ids_list = []
        try:
            with open(args.target_ids_file, 'r') as f:
                content = f.read()
                file_ids = content.replace('\n', ',').split(',')
                target_ids_list.extend([x.strip() for x in file_ids if x.strip()])
        except Exception as e:
            logging.error(f"Failed to read target IDs file: {e}")

    if target_ids_list:
        args.limit = len(target_ids_list)

    if args.continuous:
        logging.info("Starting CONTINUOUS digestion mode (Connect-Write-Disconnect)...")
        while True:
            try:
                processed = generate_digest_batch(
                    limit=args.limit, 
                    doctrinal_only=args.doctrinal_only, 
                    year=args.year, 
                    force=args.force,
                    target_ids=target_ids_list,
                    en_banc_only=args.en_banc_only,
                    start_year=args.start_year,
                    end_year=args.end_year,
                    ascending=args.ascending,
                    model_name=args.model,
                    fix_gemini_3=args.fix_gemini_3,
                    start_date=args.start_date,
                    end_date=args.end_date,
                    max_pages=args.max_pages,
                    metadata_backfill=args.metadata_backfill,
                    retry_blocked=args.retry_blocked,
                    seek_and_fill=args.seek_and_fill,
                    fill_empty=args.fill_empty
                )
                
                if processed == 0:
                    logging.info("No cases processed in this batch.")
                    if args.exit_on_finish:
                        sys.exit(100)
                    time.sleep(5)
                
            except Exception as e:
                logging.error(f"Loop error: {e}")
                time.sleep(5)
    else:
        # One-off run
        generate_digest_batch(
            limit=args.limit, 
            doctrinal_only=args.doctrinal_only, 
            year=args.year, 
            force=args.force,
            target_ids=target_ids_list,
            en_banc_only=args.en_banc_only,
            start_year=args.start_year,
            end_year=args.end_year,
            ascending=args.ascending,
            model_name=args.model,
            fix_gemini_3=args.fix_gemini_3,
            start_date=args.start_date,
            end_date=args.end_date,
            smart_backfill=args.smart_backfill,
            max_pages=args.max_pages,
            retry_blocked=args.retry_blocked,
            seek_and_fill=args.seek_and_fill,
            fill_empty=args.fill_empty
        )
