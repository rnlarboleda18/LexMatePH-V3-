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

from parse_amendment import parse_amendment_document
from apply_amendment import apply_amendment_with_ai

def get_db_connection():
    try:
        with open('local.settings.json') as f:
            settings = json.load(f)
            conn_str = settings['Values']['DB_CONNECTION_STRING']
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
    Format: "Article 123. The Title. - Body..."
    """
    # Regex for "Article X. Title. - Body" or "Article X. Title. Body"
    # Note: verify_art5 previously showed titles can be long.
    match = re.search(r'Article\s+\d+\.\s+(.*?)(?:\.\s*-\s*|\.\s+)(.*)', text, re.DOTALL)
    if match:
        title = match.group(1).strip()
        body = match.group(2).strip()
        return title, body
    
    # Fallback: Split by newline if header is on separate line
    lines = text.split('\n', 1)
    if len(lines) > 0:
        # Check if first line resembles a header
        header = lines[0]
        if "Article" in header:
             # Try to strip "Article X. "
             title_part = re.sub(r'Article\s+\d+\.\s*', '', header).strip()
             return title_part, lines[1] if len(lines) > 1 else ""
             
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
            # Insert new record
            # We lack Book/Title/Chapter structure, so we default to NULL or 'Unknown'.
            # Ideally we would infer this from neighbors, but for now getting the content visible is priority.
            
            initial_amendments = json.dumps([{
                "id": amendment_id,
                "date": amendment_date,
                "description": description
            }])
            
            insert_sql = """
                INSERT INTO rpc_codal 
                (article_num, article_title, content_md, amendments, created_at, updated_at)
                VALUES (%s, %s, %s, %s, NOW(), NOW())
            """
            print(f"DEBUG: Executing INSERT for {article_number}")
            print(f"DEBUG: SQL: {insert_sql}")
            print(f"DEBUG: Values: {(article_number, title, body[:20], initial_amendments)}")
            cur.execute(insert_sql, (article_number, title, body, initial_amendments))
            
    except Exception as e:
        print(f"    [!] Failed to sync rpc_codal: {e}")
        raise e # Re-raise to ensure failure is reported and transaction rolled back
        # Don't raise, as article_versions update might have succeeded
    finally:
        cur.close()

def apply_amendment_to_database(conn, code_id, article_number, new_content, amendment_id, amendment_date, description=None, code_short_name="RPC"):
    """
    Updates the database with a new article version.
    """
    cur = conn.cursor()
    
    try:
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
        cur.execute(insert_query, (code_id, article_number, new_content, amendment_date, amendment_id, description))
        
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

        print(f"DEBUG: Committing transaction to {conn.dsn}...")
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

def process_amendment(amendment_file, code_short_name="RPC", dry_run=False):
    print(f"\n{'='*70}")
    print(f"CODEX AMENDMENT PROCESSOR")
    print(f"{'='*70}\n")
    
    # Step 1: Parse amendment
    print(f"[1/5] Parsing amendment document...")
    try:
        amendment = parse_amendment_document(amendment_file)
        if not amendment.get('date'):
            raise ValueError(f"No valid date found in {amendment_file}")
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
    
    for idx, change in enumerate(amendment['changes'], 1):
        article_num = change['article_number']
        print(f"\n  Article {article_num} ({idx}/{len(amendment['changes'])}):")
        
        # Fetch current version
        current_article = fetch_current_article(conn, code_id, article_num)
        
        final_content = None
        
        if current_article:
             # IDEMPOTENCY CHECK:
             # If the latest version was already modified by THIS amendment, skip it.
             if current_article.get('amendment_id') == amendment['amendment_id']:
                 print(f"    [SKIP] Article {article_num} already updated by {amendment['amendment_id']}")
                 results.append({"article": article_num, "success": True, "note": "Already applied"})
                 continue
            
             # CHECK FOR REPEAL ACTION
             if change.get('action') == 'repeal':
                 print(f"    [!] REPEAL action detected for Article {article_num}")
                 # Create a tombstone version saying "REPEALED" for clarity
                 final_content = f"REPEALED BY {amendment['amendment_id']}"
                 description = f"Repealed Article {article_num} via {amendment['amendment_id']}."
                 ai_result = {'success': True, 'new_text': final_content, 'validation_result': {'confidence_score': 1.0}, 'description': description}
             else:
                 print(f"    Current version (valid from {current_article['valid_from']})")
                 
                 # Apply amendment with AI
                 print(f"    Applying amendment with AI...")
                 print(f"    [DEBUG] Current len: {len(current_article['content'])}")
                 print(f"    [DEBUG] Amendment text: {change['new_text'][:100]}...")
                 
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
             # For new insertions, we verify the text looks complete
             final_content = change['new_text']
             # Basic cleanup if not done by parser
             final_content = final_content.strip('"').strip()
            
             # Create a dummy result for reporting
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
                code_short_name=code_short_name
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
        print(f"\n⚠ DRY RUN MODE - No database changes were made")
    
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
    parser.add_argument("--file", required=True, help="Path to amendment markdown file")
    parser.add_argument("--code", default="RPC", help="Code short name (default: RPC)")
    parser.add_argument("--dry-run", action="store_true", help="Don't update database, just validate")
    
    args = parser.parse_args()
    
    result = process_amendment(args.file, args.code, args.dry_run)
    
    if not result["success"]:
        sys.exit(1)

if __name__ == "__main__":
    main()
