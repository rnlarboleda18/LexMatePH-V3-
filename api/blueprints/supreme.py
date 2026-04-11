import logging
import json
import os
from datetime import datetime, timezone
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import azure.functions as func
import psycopg2
from psycopg2.extras import RealDictCursor
from db_pool import get_db_connection, put_db_connection

# Import caching and config
import hashlib
from cache import cache_get, cache_set, cache_delete, cache_clear_pattern
from config import (
    DB_CONNECTION_STRING,
    REDIS_ENABLED,
    CACHE_TTL_DECISIONS,
    CACHE_TTL_PONENTES,
    CACHE_TTL_FLASHCARD_CONCEPTS,
    CACHE_TTL_SC_JUDICIARY_FEED,
    FLASHCARD_CONCEPTS_CACHE_KEY,
    FLASHCARD_BAR_MIN_TOS_SCORE,
    FLASHCARD_BAR_2026_ONLY_DEFAULT,
)
import re

from utils.flashcard_legal_concepts import (
    FLASHCARD_SOURCE_YEAR_MAX,
    FLASHCARD_SOURCE_YEAR_MIN,
    merge_digest_rows_to_concepts_list,
    flashcard_digest_select_sql_and_params,
    sources_keep_latest_only,
    get_primary_subject,
)

supreme_bp = func.Blueprint()

SC_JUDICIARY_FEED_URL = "https://sc.judiciary.gov.ph/feed/"
SC_FEED_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def _bar_related_post(item: dict) -> bool:
    t = (item.get("title") or "").lower()
    cats = " ".join(item.get("categories") or []).lower()
    blob = f"{t} {cats}"
    keys = (
        "bar examination",
        "bar exam",
        "bar 202",
        "barista",
        "bar bulletin",
        "philippine bar",
        "bar matters",
        "candidate",
    )
    return any(k in blob for k in keys)


def _parse_sc_judiciary_all_items(xml_bytes: bytes):
    """All RSS items in feed order (newest first as published by WordPress)."""
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    if channel is None:
        return []
    parsed = []
    for item in channel.findall("item"):
        title_el = item.find("title")
        link_el = item.find("link")
        pub_el = item.find("pubDate")
        title = (title_el.text or "").strip() if title_el is not None else ""
        link = (link_el.text or "").strip() if link_el is not None else ""
        pub = (pub_el.text or "").strip() if pub_el is not None else ""
        categories = []
        for c in item.findall("category"):
            if c is not None and c.text:
                categories.append(c.text.strip())
        desc_el = item.find("description")
        raw_desc = (desc_el.text or "").strip() if desc_el is not None else ""
        snippet = re.sub(r"<[^>]+>", " ", raw_desc)
        snippet = re.sub(r"\s+", " ", snippet).strip()[:280]
        parsed.append(
            {
                "title": title,
                "link": link,
                "pub_date": pub,
                "categories": categories,
                "snippet": snippet or None,
            }
        )
    return parsed


def _parse_sc_judiciary_rss(xml_bytes: bytes, limit: int, bar_only: bool):
    all_items = _parse_sc_judiciary_all_items(xml_bytes)
    if bar_only:
        all_items = [x for x in all_items if _bar_related_post(x)]
    return all_items[:limit]


