"""
Amendment Applicator: Uses AI to apply amendments with strict literal fidelity
"""


import os
import re
import json

from codex_validator import CodexValidator
from lexcode_genai_client import get_genai_client, get_amendment_primary_model


def _normalize_for_no_change_compare(text: str) -> str:
    """Loose normalize so Art./Article and spacing differences do not force a false 'change'."""
    t = (text or "").strip()
    t = t.replace("**", "").replace("*", "")
    t = re.sub(r"\bart\.\s*", "article ", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t)
    return t.lower().strip()


def _is_substantively_unchanged(old_text: str, new_text: str) -> bool:
    """
    True if merged output is the same article for codex purposes (no DB row / description needed).
    Uses normalized equality only so tiny real edits are not dropped.
    """
    a = _normalize_for_no_change_compare(old_text)
    b = _normalize_for_no_change_compare(new_text)
    if not a and not b:
        return True
    return a == b

# Initialize Shared Client (supports Vertex AI redirection)
client = get_genai_client()

SYSTEM_PROMPT = """You are a legal document specialist with ABSOLUTE LITERAL FIDELITY as your core directive.

**CRITICAL RULES:**
1. DO NOT paraphrase or modernize language - maintain EXACT original style
2. DO NOT translate Spanish legal terms (e.g., "reclusion perpetua", "arresto mayor")
3. DO NOT "improve" grammar, spelling, or punctuation - preserve EXACTLY as in source
4. Apply ONLY the specific changes stated in the amendment
5. Preserve all capitalization, formatting, and textual patterns exactly as they appear
6. **PRESERVE LINE BREAKS AND NEWLINES** - If the current article has numbered items on separate lines, the amended version MUST maintain this structure
7. **MAINTAIN MARKDOWN FORMATTING** - If items are formatted with line breaks (e.g., "\\n1. ...", "\\n2. ..."), preserve this exact formatting
8. **LETTERS OF THE LAW ONLY** — This database stores the **enacted text** of each provision, not legislative intent, "context," or implied effects. If the **AMENDMENT TO APPLY** block does **not** expressly amend **this** article (by quoting its new wording, or a clear amend/repeal/insert clause aimed at that article), you MUST **not** treat omission as a "formal revision," "republication," "restatement," or "confirmatory" amendment. In those cases respond with `MANUAL_REVIEW_REQUIRED: [brief reason]`.
9. **DO NOT SKIP** when the amendatory law **does** quote or clearly dictate the full updated text for this article — output that full text verbatim (including minor formatting fixes the Act itself shows). Do not omit the output.
**FORMATTING STANDARDS (CRITICAL - MUST FOLLOW EXACTLY):**
- Article headers MUST use plain text format: "Article X. Title text here"
- NO additional markdown headers (###, ##, #) on article numbers
- NO brackets around article numbers
- Body text should use plain paragraphs with proper line breaks
- Numbered/bulleted lists should use standard markdown list syntax (1., 2., etc.)
- Preserve paragraph spacing and indentation exactly as in current text
- ALL text should be in standard markdown format without special styling
- **REMOVE wrapper quotation marks** at the start/end of paragraphs if the source text is quoted (e.g., if source says "Art. 1...", output Art. 1 without the quote)
- **RUN-IN TITLES SPACING**: If an article has a run-in title (e.g., "Other deceits"), ensure proper spacing: "Title. - Body text" NOT "Title.-Body text" (dash must have space before it)

**Your task:**
You will be given:
- The CURRENT text of a legal article
- An AMENDMENT that modifies this article (OR a law that may mention this article without changing it)

**BEFORE applying any changes, you MUST determine:**
1. Does the amendment block **on its face** supply new **letters** (quoted or clearly directed text) for **this** article?
2. If **no**, the Act does not amend this article's text for codex purposes — respond `MANUAL_REVIEW_REQUIRED: Amendment does not contain express text amending this article.`
3. Examples of **not** amending the letters of the article (do **not** output unchanged text as if it were an amendment):
   - The Act never names or quotes this article and only changes other articles
   - "Related" policy (e.g. penalties elsewhere) without changing **this** provision's wording
   - The Indeterminate Sentence Law, procedural laws, or laws that change application without changing the article text

**Your response (if step 1 is yes):**
- Output ONLY the new complete article text after applying the amendment
- Start directly with "Article X." (no markdown headers, no brackets)
- Maintain ALL formatting including line breaks, indentation, and spacing
- Never output placeholder strings

**If you cannot apply the amendment with 100% confidence from the quoted/directed text:**
- Respond with: `MANUAL_REVIEW_REQUIRED: [brief reason]`

Remember: You are a TRANSCRIPTION tool for **enacted language**, not an interpretation tool. Do not invent formal or confirmatory amendments."""


