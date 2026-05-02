import os
import sys
import json
import argparse
import re
from datetime import datetime

# Add local path to imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from apply_amendment import apply_amendment_with_ai
from process_amendment import get_db_connection, fetch_current_article, apply_amendment_to_database
from lexcode_genai_client import get_genai_client, get_amendment_primary_model
from process_amendment_full_ai import classify_change_for_rpc_ingest

client = get_genai_client()

def parse_amendment_batch_with_ai(content):
    """
    Uses Gemini to extract structured amendment data from a CHUNK of raw text.
    """
    system_instruction = """You are a precise legal extraction engine. Your job is to extract amendments from Philippine legislative documents.

    Acts may amend several statutes (RPC / Act 3815, RA 8353, RA 7610, Labor Code, etc.).
    target_statute must name the **law being amended**, never the enacting Act. A special-law Section is never an RPC Article.

    Output a JSON object with this exact schema:
    {
        "amendment_id": "string (e.g., 'Republic Act No. 10951')",
        "date": "YYYY-MM-DD (string, date of approval)",
        "title": "string (the full title of the Act)",
        "changes": [
            {
                "target_statute": "RPC | RA7610 | OTHER",
                "unit_type": "article | section",
                "provision_number": "string (RPC article e.g. '266-A', or RA 7610 section number e.g. '7')",
                "new_text": "string (EXACT quoted text of the amended provision)",
                "code_reference": "optional string (same meaning as target_statute, for backward compatibility)"
            }
        ]
    }

    CRITICAL RULES:
    1. Extract "new_text" EXACTLY as it appears. Do NOT summarize.
    2. **Letters of the law only:** include an RPC row only when this Act **sets new wording** for that article (quoted block or clear amend/repeal/insert of that article). If the article is not mentioned in the amendatory sections, omit it—do not treat omission as a "formal" or confirmatory amendment.
    3. Omit articles that are only related, contextual, or indirectly affected if this Act does not change their **text**.
    4. For RPC articles use target_statute "RPC" and unit_type "article".
    5. For RA 7610 use target_statute "RA7610" and unit_type "section".
    6. For any other amended statute use target_statute "OTHER".
    """

    response = client.models.generate_content(
        model=get_amendment_primary_model(),
        contents=f"Extract amendments from this chunk of the document:\n\n{content}",
        config={
            "temperature": 0.0,
            "system_instruction": system_instruction,
            "response_mime_type": "application/json"
        }
    )
    
    try:
        text = response.text.strip()
        if text.startswith("```json"):
            text = text.replace("```json", "", 1).replace("```", "", 1).strip()
        data = json.loads(text)
        return data if isinstance(data, dict) else data[0]
    except Exception as e:
        print(f"  [ERROR] AI JSON Parse Failed for chunk: {e}")
        return None

def process_amendment_batch(
    file_path,
    code_short_name="RPC",
    dry_run=False,
    batch_size=10,
    skip_source_guard=False,
):
    print(f"\n[1/4] Batch Reading: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split into sections using Section marker
    # We look for lines starting with **Section N.**
    sections = re.split(r'(\n\*\*Section \d+\.\*\*)', content)
    
    header = sections[0]
    body_parts = sections[1:] # This contains the markers and the content
    
    # Recombine markers with their content
    refined_sections = []
    for i in range(0, len(body_parts), 2):
        if i + 1 < len(body_parts):
            refined_sections.append(body_parts[i] + body_parts[i+1])
    
    print(f"  [OK] Found {len(refined_sections)} sections to process.")
    
    all_changes = []
    amendment_info = {"id": None, "date": None}
    
    # Process in batches
    print(f"\n[2/4] Batch Extracting via AI (Size: {batch_size})...")
    for i in range(0, len(refined_sections), batch_size):
        batch = refined_sections[i:i + batch_size]
        current_chunk = header + "\n" + "\n".join(batch)
        
        print(f"  Processing Sections {i+1} to {min(i+batch_size, len(refined_sections))}...")
        batch_data = parse_amendment_batch_with_ai(current_chunk)
        
        if batch_data and "changes" in batch_data:
            all_changes.extend(batch_data["changes"])
            if not amendment_info["id"]:
                amendment_info["id"] = batch_data.get("amendment_id")
                amendment_info["date"] = batch_data.get("date")
        
        time_to_wait = 2 # Avoid aggressive rate limits
        if i + batch_size < len(refined_sections):
            import time
            time.sleep(time_to_wait)

    print(f"  [OK] Total unique changes extracted: {len(all_changes)}")
    
    # 3. Database Connection
    print(f"\n[3/4] Connecting to database...")
    conn = get_db_connection()
    if not conn: return
    
    cur = conn.cursor()
    cur.execute("SELECT code_id FROM legal_codes WHERE short_name = %s", (code_short_name,))
    row = cur.fetchone()
    if not row:
        print(f"  [FAILED] Code '{code_short_name}' not found"); return
    code_id = row[0]

    # 4. Final Application Loop
    print(f"\n[4/4] Processing Amendments (Application Phase)...")
    src_guard = None if skip_source_guard else content
    for change in all_changes:
        apply_rpc, art_num, new_text_raw, skip_reason = classify_change_for_rpc_ingest(
            change, source_markdown=src_guard
        )
        if not apply_rpc:
            print(f"\n  [SKIP] {skip_reason}")
            continue
        new_text_raw = new_text_raw or ""

        print(f"\n  RPC Article {art_num}:")
        current = fetch_current_article(conn, code_id, art_num)
        
        old_content = current['content'] if current else ""
        
        ai_result = apply_amendment_with_ai(old_content, new_text_raw, amendment_info["id"] or "Unknown")
        
        if ai_result['success'] and not dry_run:
            apply_amendment_to_database(
                conn, code_id, art_num, 
                ai_result['new_text'], 
                amendment_info["id"], 
                amendment_info["date"],
                description=ai_result.get('description')
            )
            print(f"    [OK] Database Updated")
        elif ai_result.get('no_change'):
            print(f"    [SKIP] No substantive change")
        else:
            print(f"    [FAILED] {ai_result.get('error')}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--code", default="RPC")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--no-source-guard",
        action="store_true",
        help="Disable markdown anchor/snippet validation",
    )
    args = parser.parse_args()

    process_amendment_batch(
        args.file, args.code, args.dry_run, skip_source_guard=args.no_source_guard
    )
