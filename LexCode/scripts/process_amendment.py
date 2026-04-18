from __future__ import annotations

import os
import json
import sys
import re
import psycopg2
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_api = str(_REPO_ROOT / "api")
if _api not in sys.path:
    sys.path.insert(0, _api)
from codal_text import normalize_storage_markdown

from parse_amendment import parse_amendment_document, parse_ra10951_offline_rpc_articles_134_to_136
from apply_amendment import apply_amendment_with_ai
from manual_amendment_spec import load_manual_amendment

def get_db_connection():
    conn_str = os.environ.get("DB_CONNECTION_STRING", "").strip()
    if conn_str:
        return psycopg2.connect(conn_str)
    api_settings = _REPO_ROOT / "api" / "local.settings.json"
    try:
        with open(api_settings, encoding="utf-8") as f:
            conn_str = json.load(f)["Values"]["DB_CONNECTION_STRING"]
    except Exception:
        conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
    return psycopg2.connect(conn_str)

def fetch_current_article(conn, code_id, article_number, as_of_date=None):
    """
    Fetch the current version of an article at a given date.
    """
    cur = conn.cursor()
    
    if as_of_date:
        query = """
            SELECT version_id, content, valid_from, valid_to, amendment_id
            FROM article_versions
            WHERE code_id = %s
                AND article_number = %s
                AND valid_from <= %s
                AND (valid_to IS NULL OR valid_to > %s)
            ORDER BY valid_from DESC
            LIMIT 1
        """
        cur.execute(query, (code_id, article_number, as_of_date, as_of_date))
    else:
        # Get latest version (valid_to IS NULL)
        query = """
            SELECT version_id, content, valid_from, valid_to, amendment_id
            FROM article_versions
            WHERE code_id = %s
                AND article_number = %s
                AND valid_to IS NULL
            LIMIT 1
        """
        cur.execute(query, (code_id, article_number))
    
    row = cur.fetchone()
    cur.close()
    
    if row:
        return {
            "version_id": row[0],
            "content": row[1],
            "valid_from": row[2],
            "valid_to": row[3],
            "amendment_id": row[4]
        }
    return None

def fetch_article_history(conn, code_id, article_number):
    """
    Fetches the full history chain of an article for context.
    Returns list of dicts: [{amendment_id, valid_from, description, content_snippet}]
    """
    cur = conn.cursor()
    query = """
        SELECT amendment_id, valid_from, amendment_description, content
        FROM article_versions
        WHERE code_id = %s AND article_number = %s
        ORDER BY valid_from ASC
    """
    cur.execute(query, (code_id, article_number))
    rows = cur.fetchall()
    cur.close()
    
    history = []
    for r in rows:
        # User requested FULL historical text, so we do not truncate.
        history.append({
            "amendment_id": r[0] or "Original",
            "date": str(r[1]),
            "description": r[2] or "No description",
            "content": r[3]  # Full content
        })
    return history

