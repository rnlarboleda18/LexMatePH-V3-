import os
import sys
import json
import logging
import argparse
import time
import psycopg2
import google.generativeai as genai_legacy # For types if needed, or remove
from google import genai
from google.genai import types

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_db_connection():
    if 'DATABASE_URL' not in os.environ:
        try:
            with open('local.settings.json') as f:
                settings = json.load(f)
                os.environ['DATABASE_URL'] = settings['Values']['DB_CONNECTION_STRING']
        except Exception as e:
            logging.error(f"Failed to load local.settings.json: {e}")
            raise

    return psycopg2.connect(os.environ['DATABASE_URL'])

def fix_significance(target_file, model_name, api_key):
    # Retrieve API key
    if not api_key:
         api_key = os.environ.get("GOOGLE_API_KEY")
    
    # Initialize Client (New SDK)
    client = genai.Client(api_key=api_key)
    
    # Read IDs
    try:
        with open(target_file, 'r') as f:
            ids = [line.strip() for line in f if line.strip().startswith('#') or line.strip().isdigit()]
            id_list = [int(x.replace('#', '')) for x in ids]
    except Exception as e:
        logging.error(f"Failed to read target file: {e}")
        return

    logging.info(f"Loaded {len(id_list)} cases to fix.")

    conn = get_db_connection()
    
    for case_id in id_list:
        try:
            # 1. Fetch Content
            cur = conn.cursor()
            cur.execute("SELECT full_text_md, short_title FROM sc_decided_cases WHERE id = %s", (case_id,))
            res = cur.fetchone()
            if not res:
                logging.warning(f"Case {case_id} not found.")
                continue
            
            content, title = res
            logging.info(f"Processing Case {case_id}: {title}...")

            # 2. Construct Prompt (Targeted)
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
            - **SEPARATE OPINIONS BAN**: You are STRICTLY FORBIDDEN from quoting, citing, or discussing Dissenting or Concurring opinions in the `classification_reasoning` or `significance_narrative`. The significance must be based SOLELY on the Majority Decision / Ponencia. Justice Puno's dissent in *Regala* is irrelevant to the doctrine established by the majority.

            **INPUT TEXT:**
            {content[:150000]}

            **OUTPUT FORMAT (JSON):**
            Return ONLY valid JSON with this structure:
            {{
                "classification": "REITERATION | NEW DOCTRINE | MODIFICATION | ABANDONMENT | REVERSAL",
                "classification_reasoning": "REQUIRED. Evidence and quote from the MAIN DECISION (not dissents) justifying the classification. Must not be empty.",
                "significance_narrative": "Explain the nuances and significance to Bar examinees. Avoid the word 'trap'. Use phrases like 'examinees may misappreciate'. Do not just repeat the ruling."
            }}
            """

            # 3. Generate (New SDK)
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type='application/json'
                )
            )
            
            if not response.text:
                logging.error("Empty response.")
                continue

            data = json.loads(response.text)
            while isinstance(data, list):
                if data:
                    data = data[0]
                else:
                    logging.error(f"Empty JSON list for {case_id}")
                    data = {}
                    break
            
            if not isinstance(data, dict):
                logging.error(f"Invalid data format for {case_id}: {type(data)}")
                continue
            
            # 4. Construct Field
            classification = data.get('classification', 'REITERATION')
            reasoning = data.get('classification_reasoning', '')
            narrative = data.get('significance_narrative', '')
            
            full_significance = f"[{classification}]\n\n**Reasoning:**\n{reasoning}\n\n{narrative}"
            
            # 5. Update DB
            cur.execute("""
                UPDATE sc_decided_cases 
                SET digest_significance = %s,
                    significance_category = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (full_significance, classification, case_id))
            
            conn.commit()
            logging.info(f"✅ Updated Case {case_id} Significance: [{classification}]")
            
        except Exception as e:
            logging.error(f"Error processing {case_id}: {e}")
            conn.rollback()
            time.sleep(1)

    conn.close()
    logging.info("Batch Complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-file", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--api-key", required=True)
    args = parser.parse_args()
    
    fix_significance(args.target_file, args.model, args.api_key)
