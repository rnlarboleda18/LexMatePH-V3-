"""
Export baseline manual amendment JSON specs from markdown using existing
deterministic parsers in ``parse_amendment.parse_amendment_document``.

Purpose: populate ``LexCode/Codals/manual_amendments/specs/`` for the
no-AI manual pipeline. Run from repo root::

  python LexCode/scripts/build_baseline_manual_specs.py

Inputs: known MD basenames that resolve to offline parsers (no Gemini calls).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_MD = _REPO / "LexCode" / "Codals" / "md"
_OUT_DIR = _REPO / "LexCode" / "Codals" / "manual_amendments" / "specs"
_MANIFEST = _REPO / "LexCode" / "Codals" / "manual_amendments" / "manifest.json"

# MD filename -> output JSON stem (mostly via parse_amendment_document; RA 10951 uses offline helper only)
_BASELINE_SOURCES: list[tuple[str, str]] = [
    ("Act No. 3999, December 05, 1932.md", "act_3999"),
    ("act_4117_1933.md", "act_4117"),
    ("ca_99_1936.md", "ca_99"),
    ("ca_235_1937.md", "ca_235"),
    ("ra_6968_1990.md", "ra_6968"),
    ("ra_10951_2017.md", "ra_10951"),
]


def main() -> int:
    sys.path.insert(0, str(_REPO / "LexCode" / "scripts"))
    from parse_amendment import (  # noqa: WPS433
        parse_amendment_document,
        parse_ra10951_offline_rpc_articles_134_to_136,
    )

    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    steps: list[dict[str, str]] = []

    for md_name, stem in _BASELINE_SOURCES:
        md_path = _MD / md_name
        if not md_path.is_file():
            print(f"[SKIP] Missing markdown: {md_path.relative_to(_REPO)}")
            continue
        if md_name == "ra_10951_2017.md":
            data = parse_ra10951_offline_rpc_articles_134_to_136(str(md_path))
            if not data:
                print(f"[SKIP] Offline RA 10951 parse failed (Section 6 / Art. 136): {md_path}")
                continue
            notes = (
                f"Generated from LexCode/Codals/md/{md_name} via parse_ra10951_offline_rpc_articles_134_to_136 "
                "(no AI)."
            )
        else:
            data = parse_amendment_document(str(md_path))
            notes = f"Generated from LexCode/Codals/md/{md_name} via offline/deterministic parse."
        data.pop("raw_content", None)
        payload = {
            "amendment_id": data["amendment_id"],
            "date": data["date"],
            "title": data.get("title") or "",
            "notes": notes,
            "changes": [
                {
                    "article_number": c["article_number"],
                    "new_text": c["new_text"],
                    "action": c.get("action") or "amend",
                }
                for c in data["changes"]
            ],
        }
        out_path = _OUT_DIR / f"{stem}.json"
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"[OK] Wrote {out_path.relative_to(_REPO)}")
        steps.append({"id": stem, "spec": f"specs/{stem}.json"})

    manifest = {
        "version": 1,
        "description": (
            "Ordered manual RPC amendment specs. Apply via scripts/reingest_rpc_manual_pipeline.py. "
            "Each step is one JSON file; process_amendment applies all changes in that file literally "
            "(no AI)."
        ),
        "steps": steps,
    }
    _MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    _MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[OK] Wrote {_MANIFEST.relative_to(_REPO)} ({len(steps)} steps)")
    return 0 if steps else 1


if __name__ == "__main__":
    raise SystemExit(main())
