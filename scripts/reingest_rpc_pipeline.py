"""
RPC full re-ingest orchestrator (repo root: ``scripts/reingest_rpc_pipeline.py``).

Phases
------
1. **Base codal** — ``LexCode/scripts/ingest_rpc_base_from_md.py`` reads
   ``LexCode/Codals/md/RPC.md`` (full header hierarchy via ``rpc_md_stream_parser``)
   into ``article_versions`` + ``rpc_codal``.
2. **Direct amendments** — runs ``LexCode/scripts/process_amendment.py`` on each
   amendatory statute **in chronological order** (RPC-only markdown in this repo).
3. **Implied / supplementary** — laws in ``LexCode/Codals/md/*.md`` that are not the
   base RPC and not in the direct list: writes a manifest JSON for traceability
   (no automatic merge into ``article_versions``; those do not republish RPC text).

Environment
-----------
``DB_CONNECTION_STRING`` or ``api/local.settings.json`` → ``Values.DB_CONNECTION_STRING``.

Usage
-----
  python scripts/reingest_rpc_pipeline.py
  python scripts/reingest_rpc_pipeline.py --dry-run
  python scripts/reingest_rpc_pipeline.py --only-base
  python scripts/reingest_rpc_pipeline.py --wipe-rpc-links
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_MD = _REPO / "LexCode" / "Codals" / "md"
_BASE = _REPO / "LexCode" / "scripts" / "ingest_rpc_base_from_md.py"
_PROC = _REPO / "LexCode" / "scripts" / "process_amendment.py"
_IMPLIED_OUT = _REPO / "LexCode" / "Codals" / "generated" / "rpc_implied_sources_manifest.json"

# Chronological direct amendatory sources (RPC text) — filenames under LexCode/Codals/md/
_DIRECT_AMENDMENTS: list[str] = [
    "Act No. 3999, December 05, 1932.md",
    "act_4117_1933.md",
    "ca_99_1936.md",
    "ca_235_1937.md",
    "ra_12_1946.md",
    "ra_18_1946.md",
    "ra_47_1946.md",
    "ra_1084_1954.md",
    "ra_2632_1960.md",
    "ra_4661_1966.md",
    "ra_6127_1970.md",
    "ra_6968_1990.md",
    "ra_7659_1993.md",
    "ra_8353_1997.md",
    "ra_10158_2012.md",
    "ra_10592_2013.md",
    "ra_10655_2015.md",
    "ra_10951_2017.md",
    "ra_11362_2019.md",
    "ra_11594_2021.md",
    "ra_11648_2022.md",
    "ra_11926_2022.md",
]


def _run_py(script: Path, args: list[str], *, dry_run: bool) -> int:
    cmd = [sys.executable, str(script), *args]
    print(f"\n>> {' '.join(cmd)}")
    if dry_run:
        return 0
    r = subprocess.run(cmd, cwd=str(_REPO))
    return r.returncode


def _write_implied_manifest(dry_run: bool) -> None:
    direct_set = set(_DIRECT_AMENDMENTS) | {"RPC.md"}
    implied: list[str] = []
    if _MD.is_dir():
        for p in sorted(_MD.glob("*.md")):
            if p.name in direct_set:
                continue
            implied.append(p.name)
    payload = {
        "note": (
            "These markdown files are not run through process_amendment as direct "
            "RPC codal amendments. Review for implied / supplementary interaction with the RPC."
        ),
        "files": implied,
    }
    print(f"\n[Phase 3] Implied/supplementary markdown count: {len(implied)}")
    if dry_run:
        print("[dry-run] Skipping manifest write.")
        return
    _IMPLIED_OUT.parent.mkdir(parents=True, exist_ok=True)
    _IMPLIED_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {_IMPLIED_OUT.relative_to(_REPO)}")


def main() -> None:
    ap = argparse.ArgumentParser(description="RPC base + direct amendments + implied manifest")
    ap.add_argument("--dry-run", action="store_true", help="Print steps only; no DB writes")
    ap.add_argument("--only-base", action="store_true", help="Run phase 1 only")
    ap.add_argument("--skip-amendments", action="store_true", help="Skip phase 2 (after base)")
    ap.add_argument(
        "--wipe-rpc-links",
        action="store_true",
        help="Pass through to base ingest (DELETE codal_case_links for RPC).",
    )
    ap.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on the first amendment failure. Default: continue and still write the implied manifest.",
    )
    args = ap.parse_args()

    if not _BASE.is_file():
        sys.exit(f"Missing {_BASE}")
    if not _PROC.is_file():
        sys.exit(f"Missing {_PROC}")

    base_args: list[str] = []
    if args.wipe_rpc_links:
        base_args.append("--wipe-rpc-links")

    print("=" * 72)
    print("RPC RE-INGEST PIPELINE")
    print("=" * 72)

    rc = _run_py(_BASE, base_args + (["--dry-run"] if args.dry_run else []), dry_run=args.dry_run)
    if rc != 0:
        sys.exit(rc)

    if args.only_base:
        _write_implied_manifest(args.dry_run)
        return

    amendment_failures: list[str] = []
    if not args.skip_amendments:
        for name in _DIRECT_AMENDMENTS:
            md = _MD / name
            if not md.is_file():
                print(f"\n[WARN] Missing direct amendment file, skip: {name}")
                continue
            extra: list[str] = ["--file", str(md), "--code", "RPC"]
            if name.lower() == "ra_6968_1990.md":
                extra.append("--offline-ra6968")
            # RA 10951: full file needs AI parse; offline mode only covers Art. 136 subset.
            rc = _run_py(_PROC, extra + (["--dry-run"] if args.dry_run else []), dry_run=args.dry_run)
            if rc != 0:
                amendment_failures.append(name)
                if args.fail_fast:
                    sys.exit(rc)
                print(f"\n[WARN] Amendment step failed ({name}); continuing.")

    _write_implied_manifest(args.dry_run)
    print("\n" + "=" * 72)
    print("RPC pipeline finished.")
    if amendment_failures:
        print(f"Amendment failures ({len(amendment_failures)}): {', '.join(amendment_failures)}")
        print("Set a valid GOOGLE_API_KEY (api/local.settings.json) and re-run, or use --fail-fast.")
    print("=" * 72)
    if amendment_failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
