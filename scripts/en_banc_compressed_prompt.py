# Compressed Prompt for En Banc Upgrade
# Reduces output tokens to stay within ~1M limit

COMPRESSED_PROMPT = """
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
4. **Separate Opinions (COMPRESSED FORMAT - TOP 3 ONLY):** 
   - Identify the **TOP 3 most significant** opinions only
   - Priority: Dissenting > Concurring > Separate Concurring
   - Skip routine concurrences that merely restate the majority
   - For each TOP 3: Justice name, Type, and **1-2 sentence summary**
   - Focus on WHY the opinion matters, not just WHAT it says

**INPUT TEXT:**
{content}

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

3. **TIMELINE GENERATION (Optional - Space Permitting):**
   - Extract key events with dates into a chronological list.
   - Format dates in events as consistently as possible. Use `null` if the entire timeline is missing or if space is constrained.

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

6. **EDUCATIONAL ASSETS (COMPRESSED):**
   - **Legal Concepts:** Extract 3-5 concepts with exact definitions from the case.
   - **Flashcards:** Create 2 cards (reduce from 3): Concept, Distinction, or Scenario. Do NOT ask "What is the doctrine?".
   - **Spoken Script:** 2-3 sentences maximum.

**OUTPUT FORMAT:**
Return ONLY valid JSON with these fields. Ensure no truncation.
"""

# This is used by the fleet deployment script