@supreme_bp.route(route="sc_judiciary_feed", auth_level=func.AuthLevel.ANONYMOUS)
def sc_judiciary_feed(req: func.HttpRequest) -> func.HttpResponse:
    """
    Proxies the official SC WordPress RSS feed (same origin as API = no browser CORS).
    Cached so upstream rate limits and latency stay predictable.

    Query params:
      limit — max main items (default 12, max 40)
      bar_only=1 — only Bar-related posts (legacy)
      include_bar=1 — include bar_items in the same response (one upstream fetch + parse)
      bar_limit — max bar_items when include_bar=1 (default 8, max 20)
    """
    try:
        limit = min(max(int(req.params.get("limit", "12")), 1), 40)
    except ValueError:
        limit = 12
    bar_only = str(req.params.get("bar_only", "")).lower() in ("1", "true", "yes")
    include_bar = str(req.params.get("include_bar", "")).lower() in ("1", "true", "yes")
    try:
        bar_limit = min(max(int(req.params.get("bar_limit", "8")), 1), 20)
    except ValueError:
        bar_limit = 8

    if include_bar and bar_only:
        return func.HttpResponse(
            json.dumps({"error": "invalid_params", "message": "Use include_bar or bar_only, not both."}),
            mimetype="application/json",
            status_code=400,
        )

    if include_bar:
        cache_key = f"sc_judiciary_feed:bundle:{limit}:{bar_limit}"
    else:
        cache_key = f"sc_judiciary_feed:{limit}:bar={int(bar_only)}"

    if REDIS_ENABLED:
        cached = cache_get(cache_key)
        if cached is not None:
            return func.HttpResponse(
                json.dumps(cached),
                mimetype="application/json",
                status_code=200,
                headers={"Cache-Control": f"public, max-age={min(CACHE_TTL_SC_JUDICIARY_FEED, 600)}"},
            )
    try:
        request = urllib.request.Request(
            SC_JUDICIARY_FEED_URL,
            headers={"User-Agent": SC_FEED_UA, "Accept": "application/rss+xml, application/xml, text/xml, */*"},
        )
        with urllib.request.urlopen(request, timeout=25) as resp:
            xml_bytes = resp.read()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        logging.error("sc_judiciary_feed fetch failed: %s", e)
        body = {
            "items": [],
            "source": SC_JUDICIARY_FEED_URL,
            "error": "feed_unavailable",
        }
        if include_bar:
            body["bar_items"] = []
        return func.HttpResponse(json.dumps(body), mimetype="application/json", status_code=200)

    try:
        if include_bar:
            all_items = _parse_sc_judiciary_all_items(xml_bytes)
            items = all_items[:limit]
            bar_items = [x for x in all_items if _bar_related_post(x)][:bar_limit]
        else:
            items = _parse_sc_judiciary_rss(xml_bytes, limit, bar_only)
            bar_items = None
    except ET.ParseError as e:
        logging.error("sc_judiciary_feed XML parse error: %s", e)
        body = {"items": [], "source": SC_JUDICIARY_FEED_URL, "error": "parse_error"}
        if include_bar:
            body["bar_items"] = []
        return func.HttpResponse(json.dumps(body), mimetype="application/json", status_code=200)

    payload = {
        "items": items,
        "source": SC_JUDICIARY_FEED_URL,
        "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    if include_bar:
        payload["bar_items"] = bar_items
    if REDIS_ENABLED:
        cache_set(cache_key, payload, ttl=CACHE_TTL_SC_JUDICIARY_FEED)
    return func.HttpResponse(
        json.dumps(payload),
        mimetype="application/json",
        status_code=200,
        headers={"Cache-Control": f"public, max-age={min(CACHE_TTL_SC_JUDICIARY_FEED, 600)}"},
    )


# Bar subject filter values from SupremeDecisions.jsx — must match dropdown + normalizeSubjectForColor buckets
ALLOWED_BAR_SUBJECT_FILTERS = frozenset(
    {
        "Political Law",
        "Labor Law",
        "Civil Law",
        "Taxation Law",
        "Commercial Law",
        "Criminal Law",
        "Remedial Law",
        "Legal Ethics",
    }
)


def bar_subject_canon_sql(col: str = "subject") -> str:
    """
    PostgreSQL expression that mirrors SupremeDecisions.jsx normalizeSubjectForColor:
    extract Primary: … segment (if present), then assign exactly one bar subject by
    the same keyword order as the frontend. Using subject ILIKE '%Political Law%' missed
    rows labeled only 'Constitutional Law', and double-counted rows whose text contained
    multiple subject names — so filtered totals did not tally with ponente-only counts.
    """
    # POSIX regex (substring … from) — no \s; use [[:space:]]
    seg = f"""(
        COALESCE(
            NULLIF(BTRIM(SUBSTRING(COALESCE({col}::text, '') FROM '[Pp]rimary:[[:space:]]*([^;]+)')), ''),
            BTRIM(COALESCE({col}::text, ''))
        )
    )"""
    return f"""(
        CASE
            WHEN {col} IS NULL OR BTRIM(COALESCE({col}::text, '')) = '' THEN 'Political Law'
            ELSE (
                CASE
                    WHEN {seg} ILIKE '%%Political%%' OR {seg} ILIKE '%%Constitutional%%' OR {seg} ILIKE '%%Admin%%' OR {seg} ILIKE '%%Election%%' OR {seg} ILIKE '%%Public Corp%%' THEN 'Political Law'
                    WHEN {seg} ILIKE '%%Labor%%' THEN 'Labor Law'
                    WHEN {seg} ILIKE '%%Civil%%' OR {seg} ILIKE '%%Family%%' OR {seg} ILIKE '%%Property%%' OR {seg} ILIKE '%%Succession%%' OR {seg} ILIKE '%%Obligations%%' THEN 'Civil Law'
                    WHEN {seg} ILIKE '%%Taxation%%' OR {seg} ILIKE '%%Tax%%' THEN 'Taxation Law'
                    WHEN {seg} ILIKE '%%Commercial%%' OR {seg} ILIKE '%%Mercantile%%' OR {seg} ILIKE '%%Corporate%%' OR {seg} ILIKE '%%Insurance%%' OR {seg} ILIKE '%%Transportation%%' THEN 'Commercial Law'
                    WHEN {seg} ILIKE '%%Criminal%%' THEN 'Criminal Law'
                    WHEN {seg} ILIKE '%%Remedial%%' OR {seg} ILIKE '%%Procedure%%' OR {seg} ILIKE '%%Evidence%%' THEN 'Remedial Law'
                    WHEN {seg} ILIKE '%%Ethics%%' OR {seg} ILIKE '%%Legal Ethics%%' OR {seg} ILIKE '%%Judicial%%' THEN 'Legal Ethics'
                    ELSE 'Political Law'
                END
            )
        END
    )"""


@supreme_bp.route(route="sc_decisions", auth_level=func.AuthLevel.ANONYMOUS)
def sc_decisions(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing Supreme Decisions request.')
    
    conn = None
    cur = None
    try:
        search_term = req.params.get('search', '').strip() # Don't lower() yet, FTS handles it, and don't replace hyphens!
        year = req.params.get('year')
        month = req.params.get('month', '').lower()
        subject_filter = req.params.get('subject')
        doctrinal_filter = req.params.get('doctrinal')
        division_filter = req.params.get('division')
        ponente_filter = req.params.get('ponente')
        significance_filter = req.params.get('significance')
        model_filter = req.params.get('model')
        page = int(req.params.get('page', 1))
        limit = int(req.params.get('limit', 20))
        offset = (page - 1) * limit

        # Generate cache key
        cache_key = f"sc_decisions:{search_term}:{year}:{month}:{subject_filter}:{doctrinal_filter}:{division_filter}:{ponente_filter}:{significance_filter}:{model_filter}:{page}:{limit}"
        
        # Try cache first if enabled
        if REDIS_ENABLED:
            cached_data = cache_get(cache_key)
            if cached_data:
                logging.info(f"Serving from cache: {cache_key}")
                return func.HttpResponse(
                    json.dumps(cached_data, default=str),
                    mimetype="application/json",
                    status_code=200
                )

        import time
        t_start = time.time()
        
        logging.info("Request started. Getting connection from pool...")
        t_conn_start = time.time()
        conn = get_db_connection()
        t_conn_end = time.time()
        logging.info(f"Got connection in {t_conn_end - t_conn_start:.4f}s")
        
        cur = conn.cursor(cursor_factory=RealDictCursor)

        select_cols = """
                id,
                case_number,
                short_title as title,
                short_title,
                TO_CHAR(date, 'YYYY-MM-DD') as date_str,
                EXTRACT(YEAR FROM date) as year_val,
                TRIM(TO_CHAR(date, 'Month')) as month_val,
                sc_url,
                ponente,
                subject,
                main_doctrine,
                significance_category,
                division,
                is_doctrinal,
                document_type,
                keywords,
                ai_model
        """

        # FTS Expression (Enhanced to include digest fields)
        fts_expr = """
            to_tsvector('english', 
                COALESCE(short_title, '') || ' ' || 
                COALESCE(case_number, '') || ' ' || 
                COALESCE(main_doctrine, '') || ' ' || 
                COALESCE(digest_facts, '') || ' ' || 
                COALESCE(digest_ruling, '') || ' ' || 
                COALESCE(digest_ratio, '') || ' ' || 
                COALESCE(full_text_md, '')
            )
        """

        params = []
        
        # 1. Build Base Filters (Common to all modes)
        base_where = " WHERE 1=1"
        base_params = []
        
        if year:
            base_where += " AND EXTRACT(YEAR FROM date) = %s"
            base_params.append(int(year))
        if month:
            base_where += " AND TRIM(TO_CHAR(date, 'Month')) ILIKE %s"
            base_params.append(month)
        if subject_filter:
            sf = subject_filter.strip()
            if sf in ALLOWED_BAR_SUBJECT_FILTERS:
                base_where += f" AND ({bar_subject_canon_sql('subject')}) = %s"
                base_params.append(sf)
            else:
                logging.warning("Ignoring unknown bar subject filter: %s", sf[:80])
        if division_filter:
            base_where += " AND division ILIKE %s"
            base_params.append(division_filter)
        if doctrinal_filter and doctrinal_filter.lower() == 'true':
            base_where += " AND is_doctrinal = TRUE"
        if ponente_filter:
            base_where += " AND ponente = %s"
            base_params.append(ponente_filter)
        if significance_filter:
            base_where += " AND significance_category = %s"
            base_params.append(significance_filter)
        if model_filter:
            base_where += " AND ai_model = %s"
            base_params.append(model_filter)

        # 2. Determine Search Logic (Cascading Tiers)
        final_query = ""
        final_params = []
        total_count = 0
        
        if search_term:
            # TIER 0: Exact ID Match (if numeric)
            if search_term.isdigit():
                t0_where = base_where + " AND id = %s"
                t0_params = list(base_params) + [int(search_term)]
                
                cur.execute(f"SELECT COUNT(*) as count FROM sc_decided_cases {t0_where}", t0_params)
                t0_count = cur.fetchone()['count']
                
                if t0_count > 0:
                    logging.info(f"Search Hit Tier 0 (ID Match): {t0_count} results")
                    final_query = f"SELECT {select_cols} FROM sc_decided_cases {t0_where}"
                    final_params = t0_params
                    total_count = t0_count
            
            # TIER 1: Metadata Exact/Partial Match (Short Title OR Case Number)
            # TIER 1: Metadata Exact/Partial Match (Short Title OR Case Number)
            if total_count == 0:
                # "Look first in the short_title... or case_number (implicit Metadata)"
                t1_where = base_where + " AND (case_number ILIKE %s OR short_title ILIKE %s)"
                t1_params = list(base_params) + [f"%{search_term}%", f"%{search_term}%"]
                
                t_check_start = time.time()
                cur.execute(f"SELECT COUNT(*) as count FROM sc_decided_cases {t1_where}", t1_params)
                t1_count = cur.fetchone()['count']
            
                if t1_count > 0:
                    # MATCH FOUND IN TIER 1
                    logging.info(f"Search Hit Tier 1 (Metadata): {t1_count} results")
                    final_query = f"SELECT {select_cols} FROM sc_decided_cases {t1_where} ORDER BY date DESC, id DESC"
                    final_params = t1_params
                    total_count = t1_count
                    
                else:
                    # TIER 2: Full Title Match
                    # "If none, look in full_title"
                    t2_where = base_where + " AND full_title ILIKE %s"
                    t2_params = list(base_params) + [f"%{search_term}%"]
                    
                    cur.execute(f"SELECT COUNT(*) as count FROM sc_decided_cases {t2_where}", t2_params)
                    t2_count = cur.fetchone()['count']
                    
                    if t2_count > 0:
                        # MATCH FOUND IN TIER 2
                        logging.info(f"Search Hit Tier 2 (Full Title): {t2_count} results")
                        final_query = f"SELECT {select_cols} FROM sc_decided_cases {t2_where} ORDER BY date DESC, id DESC"
                        final_params = t2_params
                        total_count = t2_count
                        
                    else:
                        # TIER 3: Full Text / FTS (Source of Truth)
                        # "Then last in the full_text_md"
                        logging.info(f"Search Fallback to Tier 3 (FTS)")
                        
                        # Standard FTS for ALL terms (including numeric)
                        # Use rank for ordering in FTS
                        t3_where = base_where + f" AND ({fts_expr} @@ websearch_to_tsquery('english', %s))"
                        t3_params = list(base_params) + [search_term]
                        final_query = f"SELECT {select_cols}, ts_rank_cd({fts_expr}, websearch_to_tsquery('english', %s)) as rank FROM sc_decided_cases {t3_where} ORDER BY rank DESC, date DESC"
                        
                        # Note: matching query placeholders:
                        # 1. ts_rank_cd(..., %s)  -> search_term
                        # 2. base_where placeholders -> base_params
                        # 3. t3_where (%s)        -> search_term
                        final_params = [search_term] + list(base_params) + [search_term]

                        # Need to count for Tier 3
                        count_q = f"SELECT COUNT(*) as count FROM sc_decided_cases {t3_where}"
                        count_p = list(base_params) + [search_term]
                        
                        cur.execute(count_q, count_p)
                        total_count = cur.fetchone()['count']

        else:
            # NO SEARCH TERM (Browse Mode)
            final_query = f"SELECT {select_cols} FROM sc_decided_cases {base_where} ORDER BY date DESC, id DESC"
            final_params = base_params
            
            # Count
            cur.execute(f"SELECT COUNT(*) as count FROM sc_decided_cases {base_where}", base_params)
            total_count = cur.fetchone()['count']

        logging.info(f"Tier Check took {time.time() - t_conn_end:.4f}s") # Reuse t_conn_end as start of logic

        # 3. Apply Pagination
        final_query += " LIMIT %s OFFSET %s"
        final_params.extend([limit, offset])

        # Execute Data Query
        t_data_start = time.time()
        cur.execute(final_query, final_params)



        results = cur.fetchall()
        t_data_end = time.time()
        logging.info(f"Data Query took {t_data_end - t_data_start:.4f}s")
        
        logging.info(f"Total Request Processing: {t_data_end - t_start:.4f}s")

        # Generate snippets for cases missing them
        for row in results:
            if not row.get('main_doctrine'):
                facts = row.get('digest_facts') or ""
                # Clean up markdown for snippet
                clean_facts = facts.replace('#', '').replace('*', '').replace('>', '').strip()
                # Remove incomplete last word from preview if truncated
                # Remove incomplete last word from preview if truncated
                row['snippet'] = (clean_facts[:200] + '...') if len(clean_facts) > 200 else clean_facts

        # Prepare response
        response_data = {
            "data": results,
            "total": total_count,
            "page": page,
            "limit": limit
        }
        
        # Cache the result if Redis is enabled
        if REDIS_ENABLED:
            cache_set(cache_key, response_data, ttl=CACHE_TTL_DECISIONS)

        # Generate ETag and Cache Headers
        response_json = json.dumps(response_data, default=str)
        etag = hashlib.md5(response_json.encode()).hexdigest()
        
        headers = {
            "Cache-Control": f"public, max-age={CACHE_TTL_DECISIONS}",
            "ETag": etag
        }

        return func.HttpResponse(
            response_json,
            mimetype="application/json",
            headers=headers,
            status_code=200
        )

    except Exception as e:
        logging.error(f"Error in sc_decisions: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
    finally:
        if cur:
            cur.close()
        if conn:
            put_db_connection(conn)
        logging.info("DB Connection closed.")

@supreme_bp.route(route="sc_decisions/ponentes", auth_level=func.AuthLevel.ANONYMOUS)
def supreme_decision_ponentes(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing Supreme Decision Ponentes request.')
    
    # Try cache first if enabled
    cache_key = "sc_decisions:ponentes"
    if REDIS_ENABLED:
        cached_data = cache_get(cache_key)
        if cached_data:
            logging.info("Serving ponentes from cache")
            return func.HttpResponse(
                json.dumps(cached_data),
                mimetype="application/json",
                status_code=200
            )
    
    try:
        conn = None
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get Distinct Ponentes, ordered
        cur.execute("""
            SELECT DISTINCT ponente 
            FROM sc_decided_cases 
            WHERE ponente IS NOT NULL AND ponente != '' 
        """)
        raw_ponentes = [row[0] for row in cur.fetchall()]
        
        # Normalize and Deduplicate logic
        normalized_set = set()
        for p in raw_ponentes:
             norm = normalize_ponente_text(p)
             if norm:
                 normalized_set.add(norm)
        
        results = sorted(list(normalized_set))
        
        cur.close()
        put_db_connection(conn)
        
        # Cache the result
        if REDIS_ENABLED:
            cache_set(cache_key, results, ttl=CACHE_TTL_PONENTES)
            
        # Generate ETag and Cache Headers
        response_json = json.dumps(results)
        etag = hashlib.md5(response_json.encode()).hexdigest()
        
        headers = {
            "Cache-Control": f"public, max-age={CACHE_TTL_PONENTES}",
            "ETag": etag
        }
        
        return func.HttpResponse(
            response_json,
            mimetype="application/json",
            headers=headers,
            status_code=200
        )

    except Exception as e:
        logging.error(f"Error in supreme_decision_ponentes: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )

@supreme_bp.route(route="sc_decisions/divisions", auth_level=func.AuthLevel.ANONYMOUS)
def supreme_decision_divisions(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing Supreme Decision Divisions request.')
    
    # Try cache first if enabled
    cache_key = "sc_decisions:divisions"
    if REDIS_ENABLED:
        cached_data = cache_get(cache_key)
        if cached_data:
            return func.HttpResponse(
                json.dumps(cached_data),
                mimetype="application/json",
                status_code=200
            )

    try:
        conn = None
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT DISTINCT division 
            FROM sc_decided_cases 
            WHERE division IS NOT NULL AND division != '' 
        """)
        raw_rows = [row[0] for row in cur.fetchall()]
        
        # Normalize: Title Case and Deduplicate
        normalized_set = set()
        for d in raw_rows:
            norm = d.strip().title()
            
            # Specific Normalization
            if "4Th" in norm or "4Th" in norm:
                norm = norm.replace("4Th", "Fourth").replace("4th", "Fourth")
            
            if norm == "Division": continue # Skip generic invalid entry
            
            if norm:
                normalized_set.add(norm)
        
        # Custom Sorting Logic
        def sort_key(division):
            d = division.lower()
            if "en banc" in d:
                return (0, d)
            if "first division" == d:
                return (1, d)
            if "second division" == d:
                return (2, d)
            if "third division" == d:
                return (3, d)
            if "fourth division" == d:
                return (4, d)
            if "fifth division" == d:
                return (5, d)
            if "sixth division" == d:
                return (6, d)
            # Group Special divisions after standard ones
            if "special" in d:
                return (10, d)
            # Others
            return (5, d)

        results = sorted(list(normalized_set), key=sort_key)
        
        cur.close()
        put_db_connection(conn)
        
        # Cache
        if REDIS_ENABLED:
            cache_set(cache_key, results, ttl=CACHE_TTL_PONENTES)
            
        return func.HttpResponse(
            json.dumps(results),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"Error in supreme_decision_divisions: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )

def _normalize_subject_bar(raw):
    if not raw:
        return ""
    s = str(raw).lower()
    if "civil" in s:
        return "Civil Law"
    if "commercial" in s or "mercantile" in s:
        return "Commercial Law"
    if "criminal" in s or "penal" in s:
        return "Criminal Law"
    if "labor" in s or "social legislat" in s:
        return "Labor Law"
    if "ethics" in s or "judicial ethics" in s:
        return "Legal Ethics"
    if "political" in s or "constitutional" in s:
        return "Political Law"
    if "remedial" in s or "procedure" in s:
        return "Remedial Law"
    if "taxation" in s or re.search(r"\btax\b", s):
        return "Taxation Law"
    return str(raw).strip()


@supreme_bp.route(route="sc_decisions/flashcard_concepts", auth_level=func.AuthLevel.ANONYMOUS)
def sc_decisions_flashcard_concepts(req: func.HttpRequest) -> func.HttpResponse:
    """Deduplicated legal concepts (flashcard_concepts table, or digest merge if empty): years 1987–2025, En Banc only.

    Query: ?subject= canonical bar subject (optional).
    ?include_peripheral=1 — include concepts labeled peripheral (default: omit them after TOS labeling).
    ?bar_focus=0 — include all non-peripheral \"core\" rows even when Bar (TOS) match score is below the minimum
        (default: only concepts with strong syllabus overlap, see FLASHCARD_BAR_MIN_TOS_SCORE).
    ?bar_2026_only=1 — keep only concepts labeled bar_2026_aligned=true (see scripts/label_flashcard_bar2026_gemini.py).
        ?bar_2026_only=0 disables even if FLASHCARD_BAR_2026_ONLY env default is on.
    """
    subject_filter = (req.params.get("subject") or "").strip()
    ns_filter = _normalize_subject_bar(subject_filter) if subject_filter else ""
    include_peripheral = (req.params.get("include_peripheral") or "").lower() in ("1", "true", "yes")
    bar_focus_off = (req.params.get("bar_focus") or "").lower() in ("0", "false", "no")
    raw_bar26 = (req.params.get("bar_2026_only") or "").strip().lower()
    if raw_bar26 in ("1", "true", "yes"):
        bar_2026_only = True
    elif raw_bar26 in ("0", "false", "no"):
        bar_2026_only = False
    else:
        bar_2026_only = FLASHCARD_BAR_2026_ONLY_DEFAULT

    def _bar_exam_aligned(c):
        """When bar exam focus is on, drop labeled rows whose TOS match is weak (e.g. core only via case_count)."""
        if bar_focus_off or include_peripheral:
            return True
        sc = c.get("tos_match_score")
        if sc is None:
            return True
        try:
            scf = float(sc)
        except (TypeError, ValueError):
            return True
        return scf >= FLASHCARD_BAR_MIN_TOS_SCORE

    def _concept_visible(c):
        if include_peripheral:
            return True
        tier = (c.get("importance_tier") or "core").strip().lower()
        if tier == "peripheral":
            return False
        if not _bar_exam_aligned(c):
            return False
        if bar_2026_only and c.get("bar_2026_aligned") is not True:
            return False
        return True

    def _build_response_payload(out_list):
        out_list = [c for c in out_list if _concept_visible(c)]
        if ns_filter:
            filtered = []
            for c in out_list:
                srcs = [s for s in c["sources"] if _normalize_subject_bar(s.get("subject")) == ns_filter]
                if srcs:
                    filtered.append({**c, "sources": srcs})
            out_list = filtered
        return {"concepts": out_list}

    bypass_cache = (req.params.get("nocache") or "").lower() in ("1", "true", "yes")

    if REDIS_ENABLED and not bypass_cache:
        cached = cache_get(FLASHCARD_CONCEPTS_CACHE_KEY)
        # Do not serve a stale empty cache — forces recompute after fixes / new data
        if (
            cached
            and isinstance(cached, dict)
            and isinstance(cached.get("concepts"), list)
            and len(cached["concepts"]) > 0
        ):
            logging.info("Serving flashcard_concepts from cache")
            payload = _build_response_payload(cached["concepts"])
            return func.HttpResponse(
                json.dumps(payload, default=str),
                mimetype="application/json",
                status_code=200,
            )

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        out = []
        stored = []
        try:
            cur.execute(
                """
                SELECT term, definition, sources, case_count, importance_tier, tos_topic_id, tos_match_score,
                       bar_2026_aligned
                FROM flashcard_concepts
                ORDER BY term
                """
            )
            stored = cur.fetchall() or []
        except Exception as ex:
            err = str(ex).lower()
            if "bar_2026_aligned" in err:
                try:
                    cur.execute(
                        """
                        SELECT term, definition, sources, case_count, importance_tier, tos_topic_id, tos_match_score
                        FROM flashcard_concepts
                        ORDER BY term
                        """
                    )
                    stored = cur.fetchall() or []
                    logging.warning(
                        "flashcard_concepts: reading without bar_2026_aligned (run sql/flashcard_bar2026_migration.sql)"
                    )
                except Exception as ex_b:
                    err_b = str(ex_b).lower()
                    if "case_count" in err_b or "importance_tier" in err_b or "does not exist" in err_b:
                        try:
                            cur.execute(
                                """
                                SELECT term, definition, sources
                                FROM flashcard_concepts
                                ORDER BY term
                                """
                            )
                            stored = cur.fetchall() or []
                            logging.warning(
                                "flashcard_concepts: reading without importance + bar_2026 columns"
                            )
                        except Exception as ex3:
                            logging.warning(
                                f"flashcard_concepts: table read failed, falling back to digest merge: {ex3}"
                            )
                            stored = []
                    else:
                        logging.warning(
                            f"flashcard_concepts: table read failed, falling back to digest merge: {ex_b}"
                        )
                        stored = []
            elif "case_count" in err or "importance_tier" in err or "does not exist" in err:
                try:
                    cur.execute(
                        """
                        SELECT term, definition, sources
                        FROM flashcard_concepts
                        ORDER BY term
                        """
                    )
                    stored = cur.fetchall() or []
                    logging.warning(
                        "flashcard_concepts: reading without importance columns (run sql/flashcard_concepts_importance_migration.sql)"
                    )
                except Exception as ex2:
                    logging.warning(
                        f"flashcard_concepts: table read failed, falling back to digest merge: {ex2}"
                    )
                    stored = []
            else:
                logging.warning(f"flashcard_concepts: table read failed, falling back to digest merge: {ex}")
                stored = []

        if stored:
            logging.info(f"flashcard_concepts: loaded {len(stored)} rows from flashcard_concepts table")
            for r in stored:
                src = r.get("sources")
                if isinstance(src, str):
                    try:
                        src = json.loads(src)
                    except Exception:
                        src = []
                if not isinstance(src, list):
                    src = []
                cc = r.get("case_count")
                try:
                    cc = int(cc) if cc is not None else 0
                except (TypeError, ValueError):
                    cc = 0
                tier = (r.get("importance_tier") or "core").strip() or "core"
                tms = r.get("tos_match_score")
                try:
                    tms_f = float(tms) if tms is not None else None
                except (TypeError, ValueError):
                    tms_f = None
                b26 = r.get("bar_2026_aligned")
                if b26 is not None and not isinstance(b26, bool):
                    b26 = bool(b26)
                out.append(
                    {
                        "term": r.get("term") or "",
                        "definition": (r.get("definition") or "").strip(),
                        "sources": sources_keep_latest_only(src),
                        "primary_subject": get_primary_subject(src),
                        "case_count": cc,
                        "importance_tier": tier,
                        "tos_topic_id": r.get("tos_topic_id"),
                        "tos_match_score": tms_f,
                        "bar_2026_aligned": b26,
                    }
                )
        else:
            sql_fb, params_fb = flashcard_digest_select_sql_and_params()
            cur.execute(sql_fb, params_fb)
            rows = cur.fetchall()
            logging.info(
                f"flashcard_concepts: legacy merge from {len(rows) if rows else 0} cases "
                f"(years {FLASHCARD_SOURCE_YEAR_MIN}–{FLASHCARD_SOURCE_YEAR_MAX}, En Banc only)"
            )
            out = merge_digest_rows_to_concepts_list(rows or [])
            for c in out:
                c.setdefault("importance_tier", "core")
                c.setdefault("tos_topic_id", None)
                c.setdefault("tos_match_score", None)
                c.setdefault("bar_2026_aligned", None)

        if REDIS_ENABLED and out:
            try:
                cache_set(
                    FLASHCARD_CONCEPTS_CACHE_KEY,
                    {"concepts": out},
                    ttl=CACHE_TTL_FLASHCARD_CONCEPTS,
                )
            except Exception as ex:
                logging.warning(f"flashcard_concepts cache set skipped: {ex}")

        payload = _build_response_payload(out)
        return func.HttpResponse(
            json.dumps(payload, default=str),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as e:
        logging.error(f"Error in sc_decisions_flashcard_concepts: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500,
        )
    finally:
        if cur:
            cur.close()
        if conn:
            put_db_connection(conn)


@supreme_bp.route(route="sc_decisions/{id:int}", auth_level=func.AuthLevel.ANONYMOUS)
def supreme_decision_detail(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing Supreme Decision Detail request.')
    
    try:
        decision_id = req.route_params.get('id')
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        

        # Fetch ALL fields for the digest
        cur.execute("SELECT * FROM sc_decided_cases WHERE id = %s", (decision_id,))
        result = cur.fetchone()
        
        if result:
            if not result.get('full_text_md'):
                 result['full_text_md'] = "*Content not available in Markdown format yet.*"

            cur.execute("""
                SELECT id, short_title as title, document_type, full_text_md 
                FROM sc_decided_cases 
                WHERE parent_id = %s
                ORDER BY id ASC
            """, (decision_id,))
            children = cur.fetchall()
            result['related_opinions'] = children

            return func.HttpResponse(
                json.dumps(result, default=str),
                mimetype="application/json",
                status_code=200
            )
        else:
            return func.HttpResponse(
                json.dumps({"error": "Not Found"}),
                mimetype="application/json",
                status_code=404
            )

    except Exception as e:
        logging.error(f"Error in supreme_decision_detail: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
    finally:
        if 'cur' in locals() and cur: cur.close()
        if 'conn' in locals() and conn: put_db_connection(conn)

@supreme_bp.route(route="sc_decisions/models", auth_level=func.AuthLevel.ANONYMOUS)
def supreme_decision_models(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing Supreme Decision Models request.')
    
    # Try cache first if enabled
    cache_key = "sc_decisions:models"
    if REDIS_ENABLED:
        cached_data = cache_get(cache_key)
        if cached_data:
            return func.HttpResponse(
                json.dumps(cached_data),
                mimetype="application/json",
                status_code=200
            )

    try:
        conn = None
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT DISTINCT ai_model 
            FROM sc_decided_cases 
            WHERE ai_model IS NOT NULL AND ai_model != '' 
            ORDER BY ai_model ASC
        """)
        results = [row[0] for row in cur.fetchall()]
        
        cur.close()
        put_db_connection(conn)
        
        # Cache
        if REDIS_ENABLED:
            cache_set(cache_key, results, ttl=CACHE_TTL_PONENTES) # same TTL as other lists
            
        return func.HttpResponse(
            json.dumps(results),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"Error in supreme_decision_models: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )

def normalize_ponente_text(ponente):
    """
    Normalize ponente name to standard format: "LASTNAME, J.:"
    Examples:
        "Antonio T. Carpio" -> "CARPIO, J.:"
        "carpio, j." -> "CARPIO, J.:"
        "CARPIO, J" -> "CARPIO, J.:"
        "Carpio" -> "CARPIO, J.:"
        "J.B.L. Reyes" -> "REYES, J.B.L., J.:"
    """
    if not ponente or not isinstance(ponente, str):
        return None
    
    # Clean up the input
    ponente = ponente.strip()
    if not ponente:
        return None
        
    # Special handling for "Per Curiam"
    if "curiam" in ponente.lower():
        return "Per Curiam"

    # Handle known special cases first (Multi-word lastnames or initials)
    # These are names where strict "last word" logic fails or we want specific formatting
    special_map = {
        "J.B.L. REYES": "REYES, J.B.L.",
        "J. B. L. REYES": "REYES, J.B.L.",
        "JOSE C. REYES, JR.": "J.C. REYES, JR.",
        "J. REYES, JR.": "J.C. REYES, JR.",
        "ANDRES B. REYES, JR.": "A. REYES, JR.",
        "A. REYES, JR.": "A. REYES, JR.",
        "RUBEN T. REYES": "REYES, R.T.",
        "R.T. REYES": "REYES, R.T.",
        "CONCHITA CARPIO MORALES": "CARPIO MORALES",
        "CONCHITA CARPIO-MORALES": "CARPIO-MORALES",
        "MARTIN S. VILLARAMA, JR.": "VILLARAMA, JR.",
        "VILLARAMA, JR.": "VILLARAMA, JR.",
        "PREBITERO J. VELASCO, JR.": "VELASCO, JR.",
        "VELASCO, JR.": "VELASCO, JR.",
        "PRESBITERO J. VELASCO, JR.": "VELASCO, JR."
    }
    
    # Check if we have a direct map for the upper version (before adding J.:)
    upper_raw = ponente.upper().replace(", J.:", "").replace(", J.", "").strip()
    if upper_raw in special_map:
        return f"{special_map[upper_raw]}, J.:"

    # Extract the lastname
    lastname = None
    
    # Pattern 1: "LASTNAME, J." or "LASTNAME, J.:" or "Lastname, J."
    if ', J' in ponente.upper():
        lastname = ponente.split(',')[0].strip()
    
    # Pattern 2: "Firstname Middlename Lastname" (full name format)
    elif ' ' in ponente and ',' not in ponente:
        # Take the last word as lastname
        parts = ponente.split()
        lastname = parts[-1]
    
    # Pattern 3: Just lastname alone
    else:
        lastname = ponente
    
    if lastname:
        # Remove any trailing periods or colons
        lastname = lastname.rstrip('.:').strip()
        
        # Cleanup any stray initials if they got caught (unlikely with simple logic but possible)
        
        # Convert to uppercase and add standard suffix
        return f"{lastname.upper()}, J.:"
    
    return None

@supreme_bp.route(route="fix_ponentes", auth_level=func.AuthLevel.ANONYMOUS)
def fix_ponentes_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Triggering Manual Ponente Fix...')
    
    try:
        conn = None
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get all distinct ponentes
        cur.execute("SELECT DISTINCT ponente FROM sc_decided_cases WHERE ponente IS NOT NULL")
        raw_rows = cur.fetchall()
        
        updates = 0
        
        for row in raw_rows:
            original = row[0]
            if not original: continue
            
            normalized = normalize_ponente_text(original)
            
            if normalized and normalized != original:
                logging.info(f"Normalizing: '{original}' -> '{normalized}'")
                cur.execute("UPDATE sc_decided_cases SET ponente = %s WHERE ponente = %s", (normalized, original))
                updates += cur.rowcount
        
        # Manual Override for A.M. No. P-09-2646 (ID 52845)
        cur.execute("UPDATE sc_decided_cases SET ponente = 'PERALTA, J.:' WHERE id = 52845")
        updates += cur.rowcount
                
        conn.commit()
        cur.close()
        
        # Clear Cache
        if REDIS_ENABLED:
            cache_delete("sc_decisions:ponentes")
            cache_clear_pattern("sc_decisions:*")
            logging.info("Cache cleared for ponentes and decisions.")

        return func.HttpResponse(
            json.dumps({"message": "Ponentes Normalized", "updates_count": updates}),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"Error in fix_ponentes: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )

@supreme_bp.route(route="backfill_per_curiam", auth_level=func.AuthLevel.ANONYMOUS)
def backfill_per_curiam_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Triggering Per Curiam Backfill...')
    
    try:
        conn = None
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Find candidates (Missing Ponente + Has Text)
        cur.execute("""
            SELECT id, full_text_md 
            FROM sc_decided_cases 
            WHERE (ponente IS NULL OR ponente = '') 
            AND full_text_md IS NOT NULL
        """)
        candidates = cur.fetchall()
        logging.info(f"Found {len(candidates)} candidates for Per Curiam check.")
        
        updates = 0
        per_curiam_regex = re.compile(r"(?i)^\s*per\s+curiam\s*[:\.]?\s*$", re.MULTILINE)
        
        for row in candidates:
            case_id = row[0]
            text = row[1]
            if not text: continue
            
            # Check regex first (anchored)
            if per_curiam_regex.search(text):
                is_match = True
            else:
                # Fallback: Check occurrence in text (case-insensitive)
                # searching entire text as requested by user
                lower = text.lower()
                if "per curiam" in lower:
                     is_match = True
            
            if is_match:
                logging.info(f"match found for Case {case_id}")
                cur.execute("UPDATE sc_decided_cases SET ponente = 'Per Curiam' WHERE id = %s", (case_id,))
                updates += cur.rowcount
                
        conn.commit()
        cur.close()
        
        return func.HttpResponse(
            json.dumps({"message": "Per Curiam Backfill Complete", "updates_count": updates, "candidates_checked": len(candidates)}),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"Error in backfill_per_curiam: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )

