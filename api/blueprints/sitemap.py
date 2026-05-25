import logging
import azure.functions as func
from db_pool import get_db_connection, put_db_connection

sitemap_bp = func.Blueprint()

SITE_BASE = "https://www.lexmateph.com"

# Static routes that always appear in the sitemap.
_STATIC_URLS = [
    {"loc": f"{SITE_BASE}/",              "changefreq": "daily",   "priority": "0.9"},
    {"loc": f"{SITE_BASE}/decisions",     "changefreq": "daily",   "priority": "1.0"},
    {"loc": f"{SITE_BASE}/bar-questions", "changefreq": "weekly",  "priority": "1.0"},
    {"loc": f"{SITE_BASE}/lexcode",       "changefreq": "weekly",  "priority": "1.0"},
    {"loc": f"{SITE_BASE}/lexplay",       "changefreq": "weekly",  "priority": "0.9"},
    {"loc": f"{SITE_BASE}/flashcards",    "changefreq": "weekly",  "priority": "0.8"},
    {"loc": f"{SITE_BASE}/lexify",        "changefreq": "weekly",  "priority": "1.0"},
    {"loc": f"{SITE_BASE}/lexmate",       "changefreq": "weekly",  "priority": "0.9"},
    {"loc": f"{SITE_BASE}/updates",       "changefreq": "weekly",  "priority": "0.5"},
    {"loc": f"{SITE_BASE}/legal",         "changefreq": "monthly", "priority": "0.3"},
]


@sitemap_bp.route(route="sitemap_decisions.xml", methods=["GET"])
def sitemap_decisions(req: func.HttpRequest) -> func.HttpResponse:
    """
    Generates a full XML sitemap covering all indexed case digests plus the
    main static routes.  Sitemap spec limits: 50 000 URLs / 50 MB per file —
    well within the ~31 000 cases currently in the database.

    Google will discover this via:
        robots.txt  →  Sitemap: https://www.lexmateph.com/api/sitemap_decisions.xml
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Fetch only the fields needed for the sitemap — keep the query fast.
        cur.execute(
            """
            SELECT id, TO_CHAR(date, 'YYYY-MM-DD') AS date_str
            FROM   sc_decided_cases
            WHERE  id IS NOT NULL
            ORDER  BY id
            """
        )
        rows = cur.fetchall()

        cur.execute("SELECT TO_CHAR(MAX(date), 'YYYY-MM-DD') FROM sc_decided_cases")
        max_date = cur.fetchone()[0] or "2026-01-01"
        cur.close()
    except Exception as exc:
        logging.error("sitemap_decisions: DB error: %s", exc)
        return func.HttpResponse(
            "Database error generating sitemap.",
            status_code=500,
            mimetype="text/plain",
        )
    finally:
        if conn:
            put_db_connection(conn)

    # Build XML manually — xml.etree is fine for this size but streaming
    # via string concatenation is faster and avoids the full DOM in memory.
    parts: list[str] = []
    parts.append('<?xml version="1.0" encoding="UTF-8"?>\n')
    parts.append(
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    )

    # Static routes first
    for s in _STATIC_URLS:
        parts.append("  <url>\n")
        parts.append(f"    <loc>{s['loc']}</loc>\n")
        parts.append(f"    <changefreq>{s['changefreq']}</changefreq>\n")
        parts.append(f"    <priority>{s['priority']}</priority>\n")
        parts.append("  </url>\n")

    # One entry per case digest
    for row in rows:
        case_id  = row[0]
        date_str = row[1]  # e.g. "2024-03-15"  — may be None

        loc = f"{SITE_BASE}/decisions/{case_id}"
        parts.append("  <url>\n")
        parts.append(f"    <loc>{loc}</loc>\n")
        if date_str:
            # Normalise to YYYY-MM-DD for the <lastmod> tag
            try:
                from datetime import datetime
                dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
                parts.append(f"    <lastmod>{dt.strftime('%Y-%m-%d')}</lastmod>\n")
            except ValueError:
                pass  # skip malformed dates
        parts.append("    <changefreq>monthly</changefreq>\n")
        parts.append("    <priority>0.7</priority>\n")
        parts.append("  </url>\n")

    parts.append("</urlset>")

    xml_body = "".join(parts)

    logging.info(
        "sitemap_decisions: generated %d case URLs + %d static URLs (%d bytes)",
        len(rows),
        len(_STATIC_URLS),
        len(xml_body),
    )

    return func.HttpResponse(
        xml_body,
        status_code=200,
        mimetype="application/xml",
        headers={
            "Cache-Control": "public, max-age=3600, s-maxage=86400",
            "Last-Modified": max_date,
        },
    )