def generate_amendment_description(current_text, new_text, amendment_id, prior_amendment_id, prior_date, history=None, model_name=None):
    """
    Fix #5: Generates a concise, professional amendment description.
    Uses the 'Short & Sharp' format: **Bold Category**: 1-2 sentences, max 60 words.
    """
    if model_name is None:
        model_name = get_amendment_primary_model()
    try:
        if not prior_amendment_id:
            prior_amendment_id = "Original/Previous Law"
        if not prior_date:
            prior_date = "Previous Date"

        history_lines = ""
        if history and len(history) > 0:
            history_lines = "PRIOR AMENDMENTS (oldest first, for continuity context):\n"
            for item in history:
                history_lines += f"  - {item.get('date','')} | {item.get('amendment_id','')}: {item.get('description','(no description)')}\n"
            history_lines += "\n"

        prompt = f"""### ROLE
You are a Senior Legal Historian and Bar Exam Subject Matter Expert specializing in the Philippine Revised Penal Code (RPC). Your goal is to provide a comprehensive analysis of how a specific amendment changes the law, specifically in the context of its entire chronological history.

### INPUT DATA
- **PREVIOUS TEXT ({prior_amendment_id}, {prior_date})**: 
{current_text[:1500]}

- **CHRONOLOGICAL HISTORY**: 
{history_lines}

- **NEW AMENDMENT ({amendment_id})**: 
{new_text[:1500]}

### CORE TASK
The codex tracks the **letters of the law**—differences in enacted **wording**—not legislative context, "ghost" effects on unstated articles, or assumptions when an article is not mentioned in the amendatory instrument.

Analyze the "New Amendment" against the "Chronological History." Describe **only** what changed in the **text** of the provision.

### OUTPUT STRUCTURE (MANDATORY)

**1. AMENDMENT CATEGORY**
[Choose one: Fine Escalation | Penalty Upgrade | Decriminalization | Element Modification | Formal Revision | Administrative Update]
- Use **Formal Revision** **only** when the amending law **literally** re-encodes or restates the **same** provision in the Act's own quoted text (true textual republication). **Never** use Formal Revision because an article was "not mentioned," "implicitly confirmed," or "contextually related."

**2. DESCRIPTION OF CHANGE**
- Summarize **literal** edits (words, phrases, punctuation, penalties as written). Do not claim the Act amended this article if the excerpt shows no change to its letters.
- If this is a subsequent amendment, specifically state: "This amendment modifies the previous change introduced by [Insert Previous RA/Law Number] by [increasing/decreasing/restating]..."

**3. LEGAL EFFECT & SUBSTANTIVE IMPACT**
- Detail how this changes the **Elements of the Crime**. (e.g., "The element of 'intent to gain' is now presumed...")
- Detail the **Penalty Shift**. (e.g., "Raised from Arresto Mayor to Prision Correccional.")
- Mention any effects on **Prescription of Crimes** or **Bail Eligibility** if applicable.
- If the amendment comes from a "Ghost" law (a law that affects the article without changing the words), explain the operational impact of that law on the RPC text.

**4. HISTORICAL CONTEXT & RELATIONSHIP**
- Explain the "Why" and "How" in relation to the previous version. 
- Example: "While RA 7659 previously increased the penalty for this article to Death, this current amendment (RA 9346) prohibits the imposition of death, effectively reverting the functional penalty to Reclusion Perpetua."
- If the amendment restores an older version of the law, note the "Reversion."

### CRITICAL RULES
1. **NO HALLUCINATION**: If the amendment history is silent on a specific detail, do not invent a reason.
2. **BAR REVIEWER TONE**: Write for a law student. Use precise terminology (e.g., "Civil Interdiction", "Accessory Penalties").
3. **CUMULATIVE VIEW**: Always treat the "New Amendment" as the latest layer. If the New Amendment overrides a change made two amendments ago, highlight that conflict/resolution.
4. **NO QUOTES**: Do not repeat the full text of the article here; focus only on the *analysis* of the change."""

        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"    [!] Failed to generate description: {e}")
        return None


