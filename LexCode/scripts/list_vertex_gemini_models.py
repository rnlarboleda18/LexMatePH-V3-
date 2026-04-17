"""
List **Gemini** base models exposed through **Vertex AI** for your current credentials.

Uses ``google.genai`` with ``vertexai=True`` (same auth as the amendment pipeline’s
Vertex path: API key **or** project + Application Default Credentials).

Inputs: env vars and/or ``api/local.settings.json`` (see ``lexcode_genai_client``).

Run from repo root::

  python LexCode/scripts/list_vertex_gemini_models.py
  python LexCode/scripts/list_vertex_gemini_models.py --json
  python LexCode/scripts/list_vertex_gemini_models.py --include-all-models
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO / "LexCode" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from lexcode_genai_client import build_vertex_genai_client, load_google_api_key  # noqa: E402

# When the ListPublisherModels RPC rejects API keys (Vertex Express), we still
# print IDs that typically work with ``.../publishers/google/models/{id}:generateContent``.
_FALLBACK_GEMINI_MODEL_IDS: tuple[str, ...] = (
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
)


def _short_model_id(full_name: str) -> str:
    full_name = (full_name or "").strip()
    if not full_name:
        return ""
    if "/" in full_name:
        return full_name.split("/")[-1]
    return full_name


def main() -> int:
    parser = argparse.ArgumentParser(description="List Gemini models on Vertex AI")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON array instead of a text table",
    )
    parser.add_argument(
        "--include-all-models",
        action="store_true",
        help="Include every listed model (not only names containing 'gemini')",
    )
    args = parser.parse_args()

    try:
        client_v1 = build_vertex_genai_client(api_version="v1")
        client_beta = build_vertex_genai_client(api_version="v1beta1")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1

    rows: list[dict[str, str]] = []

    def _collect(client) -> None:
        nonlocal rows
        rows = []
        pager = client.models.list(config={"page_size": 100, "query_base": True})
        for m in pager:
            name = (getattr(m, "name", None) or "") or ""
            disp = (getattr(m, "display_name", None) or "") or ""
            if not args.include_all_models:
                blob = f"{name} {disp}".lower()
                if "gemini" not in blob:
                    continue
            rows.append(
                {
                    "model_id": _short_model_id(name),
                    "name": name,
                    "display_name": disp,
                }
            )

    last_err: Exception | None = None
    for cli in (client_v1, client_beta):
        try:
            _collect(cli)
            last_err = None
            break
        except Exception as e:
            last_err = e
    if last_err is not None:
        key = load_google_api_key()
        msg = str(last_err)
        # ListPublisherModels rejects API keys; v1 list path can 404. With only a key,
        # we still print common publisher model IDs that usually work for generateContent.
        use_fallback = key and (
            "API keys are not supported" in msg
            or "ListPublisherModels" in msg
            or "CREDENTIALS_MISSING" in msg
            or ("404" in msg and "publishers/google/models" in msg)
            or ("Not Found" in msg and "models" in msg.lower())
        )
        if use_fallback:
            print(
                "Note: Listing models from Vertex often needs a Google Cloud **project** plus "
                "**Application Default Credentials** (`gcloud auth application-default login`). "
                "An **API key** alone is enough for **generateContent**, but not always for this list API.\n",
                file=sys.stderr,
            )
            print(
                "Printing a built-in reference list of common Gemini publisher model IDs "
                "(not fetched from the API).\n",
                file=sys.stderr,
            )
            rows = [
                {
                    "model_id": mid,
                    "name": f"publishers/google/models/{mid}",
                    "display_name": "(reference - verify in console / docs for your region)",
                }
                for mid in _FALLBACK_GEMINI_MODEL_IDS
            ]
        else:
            print(
                f"Vertex model list failed (tried v1 then v1beta1): {last_err}",
                file=sys.stderr,
            )
            return 1

    rows.sort(key=lambda r: r["model_id"].lower())

    if args.json:
        print(json.dumps(rows, indent=2))
        return 0

    print(f"Vertex Gemini models ({len(rows)})")
    print("-" * 72)
    for r in rows:
        mid = r["model_id"]
        disp = r["display_name"] or "(no display name)"
        print(f"{mid}")
        if disp and disp != mid:
            print(f"  {disp}")
        if r["name"] and r["name"] != mid:
            print(f"  full: {r['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
