import os
import json
import re
import psycopg2
from google import genai
from google.genai import types
import time
import logging
import sys
from pathlib import Path
from psycopg2.extras import RealDictCursor, register_default_jsonb, Json

# Add scripts directory to path for imports
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from load_local_settings_env import load_api_local_settings_into_environ

# Configuration
load_api_local_settings_into_environ(Path(__file__).resolve().parent.parent)

API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

VERTEX_PROJECT = os.getenv("VERTEX_AI_PROJECT")
VERTEX_LOCATION = os.getenv("VERTEX_AI_LOCATION", "us-central1")

# Client Configuration
if VERTEX_PROJECT:
    logging.info(f"Using Vertex AI Endpoint (project={VERTEX_PROJECT}, location={VERTEX_LOCATION})")
    client = genai.Client(vertexai=True, project=VERTEX_PROJECT, location=VERTEX_LOCATION)
else:
    client = genai.Client(api_key=API_KEY)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fleet_debug.log"),
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
             # SMART BACKFILL (UNIFIED STRATEGY)
             # Target: ANY case with MISSING or UNKNOWN fields.
             # Logic merged from 'Seek and Fill' as per user request to drop model classifications.
             
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
             query += " AND ai_model LIKE %s"
             params.append('gemini-3%')
             # ... (checks for missing fields) ...
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
             # Target: ANY Missing Field. Ignore Model Classification.
             
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
                   statutes_involved IS NULL OR
                   ai_model IS NULL
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
        # Exclude cases currently being processed by other workers or blocked
        # EXCEPTION: If target_ids are provided, we ignore blocked status to allow force-retry
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
                 # If target_ids provided but empty/invalid, return None to avoid processing random cases
                 return None
        
        if exclude_ids:
             # Exclude IDs we have already processed in this session (critical for --force loops)
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
             # Check for 'EN BANC' in the first 2000 characters
            query += " AND substring(full_text_md from 1 for 2000) ILIKE '%%EN BANC%%'"
            
        if start_year:
            query += " AND EXTRACT(YEAR FROM date) >= %s"
            params.append(start_year)
            
        if end_year:
            query += " AND EXTRACT(YEAR FROM date) <= %s"
            params.append(end_year)
            
        # Determine Sort Order
        if ascending:
             # Oldest to Newest
             query += " ORDER BY date ASC LIMIT 1 FOR UPDATE SKIP LOCKED"
        else:
             # Doctrinal First, then Newest to Oldest (Default)
             query += " ORDER BY is_doctrinal DESC, date DESC LIMIT 1 FOR UPDATE SKIP LOCKED"

        cur.execute(query, tuple(params))
        case = cur.fetchone()

        if not case:
            # Caller owns connection lifecycle (e.g. generate_digest_batch loop).
            return None

        case_id = case[0]
        logging.info(f"Claiming Case ID {case_id}...")
        
        # CLAIM THE CASE: Mark as PROCESSING so others don't grab it while we are disconnected
        cur.execute("UPDATE sc_decided_cases SET digest_significance = 'PROCESSING' WHERE id = %s", (case_id,))
        conn.commit()
        
        return case
        
    except Exception as e:
        logging.error(f"Error fetching case: {e}")
        conn.rollback()
        return None
    finally:
        # Do not close conn here, it is persistent
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
                # Attempt to pop. If stack empty or mismatch, ignore (could be malformed from start)
                if stack:
                    if stack[-1] == char:
                        stack.pop()
    
    # Output is truncated. 
    # If inside string, close it.
    if is_string:
        json_str += '"'
    
    # If it ends with a key (e.g. "q"), it will fail parse because of missing : and value.
    # We look for a pattern like "key" at the end of the string (after stripping whitespace).
    json_str_trimmed = json_str.rstrip()
    if json_str_trimmed.endswith('"'):
        # Primitive check: if the last brace/bracket was { or [ and we just closed a string
        # we might need a colon and a value. 
        # More robust: check if the string before the last quote was preceded by { or ,
        content_around = json_str_trimmed[-20:]
        if re.search(r'[\{\,]\s*"[^"]+"$', json_str_trimmed):
            json_str += ': "TRUNCATED"'
    
    # Remove trailing comma if present (whitespace safe)
    json_str = json_str.rstrip()
    if json_str.endswith(','):
        json_str = json_str[:-1]

    # Close remaining structures
    while stack:
        closer = stack.pop()
        json_str += closer
        
    return json_str

def preprocess_json_string(json_str):
    """Aggressively remove trailing commas and heal missing quotes on common keys."""
    # 1. Remove trailing commas
    json_str = re.sub(r',\s*\]', ']', json_str)
    json_str = re.sub(r',\s*\}', '}', json_str)
    
    # 2. Heal Missing Quotes on common string keys (q, a, term, definition)
    # Simple strategy: If "key": follows with text and ends with newline/comma/brace 
    # and doesn't have quotes, wrap it.
    for key in ['q', 'a', 'term', 'definition', 'short_title']:
        pattern = r'("' + key + r'":\s*)([a-zA-Z0-9][^,\}\n]+)(?=\s*[,\}\n])'
        json_str = re.sub(pattern, r'\1"\2"', json_str)

    return json_str