def generate_new_article_insertion_description(
    inserted_article_text: str,
    amendment_id: str,
    amendment_date: str | None,
    article_number: str,
    amendatory_excerpt: str | None = None,
    history=None,
    model_name=None,
):
    """
    Same narrative rubric as ``generate_amendment_description``, for **new** RPC articles
    (no prior codal row). Summarizes offense, penalties, and legislative insertion context.
    """
    if model_name is None:
        model_name = get_amendment_primary_model()
    try:
        body = (inserted_article_text or "").strip()
        excerpt = (amendatory_excerpt or "").strip()
        history_lines = ""
        if history and len(history) > 0:
            history_lines = "PRIOR AMENDMENTS (oldest first, for continuity context):\n"
            for item in history:
                history_lines += f"  - {item.get('date', '')} | {item.get('amendment_id', '')}: {item.get('description', '(no description)')}\n"
            history_lines += "\n"

        prompt = f"""### ROLE
You are a Senior Legal Historian and Bar Exam Subject Matter Expert specializing in the Philippine Revised Penal Code (RPC).

### CONTEXT
A **new** article — **Article {article_number}** — is being **inserted** into the codex by **{amendment_id}** (effective **{amendment_date or 'see statute'}**).
There was **no** prior RPC row for this article number; this is not a textual "diff" against old wording but a **brand-new provision**.

### FULL INSERTED ARTICLE TEXT (codal body)
```
{body[:8000]}
```

### AMENDATORY EXCERPT (statute as parsed; may include quotes)
```
{excerpt[:4000]}
```

{history_lines}

### CORE TASK
Describe this **new** provision for a codex amendment history card. Focus on **enacted wording**: offense definition, modes of commission, penalties, and any special rules — not speculative legislative intent.

### OUTPUT STRUCTURE (MANDATORY — match the usual amendment history style)

**1. AMENDMENT CATEGORY**
[Use: New Provision | Statutory Insertion]

**2. DESCRIPTION OF CHANGE**
- State that Article {article_number} is **newly introduced** by {amendment_id}.
- Summarize the **literal** elements and penalty text (no block quotes of the full article).

**3. LEGAL EFFECT & SUBSTANTIVE IMPACT**
- Elements, penalty tiers, qualifying circumstances as **written**.
- Note if it creates a **new** crime label (e.g. qualified bribery) distinct from neighboring articles.

**4. HISTORICAL CONTEXT & RELATIONSHIP**
- How it sits next to **adjacent** RPC articles if obvious from the excerpt (e.g. inserted after a given article).
- Do **not** claim prior versions of this article existed.

### CRITICAL RULES
1. **NO HALLUCINATION**: Do not invent repeals or cross-references not supported by the excerpt.
2. **BAR REVIEWER TONE**: Precise terminology.
3. **NO QUOTES**: Do not paste the full statute; analyze only."""

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"    [!] Failed to generate insertion description: {e}")
        return None


