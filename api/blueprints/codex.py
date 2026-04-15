import logging
import json
import os
import azure.functions as func
import psycopg2
from psycopg2.extras import RealDictCursor
import re
import gzip
from db_pool import get_db_connection, put_db_connection
from utils.clerk_auth import get_authenticated_user_id

codex_bp = func.Blueprint()

def compressed_json_response(data: dict | list, req: func.HttpRequest, status_code: int = 200, max_age: int = 3600) -> func.HttpResponse:
    json_str = json.dumps(data, default=str)
    headers = {
        "Cache-Control": f"public, max-age={max_age}",
        "Content-Type": "application/json"
    }
    
    accept_encoding = req.headers.get('Accept-Encoding', '')
    if 'gzip' in accept_encoding.lower():
        compressed_body = gzip.compress(json_str.encode('utf-8'))
        headers['Content-Encoding'] = 'gzip'
        return func.HttpResponse(body=compressed_body, headers=headers, status_code=status_code)
    else:
        return func.HttpResponse(body=json_str, headers=headers, status_code=status_code)

# Cache schema column lookups so information_schema is hit once per worker, not per request
_col_cache: dict[str, list[str]] = {}

def _get_columns(cur, table_name: str) -> list[str]:
    if table_name not in _col_cache:
        cur.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
            (table_name,)
        )
        _col_cache[table_name] = [r['column_name'] for r in cur.fetchall()]
    return _col_cache[table_name]

