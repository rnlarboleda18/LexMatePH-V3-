"""
Amendment Applicator: Uses AI to apply amendments with strict literal fidelity
"""


import os
import re
import json
from google import genai
from codex_validator import CodexValidator

# Configure Gemini
API_KEY = "REDACTED_API_KEY_HIDDEN"
try:
    with open('local.settings.json') as f:
        settings = json.load(f)
        if 'GOOGLE_API_KEY' in settings['Values']:
            API_KEY = settings['Values']['GOOGLE_API_KEY']
except:
    pass

# Initialize Client
client = genai.Client(api_key=API_KEY)

SYSTEM_PROMPT = """You are a legal document specialist with ABSOLUTE LITERAL FIDELITY as your core directive.

**CRITICAL RULES:**
1. DO NOT paraphrase or modernize language - maintain EXACT original style
2. DO NOT translate Spanish legal terms (e.g., "reclusion perpetua", "arresto mayor")
3. DO NOT "improve" grammar, spelling, or punctuation - preserve EXACTLY as in source
4. Apply ONLY the specific changes stated in the amendment
5. Preserve all capitalization, formatting, and textual patterns exactly as they appear
6. **PRESERVE LINE BREAKS AND NEWLINES** - If the current article has numbered items on separate lines, the amended version MUST maintain this structure
7. **MAINTAIN MARKDOWN FORMATTING** - If items are formatted with line breaks (e.g., "\\n1. ...", "\\n2. ..."), preserve this exact formatting
8. **DETECT NO-CHANGE SCENARIOS** - If the amendment does NOT actually modify THIS SPECIFIC article (e.g., it's a related law that has indirect implications but doesn't change the text), respond with: "NO_SUBSTANTIVE_CHANGE"

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
1. Does this amendment actually MODIFY the substantive text of this article?
2. Or does it merely reference/relate to this article without changing it?
3. Examples of NO-CHANGE scenarios:
   - The Indeterminate Sentence Law (ISLAW) affects sentencing for crimes under the RPC but doesn't change the text of RPC articles
   - A law that suspends application of an article without amending its text
   - A procedural law that changes HOW an article is applied but not WHAT the article says

**Your response options:**
1. **If amendment DOES substantively change this article's text:**
   - Output ONLY the new complete article text after applying the amendment
   - Start directly with "Article X." (no markdown headers, no brackets)
   - Maintain ALL formatting including line breaks, indentation, and spacing
   
2. **If amendment does NOT change this article's text:**
   - Respond EXACTLY with: "NO_SUBSTANTIVE_CHANGE"
   - This signals that no new version should be created in the database
   
3. **If you cannot determine with 100% confidence:**
   - Respond with: "MANUAL_REVIEW_REQUIRED: [brief reason]"

Remember: You are a TRANSCRIPTION tool, not an interpretation tool. Literal fidelity AND formatting preservation are paramount. DO NOT create false amendments - if the text doesn't actually change, say NO_SUBSTANTIVE_CHANGE."""


def generate_amendment_description(current_text, new_text, amendment_id, prior_amendment_id, prior_date, history=None, model_name="gemini-3-flash-preview"):
    """
    Generates a detailed description of the changes made by an amendment.
    """
    try:
        # Default fallback if prior info is missing
        if not prior_amendment_id: prior_amendment_id = "Original/Previous Law"
        if not prior_date: prior_date = "Previous Date"

        history_context = ""
        if history and len(history) > 0:
            history_context = "**FULL HISTORY OF AMENDMENTS TO THIS ARTICLE:**\n"
            for item in history:
                history_context += f"- [{item['date']}] {item['amendment_id']}: {item['description']}\n"
                history_context += f"  Full Text:\n  ```\n{item['content']}\n  ```\n\n"
            history_context += "\n"

        prompt = f"""Compare the BEFORE and AFTER versions of this Philippine legal article amended by {amendment_id}.
        
        {history_context}
        
        BEFORE (Governed by {prior_amendment_id}, effective {prior_date}):
        {current_text}

        AFTER (Amended by {amendment_id}):
        {new_text}

        Task: Write a DETAILED description of the changes (aim for 3-5 sentences).
        1. **History**: Briefly mention the context of previous amendments if relevant (look at the provided history).
        2. **Specifics**: Detail the exact changes (e.g. "raised fine from X to Y").
        3. **Implications**: Explain the legal effect (e.g. "This effectively decriminalizes...", "This reclassifies the offense...").
        
        Structure the response as a coherent paragraph. DO NOT start or end with quotation marks.
        """
        
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"    [!] Failed to generate description: {e}")
        return None

def apply_amendment_with_ai(current_text, amendment_text, amendment_id, prior_amendment_id=None, prior_date=None, history=None, model_name="gemini-3-flash-preview"):
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
        # Configure model with safety settings off
        config = {
            "temperature": 0.0,  # Maximum determinism
            "top_p": 0.95,
            "top_k": 1,
            "max_output_tokens": 8192,
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
1. FIRST, determine if this amendment actually CHANGES the substantive text of this article.
2. If YES - apply the changes and output the new article text.
3. If NO - respond with exactly: "NO_SUBSTANTIVE_CHANGE"

Remember: Only create a new version if the article's legal text actually changes. If this is a related law that affects how the article is applied but doesn't modify its text, respond with NO_SUBSTANTIVE_CHANGE."""
        
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
        
        # Check if AI determined no changes needed
        if ai_output == "NO_SUBSTANTIVE_CHANGE":
            return {
                "success": False,
                "no_change": True,
                "error": "Article not substantively modified by this amendment",
                "ai_response": ai_output
            }
        
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
        
        # Success!
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