def parse_article_title_body(text):
    """
    Extracts title and body from article text.
    Formats:
      - "Article 123. The Title. - Body..." / "Art. 123. *Title* – Body..."
      - "Article 123. Title. Body" (first sentence break)
    """
    text = (text or "").strip()
    if not text:
        return None, ""

    # RA-style italic run-in title after Art. N. ... *title* - body
    # Using a comprehensive dash set: hyphen (-), en-dash (–), em-dash (—)
    DASHES = r"[-–—]"
    
    m_italic = re.match(
        rf"^(?:Article|Art\.)\s+(\d+[A-Za-z-]*)\.\s*\*(.+?)\*\s*{DASHES}\s*(.+)$",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    def clean_title(t):
        if not t: return ""
        # Remove markdown bold/italic markers
        t = re.sub(r"[\*_]+", "", t).strip()
        # Title case but keep Roman numerals or specific legal acronyms if possible 
        # (For now simple .title() is requested)
        return t.title()

    if m_italic:
        title = m_italic.group(2)
        return clean_title(title), m_italic.group(3).strip()

    # Generic split: "Article N. Title [Separator] Body"
    # Prioritize ". - " or ".* - " or " - " (even without period if starred)
    m_dash = re.search(
        rf"^(?:Article|Art\.)\s+(\d+[A-Za-z-]*)\.\s+(.*?[\.\*]?)\s*{DASHES}\s+(.*)$",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if m_dash:
        title = m_dash.group(2)
        return clean_title(title), m_dash.group(3).strip()

    # Try with first sentence period (restricted to first line to prevent greediness)
    m_period = re.search(
        r"^(?:Article|Art\.)\s+(\d+[A-Za-z-]*)\.\s+([^\n.]+?)\.\s+(.*)$",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if m_period:
        title = m_period.group(2)
        return clean_title(title), m_period.group(3).strip()

    # Fallback: first line starts with Article (full word) and body on following lines
    lines = text.split("\n", 1)
    if lines and "Article" in lines[0] and re.search(r"Article\s+\d+", lines[0], re.IGNORECASE):
        title_part = re.sub(r"Article\s+\d+\.\s*", "", lines[0])
        return clean_title(title_part), lines[1] if len(lines) > 1 else ""

    return None, text

def update_const_codal(conn, article_number, new_content, amendment_id, amendment_date, description, code_short_name):
    """
    Syncs the update to the main const_codal view table.
    """
    cur = conn.cursor()
    try:
        # const_codal stores article_num as e.g. FC-I-36
        # we can search by LIKE '%-' || %s OR article_num = %s
        cur.execute("SELECT id, amendments, article_title FROM const_codal WHERE book_code = %s AND (article_num = %s OR article_num LIKE '%%-' || %s)", (code_short_name, article_number, article_number))
        row = cur.fetchone()
        
        if row:
            cid, existing_amendments, existing_title = row
            
            # Update Amendments JSON
            if existing_amendments is None:
                existing_amendments = []
            elif isinstance(existing_amendments, str):
                existing_amendments = json.loads(existing_amendments)
            
            # Avoid duplicates
            if not any(a.get('id') == amendment_id for a in existing_amendments):
                existing_amendments.append({
                    "id": amendment_id,
                    "date": amendment_date,
                    "description": description
                })
            
            # Update Row
            update_sql = """
                UPDATE const_codal 
                SET content_md = %s,
                    amendments = %s,
                    updated_at = NOW()
                WHERE id = %s
            """
            cur.execute(update_sql, (normalize_storage_markdown(new_content), json.dumps(existing_amendments), cid))
            print(f"    [SYNC] const_codal updated for Art {article_number}")
            
        else:
            print(f"    [SYNC] Article {article_number} not found in const_codal. Treating as new insertion not fully supported for const_codal yet.")
            
    except Exception as e:
        print(f"    [!] Failed to sync const_codal: {e}")
        raise e
    finally:
        cur.close()

def update_rpc_codal(conn, article_number, new_content, amendment_id, amendment_date, description):
    """
    Syncs the update to the main rpc_codal view table.
    """
    cur = conn.cursor()
    try:
        # 1. Parse new Title and Body
        title, body = parse_article_title_body(new_content)
        body = normalize_storage_markdown(body)
        if not title:
            # If parsing fails, use a placeholder or keep existing?
            # Better to fetch existing loop? No, assume the amendment provides the full text including title.
            # If we match "Article X.", use the rest as title?
             title = "Unknown Title"

        # 2. Check if article exists in rpc_codal
        cur.execute("SELECT id, amendments, article_title FROM rpc_codal WHERE article_num = %s", (article_number,))
        row = cur.fetchone()
        
        if row:
            rpc_id, existing_amendments, existing_title = row
            
            # Fallback for title if parsing failed (common in Repeals or partial text updates)
            if title == "Unknown Title" and existing_title:
                title = existing_title
                # Optional: Mark as [REPEALED] if content clearly says so?
                if "REPEALED" in new_content.upper():
                    if not "[REPEALED]" in title:
                        title += " [REPEALED]"

            # Update Amendments JSON
            if existing_amendments is None:
                existing_amendments = []
            elif isinstance(existing_amendments, str):
                existing_amendments = json.loads(existing_amendments)
            
            # Avoid duplicates
            if not any(a.get('id') == amendment_id for a in existing_amendments):
                existing_amendments.append({
                    "id": amendment_id,
                    "date": amendment_date,
                    "description": description
                })
            
            # Update Row
            update_sql = """
                UPDATE rpc_codal 
                SET article_title = %s,
                    content_md = %s,
                    amendments = %s,
                    updated_at = NOW()
                WHERE id = %s
            """
            cur.execute(update_sql, (title, body, json.dumps(existing_amendments), rpc_id))
            print(f"    [SYNC] rpc_codal updated for Art {article_number}")
            
        else:
            print(f"    [SYNC] Article {article_number} not found in rpc_codal. Inserting new record.")
            # Copy Book/Title/Chapter from Art. 134 (RA 6968 inserts 134-A immediately after 134).
            cur.execute(
                """
                SELECT book, book_label, title_num, title_label, chapter_label, chapter_num,
                       section_label, section_num
                FROM rpc_codal
                WHERE article_num = '134'
                LIMIT 1
                """
            )
            anchor = cur.fetchone()
            initial_amendments = json.dumps(
                [{"id": amendment_id, "date": amendment_date, "description": description}]
            )
            if anchor:
                (
                    book,
                    book_label,
                    title_num,
                    title_label,
                    chapter_label,
                    chapter_num,
                    section_label,
                    section_num,
                ) = anchor
                insert_sql = """
                    INSERT INTO rpc_codal
                    (article_num, article_title, content_md, amendments,
                     book, book_label, title_num, title_label, chapter_label, chapter_num,
                     section_label, section_num, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """
                cur.execute(
                    insert_sql,
                    (
                        article_number,
                        title,
                        body,
                        initial_amendments,
                        book,
                        book_label,
                        title_num,
                        title_label,
                        chapter_label,
                        chapter_num,
                        section_label,
                        section_num,
                    ),
                )
            else:
                insert_sql = """
                    INSERT INTO rpc_codal
                    (article_num, article_title, content_md, amendments, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, NOW(), NOW())
                """
                cur.execute(insert_sql, (article_number, title, body, initial_amendments))
            
    except Exception as e:
        print(f"    [!] Failed to sync rpc_codal: {e}")
        raise e # Re-raise to ensure failure is reported and transaction rolled back
        # Don't raise, as article_versions update might have succeeded
    finally:
        cur.close()

def apply_amendment_to_database(
    conn,
    code_id,
    article_number,
    new_content,
    amendment_id,
    amendment_date,
    description=None,
    code_short_name="RPC",
    replace_active_version=False,
):
    """
    Updates the database with a new article version.

    If replace_active_version is True, updates the current open row (valid_to IS NULL) in place
    instead of closing it and inserting a duplicate tip — used when --force re-applies the same
    amendment_id to correct bad content.
    """
    cur = conn.cursor()
    
    try:
        if replace_active_version:
            cur.execute(
                """
                UPDATE article_versions
                SET content = %s, amendment_description = %s
                WHERE code_id = %s
                  AND article_number = %s
                  AND valid_to IS NULL
                """,
                (new_content, description, code_id, article_number),
            )
            if cur.rowcount == 0:
                replace_active_version = False

        if not replace_active_version:
            # Step 1: Close current version
            update_query = """
                UPDATE article_versions
                SET valid_to = %s
                WHERE code_id = %s
                AND article_number = %s
                AND valid_to IS NULL
            """
            cur.execute(update_query, (amendment_date, code_id, article_number))

            # Step 2: Insert new version
            insert_query = """
                INSERT INTO article_versions
                (code_id, article_number, content, valid_from, valid_to, amendment_id, amendment_description)
                VALUES (%s, %s, %s, %s, NULL, %s, %s)
            """
            cur.execute(
                insert_query,
                (code_id, article_number, new_content, amendment_date, amendment_id, description),
            )
        
        # Step 3: Sync to main Present View
        if code_short_name == "RPC":
            update_rpc_codal(conn, article_number, new_content, amendment_id, amendment_date, description)
        elif code_short_name in ["FC", "CONST"]:
            update_const_codal(conn, article_number, new_content, amendment_id, amendment_date, description, code_short_name)
        
        # Step 4: Auto-Generate Structural Map for Band Visualization
        try:
            print(f"    [MAP] Generating structural map for Art {article_number}...")
            # Use local import to avoid circular dependency issues if any
            from structural_mapper import generate_and_save_map
            generate_and_save_map(article_number, conn=conn)
        except Exception as map_err:
            print(f"    [WARN] Failed to generate structural map: {map_err}")

        print("DEBUG: Committing transaction...")
        try:
            conn.commit()
            print("DEBUG: Commit successful.")
            return True
        except Exception as commit_err:
            print(f"DEBUG: Commit FAILED: {commit_err}")
            raise commit_err
        
    except Exception as e:
        conn.rollback()
        print(f"Database error: {e}")
        with open("error_log.txt", "a") as f:
            f.write(f"Article {article_number} DB Error: {str(e)}\n")
        return False
    finally:
        cur.close()

def process_amendment(
    amendment_file=None,
    code_short_name="RPC",
    dry_run=False,
    force=False,
    only_article=None,
    offline_ra6968=False,
    offline_ra10951_rpc=False,
    amendment_json_path=None,
):
    print(f"\n{'='*70}")
    print(f"CODEX AMENDMENT PROCESSOR")
    print(f"{'='*70}\n")

    only_key = str(only_article).strip() if only_article is not None else None

    json_path: Path | None = None
    if amendment_json_path:
        json_path = Path(amendment_json_path)
        if not json_path.is_file():
            json_path = _REPO_ROOT / amendment_json_path
        if not json_path.is_file():
            return {"success": False, "error": f"Amendment JSON not found: {amendment_json_path}"}
        json_path = json_path.resolve()

    if json_path and (offline_ra6968 or offline_ra10951_rpc):
        return {
            "success": False,
            "error": "Do not combine --amendment-json with --offline-ra6968 or --offline-ra10951-rpc.",
        }

    if not json_path:
        if not amendment_file:
            return {"success": False, "error": "Provide amendment_file or amendment_json_path."}
        path = Path(amendment_file)
        if not path.is_file():
            path = _REPO_ROOT / amendment_file
        if not path.is_file():
            return {"success": False, "error": f"Amendment file not found: {amendment_file}"}
        amendment_file = str(path.resolve())

        if offline_ra6968 and offline_ra10951_rpc:
            return {
                "success": False,
                "error": "Use only one of --offline-ra6968 or --offline-ra10951-rpc.",
            }
        if offline_ra6968 and "ra_6968" not in str(amendment_file).lower():
            return {
                "success": False,
                "error": "--offline-ra6968 is only valid for LexCode/Codals/md/ra_6968_1990.md",
            }
        if offline_ra10951_rpc and "ra_10951" not in str(amendment_file).lower():
            return {
                "success": False,
                "error": "--offline-ra10951-rpc is only valid for LexCode/Codals/md/ra_10951_2017.md",
            }

    apply_literal = bool(json_path or offline_ra6968 or offline_ra10951_rpc)

    # Step 1: Parse amendment (markdown / offline flags) or load manual JSON
    print(f"[1/5] Parsing amendment document...")
    try:
        if json_path:
            amendment = load_manual_amendment(json_path)
            if not amendment.get("changes"):
                raise ValueError("Manual spec has no changes")
            print(f"  [OK] Loaded manual JSON: {json_path}")
        elif offline_ra10951_rpc:
            amendment = parse_ra10951_offline_rpc_articles_134_to_136(amendment_file)
            if not amendment or not amendment.get("changes"):
                raise ValueError(
                    "Offline RA 10951 RPC extract failed (expected Section 6 / Article 136 block)."
                )
            print("  [OK] Using offline RA 10951 RPC extract (Article 136 only in this source).")
        else:
            amendment = parse_amendment_document(amendment_file)
        if not amendment.get("date"):
            raise ValueError("No valid date in amendment payload")
        print(f"  [OK] Amendment ID: {amendment['amendment_id']}")
        print(f"  [OK] Date: {amendment['date']}")
        print(f"  [OK] Changes found: {len(amendment['changes'])}")
    except Exception as e:
        print(f"  [X] Failed to parse: {e}")
        return {"success": False, "error": str(e)}
    
    # Step 2: Connect to database
    print(f"\n[2/5] Connecting to database...")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get code_id
        cur.execute("SELECT code_id FROM legal_codes WHERE short_name = %s", (code_short_name,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Code '{code_short_name}' not found in database")
        code_id = row[0]
        print(f"  [OK] Code ID: {code_id}")
        
    except Exception as e:
        print(f"  [X] Database connection failed: {e}")
        return {"success": False, "error": str(e)}
    
    # Step 3: Process each change
    print(f"\n[3/5] Processing amendments...")
    results = []
    matched_changes = 0
    
    for idx, change in enumerate(amendment['changes'], 1):
        article_num = change['article_number']
        if only_key is not None and str(article_num) != only_key:
            continue
        matched_changes += 1
        print(f"\n  Article {article_num} ({idx}/{len(amendment['changes'])}):")
        
        # Fetch current version
        current_article = fetch_current_article(conn, code_id, article_num)
        
        final_content = None
        replace_active = bool(
            force
            and current_article
            and current_article.get("amendment_id") == amendment["amendment_id"]
        )
        
        if current_article:
             # IDEMPOTENCY CHECK:
             # If the latest version was already modified by THIS amendment, skip it.
             if current_article.get('amendment_id') == amendment['amendment_id'] and not force:
                 print(f"    [SKIP] Article {article_num} already updated by {amendment['amendment_id']}")
                 results.append({"article": article_num, "success": True, "note": "Already applied"})
                 continue
             if replace_active:
                 print(f"    [FORCE] Re-applying {amendment['amendment_id']} on Article {article_num} (in-place active version)")
            
             # CHECK FOR REPEAL ACTION
             if change.get('action') == 'repeal':
                 print(f"    [!] REPEAL action detected for Article {article_num}")
                 # Create a tombstone version saying "REPEALED" for clarity
                 final_content = f"REPEALED BY {amendment['amendment_id']}"
                 description = f"Repealed Article {article_num} via {amendment['amendment_id']}."
                 ai_result = {'success': True, 'new_text': final_content, 'validation_result': {'confidence_score': 1.0}, 'description': description}
             elif apply_literal:
                 print(f"    [LITERAL] Applying literal new_text (no merge model).")
                 final_content = normalize_storage_markdown(change["new_text"])
                 description = (
                     f"Literal codal text from {amendment['amendment_id']} source file (offline pipeline)."
                 )
                 ai_result = {
                     "success": True,
                     "new_text": final_content,
                     "validation_result": {"confidence_score": 1.0},
                     "description": description,
                 }
             else:
                 print(f"    Current version (valid from {current_article['valid_from']})")
                 
                 # Apply amendment with AI
                 print(f"    Applying amendment with AI...")
                 print(f"    [DEBUG] Current len: {len(current_article['content'])}")
                 # Safe print for windows terminals
                 safe_text = change['new_text'][:100].encode('cp1252', 'replace').decode('cp1252')
                 print(f"    [DEBUG] Amendment text: {safe_text}...")
                 
                 # Extract prior info
                 prior_id = current_article.get('amendment_id')
                 if not prior_id: prior_id = "Original RPC (Act No. 3815)"
                 prior_date = str(current_article.get('valid_from', '1932-01-01'))
    
                 # Fetch full history for context
                 history = fetch_article_history(conn, code_id, article_num)
    
                 ai_result = apply_amendment_with_ai(
                     current_article['content'], 
                     change['new_text'],
                     amendment_id=amendment['amendment_id'],
                     prior_amendment_id=prior_id,
                     prior_date=prior_date,
                     history=history
                 )
                
                 if not ai_result['success']:
                    # Check if it's a no-change scenario
                    if ai_result.get('no_change'):
                        print(f"    [SKIP] Article not substantively modified by this amendment")
                        results.append({"article": article_num, "success": True, "note": "No substantive change"})
                        continue
                    
                    print(f"    [X] AI application failed: {ai_result['error']}")
                    results.append({"article": article_num, "success": False, "error": ai_result['error']})
                    continue
                
                 print(f"    [OK] AI application successful (confidence: {ai_result['validation_result']['confidence_score']:.2f})")
                 final_content = ai_result['new_text']
                 description = ai_result['description']
        else:
             print(f"    [!] Article {article_num} not found in database - Treating as NEW INSERTION.")
             if apply_literal:
                 final_content = normalize_storage_markdown(change["new_text"])
                 description = (
                     f"Inserted Article {article_num} via {amendment['amendment_id']} (offline literal)."
                 )
             else:
                 # For new insertions, we verify the text looks complete
                 final_content = change['new_text']
                 # Basic cleanup if not done by parser
                 final_content = final_content.strip('"').strip()
                 description = f"Inserted Article {article_num} via {amendment['amendment_id']}."
             ai_result = {'success': True, 'new_text': final_content, 'validation_result': {'confidence_score': 1.0}, 'description': description}

        # Update database
        if not dry_run:
            success = apply_amendment_to_database(
                conn, code_id, article_num,
                final_content,
                amendment['amendment_id'],
                amendment['date'],
                description=description,
                code_short_name=code_short_name,
                replace_active_version=replace_active,
            )
            if success:
                print(f"    [OK] Database updated")
                results.append({"article": article_num, "success": True})
            else:
                print(f"    [X] Database update failed")
                results.append({"article": article_num, "success": False, "error": "DB update failed"})
        else:
            print(f"    [/] Dry run - database not updated")
            results.append({"article": article_num, "success": True, "dry_run": True})
    
    if only_key is not None and matched_changes == 0:
        conn.close()
        return {
            "success": False,
            "error": f"No amendment change matched --only-article {only_key!r}",
        }

    # Step 4: Generate report
    print(f"\n{'='*70}")
    print(f"SUMMARY REPORT")
    print(f"{'='*70}")
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    print(f"Total Changes: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    if dry_run:
        print(f"\n[!] DRY RUN MODE - No database changes were made")
    
    conn.close()
    
    return {
        "success": failed == 0,
        "amendment_id": amendment['amendment_id'],
        "total": len(results),
        "successful": successful,
        "failed": failed,
        "results": results
    }

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Process legal amendment documents")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", default=None, help="Path to amendment markdown file")
    src.add_argument(
        "--amendment-json",
        dest="amendment_json",
        default=None,
        metavar="PATH",
        help="Manual amendment spec JSON (literal apply, no AI merge). Used by reingest_rpc_manual_pipeline.py.",
    )
    parser.add_argument("--code", default="RPC", help="Code short name (default: RPC)")
    parser.add_argument("--dry-run", action="store_true", help="Don't update database, just validate")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-apply even if article_versions already shows this amendment_id (fixes bad prior apply).",
    )
    parser.add_argument(
        "--only-article",
        default=None,
        metavar="NUM",
        help="Process only this article_number from the parsed changes (e.g. 136).",
    )
    parser.add_argument(
        "--offline-ra6968",
        action="store_true",
        help="For ra_6968_1990.md: use literal Section extracts (no Gemini merge). Requires deterministic parse.",
    )
    parser.add_argument(
        "--offline-ra10951-rpc",
        action="store_true",
        help=(
            "For ra_10951_2017.md: extract RA 10951 Section 6 (RPC Art. 136 fines) only; apply literally. "
            "Articles 134, 134-A, and 135 are not amended by RA 10951 in this markdown."
        ),
    )
    
    args = parser.parse_args()
    
    result = process_amendment(
        args.file,
        args.code,
        args.dry_run,
        force=args.force,
        only_article=args.only_article,
        offline_ra6968=args.offline_ra6968,
        offline_ra10951_rpc=args.offline_ra10951_rpc,
        amendment_json_path=args.amendment_json,
    )
    
    if not result["success"]:
        sys.exit(1)

if __name__ == "__main__":
    main()
