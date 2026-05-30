import logging
import azure.functions as func
from db_pool import get_db_connection, put_db_connection

sitemap_bp = func.Blueprint()

SITE_BASE = "https://www.lexmateph.com"
PAGE_SIZE = 45000


@sitemap_bp.route(route="sitemap_decisions.xml", methods=["GET"])
def sitemap_decisions(req: func.HttpRequest) -> func.HttpResponse:
    """
    Paginated sitemap for all case digest URLs.
    Accepts ?page=N (1-indexed). Each page contains up to PAGE_SIZE URLs.
    Static app routes live in sitemap_pages.xml — not duplicated here.

    Referenced by sitemap.xml as:
        sitemap_decisions.xml?page=1
        sitemap_decisions.xml?page=2
        ...
    """
    try:
        page = max(1, int(req.params.get("page", "1")))
    except ValueError:
        page = 1

    offset = (page - 1) * PAGE_SIZE

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT id
            FROM   sc_decided_cases
            WHERE  id IS NOT NULL
            ORDER  BY id
            LIMIT  %s OFFSET %s
            """,
            (PAGE_SIZE, offset),
        )
        rows = cur.fetchall()
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

    parts: list[str] = []
    parts.append('<?xml version="1.0" encoding="UTF-8"?>\n')
    parts.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')

    for row in rows:
        case_id = row[0]
        parts.append("  <url>\n")
        parts.append(f"    <loc>{SITE_BASE}/decisions/{case_id}</loc>\n")
        parts.append("    <changefreq>monthly</changefreq>\n")
        parts.append("    <priority>0.7</priority>\n")
        parts.append("  </url>\n")

    parts.append("</urlset>")

    xml_body = "".join(parts)

    logging.info(
        "sitemap_decisions: page=%d, %d URLs (%d bytes)",
        page,
        len(rows),
        len(xml_body),
    )

    return func.HttpResponse(
        xml_body,
        status_code=200,
        mimetype="application/xml",
        headers={"Cache-Control": "public, max-age=3600, s-maxage=86400"},
    )
