"""
reingest_content.py
====================
Simple, targeted script to directly patch content_md in rpc_codal
for specific articles from a markdown source file.

NO AI, NO amendment history, NO info-icon changes.
Just a direct content update.

Usage:
    python reingest_content.py --file <path_to_md> --articles 266-A,266-B,266-C,266-D
"""

import os
import re
import sys
import json
import argparse
import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_connection():
    try:
        with open(os.path.join(os.path.dirname(__file__), '..', '..', 'local.settings.json')) as f:
            settings = json.load(f)
            conn_str = settings['Values']['DB_CONNECTION_STRING']
    except Exception:
        conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
    return psycopg2.connect(conn_str)


def parse_articles_from_md(md_path):
    """
    Parse a markdown file and extract individual articles.
    Returns dict: { article_number: { title, body } }
    """
    with open(md_path, 'r', encoding='utf-8') as f:
        text = f.read()

    articles = {}

    # Match patterns like: "Article 266-A. Title. - Body" or Article 266-A. Title.\nBody
    # Split on Article boundaries
    pattern = r'"?Article\s+([\w\-]+)\.\s*(.*?)(?=\n"?Article\s+[\w\-]+\.|\Z)'
    matches = re.findall(pattern, text, re.DOTALL)

    for num, rest in matches:
        rest = rest.strip()
        # Try to split title from body at " - " or first newline
        title_body = re.split(r'\s+-\s+|\n', rest, maxsplit=1)
        title = title_body[0].strip().strip('*').strip()
        body = title_body[1].strip() if len(title_body) > 1 else ''

        # Clean markdown italics from title
        title = re.sub(r'\*', '', title)

        articles[num] = {'title': title, 'body': body}
        print(f"  Parsed Article {num}: title='{title[:50]}...' body_len={len(body)}")

    return articles


def reingest_articles(md_path, target_articles):
    """
    Patch content_md (and optionally article_title) for the specified articles
    directly in rpc_codal.
    """
    print(f"\n{'='*60}")
    print(f"REINGEST: Direct Content Patch")
    print(f"Source: {md_path}")
    print(f"Targets: {', '.join(target_articles)}")
    print(f"{'='*60}\n")

    # 1. Parse markdown
    print("[1/3] Parsing markdown source...")
    parsed = parse_articles_from_md(md_path)
    if not parsed:
        print("  [!] No articles found in file. Aborting.")
        return

    # 2. Connect to DB
    print("\n[2/3] Connecting to database...")
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    print(f"  [OK] Connected to: {conn.dsn.split('@')[-1]}")

    # 3. Patch each target article
    print("\n[3/3] Patching articles...")
    results = []

    for art_num in target_articles:
        art_num = art_num.strip()
        if art_num not in parsed:
            print(f"  [!] Article {art_num} NOT found in markdown. Skipping.")
            results.append({'article': art_num, 'success': False, 'reason': 'Not in markdown'})
            continue

        data = parsed[art_num]
        title = data['title']
        body = data['body']

        # Check if article exists in rpc_codal
        cur.execute("SELECT id, article_num, article_title FROM rpc_codal WHERE article_num = %s", (art_num,))
        row = cur.fetchone()

        if row:
            cur.execute("""
                UPDATE rpc_codal
                SET content_md = %s,
                    updated_at = NOW()
                WHERE article_num = %s
            """, (body, art_num))
            print(f"  [OK] Updated Article {art_num} (id={row['id']}) — content_md set ({len(body)} chars)")
            results.append({'article': art_num, 'success': True, 'action': 'updated'})
        else:
            print(f"  [!] Article {art_num} not found in rpc_codal. Skipping (use process_amendment.py to insert new articles).")
            results.append({'article': art_num, 'success': False, 'reason': 'Not in rpc_codal'})

    conn.commit()
    cur.close()
    conn.close()

    # Summary
    print(f"\n{'='*60}")
    print(f"DONE — {sum(1 for r in results if r['success'])}/{len(results)} articles updated.")
    for r in results:
        status = "[OK]" if r['success'] else "[!]"
        note = r.get('action', r.get('reason', ''))
        print(f"  {status} Article {r['article']}: {note}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Directly patch rpc_codal content_md from a markdown source file.")
    parser.add_argument("--file", required=True, help="Path to the markdown source file (e.g. ra_8353_1997.md)")
    parser.add_argument("--articles", required=True, help="Comma-separated list of article numbers to patch (e.g. 266-A,266-B,266-C,266-D)")
    args = parser.parse_args()

    target_articles = [a.strip() for a in args.articles.split(',')]
    reingest_articles(args.file, target_articles)


if __name__ == "__main__":
    main()
