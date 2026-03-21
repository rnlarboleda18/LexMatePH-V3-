import os
import json
import psycopg2
from openai import OpenAI
import time
import logging
import sys
from psycopg2.extras import RealDictCursor, register_default_jsonb, Json

# Configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

# Fallback to local.settings.json
if not OPENAI_API_KEY:
    try:
        with open('local.settings.json', 'r') as f:
            settings = json.load(f)
            OPENAI_API_KEY = settings.get('Values', {}).get('OPENAI_API_KEY')
    except:
        pass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_db_connection():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    register_default_jsonb(conn_or_curs=conn, globally=True)
    return conn

# --- PROMPT FOR SIGNIFICANCE ONLY (From Gemini) ---
sys_instruction = """ROLE: You are an Expert Legal Analyst and Senior Bar Reviewer.
GOAL: re-evaluate the SIGNIFICANCE and CLASSIFICATION of the provided Supreme Court decision.
OUTPUT: Strict JSON.
NARRATIVE STYLE: Do not repeat the ruling. Focus on the nuances. Explain why this case is significant. Avoid colloquial terms like "Bar trap" or "student errors". Instead use professional phrasing like "Bar examinees may misapply..." or "It is crucial to distinguish..."."""

prompt_template = """
**TASK:**
Analyze the provided text. Determine the **Significance Classification** and **Main Doctrine**.

**CRITICAL RULES:**
1. **Classification:** Must be one of: `REITERATION`, `NEW DOCTRINE`, `MODIFICATION`, `ABANDONMENT`, `REVERSAL`.

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
- **Startlingly Clear Rule**: Modifying a penalty (e.g. Death -> Life) or damages is **NEVER** a "MODIFICATION" of doctrine. It is a **REITERATION** of the sentencing guidelines. Classify as **REITERATION**.

**INPUT TEXT:**
{text_content}

**OUTPUT FORMAT (JSON):**
{{
    "significance_category": "REITERATION | NEW DOCTRINE | MODIFICATION | ABANDONMENT | REVERSAL",
    "classification": "REITERATION | NEW DOCTRINE | MODIFICATION | ABANDONMENT | REVERSAL", 
    "classification_reasoning": "Evidence and quote from the text justifying the classification...",
    "significance_narrative": "Explain the nuances and significance to Bar examinees. Avoid the word 'trap'. Use phrases like 'examinees may misappreciate'. Do not just repeat the ruling."
}}
"""

def generate_digest_batch(target_ids, model_name="gpt-4o"):
    if not OPENAI_API_KEY:
        logging.error("OPENAI_API_KEY not set.")
        return 0

    client = OpenAI(api_key=OPENAI_API_KEY)
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 1. Fetch Cases
    query = f"SELECT id, full_text_md, short_title FROM sc_decided_cases WHERE id IN %s"
    cur.execute(query, (tuple(target_ids),))
    rows = cur.fetchall()
    
    print(f"Processing {len(rows)} cases with {model_name}...")
    
    processed_count = 0
    
    for row in rows:
        case_id = row[0]
        full_text = row[1]
        
        # Safe Truncation (OpenAI has 128k context, but let's stay safe around 300k chars ~ 75k tokens)
        safe_text = full_text[:300000]
        
        prompt = prompt_template.format(text_content=safe_text)
        
        try:
            if model_name.startswith("gpt-5") or model_name.startswith("o1") or model_name.startswith("o3"):
                 # Reasoning Model Logic
                 final_prompt = f"{sys_instruction}\n\n{prompt}"
                 call_kwargs = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": final_prompt}],
                 }
            else:
                 # Standard Logic
                 call_kwargs = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": sys_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    "response_format": { "type": "json_object" },
                    "temperature": 0.1
                 }

            response = client.chat.completions.create(**call_kwargs)
             
            content = response.choices[0].message.content
            data = json.loads(content)
             
            # Parse Output
            sig_cat = data.get('significance_category') or data.get('classification')
            reasoning = data.get('classification_reasoning') or ""
            narrative = data.get('significance_narrative') or ""
             
            full_significance = f"[{sig_cat}]\n\n"
            if reasoning: full_significance += f"**Reasoning:** {reasoning}\n\n"
            if narrative: full_significance += f"**Significance:** {narrative}"
            full_significance = full_significance.strip()
             
            # Update DB
            cur.execute("""
                UPDATE sc_decided_cases
                SET digest_significance = %s,
                    significance_category = %s,
                    ai_model = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (full_significance, sig_cat, model_name, case_id))
             
            conn.commit()
            logging.info(f"Updated Case {case_id}: {sig_cat} ({model_name})")
            processed_count += 1
             
        except Exception as e:
            logging.error(f"Error processing {case_id}: {e}")
            conn.rollback()
            
    conn.close()
    return processed_count

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-ids", type=str, required=True)
    parser.add_argument("--model", type=str, default="gpt-4o-mini")
    
    args = parser.parse_args()
    
    ids_list = [int(x.strip()) for x in args.target_ids.split(',')]
    generate_digest_batch(ids_list, model_name=args.model)
