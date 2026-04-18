
import os
import sys
import re
import json
from google import genai
from google.genai import types

from lexcode_genai_client import get_genai_client, get_amendment_primary_model, get_amendment_chunk_model

# Initialize Shared Client (supports Vertex AI redirection)
client = get_genai_client()

def clean_text(text):
    """
    Cleans up encoding artifacts and normalizes text.
    """
    text = text.replace("â€“", "-").replace("â€œ", '"').replace("â€", '"').replace("â€™", "'")
    return text

def _slice_ra6968_section_body(content: str, section_num: int):
    """Return markdown after **Section N.** through the line before **Section N+1.**."""
    nxt = section_num + 1
    m = re.search(
        rf"\*\*Section\s+{section_num}\.\*\*(.*?)(?=\n\*\*Section\s+{nxt}\.)",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    return m.group(1).strip() if m else None


def _ra6968_quoted_payload_to_new_text(section_inner: str) -> str:
    """
    After the 'read as follows:' / 'adding a new article as follows:' preamble, RA 6968 uses
    one or more opening-double-quote lines. Strip those wrappers per line and join paragraphs.
    """
    m = re.search(
        r"(?:read as follows:\s*\n+|adding a new article as follows:\s*\n+)(.*)$",
        section_inner,
        re.DOTALL | re.IGNORECASE,
    )
    if not m:
        return ""
    blob = m.group(1).strip()
    lines = blob.split("\n")
    cleaned: list[str] = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith('"'):
            s = s[1:]
        if s.endswith('"'):
            s = s[:-1]
        cleaned.append(s)
    return "\n\n".join(cleaned).strip()


def _parse_ra6968_offline(content: str):
    """
    Deterministic parse of LexCode/Codals/md/ra_6968_1990.md (no Gemini).
    Returns the same shape as the AI parser before process_ai_result.
    """
    s2 = _slice_ra6968_section_body(content, 2)
    s3 = _slice_ra6968_section_body(content, 3)
    s4 = _slice_ra6968_section_body(content, 4)
    s5 = _slice_ra6968_section_body(content, 5)
    if not all((s2, s3, s4, s5)):
        return None
    t134 = _ra6968_quoted_payload_to_new_text(s2)
    t134a = _ra6968_quoted_payload_to_new_text(s3)
    t135 = _ra6968_quoted_payload_to_new_text(s4)
    t136 = _ra6968_quoted_payload_to_new_text(s5)
    if not all((t134, t134a, t135, t136)):
        return None
    return {
        "amendment_id": "Republic Act No. 6968",
        "date": "1990-10-24",
        "title": (
            "An Act Punishing the Crime of Coup D′ÉTAT by Amending Articles 134, 135 and 136 "
            "of Chapter One, Title Three of Act No. 3815 (RPC), and for Other Purposes"
        ),
        "changes": [
            {"article_number": "134", "new_text": t134, "action": "amend"},
            {"article_number": "134-A", "new_text": t134a, "action": "insert"},
            {"article_number": "135", "new_text": t135, "action": "amend"},
            {"article_number": "136", "new_text": t136, "action": "amend"},
        ],
    }


def _ra10951_gt_blockquote_payload_to_plain(payload: str) -> str:
    """Strip leading `>` blockquote markers and amendatory double-quotes (RA 10951 markdown)."""
    lines_out: list[str] = []
    for raw_line in payload.split("\n"):
        s = raw_line.strip()
        if not s:
            continue
        if s.startswith(">"):
            s = s[1:].strip()
        if s.startswith('"'):
            s = s[1:]
        if s.endswith('"'):
            s = s[:-1]
        lines_out.append(s)
    return "\n\n".join(lines_out).strip()


def parse_ra10951_offline_rpc_articles_134_to_136(filepath: str):
    """
    Deterministic extract for RA 10951 as it affects RPC Art. 134–136 *in this repo's md*.

    In `LexCode/Codals/md/ra_10951_2017.md`, only **Section 6** amends **Article 136** (fines after
    RA 6968). Articles 134, 134-A, and 135 are not further amended by RA 10951 in that file, so the
    returned `changes` list contains **only article 136**.

    Returns the same shape as parse_amendment_document (post- process_ai_result).
    """
    with open(filepath, encoding="utf-8") as f:
        content = clean_text(f.read())
    m = re.search(
        r"\*\*Section\s+6\.\*\*(.*?)(?=\n\*\*Section\s+7\.)",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if not m:
        return None
    inner = m.group(1)
    if not re.search(r"Article\s+136", inner, re.IGNORECASE):
        return None
    m2 = re.search(
        r"hereby\s+amended\s+to\s+read\s+as\s+follows:\s*\n+(.*)$",
        inner,
        re.DOTALL | re.IGNORECASE,
    )
    if not m2:
        return None
    payload = m2.group(1).strip()
    t136 = _ra10951_gt_blockquote_payload_to_plain(payload)
    if not t136:
        return None
    raw = {
        "amendment_id": "Republic Act No. 10951",
        "date": "2017-08-29",
        "title": (
            "An Act Adjusting the Amount or the Value of Property and Damage on Which a Penalty is "
            "Based and the Fines Imposed Under the Revised Penal Code (RA 10951)"
        ),
        "changes": [{"article_number": "136", "new_text": t136, "action": "amend"}],
    }
    return process_ai_result(raw, content)


def parse_amendment_document(filepath):
    """
    Main entry point. Reads file, detects size, and chooses strategy.
    """
    print(f"Reading amendment file: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Step 1: Clean Content
    content = clean_text(content)

    base = os.path.basename(filepath).replace("\\", "/").lower()
    if base == "ra_6968_1990.md":
        offline = _parse_ra6968_offline(content)
        if offline:
            print("  [OK] Using offline deterministic parser for Republic Act No. 6968.")
            return process_ai_result(offline, content)

    if base == "ra_10951_2017.md":
        offline_ra10951 = parse_ra10951_offline_rpc_articles_134_to_136(filepath)
        if offline_ra10951:
            print(
                "  [OK] Using offline deterministic parser for Republic Act No. 10951 "
                "(RPC Art. 136 fines / Section 6)."
            )
            return offline_ra10951

    # Check size - if small (< 30k chars), use single shot
    if len(content) < 30000:
        try:
            return parse_full_document_ai(content)
        except Exception as e:
            if os.path.basename(filepath).replace("\\", "/").lower() == "ra_6968_1990.md":
                offline = _parse_ra6968_offline(content)
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
    # We regex split but keep delimiters
    # Pattern: Look for "**Section" or just "Section" at start of line
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
            # Continue to next batch? Or fail? let's fail to be safe
            raise e
            
    # 4. Construct final object
    final_result = {
        "amendment_id": metadata.get('amendment_id'),
        "date": metadata.get('date'),
        "title": metadata.get('title'),
        "changes": all_changes
    }
    
    return process_ai_result(final_result, content)

def _strip_trailing_act_sections_from_rpc136(new_text: str, article_number: str) -> str:
    """
    RA 6968 (and similar) markdown places Art. 136 immediately before **Section 6** (repealing clause).
    Gemini sometimes concatenates Sections 6–8 + 'Approved:' into new_text. Drop everything from the
    first such marker onward (codal body must be only the amendatory article text).
    """
    if not new_text or str(article_number).strip() != "136":
        return new_text
    t = new_text.replace("\r\n", "\n").strip()
    cut_patterns = [
        r"\n\s*\*\*Section\s+6\.",
        r"\n\s*#{1,6}\s*Section\s+6\.",
        r"\n\s*Section\s+6\.\s*\*?\*?Repealing",
        r"\n\s*-\s*All laws, executive orders, rules and regulations,\s*or any part thereof inconsistent",
        r"\n\s*Approved:\s*",
        r"\n\s*\*\*Section\s+7\.\s*\*?\*?Separability",
    ]
    earliest = None
    for pat in cut_patterns:
        m = re.search(pat, t, re.IGNORECASE | re.MULTILINE)
        if m:
            earliest = m.start() if earliest is None else min(earliest, m.start())
    if earliest is not None:
        t = t[:earliest].strip()
    # Drop a trailing line that is only a closing quote from the amendatory extract
    t = re.sub(r'\n\s*"\s*$', "", t)
    return t.strip()


def process_ai_result(result, raw_content):
    """
    Standardizes the AI JSON output.
    """
    cleaned_changes = []
    for change in result.get('changes', []):
        text = change.get('new_text', '').strip()
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1].strip()

        text = _strip_trailing_act_sections_from_rpc136(text, str(change.get("article_number", "")))
            
        cleaned_changes.append({
            "article_number": str(change['article_number']), # Force string
            "new_text": text,
            "action": change.get("action", "amend").lower()
        })

    return {
        "amendment_id": result.get('amendment_id'),
        "date": result.get('date'),
        "title": result.get('title'),
        "changes": cleaned_changes,
        "raw_content": raw_content
    }

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
