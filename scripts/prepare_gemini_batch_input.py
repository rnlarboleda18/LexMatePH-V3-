import json
import psycopg
import os

# --- CONFIGURATION ---
INPUT_FILE = "batch_test_ids_random_10.txt"
OUTPUT_FILE = "batch_en_banc_random_10.jsonl"
MODEL_NAME = "models/gemini-3-flash-preview"
LIMIT = 10

settings = json.load(open('api/local.settings.json'))
conn_str = settings['Values']['DB_CONNECTION_STRING']

PROMPT_TEMPLATE = """
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
4. **Separate Opinions (CRITICAL - SCAN EXHAUSTIVELY):** You MUST identify and summarize **ALL** Concurring, Dissenting, Separate Concurring, and Separate Dissenting Opinions found in the text. En Banc cases often have 10+ separate opinions—scan the ENTIRE document thoroughly, including footnotes and signature blocks, to capture every opinion. For the Ponente, identify if they expressed a personal "Separate View" distinct from the majority. The `summary` field for each opinion MUST be populated with at least 3-4 sentences; it cannot be null.

**INPUT TEXT:**
{content}

**YOUR GOAL:**
Analyze the provided legal text and generate a structured, educational JSON digest for Bar Review students.

**STRICT DATA INTEGRITY RULES:**
1. **No Hallucinations:** If a specific detail date, justice, fact) is NOT found in the text, return `null` for strings/dates or an empty array `[]` for lists. Do NOT invent data.
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
   - **Facts Structure:** The "digest_facts" section MUST follow this three-part structure. **CRITICAL:** You MUST insert exactly TWO newline characters (`\\n\\n`) between each section to ensure they appear as separate paragraphs in the UI. Do NOT run them together.
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
     [REITERATION | NEW DOCTRINE | ABANDONMENT | MODIFICATION]]

     **Step B: Reasoning & Evidence (Mandatory)**
     Provide a **classification_reasoning** sentence. If you classify as NEW DOCTRINE, ABANDONMENT, or MODIFICATION, you MUST quote the specific sentence where the Court indicates this change (e.g., "We now abandon the ruling in...").

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
    "significance_category": "REITERATION | NEW DOCTRINE | ...",
    "classification": "REITERATION | NEW DOCTRINE | ...",
    "classification_reasoning": "Evidence and quote from the text justifying the classification...",
    "significance_narrative": "Detailed explanation of Bar Traps and significance...",
    "relevant_doctrine": "...",
    "document_type": "...",
    "case_number": "...",
    "date": "YYYY-MM-DD",
    "court_division": "En Banc | Division",
    "ponente": "...",
    "subject": "Primary: ...; Secondary: ...",
    "keywords": ["..."],
    "statutes_involved": ["..."],
    "main_doctrine": "...",
    "cited_cases": [
        {{"title": "...", "relationship": "Applied | Distinguished", "elaboration": "..."}}
    ],
    "timeline": [
        {{"date": "...", "event": "..."}}
    ],
    "digest_facts": "...",
    "digest_issues": "...",
    "digest_ruling": "...",
    "digest_ratio": "...",
    "legal_concepts": [
        {{"concept": "...", "definition": "...", "citation": "..."}}
    ],
    "flashcards": [
        {{"front": "...", "back": "..."}}
    ],
    "spoken_script": "...",
    "separate_opinions": [
       {{"justice": "...", "type": "Concurring | Dissenting | ...", "summary": "..."}}
    ],
    "secondary_rulings": [
        {{"topic": "...", "ruling": "..."}}
    ]
}}
"""

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    # Read IDs
    with open(INPUT_FILE, 'r') as f:
        # Robustly read lines, stripping whitespace/newlines
        ids = [line.strip() for line in f if line.strip()]

    target_ids = ids[:LIMIT]
    print(f"Preparing batch for {len(target_ids)} cases...")

    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            # Fetch content
            cur.execute("""
                SELECT id, full_text_md 
                FROM sc_decided_cases 
                WHERE id = ANY(%s)
            """, (target_ids,))
            
            rows = cur.fetchall()

    if not rows:
        print("No rows found.")
        return

    print(f"Fetched {len(rows)} rows. Generating JSONL...")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for r in rows:
            case_id = str(r[0])
            content = r[1]
            if not content:
                print(f"Skipping {case_id} (No content)")
                continue

            # Limit content size roughly to avoid hitting massive token limits (though Gemini has 1M-2M context)
            # 1M tokens is huge, so we likely don't need to truncate much.
            # But let's be safe if it's junk.
            if len(content) < 100:
                 print(f"Skipping {case_id} (Too short)")
                 continue

            # Construct request
            full_prompt = PROMPT_TEMPLATE.format(content=content)
            
            # Request Object for Gemini Batch
            # Check official Google GenAI Batch Input File format:
            # Each line: {"custom_id": "...", "method": "generateContent", "request": {...}}
            
            req = {
                "custom_id": f"req-{case_id}",
                "method": "generateContent",
                "request": {
                    "model": MODEL_NAME,
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": full_prompt}]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.2, # Low temp for factual digest
                        "responseMimeType": "application/json"
                    }
                }
            }
            
            f.write(json.dumps(req) + "\n")
            print(f"Added request for {case_id}")

    print(f"Successfully created {OUTPUT_FILE}")
    print(f"API Key for submission: REDACTED_API_KEY_HIDDEN")

if __name__ == "__main__":
    main()