def normalize_ponente(ponente):
    """
    Normalize ponente name to standard format: "LASTNAME, J.:"
    Examples:
        "Antonio T. Carpio" -> "CARPIO, J.:"
        "carpio, j." -> "CARPIO, J.:"
        "CARPIO, J" -> "CARPIO, J.:"
        "Carpio" -> "CARPIO, J.:"
    """
    if not ponente or not isinstance(ponente, str):
        return None
    
    # Clean up the input
    ponente = ponente.strip()
    if not ponente:
        return None
    
    # Already in correct format (uppercase with J.:)
    if ponente.isupper() and ', J.:' in ponente:
        return ponente
    
    # Extract the lastname
    lastname = None
    
    # Pattern 1: "LASTNAME, J." or "LASTNAME, J.:" or "Lastname, J."
    if ', J' in ponente.upper():
        lastname = ponente.split(',')[0].strip()
    
    # Pattern 2: "Firstname Middlename Lastname" (full name format)
    elif ' ' in ponente and ',' not in ponente:
        # Take the last word as lastname
        parts = ponente.split()
        lastname = parts[-1]
    
    # Pattern 3: Just lastname alone
    else:
        lastname = ponente
    
    if lastname:
        # Remove any trailing periods or colons
        lastname = lastname.rstrip('.:').strip()
        # Convert to uppercase and add standard suffix
        return f"{lastname.upper()}, J.:"
    
    return None

