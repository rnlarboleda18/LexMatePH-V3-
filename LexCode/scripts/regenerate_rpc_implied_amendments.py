"""
regenerate_rpc_implied_amendments.py
------------------------------------
Rewrite ``legal_effect`` strings in ``api/data/rpc_implied_amendments.json`` using
Vertex Gemini (same auth stack as ``lexcode_genai_client.py``).

Usage:
  python LexCode/scripts/regenerate_rpc_implied_amendments.py [--dry-run] [--only-article N]

Requires ADC / GOOGLE_CLOUD_PROJECT per ``lexcode_genai_client.py``.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
OUT_JSON = REPO_ROOT / "api" / "data" / "rpc_implied_amendments.json"

sys.path.insert(0, str(SCRIPT_DIR))

from lexcode_genai_client import get_amendment_primary_model, get_genai_client  # noqa: E402


def _regenerate_legal_effect(
    client,
    model: str,
    article_num: str,
    law: str,
    previous: str,
) -> str:
    prompt = f"""You edit Philippine legal reference summaries for a codal viewer.

RPC Article **{article_num}** is affected in practice by this superseding or special law (often without an express RPC amendatory clause):

**Law:** {law}

**Current summary:**
{previous}

Rewrite **legal_effect** as **2–5 sentences** in plain English. You may start with a short topic label and colon (e.g. "Characterization shift:") when it fits. Optional **bold** in markdown only for that label phrase. Do not invent Supreme Court cases or statutory sections; keep any specific citations that already appear in the current summary unless they are clearly wrong.

Return **only** valid JSON:
{{"legal_effect": "..."}}"""
    resp = client.models.generate_content(
        model=model,
        contents=prompt,
        config={"temperature": 0.2, "response_mime_type": "application/json"},
    )
    raw = (resp.text or "").strip()
    data = json.loads(raw)
    le = (data.get("legal_effect") or "").strip()
    if not le:
        raise ValueError("Model returned empty legal_effect")
    return le


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate RPC implied amendment blurbs (Vertex AI)")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing JSON")
    parser.add_argument(
        "--only-article",
        type=str,
        default=None,
        metavar="N",
        help="Only process this article number key (e.g. 263)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.4,
        help="Seconds between API calls (default 0.4)",
    )
    args = parser.parse_args()

    if not OUT_JSON.is_file():
        raise SystemExit(f"Missing {OUT_JSON}")

    with open(OUT_JSON, encoding="utf-8") as f:
        data: dict[str, list] = json.load(f)

    client = get_genai_client()
    model = get_amendment_primary_model()
    print(f"Model: {model}")
    print(f"Output: {OUT_JSON}")
    if args.dry_run:
        print("DRY RUN — no file write")

    keys = sorted(data.keys(), key=lambda k: int(k) if str(k).isdigit() else 0)
    if args.only_article is not None:
        k = str(args.only_article).strip()
        if k not in data:
            raise SystemExit(f"Article key not in JSON: {k}")
        keys = [k]

    updated = json.loads(json.dumps(data))  # deep copy via JSON
    total = 0
    for article_num in keys:
        entries = updated.get(article_num) or []
        for i, entry in enumerate(entries):
            law = (entry.get("law") or "").strip()
            prev = (entry.get("legal_effect") or "").strip()
            if not law or not prev:
                print(f"  skip {article_num}[{i}]: missing law or legal_effect")
                continue
            print(f"  Article {article_num} — {law[:60]}…")
            if args.dry_run:
                total += 1
                continue
            try:
                new_le = _regenerate_legal_effect(client, model, article_num, law, prev)
            except Exception as exc:
                print(f"    ERROR: {exc}")
                raise
            updated[article_num][i]["legal_effect"] = new_le
            total += 1
            time.sleep(max(0.0, args.sleep))

    if args.dry_run:
        print(f"Would refresh {total} entr(y/ies).")
        return

    backup = OUT_JSON.with_suffix(".json.bak")
    backup.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {total} updated entr(y/ies). Backup: {backup}")


if __name__ == "__main__":
    main()
