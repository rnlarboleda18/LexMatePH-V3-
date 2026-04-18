"""
Amendment markdown → structured payload (``changes``, metadata).

**Deterministic first** — ``try_deterministic_amendment_parse`` runs before any Gemini call so
known sources keep **textual fidelity** without a generative extract step. Larger or unknown files
fall back to AI parsing (see ``lexcode_genai_client``); merge behavior is in ``apply_amendment``.
"""
import os
import sys
import re
import json

from lexcode_genai_client import get_genai_client, get_amendment_primary_model, get_amendment_chunk_model

from deterministic_lexcode import (
    clean_text,
    normalize_amendment_payload,
    parse_ra10951_offline_rpc_articles_134_to_136,
    parse_ra6968_offline,
    try_deterministic_amendment_parse,
)

# Initialize Shared Client (supports Vertex AI redirection)
client = get_genai_client()

# Same as normalize_amendment_payload (AI + deterministic outputs).
process_ai_result = normalize_amendment_payload


def parse_amendment_document(filepath):
    """
    Main entry point. Reads file, detects size, and chooses strategy.
    """
    print(f"Reading amendment file: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    content = clean_text(content)

    det = try_deterministic_amendment_parse(filepath, content=content)
    if det:
        base = os.path.basename(filepath).replace("\\", "/").lower()
        if base == "ra_6968_1990.md":
            print("  [OK] Using offline deterministic parser for Republic Act No. 6968.")
        elif base == "ra_10951_2017.md":
            print(
                "  [OK] Using offline deterministic parser for Republic Act No. 10951 "
                "(RPC Art. 136 fines / Section 6)."
            )
        return det

    # Check size - if small (< 30k chars), use single shot
    if len(content) < 30000:
        try:
            return parse_full_document_ai(content)
        except Exception as e:
            if os.path.basename(filepath).replace("\\", "/").lower() == "ra_6968_1990.md":
                offline = parse_ra6968_offline(content)
                if offline:
                    print(f"  [WARN] AI parse failed ({e}); falling back to offline RA 6968 extractor.")
                    return process_ai_result(offline, content)
            raise

    print(f"  [INFO] Large document detected ({len(content)} chars). Using batch processing...")
    return parse_chunked_document_ai(content)

def parse_metadata_ai(header_content):
    """
    Extracts purely metadata (ID, Date, Title) from the document header.
    """
    prompt = """Extract metadata from this legal document header.
    Return JSON: { "amendment_id": "string", "date": "YYYY-MM-DD", "title": "string" }
    
    Header content:
    """ + f"```\n{header_content}\n```"

    try:
        model = get_amendment_primary_model()
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={"response_mime_type": "application/json", "temperature": 0.0}
        )
        return json.loads(response.text)
    except:
        return {}

def parse_full_document_ai(content):
    """
    Original single-shot logic for smaller files.
    """
    prompt = get_parser_prompt(content)
    try:
        model = get_amendment_primary_model()
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={"response_mime_type": "application/json", "temperature": 0.0}
        )
        result = json.loads(response.text)
        return process_ai_result(result, content)
    except Exception as e:
        print(f"AI Parse Error: {e}")
        raise e

def parse_chunked_document_ai(content):
    """
    Splits large documents into chunks (by Section) and processes them iteratively.
    """
    # 1. Extract Metadata from the first 5000 chars
    metadata = parse_metadata_ai(content[:5000])

    # 2. Split by "**Section" or "Section"
    sections = re.split(r'(?=\n\s*(?:\*\*|)?Section\s+\d+)', content.strip())

    # Filter empty
    sections = [s for s in sections if s.strip()]

    # 3. Batch sections
    BATCH_SIZE = 15
    all_changes = []

    import math
    num_batches = math.ceil(len(sections) / BATCH_SIZE)

    print(f"  [INFO] Split into {len(sections)} sections. Processing in {num_batches} batches...")

    for i in range(0, len(sections), BATCH_SIZE):
        batch = sections[i:i+BATCH_SIZE]
        batch_text = "\n".join(batch)

        print(f"    Processing batch {i//BATCH_SIZE + 1}/{num_batches}...")

        prompt = get_parser_prompt(batch_text, extract_metadata=False)
        try:
            model = get_amendment_chunk_model()
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config={"response_mime_type": "application/json", "temperature": 0.0}
            )
            result = json.loads(response.text)
            changes = result.get('changes', [])
            all_changes.extend(changes)
        except Exception as e:
            print(f"    [!] Error in batch {i//BATCH_SIZE + 1}: {e}")
            raise e

    # 4. Construct final object
    final_result = {
        "amendment_id": metadata.get('amendment_id'),
        "date": metadata.get('date'),
        "title": metadata.get('title'),
        "changes": all_changes
    }

    return process_ai_result(final_result, content)

def get_parser_prompt(content, extract_metadata=True):
    meta_instruction = ""
    if extract_metadata:
        meta_instruction = """
    1. **amendment_id**: The identifier of the law.
    2. **date**: The date of approval (YYYY-MM-DD).
    3. **title**: The comprehensive title."""

    prompt = f"""You are a specialized Legal Text Parser.

    **CRITICAL INSTRUCTION - TEXTUAL FIDELITY:**
    When extracting "new_text", provide a **LITERAL, 100% EXACT COPY** of the amendatory RPC provision only.
    - NO PARAPHRASING.
    - PRESERVE PUNCTUATION.
    - **STOP at the end of the quoted / amendatory article text.** Do NOT append from the same Act:
      repealing clauses, separability clauses, effectivity clauses, enrollment lines, or "Approved:" dates.

    **Extraction Targets:**{meta_instruction}
    4. **changes**: List of amendments. For each:
       - **article_number**: String (e.g. "125", "172-A"). MUST capture suffix letters.
       - **new_text**: FULL text of the amended RPC article only (LITERAL COPY). If repealed, write "REPEALED".
       - **action**: "amend", "insert", or "repeal".

    **Input Document:**
    ```
    {content}
    ```

    **Output Format:**
    JSON: {{ "changes": [ {{ "article_number": "123", "new_text": "...", "action": "amend" }}, {{ "article_number": "172-A", "new_text": "...", "action": "insert" }} ] {', "amendment_id": "...", "date": "...", "title": "..."' if extract_metadata else ''} }}
    """
    return prompt

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="Path to amendment markdown file")
    args = parser.parse_args()

    if args.file:
        try:
            res = parse_amendment_document(args.file)
            print("Parsing successful!")
            print(json.dumps(res, indent=2))
        except Exception as e:
            print(f"Failed to parse: {e}")
            sys.exit(1)
