# Decision Page SSR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve a server-rendered HTML page for every `/decisions/{id}` URL so Google indexes each of the 50,000 case digests with real content instead of an empty SPA shell.

**Architecture:** A new Azure Function blueprint (`decision_page`) queries PostgreSQL for a case by ID and returns a lightweight, semantic HTML page containing the full case digest. Azure SWA's route config is updated to rewrite `/decisions/{id}` requests to this function. Client-side SPA navigation is unaffected (React Router handles those in memory without a server round-trip).

**Tech Stack:** Python 3.10, Azure Functions v2 (Blueprint pattern), psycopg2, Azure Static Web Apps route rewrite

---

## Smoke Test Rule (applies to every deploy)

Before every deploy, run the smoke test script locally against `func start`. Do not push until all assertions pass.

```
cd api && func start          # terminal 1
python tools/test_decision_page.py  # terminal 2 — must show OK for all checks
```

---

## File Map

| Action | File |
|---|---|
| Create | `api/blueprints/decision_page.py` |
| Create | `api/tools/test_decision_page.py` |
| Modify | `api/function_app.py` |
| Modify | `src/frontend/public/staticwebapp.config.json` |
| Modify | `src/frontend/dist/staticwebapp.config.json` |

---

## Task 1: Write the failing smoke test first

**Files:**
- Create: `api/tools/test_decision_page.py`

- [ ] **Step 1: Create the smoke test**

```python
"""
Smoke test for the decision_page Azure Function.
Run with: python api/tools/test_decision_page.py
Requires func start to be running on localhost:7071.
"""
import sys
import urllib.request
import urllib.error

BASE = "http://localhost:7071/api/decision_page"
KNOWN_ID = "1534"   # real case ID from the GSC failing URL list


def check(label, condition, detail=""):
    if condition:
        print(f"  OK  {label}")
    else:
        print(f"  FAIL {label}" + (f": {detail}" if detail else ""))
        sys.exit(1)


def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return r.status, r.read().decode("utf-8"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8"), {}


print(f"\n=== decision_page smoke test ===\n")

# --- Case 1: known good ID ---
print(f"[1] GET /api/decision_page/{KNOWN_ID}")
status, body, headers = fetch(f"{BASE}/{KNOWN_ID}")
check("status 200", status == 200, status)
check("content-type text/html", "text/html" in headers.get("Content-Type", ""), headers.get("Content-Type"))
check("<title> present", "<title>" in body)
check("canonical tag present", 'rel="canonical"' in body)
check("meta description present", 'name="description"' in body)
check("case_number or GR present", "G.R." in body or "A.M." in body or str(KNOWN_ID) in body)
check("JSON-LD present", "application/ld+json" in body)
check("LexMatePH branding", "LexMatePH" in body)

# --- Case 2: non-existent ID ---
print(f"\n[2] GET /api/decision_page/999999999")
status, body, _ = fetch(f"{BASE}/999999999")
check("status 404 for unknown id", status == 404, status)

# --- Case 3: non-numeric ID ---
print(f"\n[3] GET /api/decision_page/abc")
status, body, _ = fetch(f"{BASE}/abc")
check("status 404 for non-numeric id", status == 404, status)

print(f"\nAll checks passed.\n")
```

- [ ] **Step 2: Run the test — expect it to fail with connection refused (function doesn't exist yet)**

```
python api/tools/test_decision_page.py
```

Expected: `urllib.error.URLError: <urlopen error [Errno 111] Connection refused>` or similar — confirms the test is wired up correctly before the implementation exists.

---

## Task 2: Create the decision_page blueprint

**Files:**
- Create: `api/blueprints/decision_page.py`

- [ ] **Step 1: Create the blueprint file**

```python
import re
import logging
import azure.functions as func
from db_pool import get_db_connection, put_db_connection
from cache import cache_get, cache_set

decision_page_bp = func.Blueprint()

SITE_BASE = "https://www.lexmateph.com"
_CACHE_TTL = 3600  # 1 hour — cases rarely change


def _strip_md(text: str) -> str:
    """Remove common Markdown syntax for plain-text output."""
    if not text:
        return ""
    text = re.sub(r"#{1,6}\s+", "", text)
    text = re.sub(r"[*_`>~]", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def _esc(s) -> str:
    """HTML-escape a value for safe embedding in attributes or text."""
    s = str(s) if s is not None else ""
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
    )