def save_digest_result(case_id, full_text, data, significance, conn, model_name=None, smart_backfill=False):
    # conn passed from argument
    cur = conn.cursor()
    try:
        # SMART BACKFILL LOGIC (SIMPLIFIED):
        # If smart_backfill rule is active:
        # ALWAYS PRESERVE existing data. Only fill holes.
        # Rationale: User wants to "seek and fill" regardless of previous model.
        
        do_overwrite = True
        
        def ensure_json(obj):
            if isinstance(obj, (dict, list)):
                return json.dumps(obj)
            return obj if obj else None

        if smart_backfill:
             do_overwrite = False
             logging.info(f"Smart Backfill: Preserving existing data (Partial Update) for Case {case_id}")

        # --- NEW CONCATENATION LOGIC ---
        # Combine Reasoning + Bar Traps Audit into one 'digest_significance' blob
        reasoning = data.get('classification_reasoning') or ""
        narrative = data.get('significance_narrative') or data.get('digest_significance') or ""
        
        full_significance = ""
        if reasoning:
            full_significance += f"**Reasoning:**\n{reasoning}\n\n"
        if narrative:
            full_significance += f"{narrative}"
            
        # If both are empty, fallback to whatever 'significance' arg was passed (which might be raw or empty)
        if not full_significance.strip():
            full_significance = significance 
        else:
            full_significance = full_significance.strip()
            
        # Override the 'significance' variable to use our combined version
        significance = full_significance
        # -------------------------------

        # Normalize ponente name to standard format
        raw_ponente = data.get('ponente')
        normalized_ponente = normalize_ponente(raw_ponente) if raw_ponente else None

        if not do_overwrite:
            # CONDITIONAL UPDATE (Only fill holes + Metadata)
            cur.execute("""
                UPDATE sc_decided_cases 
                SET 
                    -- Metadata (Always Update if missing)
                    case_number = COALESCE(case_number, %s),
                    date = COALESCE(date, %s),
                    short_title = COALESCE(short_title, %s),
                    division = COALESCE(division, %s),
                    ponente = COALESCE(ponente, %s),
                    document_type = COALESCE(document_type, %s),
                    subject = COALESCE(subject, %s),
                    
                    -- Digest Fields (Fill if NULL)
                    digest_facts = COALESCE(digest_facts, %s),
                    digest_issues = COALESCE(digest_issues, %s),
                    digest_ruling = COALESCE(digest_ruling, %s),
                    digest_ratio = COALESCE(digest_ratio, %s),
                    digest_significance = COALESCE(NULLIF(digest_significance, 'PROCESSING'), %s),
                    significance_category = COALESCE(significance_category, %s),
                    keywords = COALESCE(NULLIF(keywords::text, '[]')::jsonb, %s),
                    timeline = COALESCE(NULLIF(timeline::text, '[]')::jsonb, %s),
                    legal_concepts = COALESCE(NULLIF(legal_concepts::text, '[]')::jsonb, %s),
                    flashcards = COALESCE(NULLIF(flashcards::text, '[]')::jsonb, %s),
                    spoken_script = COALESCE(spoken_script, %s),
                    main_doctrine = COALESCE(main_doctrine, %s),
                    secondary_rulings = COALESCE(NULLIF(secondary_rulings::text, '[]')::jsonb, %s),
                    cited_cases = COALESCE(NULLIF(cited_cases::text, '[]')::jsonb, %s),
                    statutes_involved = COALESCE(NULLIF(statutes_involved::text, '[]')::jsonb, %s),
                    separate_opinions = COALESCE(NULLIF(separate_opinions::text, '[]')::jsonb, %s),
                    ai_model = COALESCE(ai_model, %s),

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
                model_name,
                
                case_id
            ))
        else:
            # STANDARD OVERWRITE UPDATE
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
                significance, # Use the constructed full text
 
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

        # FORCE UPDATE SIGNIFICANCE TO BE ABSOLUTELY SURE
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
        # Do not close conn here
        pass



def _clear_processing_claim(conn, case_id: int) -> None:
    """Release PROCESSING lock when exiting without a successful save_digest_result."""
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE sc_decided_cases SET digest_significance = NULL WHERE id = %s AND digest_significance = 'PROCESSING'",
            (case_id,),
        )
        conn.commit()
    except Exception as e:
        logging.error("Failed to clear PROCESSING for case %s: %s", case_id, e)
        try:
            conn.rollback()
        except Exception:
            pass


def generate_digest_batch(limit=10, doctrinal_only=False, year=None, force=False, target_ids=None, en_banc_only=False, start_year=None, end_year=None, ascending=False, exclude_ids=None, model_name=None, fix_gemini_3=False, start_date=None, end_date=None, smart_backfill=False, max_pages=None, metadata_backfill=False, retry_blocked=False, seek_and_fill=False, fill_empty=False):
    
    conn = get_db_connection()
    # ... (connection check omitted, assuming verify_connection or just proceed) ...
    # Do not close conn here

    processed_count = 0
    
    # Initialize exclude_ids if not provided
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
            # PHASE 2: AI Processing (No DB Connection)
            logging.info(f"Processing content for Case ID {case_id}...")
            
            # Pre-cleaning for prompt
            safe_content = content
            
            prompt = f"""
            **ROLE:**
            Senior Reporter for the Supreme Court of the Philippines. Your objective is to extract a precise, clinical case digest for a professional Bar Review Database.
            **STYLE:**
            Formal, forensic, and objective. Use the exact legal terminology found in Philippine Jurisprudence. 
            **TASK:**
            Distill the provided text into a high-yield digest while maintaining the "Language of the Law."
            **INSTRUCTIONS:**
            1. **Legal Verbatim:** Use the actual words and phrases from the input text (e.g., "treachery," "evident premeditation," "grave abuse of discretion"). Do not sanitize legal terms, as they are essential for Bar Exam preparation.
            2. **Clinical Focus:** Filter out emotional narratives. Retain only the facts necessary to satisfy the elements of the crime or the legal doctrine.
            3. **Safety Protocol:** Only redact or abstract content if it involves the specific names of victims in sensitive cases (e.g., use "AAA" or "The Victim" per RA 9262 protocols), but keep the description of the legal acts intact.
            4. **Separate Opinions (MINIMAL FORMAT - ALL Justices, NO SUMMARIES):** Identify ALL Justices who filed separate opinions. For each, provide ONLY the Justice name and Type. Types: "Dissenting", "Concurring", "Separate Concurring", "Separate Dissenting". Format example: {{"justice": "Leonardo-De Castro, J.", "type": "Dissenting"}}. **CRITICAL: DO NOT include a summary field** - output should be compact with just name + type for each Justice.
 You MUST identify and summarize **ALL** Concurring, Dissenting, Separate Concurring, and Separate Dissenting Opinions found in the text. En Banc cases often have 10+ separate opinions—scan the ENTIRE document thoroughly, including footnotes and signature blocks, to capture every opinion. For the Ponente, identify if they expressed a personal "Separate View" distinct from the majority. The `summary` field for each opinion MUST be populated with at least 3-4 sentences; it cannot be null.

            **INPUT TEXT:**
            {safe_content}
            
            **YOUR GOAL:**
            Analyze the provided legal text and generate a structured, educational JSON digest for Bar Review students.

            **STRICT DATA INTEGRITY RULES:**
            1. **No Hallucinations:** If a specific detail (date, justice, fact) is NOT found in the text, return `null` for strings/dates or an empty array `[]` for lists. Do NOT invent data.
            2. **JSON Safety:** You MUST escape all double quotes (") and control characters (newlines \\n, tabs \\t) within string values to ensure valid JSON parsing.
            3. **Database Compatibility:** Follow ISO formats exactly.
            4. **Structural Alignment:** For every issue listed in "digest_issues", there MUST be a corresponding and clearly labeled bullet point in "digest_ratio" (e.g., "* **On Issue 1:** ...", "* **On Issue 2:** ..."). Do NOT group issues together or skip indices.
            5. **Acronyms & Abbreviations:** You MUST define all acronyms and abbreviations in full upon their first occurrence in the text (e.g., "Sexual Orientation, Gender Identity and Expression, and Sex Characteristics (SOGIESC)"). Subsequent mentions can use the acronym alone. Do NOT use undefined acronyms.
            6. **No "None" Strings:** If a field has no data, use `null` or `[]`. Do not write the literal string "None" or "N/A".

            **YOUR TASKS (Execute in Order):**

            1. **EXTRACT METADATA & STATUTES:**
               - **Document Type:** Identify if this is a [Decision | Resolution | Concurring Opinion | Dissenting Opinion | Separate Opinion].
               - **Short Title (SC 2023 Rule):** Follow the Supreme Court Stylebook (2023). 
                 * **General Rule:** The short title should ideally be the surname of the first party listed in the full title (e.g., "Falcis").
                 * **Exceptions:** If the surname is very common, use the other party's surname. For "People" cases, use the surname of the accused (e.g., "Dela Cruz"). For government agencies, use the acronym (e.g., "COMELEC").
                 * **Usage:** This `short_title` field will be used for citations (e.g., "Falcis v. Civil Registrar General"). Ensure it follows the format "Petitioner v. Respondent" using surnames/acronyms only, sentence case, and "v." instead of "vs.".
               - **Court Body:** En Banc vs. Division.
               - **Ponente:** Justice Name.
               - **Subject:** Identify the primary and secondary subjects. Choose from: [Political, Civil, Commercial, Labor, Criminal, Taxation, Ethics, Remedial]. Provide as "Primary: [Subject]; Secondary: [Subject1, Subject2]". If only one applies, just list it as Primary.
               - **Keywords:** Extract 5-10 specific legal keywords.
               - **Statutes Involved:** Scan for specific laws cited (e.g., "Article 36, Family Code"). Limit to the **Top 5 most relevant** statutes.
               - **Main Doctrine (ELABORATE):** Provide a **comprehensive 3-5 sentence explanation** of the primary legal doctrine established or applied by this case. Explain the rule, its rationale, and its significance for Philippine jurisprudence. Do NOT just state the doctrine—elaborate on its meaning and application.

            2. **JURISPRUDENCE MAPPING (Contextual):**
               - Identify Supreme Court cases cited in the text.
               - **Classify the relationship:** "Applied" or "Distinguished".
               - **Elaboration:** You MUST provide 2-3 sentences explaining EXACTLY how the case was applied or why it was distinguished. Do NOT just list the case.
               - **LIMIT RULES (CRITICAL):**
                 * **Maximum Total:** 10 cited cases.
                 * **Priority - Distinguished Cases:** Include ALL distinguished cases, up to a maximum of 5.
                 * **Applied Cases:** Include ONLY those cases that the Court explicitly emphasized or relied upon as the main precedents. Skip minor citations.
                 * If you have space after Distinguished cases (up to 10 total), add the most important Applied cases.
               - **Constraint:** Ensure the 'elaboration' field in the JSON output is populated.

            3. **TIMELINE GENERATION (For UI Rendering):**
               - Extract key events with dates into a chronological list.
               - Format dates in events as consistently as possible. Use `null` if the entire timeline is missing.

            4. **DIGEST THE CASE (CHRONOLOGICAL):**
               - **Facts Structure:** The "digest_facts" section MUST follow this three-part structure. **CRITICAL:** You MUST insert exactly TWO newline characters (`\n\n`) between each section to ensure they appear as separate paragraphs in the UI. Do NOT run them together.
                 * **The Antecedents:** The underlying events/dispute.
                 * **Procedural History:** The path through lower courts/agencies.
                 * **The Petition** (or **The Appeal**): Specifically describe the procedural vehicle (e.g., Rule 45 petition) and the main arguments raised by the petitioner/appellant to the Supreme Court.
               - **Issues:** Provide a list of ALL issues (Procedural & Substantive) using **BULLET POINTS**.
               - **Ruling:** Final Verdict and Dispositive Portion.
               - **Ratio (POINT-BY-POINT):**
                 - Address every issue using the bullet points from the Issues section.
                 - **Reasoning Requirement:** For each issue, elaborate clearly how the Supreme Court reasoned. Provide a **MINIMUM of 5 sentences** per issue.
                 - **Citation Rule:** Explicitly name referenced cases (e.g., "Applying *Tan-Andal*...").

            5. **SIGNIFICANCE (THE "BAR TRAPS"):**

                 **Step A: Primary Classification**
                 [REITERATION | NEW DOCTRINE | ABANDONMENT | MODIFICATION | CLARIFICATION | REVERSAL]
                 
                 **Classification Definitions:**
                 - **NEW DOCTRINE**: Establishes a new legal principle or rule on a novel issue.
                 - **REITERATION**: Reaffirms or applies an existing doctrine without change.
                 - **MODIFICATION**: Modifies, adjusts, or refines an existing doctrine or ruling.
                 - **CLARIFICATION**: The Supreme Court clarifies the application of law or doctrine (e.g., resolving ambiguity, providing guidance on interpretation).
                 - **ABANDONMENT**: Explicitly abandons, overturns, or departs from a previous doctrine.
                 - **REVERSAL**: This means reversal of the Supreme Court of its own Decision (Not the Supreme Court reversing the lower courts). The Supreme Court in its Resolution reverses its OWN Decision on Motion for Reconsideration of either of the Party regardless of how many motions were filed. This classification (REVERSAL) should be accompanied by any of the other classification eg Modification etc, (depending on the final resolution). SO the Output should be "REVERSAL" and "MODIFICATION" or "REVERSAL" and "ABANDONMENT"

                 **Step B: Reasoning & Evidence (Mandatory)**
                 Provide a **classification_reasoning** sentence. If you classify as NEW DOCTRINE, ABANDONMENT, MODIFICATION, or CLARIFICATION, you MUST quote the specific sentence where the Court indicates this (e.g., "We now abandon the ruling in...", "We clarify that...", "We modify our prior ruling...").

                 **Step C: Collateral Matters (Mandatory Check)**
                 Scan for "Bar Exam Traps": Quantum of Proof changes, Win/Loss paradoxes, Procedural anomalies, Prospective applications, Novel definitions.

            6. **EDUCATIONAL ASSETS:**
               - **Legal Concepts:**
                 - Extract 5 concepts: "Concept - Definition".
                 - **Rule:** Use EXACT wording from the case for the definition.
                 - **Citations:** Cite the source case AND the specific provision of the law (e.g., "Article 3, Section 1, 1987 Constitution").
               - **Flashcards:** Create 3 cards (Concept, Distinction, Scenario). Do NOT ask "What is the doctrine?".

            **OUTPUT FORMAT:**
            Return ONLY valid JSON:
            {{
                "full_title": "...",
                "short_title": "...",
                "significance_category": "REITERATION | NEW DOCTRINE | CLARIFICATION | MODIFICATION | ABANDONMENT | REVERSAL", 
                "classification": "REITERATION | NEW DOCTRINE | CLARIFICATION | MODIFICATION | ABANDONMENT | REVERSAL",
                "classification_reasoning": "Evidence and quote from the text justifying the classification...",
                "significance_narrative": "Detailed explanation of Bar Traps and significance...",
                "relevant_doctrine": "...",
                "statutes_involved": [
                    {{"law": "Family Code", "provision": "Article 36"}},
                    {{"law": "Rules of Court", "provision": "Rule 65, Sec. 1"}}
                ],
                "main_doctrine": "...",
                "keywords": ["Keyword1", "Keyword2"],
                "court_division": "En Banc | Third Division",
                "ponente": "...",
                "document_type": "Decision | Resolution | ...",
                "subject": "Primary: [Subject]; Secondary: [Subject1, Subject2]",
                "date": "YYYY-MM-DD",
                "case_number": "...",
                
                "digest_facts": "1. **The Antecedents:** ... \\n\\n 2. **Procedural History:** ...",
                "issue": "* Issue 1\\n* Issue 2 (STRICT: Return as a single Markdown string with bullet points, NOT a JSON array)",
                "ruling": "...",
                "ratio": "* **On Issue 1:** [5+ sentences of reasoning...]\\n* **On Issue 2:** [5+ sentences...](STRICT: Return as a single Markdown string with bullet points, NOT a JSON array. **CRITICAL:** All reasoning for a single issue MUST be contained within its corresponding bullet point. DO NOT create separate bullets labeled 'Continued' or 'Incurability' etc. Place ALL analysis for Issue 1 under the '**On Issue 1:**' bullet point.)",
                
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
                "legal_concepts": [
                    {{"term": "Political Question", "definition": "those questions which... [citing Article X, Section Y]"}},
                    {{"term": "Buyer in Good Faith", "definition": "... [citing Case Title]"}}
                ],
                "separate_opinions": [
                    {{"justice": "Name", "type": "Concurring", "summary": "...", "text": "..."}}
                ],
                "secondary_rulings": [
                    {{"topic": "Quantum of Proof", "ruling": "..."}}
                ]
            }}
            """
            
            
            response = None
            used_model = model_name
            
            logging.info(f"Attempting digest with {model_name}...")
            try:
                # System Instruction for Legal Context (Bypasses some filters)
                sys_instruction = """ROLE: You are a highly precise Legal Data Extraction Engine specialized in Philippine Jurisprudence for a Bar Review application. Your task is to transform raw legal text into a structured, clinical analysis for academic use.

TONE & SCOPE: Maintain a neutral, professional, and purely academic tone. Treat all descriptions of events as "Case Facts" or "Testimony" for evidentiary analysis. Do not use sensationalist language. Terminology regarding crimes is strictly for legal classification."""

                # Using google-genai v1beta client
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=sys_instruction,
                        temperature=0.1,
                        response_mime_type='application/json',
                        safety_settings=[
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                            ),
                        ]
                    )
                )
                
            except Exception as e:
                logging.error(f"Model {model_name} Error: {e}")
                _clear_processing_claim(conn, case_id)
                continue
            
            # Final Check: Did we get a valid response?
            if not response or not response.candidates:
                logging.error(f"All model tiers failed for Case {case_id}.")
                blocked_ok = False
                try:
                    cur_b = conn.cursor()
                    cur_b.execute(
                        "UPDATE sc_decided_cases SET digest_significance = 'BLOCKED_SAFETY' WHERE id = %s",
                        (case_id,),
                    )
                    conn.commit()
                    blocked_ok = cur_b.rowcount > 0
                    if blocked_ok:
                        logging.info(f"Successfully marked Case {case_id} as BLOCKED_SAFETY in DB.")
                except Exception as e:
                    conn.rollback()
                    logging.error(f"Failed to update DB for blocked case {case_id}: {e}")
                if not blocked_ok:
                    _clear_processing_claim(conn, case_id)
                continue

            # Check for empty response (common in blocks)
            if not response.text:
                logging.warning(f"Case {case_id} returned empty text.")
                try:
                    logging.info(f"DEBUG CANDIDATES: {response.candidates}")
                    logging.info(f"DEBUG USAGE: {response.usage_metadata}")
                except Exception:
                    pass

                logging.warning(f"Marking as BLOCKED_SAFETY.")
                blocked_ok = False
                try:
                    cur_b = conn.cursor()
                    cur_b.execute(
                        "UPDATE sc_decided_cases SET digest_significance = 'BLOCKED_SAFETY' WHERE id = %s",
                        (case_id,),
                    )
                    conn.commit()
                    blocked_ok = cur_b.rowcount > 0
                except Exception as e:
                    conn.rollback()
                    logging.error(f"Failed to mark BLOCKED_SAFETY for empty text case {case_id}: {e}")
                if not blocked_ok:
                    _clear_processing_claim(conn, case_id)
                continue
            
            # Parse JSON safely
            try:
                clean_text = response.text.replace('```json', '').replace('```', '').strip()
                clean_text = preprocess_json_string(clean_text)
                data = json.loads(clean_text)
            except ValueError:
                logging.warning(f"JSON Parsing failed. Attempting repair for Case {case_id}...")
                try:
                     repaired_text = repair_truncated_json(clean_text)
                     data = json.loads(repaired_text)
                     logging.info(f"JSON Repair SUCCESS for Case {case_id}")
                except Exception as repair_err:
                     logging.error(f"JSON Repair FAILED for Case {case_id}: {repair_err}")
                     logging.error(f"Failed response sample: {response.text[:100]}...")
                     with open(f"failed_digest_{case_id}.txt", "w", encoding="utf-8") as f:
                        f.write(response.text)
                     logging.info(f"Dumped failed response to failed_digest_{case_id}.txt")
                     _clear_processing_claim(conn, case_id)
                     continue
            
            # Handle case where AI returns a list instead of dict
            if isinstance(data, list):
                logging.warning(f"AI returned a list for Case {case_id}, extracting first element...")
                if len(data) > 0:
                    data = data[0]
                else:
                    logging.error(f"Empty list returned for Case {case_id}, skipping...")
                    _clear_processing_claim(conn, case_id)
                    continue
            
            # Construct composite significance field
            classification = data.get('classification') or data.get('significance_category', 'REITERATION')
            significance_text = f"[{classification}]\n{data.get('classification_reasoning', '')}\n{data.get('digest_significance', '')}"
            
            logging.info(f"DEBUG: Generated Keys: {list(data.keys())}")
            logging.info(f"DEBUG: Significance Text len: {len(significance_text)}")
            logging.info(f"DEBUG: Significance Text Preview: {significance_text[:100]}")
            narrative = data.get('significance_narrative', '') 
            rel_doctrine = data.get('relevant_doctrine', '')
            
            # Extract new fields for columns
            data['significance_category'] = classification 
            
            # The original significance_text construction was more complex,
            # but the user's instruction implies a simpler one for logging.
            # Re-constructing based on the original logic for consistency with other fields.
            reasoning = data.get('classification_reasoning', '')
            significance_text = f"[{classification}]\n\n**Reasoning:** {reasoning}\n\n{narrative}"
            if rel_doctrine:
                significance_text += f"\n\n**Relevant Doctrine:** {rel_doctrine}"

            # PHASE 3: Save Result
            # Note: For seek_and_fill, we reuse smart_backfill logic in save_digest_result 
            # to handle "Partial Updates" vs "Weak Model Overwrites" safely.
            effective_smart_backfill = smart_backfill or seek_and_fill
            
            save_digest_result(case_id, content, data, significance_text, conn=conn, model_name=used_model, smart_backfill=effective_smart_backfill)
            
            processed_count += 1
            
            # Add to exclude list to prevent reprocessing in subsequent loop iterations
            exclude_ids.append(case_id)
            
            time.sleep(1) # Small pause
            
        except Exception as e:
            logging.error(f"Failed to process Case ID {case_id}: {e}")
            
            # Rate Limit Backoff (Check this FIRST before resetting lock, to avoid thrashing)
            if "429" in str(e) or "ResourceExhausted" in str(e) or "Quota" in str(e):
                logging.warning("Hit Rate Limit (429). Sleeping for 90s...")
                time.sleep(90)
                # Retry logic? For now, we just skip this case and let the lock reset or expire.
                # Actually, if we hit 429, we likely want to STOP this batch or retry the SAME case?
                # But here we catch, log, and fall through to Reset Lock.
                # That's fine, resetting lock allows another worker (or this one) to try later.
            
            try:
                # Reset processing tag on error so it doesn't stay locked forever
                # Use persistent conn
                conn.rollback() # Rollback any pending trans
                cur = conn.cursor()
                cur.execute("UPDATE sc_decided_cases SET digest_significance = NULL WHERE id = %s AND digest_significance = 'PROCESSING'", (case_id,))
                conn.commit()
                logging.info(f"Reset lock for Case ID {case_id}")
            except Exception as reset_error:
                logging.error(f"Failed to reset lock for Case ID {case_id}: {reset_error}")

    conn.close()
    return processed_count


def _dedupe_target_ids_preserve(ids: list[str]) -> list[str]:
    """Strip, drop empties, preserve order, first occurrence wins."""
    seen: set[str] = set()
    out: list[str] = []
    for raw in ids:
        x = (raw or "").strip()
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def _gemini_digest_child_command(args, *, limit: int, target_ids_csv: str | None) -> list[str]:
    """Argv for a single-worker child (``--workers 1``); used when parent runs with ``--workers`` > 1."""
    cmd = [sys.executable, os.path.abspath(__file__), "--workers", "1", "--limit", str(limit)]
    if target_ids_csv is not None:
        cmd.extend(["--target-ids", target_ids_csv])
    if args.doctrinal_only:
        cmd.append("--doctrinal-only")
    if args.year is not None:
        cmd.extend(["--year", str(args.year)])
    if args.exit_on_finish:
        cmd.append("--exit-on-finish")
    if args.force:
        cmd.append("--force")
    if args.en_banc_only:
        cmd.append("--en-banc-only")
    if args.start_year is not None:
        cmd.extend(["--start-year", str(args.start_year)])
    if args.end_year is not None:
        cmd.extend(["--end-year", str(args.end_year)])
    if args.start_date:
        cmd.extend(["--start-date", args.start_date])
    if args.end_date:
        cmd.extend(["--end-date", args.end_date])
    cmd.extend(["--model", args.model])
    if args.ascending:
        cmd.append("--ascending")
    if args.fix_gemini_3:
        cmd.append("--fix-gemini-3")
    if args.smart_backfill:
        cmd.append("--smart-backfill")
    if args.metadata_backfill:
        cmd.append("--metadata-backfill")
    if args.seek_and_fill:
        cmd.append("--seek-and-fill")
    if args.retry_blocked:
        cmd.append("--retry-blocked")
    if args.max_pages is not None:
        cmd.extend(["--max-pages", str(args.max_pages)])
    if args.fill_empty:
        cmd.append("--fill-empty")
    if args.api_key:
        cmd.extend(["--api-key", args.api_key])
    if args.vertex_project:
        cmd.extend(["--vertex-project", args.vertex_project])
    if args.vertex_location:
        cmd.extend(["--vertex-location", args.vertex_location])
    return cmd


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
    parser.add_argument("--target-ids-file", type=str, help="Path to text file containing comma-separated or newline-separated IDs")
    parser.add_argument("--en-banc-only", action="store_true", help="Only process EN BANC cases")
    parser.add_argument("--start-year", type=int, help="Start year filter (inclusive)")
    parser.add_argument("--end-year", type=int, help="End year filter (inclusive)")
    parser.add_argument("--start-date", type=str, help="Start date filter (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date filter (YYYY-MM-DD)")
    parser.add_argument("--model", type=str, default="gemini-2.5-flash", help="Gemini Model to use")
    parser.add_argument("--ascending", action="store_true", help="Process from oldest to newest")
    parser.add_argument("--fix-gemini-3", action="store_true", help="Backfill mode for Gemini 3 cases with missing fields")
    parser.add_argument("--smart-backfill", action="store_true", help="Smart Backfill: Overwrite weak models, fill incomplete strong models")
    parser.add_argument("--metadata-backfill", action="store_true", help="Metadata Backfill: Target cases with missing date, title, etc.")
    parser.add_argument("--seek-and-fill", action="store_true", help="Seek any empty fields or weak models and fill them.")
    parser.add_argument("--retry-blocked", action="store_true", help="Target BLOCKED_SAFETY cases")
    parser.add_argument("--max-pages", type=int, help="Max length in pages (approx 3000 chars/page)")
    parser.add_argument("--fill-empty", action="store_true", help="Target only cases with empty digest fields/BLOCKED status")
    parser.add_argument("--api-key", type=str, help="Custom API key for this run")
    parser.add_argument("--vertex-project", type=str, help="Vertex AI Project ID (enables aiplatform endpoint)")
    parser.add_argument("--vertex-location", type=str, default="us-central1", help="Vertex AI Location")
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Parallel child processes (each runs with --workers 1). Ignored with --continuous.",
    )

    args = parser.parse_args()
    
    # Configure Model and Client from Args
    if args.vertex_project or os.getenv("VERTEX_AI_PROJECT"):
        v_project = args.vertex_project or os.getenv("VERTEX_AI_PROJECT")
        v_loc = args.vertex_location or os.getenv("VERTEX_AI_LOCATION", "us-central1")
        logging.info(f"Override: Using Vertex AI Endpoint (project={v_project}, location={v_loc})")
        client = genai.Client(vertexai=True, project=v_project, location=v_loc)
    elif args.api_key:
        logging.info(f"Using Custom API Key for this run.")
        client = genai.Client(api_key=args.api_key)
    
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
                # Handle both newlines and commas
                file_ids = content.replace("\n", ",").split(",")
                target_ids_list.extend([x.strip() for x in file_ids if x.strip()])
            logging.info(f"Loaded {len(target_ids_list)} target IDs from file: {args.target_ids_file}")
        except Exception as e:
            logging.error(f"Failed to read target IDs file: {e}")

    if target_ids_list:
        target_ids_list = _dedupe_target_ids_preserve(target_ids_list)

    # Override limit if specific targets are set to prevent looping/overwriting
    if target_ids_list:
        args.limit = len(target_ids_list)
        logging.info(f"Target IDs provided. Setting limit to {args.limit} to process each exactly once.")

    workers = max(1, int(args.workers))

    if not args.continuous and workers > 1:
        import subprocess
        from concurrent.futures import ThreadPoolExecutor, as_completed

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        def _run_digest_child(cmd: list[str]) -> int:
            logging.info("Parallel digest child: %s", " ".join(cmd))
            return int(subprocess.run(cmd, cwd=repo_root).returncode)

        if target_ids_list:
            ids = target_ids_list
            pool_workers = min(workers, len(ids))
            rcs: list[int] = []
            with ThreadPoolExecutor(max_workers=pool_workers) as pool:
                futures = [
                    pool.submit(
                        _run_digest_child,
                        _gemini_digest_child_command(args, limit=1, target_ids_csv=str(xid)),
                    )
                    for xid in ids
                ]
                for fut in as_completed(futures):
                    rcs.append(fut.result())
            bad = [r for r in rcs if r not in (0, 100)]
            if bad:
                sys.exit(bad[0])
            if rcs and all(r == 100 for r in rcs):
                sys.exit(100)
            sys.exit(0)

        processed_total = 0
        limit_total = args.limit
        while processed_total < limit_total:
            wave = min(workers, limit_total - processed_total)
            rcs = []
            with ThreadPoolExecutor(max_workers=wave) as pool:
                futures = [
                    pool.submit(
                        _run_digest_child,
                        _gemini_digest_child_command(args, limit=1, target_ids_csv=None),
                    )
                    for _ in range(wave)
                ]
                for fut in as_completed(futures):
                    rcs.append(fut.result())
            successes = sum(1 for r in rcs if r == 0)
            if successes == 0:
                sys.exit(100 if processed_total == 0 else 0)
            processed_total += successes
        sys.exit(0)

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
                    smart_backfill=args.smart_backfill,
                    max_pages=args.max_pages,
                    metadata_backfill=args.metadata_backfill,
                    retry_blocked=args.retry_blocked,
                    seek_and_fill=args.seek_and_fill,
                    fill_empty=args.fill_empty,
                )

                if processed == 0:
                    logging.info("No cases processed in this batch.")
                    if args.exit_on_finish:
                        logging.info("Exiting as requested (--exit-on-finish).")
                        sys.exit(100)  # SIGNAL: NO WORK LEFT
                    time.sleep(5)
                
            except Exception as e:
                logging.error(f"Loop error: {e}")
                time.sleep(5)
    else:
        # One-off run
        count = generate_digest_batch(
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
            metadata_backfill=args.metadata_backfill,
            retry_blocked=args.retry_blocked,
            seek_and_fill=args.seek_and_fill,
            fill_empty=args.fill_empty
        )
        if count == 0:
            sys.exit(100)