def apply_amendment_with_ai(current_text, amendment_text, amendment_id, prior_amendment_id=None, prior_date=None, history=None, model_name=None):
    """
    Uses Gemini AI to apply an amendment to an article.
    
    Args:
        current_text: Current article text (BEFORE)
        amendment_text: The text of the amendment itself
        amendment_id: The ID of the NEW amending law
        prior_amendment_id: The ID of the law governing the BEFORE version
        prior_date: The effective date of the BEFORE version
        history: List of previous versions for context
        model_name: Gemini model to use
    
    Returns:
        dict: {
            "success": bool,
            "new_text": str (if successful),
            "validation_result": dict,
            "ai_response": str,
            "description": str,
            "error": str (if failed)
        }
    """
    
    try:
        if not model_name:
            model_name = get_amendment_primary_model()
            
        # Configure model with safety settings off
        config = {
            "temperature": 0.0,  # Maximum determinism
            "top_p": 0.95,
            "top_k": 1,
            "safety_settings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        }
        
        # Construct prompt
        user_prompt = f"""**CURRENT ARTICLE TEXT:**
```
{current_text}
```

**AMENDMENT TO APPLY:**
```
{amendment_text}
```

**YOUR TASK:**
Apply the changes and output the complete, updated text of the article. Do not omit the article if the change is merely formatting or adding a title. Output exactly what the law says the text should be now."""
        
        # Generate response
        response = client.models.generate_content(
            model=model_name,
            contents=[SYSTEM_PROMPT, user_prompt],
            config=config
        )
        ai_output = response.text.strip()
        
        # Clean markdown formatting that AI might add
        # Remove code fences
        if ai_output.startswith("```") and ai_output.endswith("```"):
            # Remove opening fence (might have language identifier)
            lines = ai_output.split('\n')
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            ai_output = '\n'.join(lines)
        
        # ---------------------------------------------------------
        # COMPLIANCE ENFORCER: Strict Regex Output Cleaning
        # ---------------------------------------------------------
        
        # 1. Remove Leading/Wrapper Quotes on any line
        # Matches start of line, optional whitespace, quote, optional whitespace
        # Replaces with empty string (strips it completely)
        ai_output = re.sub(r'(?m)^\s*"\s*', '', ai_output)
        
        # 2. Remove Inline Sentence-Start Quotes (Artifacts from amending laws)
        # Matches: Punctuation + Whitespace + Quote + Uppercase Letter
        # Example: `therein. "The` -> `therein. The`
        # Handles period, question mark, exclamation point, and colon
        ai_output = re.sub(r'([\.\?!:])\s+"([A-Z])', r'\1 \2', ai_output)

        # 3. Remove Header Markdown (if valid headers are "Article X.")
        ai_output = re.sub(r'(?m)^(###|##|#)\s*', '', ai_output)

        # 4. Remove Trailing Wrapper Quote
        # Only if the very last character is a quote (cleanup)
        if ai_output.strip().endswith('"'):
             ai_output = ai_output.strip()[:-1]
        
        # 5. Fix Merged Run-In Titles
        # Matches: "Title text.-Body" and inserts space: "Title text. - Body"
        # Pattern: period followed immediately by dash (no space)
        ai_output = re.sub(r'\.(\s*)-(\s*)', r'. - ', ai_output)
             
        ai_output = ai_output.strip()
        
        # The python bypass check was completely removed to ensure all amendments are kept.
        
        # Check if AI requested manual review
        if ai_output.startswith("MANUAL_REVIEW_REQUIRED"):
            return {
                "success": False,
                "error": ai_output,
                "ai_response": ai_output
            }
        
        # Validate the AI output
        validator = CodexValidator()
        validation_result = validator.validate_amendment(current_text, ai_output)
        
        # Check confidence threshold
        if validation_result["confidence_score"] < 0.5:
            print(f"    [DEBUG] Validation Errors: {validation_result.get('errors')}")
            print(f"    [DEBUG] Validation Warnings: {validation_result.get('warnings')}")
            return {
                "success": False,
                "error": f"Low confidence score: {validation_result['confidence_score']:.2f}",
                "validation_result": validation_result,
                "ai_response": ai_output,
                "new_text": ai_output  # Include for manual review
            }
        
        # Check for errors
        if not validation_result["valid"]:
            return {
                "success": False,
                "error": "Validation failed: " + "; ".join(validation_result["errors"]),
                "validation_result": validation_result,
                "ai_response": ai_output,
                "new_text": ai_output  # Include for manual review
            }

        # Ghost / false-positive extractions: law never changed this article text.
        # Skip DB + skip long "no substantive change" descriptions (saves cost and UI noise).
        if current_text.strip() and _is_substantively_unchanged(current_text, ai_output):
            return {
                "success": False,
                "no_change": True,
                "error": "Merged text matches current article; skipping persist and description.",
                "validation_result": validation_result,
                "ai_response": ai_output,
                "new_text": ai_output,
                "description": None,
            }
        
        # Success! Generate description
        description = generate_amendment_description(current_text, ai_output, amendment_id, prior_amendment_id, prior_date, history=history)
        
        return {
            "success": True,
            "new_text": ai_output,
            "validation_result": validation_result,
            "ai_response": ai_output,
            "description": description
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"AI Error: {str(e)}"
        }

def test_applicator():
    """Test the amendment applicator"""
    
    # Test with a simple amendment
    current = """ART. 329. Other mischiefs.-The mischiefs not included in the next preceding article shall be punished:
1. By arresto mayor, if the value of the damage caused exceeds 500 Pesos;
2. By arresto menor, if such value does not exceed 500 pesos."""
    
    amendment = """Article three hundred and twenty-nine is hereby amended to read as follows:
"ART. 329. Other mischiefs.-The mischiefs not included in the next preceding article shall be punished:
1. By arresto mayor in its medium and maximum periods, if the value of the damage caused exceeds 1,000 Pesos;
2. By arresto mayor in its minimum and medium periods, if such value is over 200 pesos but does not exceed 1,000; and
3. By arresto menor or fine of not less than the value of the damage caused and not more than 200 pesos, if the amount involved does not exceed 200 pesos or cannot be estimated.\""""
    
    print("Testing Amendment Applicator...")
    print("=" * 60)
    
    result = apply_amendment_with_ai(current, amendment, "TEST_AMENDMENT_ID")
    
    if result["success"]:
        print("✓ SUCCESS")
        print(f"Confidence: {result['validation_result']['confidence_score']:.2f}")
        print("\nNew Text:")
        print(result["new_text"])
    else:
        print("✗ FAILED")
        print(f"Error: {result['error']}")
        if "validation_result" in result:
            print(f"Errors: {result['validation_result']['errors']}")
            print(f"Warnings: {result['validation_result']['warnings']}")

if __name__ == "__main__":
    test_applicator()