def _section(heading: str, raw_text: str) -> str:
    """Return an HTML <section> block or empty string if no content."""
    text = _strip_md(raw_text)
    if not text:
        return ""
    # Split on double newlines to get paragraphs
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    paras_html = "".join(f"<p>{_esc(p)}</p>\n" for p in paragraphs)
    return (
        f'<section class="digest-section">\n'
        f'  <h2>{heading}</h2>\n'
        f'  {paras_html}'
        f'</section>\n'
    )


def _build_html(case: dict) -> str:
    case_label = _esc(case["short_title"] or case.get("full_title") or f"Case {case['id']}")
    gr         = _esc(case.get("case_number") or "")
    date_str   = str(case.get("date") or "")[:10]
    ponente    = _esc(case.get("ponente") or "")
    subject    = _esc(case.get("subject") or "")
    category   = _esc(case.get("significance_category") or "")

    page_title = f"{case_label} [{gr}] · LexMatePH" if gr else f"{case_label} · LexMatePH"
    canonical  = f"{SITE_BASE}/decisions/{case['id']}"

    facts_plain = _strip_md(case.get("digest_facts") or case.get("digest_ruling") or "")
    if len(facts_plain) > 160:
        meta_desc = facts_plain[:157] + "…"
    elif facts_plain:
        meta_desc = facts_plain
    else:
        meta_desc = (
            f"Case digest: {case_label}"
            + (f" ({gr})" if gr else "")
            + ". Philippine Supreme Court jurisprudence on LexMatePH."
        )
    meta_desc_esc = _esc(meta_desc)

    facts_html   = _section("Facts", case.get("digest_facts") or "")
    issues_html  = _section("Issue(s)", case.get("digest_issues") or "")
    ruling_html  = _section("Ruling", case.get("digest_ruling") or "")
    ratio_html   = _section("Ratio Decidendi", case.get("digest_ratio") or "")
    doctrine_html = _section("Main Doctrine", case.get("main_doctrine") or "")

    schema = {
        "@context": "https://schema.org",
        "@type": "LegalCase",
        "name": case_label,
        "identifier": gr,
        "datePublished": date_str,
        "url": canonical,
        "description": meta_desc,
        "publisher": {
            "@type": "Organization",
            "name": "Supreme Court of the Philippines"
        },
        "inLanguage": "en-PH"
    }
    if ponente:
        schema["author"] = {"@type": "Person", "name": ponente}

    import json
    schema_json = json.dumps(schema)

    meta_parts = []
    if gr:        meta_parts.append(gr)
    if date_str:  meta_parts.append(date_str)
    if ponente:   meta_parts.append(f"J. {ponente}")
    if subject:   meta_parts.append(subject)
    meta_line = " · ".join(meta_parts)

    badge = f'<span class="badge">{category}</span>' if category else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_esc(page_title)}</title>
  <meta name="description" content="{meta_desc_esc}">
  <meta name="author" content="LexMatePH">
  <link rel="canonical" href="{canonical}">

  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical}">
  <meta property="og:title" content="{_esc(page_title)}">
  <meta property="og:description" content="{meta_desc_esc}">
  <meta property="og:site_name" content="LexMatePH">
  <meta property="og:locale" content="en_PH">

  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{_esc(page_title)}">
  <meta name="twitter:description" content="{meta_desc_esc}">

  <script type="application/ld+json">{schema_json}</script>

  <style>
    *,*::before,*::after{{box-sizing:border-box}}
    body{{font-family:system-ui,-apple-system,sans-serif;max-width:800px;margin:0 auto;padding:2rem 1rem;color:#1e293b;line-height:1.6;background:#f8fafc}}
    a{{color:#4f46e5;text-decoration:none}}
    a:hover{{text-decoration:underline}}
    header{{display:flex;align-items:center;gap:1rem;border-bottom:2px solid #e2e8f0;padding-bottom:1rem;margin-bottom:2rem}}
    .logo{{font-weight:800;font-size:1.1rem;color:#4f46e5}}
    .logo span{{color:#64748b;font-weight:400}}
    h1{{font-size:1.4rem;font-weight:800;color:#0f172a;margin:0 0 0.5rem}}
    .meta{{color:#64748b;font-size:0.85rem;margin-bottom:0.75rem}}
    .badge{{display:inline-block;background:#ede9fe;color:#5b21b6;font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;padding:0.2rem 0.5rem;border-radius:999px;margin-bottom:1rem}}
    .digest-section{{margin-bottom:1.75rem}}
    .digest-section h2{{font-size:0.75rem;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:#94a3b8;margin:0 0 0.5rem;border-bottom:1px solid #e2e8f0;padding-bottom:0.3rem}}
    .digest-section p{{margin:0 0 0.75rem;color:#334155}}
    .cta-bar{{background:#4f46e5;border-radius:0.75rem;padding:1.25rem 1.5rem;margin:2rem 0;display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap}}
    .cta-bar p{{color:#e0e7ff;margin:0;font-size:0.875rem}}
    .cta-bar a{{background:white;color:#4f46e5;font-weight:700;padding:0.5rem 1rem;border-radius:0.5rem;white-space:nowrap;font-size:0.875rem}}
    footer{{border-top:1px solid #e2e8f0;margin-top:3rem;padding-top:1rem;font-size:0.8rem;color:#94a3b8}}
  </style>
</head>
<body>
  <header>
    <div class="logo"><a href="{SITE_BASE}">LexMatePH</a> <span>· Philippine Legal Research</span></div>
  </header>

  <article>
    <h1>{case_label}</h1>
    <div class="meta">{_esc(meta_line)}</div>
    {badge}

    {facts_html}
    {issues_html}
    {ruling_html}
    {ratio_html}
    {doctrine_html}
  </article>

  <div class="cta-bar">
    <p>Access audio review, related cases, codal links, and more.</p>
    <a href="{SITE_BASE}/decisions">Open LexMatePH &rarr;</a>
  </div>

  <footer>
    &copy; LexMatePH &mdash; Data sourced from publicly available SC decisions.
    <a href="{SITE_BASE}/legal">Privacy &amp; Terms</a>
  </footer>
</body>
</html>"""


@decision_page_bp.route(
    route="decision_page/{case_id}",
    methods=["GET"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
def decision_page(req: func.HttpRequest, case_id: str) -> func.HttpResponse:
    if not case_id.isdigit():
        return func.HttpResponse("Not found.", status_code=404)

    cache_key = f"dpage:{case_id}"
    cached = cache_get(cache_key)
    if cached:
        return func.HttpResponse(
            cached,
            status_code=200,
            mimetype="text/html; charset=utf-8",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                id, case_number, short_title, full_title,
                TO_CHAR(date, 'YYYY-MM-DD') AS date,
                ponente, subject, significance_category,
                digest_facts, digest_issues, digest_ruling,
                digest_ratio, main_doctrine
            FROM sc_decided_cases
            WHERE id = %s
            """,
            (int(case_id),),
        )
        row = cur.fetchone()
        cur.close()
    except Exception as exc:
        logging.error("decision_page: DB error id=%s: %s", case_id, exc)
        return func.HttpResponse("Database error.", status_code=500)
    finally:
        if conn:
            put_db_connection(conn)

    if not row:
        return func.HttpResponse("Case not found.", status_code=404)

    cols = [
        "id", "case_number", "short_title", "full_title", "date",
        "ponente", "subject", "significance_category",
        "digest_facts", "digest_issues", "digest_ruling",
        "digest_ratio", "main_doctrine",
    ]
    case = dict(zip(cols, row))

    html = _build_html(case)
    cache_set(cache_key, html, ttl=_CACHE_TTL)

    return func.HttpResponse(
        html,
        status_code=200,
        mimetype="text/html; charset=utf-8",
        headers={"Cache-Control": "public, max-age=3600, s-maxage=86400"},
    )
```

- [ ] **Step 2: Commit**

```
git add api/blueprints/decision_page.py api/tools/test_decision_page.py
git commit -m "feat(ssr): add decision_page blueprint and smoke test"
```

---

## Task 3: Register blueprint in function_app.py

**Files:**
- Modify: `api/function_app.py`

- [ ] **Step 1: Add import and registration**

In `api/function_app.py`, inside the `try` block with the other blueprints, add:

```python
    from blueprints.decision_page import decision_page_bp
    # ... (add after sitemap_bp registration)
    app.register_functions(decision_page_bp)
```

- [ ] **Step 2: Commit**

```
git add api/function_app.py
git commit -m "feat(ssr): register decision_page blueprint"
```

---

## Task 4: Update SWA route config

**Files:**
- Modify: `src/frontend/public/staticwebapp.config.json`
- Modify: `src/frontend/dist/staticwebapp.config.json`

- [ ] **Step 1: Add the rewrite rule to `public/staticwebapp.config.json`**

Add this as the **first entry** in the `"routes"` array, before all existing routes:

```json
{
    "route": "/decisions/{case_id}",
    "rewrite": "/api/decision_page/{case_id}"
}
```

The full `routes` array beginning should look like:
```json
"routes": [
    {
        "route": "/decisions/{case_id}",
        "rewrite": "/api/decision_page/{case_id}"
    },
    {
        "route": "/robots.txt",
        ...
    },
    ...
]
```

- [ ] **Step 2: Apply the same change to `dist/staticwebapp.config.json`**

Same edit — first entry in `routes`.

- [ ] **Step 3: Commit**

```
git add src/frontend/public/staticwebapp.config.json src/frontend/dist/staticwebapp.config.json
git commit -m "feat(ssr): rewrite /decisions/{id} to decision_page function"
```

---

## Task 5: Smoke test locally

- [ ] **Step 1: Start the local Azure Functions runtime**

```
cd api && func start
```

Wait until you see `Host lock lease acquired` in the output — the runtime is ready.

- [ ] **Step 2: Run the smoke test**

In a second terminal:

```
python api/tools/test_decision_page.py
```

Expected output:
```
=== decision_page smoke test ===

[1] GET /api/decision_page/1534
  OK  status 200
  OK  content-type text/html
  OK  <title> present
  OK  canonical tag present
  OK  meta description present
  OK  case_number or GR present
  OK  JSON-LD present
  OK  LexMatePH branding

[2] GET /api/decision_page/999999999
  OK  status 404 for unknown id

[3] GET /api/decision_page/abc
  OK  status 404 for non-numeric id

All checks passed.
```

- [ ] **Step 3: Manual spot-check in browser**

Open `http://localhost:7071/api/decision_page/1534` in a browser. Verify:
- Case title visible in the page heading
- Facts / Ruling sections render as readable paragraphs
- "Open LexMatePH" CTA button is visible
- No raw markdown symbols (`**`, `##`, etc.) visible

**Do not proceed to Task 6 if any check fails.**

---

## Task 6: Deploy and verify live

- [ ] **Step 1: Push to main (triggers SWA deployment)**

```
git push origin main
```

- [ ] **Step 2: Wait for deployment to complete**

Check GitHub Actions or Azure portal for deployment status. Wait for green.

- [ ] **Step 3: Live smoke test — hit production**

Replace `localhost:7071/api` with `https://www.lexmateph.com/api` and run the same checks manually:

```
curl -I https://www.lexmateph.com/api/decision_page/1534
# Expect: HTTP/2 200, content-type: text/html
```

- [ ] **Step 4: Test the SWA rewrite**

```
curl -I https://www.lexmateph.com/decisions/1534
# Expect: HTTP/2 200, content-type: text/html (served by the function via rewrite)
```

- [ ] **Step 5: Verify SPA client-side navigation still works**

Open `https://www.lexmateph.com` in a browser. Navigate to SC Decisions. Click any case card. Verify the modal opens normally — this confirms client-side navigation is unaffected by the SWA rewrite (React Router handles it without a server round-trip).

- [ ] **Step 6: Test the live URL in GSC**

In Google Search Console → URL Inspection → paste `https://www.lexmateph.com/decisions/1534` → click **Test Live URL**. Verify the rendered page shows the case title and content.

---

## Self-Review

**Spec coverage:**
- ✅ Server-rendered HTML for `/decisions/{id}` — Task 2
- ✅ Proper `<title>`, `<meta description>`, canonical, JSON-LD — Task 2 `_build_html`
- ✅ SWA routing rewrite — Task 4
- ✅ Client-side SPA navigation unaffected — verified in Task 6 Step 5
- ✅ Caching to avoid DB hit on every Googlebot crawl — Task 2 `cache_set`
- ✅ 404 for unknown/invalid IDs — Task 2, tested in smoke test
- ✅ Smoke test before deploy — Task 5

**Placeholder scan:** None found — all code blocks are complete.

**Type consistency:** `case` dict keys defined in `cols` list match all `case.get()` calls in `_build_html`.