def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    '''
    if not text: return []
    return [ int(c) if c.isdigit() else c for c in re.split(r'(\d+)', str(text)) ]

def int_to_roman(num):
    val = [1000,900,500,400,100,90,50,40,10,9,5,4,1]
    syms = ['M','CM','D','CD','C','XC','L','XL','X','IX','V','IV','I']
    result = ''
    try:
        num = int(num)
        for i in range(len(val)):
            while num >= val[i]:
                result += syms[i]
                num -= val[i]
    except:
        return str(num)
    return result

def clean_structural_label(label):
    if not label: return ""
    # Remove "TITLE ONE: ", "CHAPTER ONE: " etc.
    cleaned = re.sub(r'^(TITLE|CHAPTER)\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN)\s*:?\s*', '', label, flags=re.IGNORECASE)
    return cleaned.strip()

def _attach_link_counts(cur, articles, statute_id):
    if not articles: return
    article_nums = [str(a.get('key_id') or a.get('article_number') or "").strip() for a in articles]
    query = """
        SELECT provision_id, target_paragraph_index, COUNT(*) as link_count
        FROM codal_case_links 
        WHERE statute_id = %s 
          AND provision_id = ANY(%s)
          AND target_paragraph_index IS NOT NULL
        GROUP BY provision_id, target_paragraph_index
    """
    try:
         cur.execute(query, (statute_id, article_nums))
         link_map = {}
         fetched_rows = cur.fetchall()
         for r in fetched_rows:
             art = str(r['provision_id']).strip()
             idx = r['target_paragraph_index']
             if art not in link_map: link_map[art] = {}
             link_map[art][idx] = r['link_count']
             
         # with open("C:/tmp/codex_debug.txt", "a") as f:
         #      f.write(f"[_attach_link_counts] Statute: {statute_id} | Articles: {len(articles)} | ArticleNums_Sample: {article_nums[:3]} | FetchedRows: {len(fetched_rows)} | LinkMapKeys: {len(link_map)}\n")
              
         for art in articles:
             anum = str(art.get('key_id') or art.get('article_number') or "").strip()
             art['paragraph_links'] = link_map.get(anum, {})
    except Exception as e:
         # import traceback
         # with open("C:/tmp/codex_debug.txt", "a") as f:
         #      f.write(f"--- ERROR IN ATTACH_LINK_COUNTS ---\n{traceback.format_exc()}\n")
         logging.error(f"Error attaching link counts in codex.py: {e}")
         for art in articles: art['paragraph_links'] = {}

@codex_bp.route(route="codex/versions", auth_level=func.AuthLevel.ANONYMOUS)
def get_codex_versions(req: func.HttpRequest) -> func.HttpResponse:
    short_name = req.params.get('short_name')
    target_date = req.params.get('date') # Format YYYY-MM-DD
    
    if not short_name:
         return func.HttpResponse(json.dumps({"error": "short_name required"}), status_code=400)

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        import db_pool
        logging.info(f"CODAL API: Using DB_CONNECTION_STRING={db_pool.DB_CONNECTION_STRING}")

        # 1. Get Code ID
        cur.execute("SELECT code_id, full_name, description FROM legal_codes WHERE short_name = %s", (short_name.upper(),))
        code_meta = cur.fetchone()
        
        if not code_meta:
             return func.HttpResponse(
                 json.dumps(
                     {
                         "error": "Code not found",
                         "detail": f"No legal_codes row for short_name={short_name.upper()!r}. "
                         "For RCC run: python scripts/rcc_codal_cli.py schema",
                     }
                 ),
                 status_code=404,
                 mimetype="application/json",
             )
        
        code_id = code_meta['code_id']
        
        # SPECIALIZED TABLE HANDLERS (CONST, FC, LABOR, RPC, CIV)
        SPECIAL_TABLES = {
            'CONST': 'consti_codal',
            'FC': 'fc_codal',
            'LABOR': 'labor_codal',
            'RPC': 'rpc_codal',
            'CIV': 'civ_codal',
            'RCC': 'rcc_codal',
            'ROC': 'roc_codal'
        }
        
        if short_name.upper() in SPECIAL_TABLES:
             table_name = SPECIAL_TABLES[short_name.upper()]
             
             cols = _get_columns(cur, table_name)
             
             has_list_order = "list_order" in cols
             has_book_code = "book_code" in cols
             
             # Use SELECT * for maximum compatibility with all codal table schemas
             query = f"SELECT * FROM {table_name}"
             if has_book_code:
                 query += " WHERE book_code = %s"
                 cur.execute(query, (short_name.upper(),))
             elif table_name == 'rpc_codal':
                 # RPC articles MUST have a book (1 or 2). NULL indicates misclassified data.
                 query += " WHERE book IS NOT NULL"
                 cur.execute(query)
             else:
                 cur.execute(query)
             
             rows = cur.fetchall()

             # DEFINITIVE SORTING: Use list_order if available, otherwise human-friendly natural sort on article_num
             if has_list_order:
                 rows.sort(key=lambda x: x['list_order'] or 99999)
             else:
                 # ROC uses rule_section_label
                 art_col = 'rule_section_label' if short_name.upper() == 'ROC' else 'article_num'
                 rows.sort(key=lambda x: natural_keys(str(x[art_col]) if x.get(art_col) else ""))

             mapped_rows = []
             prev_book = None
             prev_title = None
             prev_chapter = None
             prev_section = None # For ROC/General
             prev_art_lvl = None # For Constitution Articles

             for r in rows:
                 # Clean Schema Mapping
                 content_to_send = r.get('content_md') or r.get('content') or ""
                 
                 # ROC Schema Mapping
                 if short_name.upper() == 'ROC':
                     book_lbl = r.get('part_title') or ""
                     book_n = r.get('part_num')
                     title_lbl = r.get('rule_title_full') or ""
                     title_n = r.get('rule_num')
                     chapter_lbl = r.get('group_1_title') or ""
                     chapter_n = r.get('group_1_num')
                     section_lbl = r.get('group_2_title') or ""
                     article_num = str(r.get('rule_section_label') or "")
                 elif short_name.upper() == 'CONST':
                     # Map new consti_codal schema to standard headers
                     book_lbl = ""
                     book_n = ""
                     title_lbl = f"{r.get('article_label', '')}"
                     if r.get('article_title'):
                         title_lbl += f"\n{r['article_title']}"
                     chapter_lbl = ""
                     chapter_n = ""

                     # Preamble Handling
                     if "PREAMBLE" in title_lbl.upper():
                         title_lbl = "PREAMBLE"

                     # Use only the top-level Roman numeral part of article_num as the
                     # title change key so the ARTICLE header fires once per article,
                     # not once per section.  "IX-A-1" → "IX", "II-3" → "II".
                     raw_art_num = str(r.get('article_num') or '')
                     title_n = raw_art_num.split('-')[0] if raw_art_num else None

                     # Hide section_label entirely for CONST because it's rendered inline by ArticleNode
                     section_lbl = ""

                     article_num = raw_art_num

                     # Skip stub chapter-header rows: article_num has no '-' and content is very short.
                     # e.g. 'II', 'X', 'XIV' are nav dividers, NOT real audio articles.
                     # Real single-section articles like National Territory ('I') have long content.
                     if ('-' not in article_num
                             and len((content_to_send or '').strip()) < 50
                             and 'PREAMBLE' not in title_lbl.upper()):
                         continue

                 elif short_name.upper() == 'FC':
                     book_lbl = "FAMILY CODE"
                     book_n = "1"
                     title_lbl = f"{r.get('article_label', '')} {r.get('article_title', '')}".strip()
                     title_n = ""
                     chapter_lbl = ""
                     # Sub-sections (Chapters vs generic sections)
                     s_lbl = r.get('section_label') or ""
                     if s_lbl.lower().startswith('chapter'):
                         chapter_lbl = s_lbl
                         section_lbl = ""
                     else:
                         section_lbl = s_lbl
                     chapter_n = ""
                     raw_anum = r.get('article_num') or ""
                     article_num = str(raw_anum.split('-')[-1] if '-' in raw_anum else raw_anum)
                 else:
                     book_lbl = r.get('book_label') or ""
                     # civ_codal / rcc_codal / rpc_codal / labor_codal use column "book", not book_num
                     book_n = r.get('book')
                     if book_n is None:
                         book_n = r.get('book_num')
                     title_lbl = clean_structural_label(r.get('title_label'))
                     title_n = r.get('title_num')
                     chapter_lbl = clean_structural_label(r.get('chapter_label'))
                     chapter_n = r.get('chapter_num')
                     section_lbl = clean_structural_label(r.get('section_label'))
                     article_num = str(r.get('article_num') or "")

                 if book_n and str(book_n) not in ['0', 'None', ''] and short_name.upper() not in ['CONST', 'FC']:
                     if short_name.upper() == 'ROC':
                         book_lbl = f"Part {book_n} - {book_lbl}" if book_lbl else f"Part {book_n}"
                     else:
                         book_lbl = f"Book {book_n} - {book_lbl}" if book_lbl else f"Book {book_n}"
                 
                 if title_n and str(title_n) not in ['0', 'None', ''] and short_name.upper() not in ['CONST', 'FC']:
                     if short_name.upper() == 'ROC':
                         # Do not prepend for ROC, LexCodeStream.jsx dynamically hoists the Rule N header 
                         pass
                     else:
                         title_lbl = f"Title {int_to_roman(title_n)} - {title_lbl}" if title_lbl else f"Title {int_to_roman(title_n)}"

                 if chapter_n and str(chapter_n) not in ['0', 'None', ''] and short_name.upper() not in ['CONST', 'FC']:
                     chapter_lbl = f"Chapter {int_to_roman(chapter_n)} - {chapter_lbl}" if chapter_lbl else f"Chapter {int_to_roman(chapter_n)}"

                 # Injection
                 injections = []

                 if book_lbl and prev_book != book_lbl:
                     injections.append(f"## {book_lbl}")
                     prev_book = book_lbl
                 if title_lbl and prev_title != title_lbl:
                     injections.append(f"## {title_lbl}")
                     prev_title = title_lbl
                 if chapter_lbl and prev_chapter != chapter_lbl:
                     injections.append(f"## {chapter_lbl}")
                     prev_chapter = chapter_lbl
                 if section_lbl and prev_section != section_lbl:
                     injections.append(f"## {section_lbl}")
                     prev_section = section_lbl

                 # LexCodeStream (CodalStream) already hoists book/title/chapter/section from row fields.
                 # Prepending "## …" here then "Article N." on the same line duplicates headers and leaves
                 # raw "##" in the body (not at line start, so ReactMarkdown does not render headings).
                 _append_embedded_codal_markdown = short_name.upper() not in (
                     "RCC",
                     "CIV",
                     "LABOR",
                     "RPC",
                     "FC",
                 )

                 if injections and _append_embedded_codal_markdown:
                     content_to_send = "\n\n".join(injections) + "\n\n" + content_to_send

                 # Format for prefix Article X
                 if short_name.upper() in ['LABOR', 'RPC', 'CIV', 'RCC', 'FC']:
                     if _append_embedded_codal_markdown:
                         art_title = r.get('article_title') or ""
                         prefix = f"Article {article_num}."
                         if art_title:
                             prefix += f" **{art_title}** -"
                         content_to_send = f"{prefix} {content_to_send}"

                 # Footnotes
                 fn_json = r.get('footnotes')
                 if fn_json:
                     fn_list = json.loads(fn_json) if isinstance(fn_json, str) else fn_json
                     if fn_list:
                         content_to_send += "\n\n---\n**Footnotes:**\n"
                         for fn in fn_list:
                             content_to_send += f"[{fn['marker']}]{fn['text']}\n"
                         content_to_send += "---\n"

                 mapped_rows.append({
                     "version_id": str(r['id']), 
                      "id": str(r['id']),
                     "key_id": article_num,
                    "article_number": article_num,
                    "article_title": "",
                    "group_header": r.get('group_header') or "",
                    "section_label": section_lbl,
                     "book": book_n,
                     "book_label": book_lbl,
                     "title_num": title_n,
                     "title_label": title_lbl,
                     "chapter_label": chapter_lbl,
                     "content": content_to_send,
                     "content_md": content_to_send,
                     "valid_from": r.get('created_at'),
                     "valid_to": None,
                     "amendment_history": [] 
                 })
                 
             _attach_link_counts(cur, mapped_rows, short_name.upper())
             return compressed_json_response({
                "metadata": code_meta,
                "articles": mapped_rows,
                "date": target_date or "latest"
             }, req, 200, max_age=(0 if short_name.upper() == "CONST" else 3600) if not target_date else 86400)

        # 2. Query Active Versions
        if target_date:
            date_clause = "valid_from <= %s AND (valid_to IS NULL OR valid_to > %s)"
            params = (code_id, target_date, target_date)
        else:
            date_clause = "valid_to IS NULL" 
            params = (code_id,)
            
        cur.execute(f"""
            SELECT version_id, article_number, content, valid_from, valid_to, amendment_id, amendment_description
            FROM article_versions
            WHERE code_id = %s AND {date_clause}
        """, params)
        active_rows = cur.fetchall()
        
        # 3. Query Full Amendment History
        article_numbers = [row['article_number'] for row in active_rows]
        history_map = {}
        if article_numbers:
            cur.execute("""
                SELECT article_number, amendment_id, valid_from, valid_to, amendment_description, content
                FROM article_versions
                WHERE code_id = %s AND article_number = ANY(%s)
                ORDER BY article_number, valid_from ASC
            """, (code_id, article_numbers))
            history_rows = cur.fetchall()
            
            for h_row in history_rows:
                art_num = h_row['article_number']
                if art_num not in history_map:
                    history_map[art_num] = []
                if not history_map[art_num] or history_map[art_num][-1]['content'] != h_row['content']:
                    history_map[art_num].append({
                        'amendment_id': h_row['amendment_id'],
                        'valid_from': h_row['valid_from'],
                        'valid_to': h_row['valid_to'],
                        'amendment_description': h_row['amendment_description'],
                        'content': h_row['content']
                    })
            for art_num, history in history_map.items():
                for version in history: del version['content']
        
        for row in active_rows:
            row['amendment_history'] = history_map.get(row['article_number'], [])
        
        active_rows.sort(key=lambda x: natural_keys(x['article_number']))
        
        cur.close()
        return compressed_json_response({
            "metadata": code_meta, 
            "articles": active_rows, 
            "date": target_date or "latest"
        }, req, 200, max_age=3600 if not target_date else 86400)

    except Exception as e:
        logging.error(f"Codex API Error: {e}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)
    finally:
        if conn:
            put_db_connection(conn)

@codex_bp.route(route="codex/amendments", auth_level=func.AuthLevel.ANONYMOUS)
def get_codex_amendments(req: func.HttpRequest) -> func.HttpResponse:
    short_name = req.params.get('short_name')
    if not short_name:
         return func.HttpResponse(json.dumps({"error": "short_name required"}), status_code=400)
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT code_id FROM legal_codes WHERE short_name = %s", (short_name,))
        row = cur.fetchone()
        if not row:
             return func.HttpResponse(json.dumps({"error": "Code not found"}), status_code=404)
        code_id = row['code_id']
        cur.execute("""
            SELECT amendment_id, MIN(valid_from) as date, array_agg(article_number) as articles
            FROM article_versions
            WHERE code_id = %s AND amendment_id IS NOT NULL AND amendment_id != 'Act No. 3815'
            GROUP BY amendment_id ORDER BY MIN(valid_from) ASC
        """, (code_id,))
        rows = cur.fetchall()
        for row in rows:
            if row['articles']: row['articles'].sort(key=natural_keys)
        cur.close()
        return compressed_json_response(rows, req, 200, max_age=7200)
    except Exception as e:
        logging.error(f"Codex Amendments API Error: {e}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)
    finally:
        if conn: put_db_connection(conn)

@codex_bp.route(route="codex/jurisprudence", auth_level=func.AuthLevel.ANONYMOUS)
def get_codex_jurisprudence(req: func.HttpRequest) -> func.HttpResponse:
    # ── Subscription gate: Juris+ required ────────────────────────────────────
    TIER_ORDER = ['free', 'amicus', 'juris', 'barrister']
    REQUIRED_TIER = 'juris'

    auth_header = (
        req.headers.get("X-Clerk-Authorization") or req.headers.get("Authorization") or ""
    ).strip()

    if not auth_header:
        return func.HttpResponse(
            json.dumps({"error": "Authentication required", "required_tier": REQUIRED_TIER}),
            mimetype="application/json", status_code=401,
        )

    clerk_id, auth_error = get_authenticated_user_id(req)
    if auth_error or not clerk_id:
        return func.HttpResponse(
            json.dumps({"error": "Unauthorized", "detail": auth_error}),
            mimetype="application/json", status_code=401,
        )

    provision_id = req.params.get('provision_id')
    statute_id = req.params.get('statute_id')
    subject_filter = req.params.get('subject')
    if not provision_id or not statute_id:
        return func.HttpResponse(json.dumps({"error": "statute_id and provision_id required"}), status_code=400)

    # One pooled connection for tier check + links (avoids two checkout round-trips per open).
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute(
                "SELECT subscription_tier, is_admin FROM users WHERE clerk_id = %s",
                (clerk_id,),
            )
            row = cur.fetchone()
            user_tier = (row.get("subscription_tier") if row else None) or "free"
            is_admin = bool((row.get("is_admin") if row else False) or False)
            try:
                tier_idx = TIER_ORDER.index(user_tier)
            except ValueError:
                tier_idx = 0
            if not is_admin and tier_idx < TIER_ORDER.index(REQUIRED_TIER):
                return func.HttpResponse(
                    json.dumps({
                        "error": "Juris subscription required",
                        "required_tier": REQUIRED_TIER,
                        "current_tier": user_tier,
                    }),
                    mimetype="application/json", status_code=403,
                )
        except Exception as gate_err:
            logging.warning("codex/jurisprudence tier check error (allowing through): %s", gate_err)

        STATUTE_MAPPING = {'FC': 'FAM', 'LABOR': 'LAB'}
        statute_id = STATUTE_MAPPING.get(statute_id.upper(), statute_id.upper())
        clean_id = provision_id.lower().replace('article', '').replace('art.', '').strip().rstrip('.').upper()
        target_ids = list(set([provision_id, clean_id]))
        # FAM links in DB use the display article segment (e.g. "1"), not raw fc_codal keys (e.g. "FC-I-1").
        if statute_id == 'FAM' and '-' in str(provision_id):
            tail = str(provision_id).split('-')[-1].strip()
            if tail:
                target_ids = list(set(target_ids + [tail]))
        if statute_id == 'RPC':
            mapping = {'266-A': ['266-A', '335'], '266-B': ['266-B', '335'], '335': ['335', '266-A']}
            if clean_id in mapping:
                target_ids = mapping[clean_id]
        or_conditions = []
        params = [statute_id]
        for tid in target_ids:
            or_conditions.append("(l.provision_id = %s OR l.provision_id ILIKE 'Article ' || %s OR l.provision_id ILIKE 'Art. ' || %s)")
            params.extend([tid, tid, tid])
        where_clause = " OR ".join(or_conditions)
        cur.execute(f"""
            SELECT l.id as link_id, l.case_id,
            CASE WHEN l.specific_ruling = 'General' OR l.specific_ruling IS NULL OR l.specific_ruling = '' THEN COALESCE(s.main_doctrine, s.digest_ruling, s.digest_ratio, 'View full case for details.') ELSE l.specific_ruling END as specific_ruling,
            l.ratio_index, l.citation_rank, l.subject_area, l.is_resolved, l.target_paragraph_index, l.version_id, s.short_title, s.date as case_date, s.sc_url, s.ponente
            FROM codal_case_links l JOIN sc_decided_cases s ON l.case_id = s.id
            WHERE l.statute_id = %s AND ({where_clause})
            {'AND l.subject_area = %s' if subject_filter else ''}
            ORDER BY s.date DESC, l.citation_rank ASC
        """, tuple(params + ([subject_filter] if subject_filter else [])))
        rows = cur.fetchall()
        return compressed_json_response(rows, req, 200, max_age=1800)
    except Exception as e:
        logging.error(f"Codex Jurisprudence API Error: {e}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)
    finally:
        if cur:
            cur.close()
        if conn:
            put_db_connection(conn)
