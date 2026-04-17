"""
RPC manual re-ingest pipeline (no AI parsing, no AI merge).

Phases
------
1. **Base codal** — same as ``reingest_rpc_pipeline.py`` (``ingest_rpc_base_from_md.py``).
2. **Manual amendments** — for each entry in
   ``LexCode/Codals/manual_amendments/manifest.json``, runs **one subprocess**
   per step: ``process_amendment.py --amendment-json <spec>`` so amendments are
   applied **one legislative package at a time** (each spec can list multiple
   articles; all are literal ``new_text``).
3. **Implied manifest** — same JSON sidecar as the main RPC pipeline.

Authoring specs
---------------
- Run ``python LexCode/scripts/build_baseline_manual_specs.py`` to (re)generate
  JSON from markdown for acts that already have deterministic parsers.
- Add new steps to ``manifest.json`` and new files under ``manual_amendments/specs/``.
- Schema is validated by ``LexCode/scripts/manual_amendment_spec.py``.

Environment
-----------
``DB_CONNECTION_STRING`` or ``api/local.settings.json`` → ``Values.DB_CONNECTION_STRING``.

Usage
-----
  python scripts/reingest_rpc_manual_pipeline.py
  python scripts/reingest_rpc_manual_pipeline.py --dry-run
  python scripts/reingest_rpc_manual_pipeline.py --only-base
  python scripts/reingest_rpc_manual_pipeline.py --from-step 3
  python scripts/reingest_rpc_manual_pipeline.py --only-id ra_6968
  python scripts/reingest_rpc_manual_pipeline.py --pause
  python scripts/reingest_rpc_manual_pipeline.py --continue-on-errors
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
_MANUAL_ROOT = _REPO / "LexCode" / "Codals" / "manual_amendments"
_DEFAULT_MANIFEST = _MANUAL_ROOT / "manifest.json"
_IMPLIED_OUT = _REPO / "LexCode" / "Codals" / "generated" / "rpc_implied_sources_manifest.json"

# Same direct list as ``reingest_rpc_pipeline.py`` for implied-file discovery only.
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
            "Manual RPC pipeline: these markdown files are not auto-applied. "
            "Use manual_amendments/specs/*.json for codal text you intend to publish."
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


def _load_manifest(manifest_path: Path) -> list[dict[str, str]]:
    if not manifest_path.is_file():
        sys.exit(
            f"Missing manual manifest: {manifest_path}\n"
            "Run: python LexCode/scripts/build_baseline_manual_specs.py"
        )
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    steps = data.get("steps")
    if not isinstance(steps, list) or not steps:
        sys.exit(f"manifest.json has no steps: {manifest_path}")
    out: list[dict[str, str]] = []
    for i, s in enumerate(steps):
        if not isinstance(s, dict):
            sys.exit(f"manifest steps[{i}] must be an object")
        sid = str(s.get("id") or "").strip()
        spec = str(s.get("spec") or "").strip()
        if not sid or not spec:
            sys.exit(f"manifest steps[{i}] requires id and spec")
        out.append({"id": sid, "spec": spec})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description="RPC base + manual JSON amendments (no AI) + implied manifest",
    )
    ap.add_argument("--dry-run", action="store_true", help="Print subprocess commands; no DB writes")
    ap.add_argument("--only-base", action="store_true", help="Run phase 1 only, then implied manifest")
    ap.add_argument("--skip-amendments", action="store_true", help="Skip phase 2 (after base)")
    ap.add_argument(
        "--wipe-rpc-links",
        action="store_true",
        help="Pass through to base ingest (DELETE codal_case_links for RPC).",
    )
    ap.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help=f"Override manifest path (default: {_DEFAULT_MANIFEST})",
    )
    ap.add_argument(
        "--from-step",
        type=int,
        default=1,
        metavar="N",
        help="1-based index into manifest steps to start from (default: 1)",
    )
    ap.add_argument("--only-id", default=None, metavar="ID", help="Run only the step with this manifest id")
    ap.add_argument(
        "--pause",
        action="store_true",
        help="Wait for Enter after each amendment subprocess (review DB between steps).",
    )
    ap.add_argument(
        "--continue-on-errors",
        action="store_true",
        help="Continue after a failed step (default: stop on first failure).",
    )
    args = ap.parse_args()

    manifest_path = args.manifest.resolve() if args.manifest is not None else _DEFAULT_MANIFEST

    if not _BASE.is_file():
        sys.exit(f"Missing {_BASE}")
    if not _PROC.is_file():
        sys.exit(f"Missing {_PROC}")

    base_args: list[str] = []
    if args.wipe_rpc_links:
        base_args.append("--wipe-rpc-links")

    print("=" * 72)
    print("RPC MANUAL RE-INGEST PIPELINE (no AI)")
    print("=" * 72)

    rc = _run_py(_BASE, base_args + (["--dry-run"] if args.dry_run else []), dry_run=args.dry_run)
    if rc != 0:
        sys.exit(rc)

    if args.only_base:
        _write_implied_manifest(args.dry_run)
        print("\n" + "=" * 72)
        print("Manual RPC pipeline finished (--only-base).")
        print("=" * 72)
        return

    failures: list[str] = []
    if not args.skip_amendments:
        steps = _load_manifest(manifest_path)
        start_idx = max(1, int(args.from_step))
        only_id = (args.only_id or "").strip() or None

        matched_only = False
        for i, step in enumerate(steps, start=1):
            if i < start_idx:
                continue
            sid = step["id"]
            if only_id is not None and sid != only_id:
                continue
            if only_id is not None:
                matched_only = True
            spec_rel = step["spec"]
            spec_path = (_MANUAL_ROOT / spec_rel).resolve()
            if not spec_path.is_file():
                msg = f"Missing spec file: {spec_path}"
                print(f"\n[ERROR] {msg}")
                failures.append(f"{sid} ({spec_rel})")
                if not args.continue_on_errors:
                    sys.exit(1)
                continue

            print(f"\n--- Manual step {i}/{len(steps)}: id={sid} ---")
            extra = ["--amendment-json", str(spec_path), "--code", "RPC"]
            rc = _run_py(_PROC, extra + (["--dry-run"] if args.dry_run else []), dry_run=args.dry_run)
            if rc != 0:
                failures.append(sid)
                if not args.continue_on_errors:
                    print(f"\n[ERROR] Step failed: {sid} (exit {rc})")
                    sys.exit(rc)
                print(f"\n[WARN] Step failed ({sid}); continuing (--continue-on-errors).")

            if args.pause and not args.dry_run:
                input(f"[pause] Press Enter to continue after step {sid!r}... ")

        if only_id is not None and not matched_only:
            sys.exit(f"No manifest step matched --only-id {only_id!r}")

    _write_implied_manifest(args.dry_run)
    print("\n" + "=" * 72)
    print("Manual RPC pipeline finished.")
    if failures:
        print(f"Failures ({len(failures)}): {', '.join(failures)}")
    print("=" * 72)
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
