"""
ai_amendment_pipeline.py
------------------------
Sequentially ingest the configured list of direct RPC amendatory markdown files
using the full-AI path in ``process_amendment_full_ai.py`` (Gemini extraction +
``apply_amendment_with_ai`` merge into the database).

Models are chosen in ``lexcode_genai_client.py`` (primary: ``get_amendment_primary_model()``,
chunked parse: ``get_amendment_chunk_model()`` — default gemini-2.5-pro / gemini-2.5-flash).

Usage (repo root — one shot: reset RPC from RPC.md, then all-AI amendments up through RA 10655):
    # Easiest: live output in the terminal (optional log file):
    .\\run_ai_reingest_before_10951_live.ps1

    python LexCode/scripts/ai_amendment_pipeline.py --reset-and-ai-before-10951

    # Progress in the terminal *and* a log file (PowerShell) — do not use *>> only, or the console stays empty:
    $env:PYTHONUNBUFFERED="1"
    python LexCode/scripts/ai_amendment_pipeline.py --reset-and-ai-before-10951 2>&1 | Tee-Object -FilePath ai_reingest_before_10951.log

    # Or manually:
    python LexCode/scripts/ingest_rpc_base_from_md.py --wipe-rpc-links
    python LexCode/scripts/ai_amendment_pipeline.py --stop-before ra_10951_2017
    # Options:
    python LexCode/scripts/ai_amendment_pipeline.py [--ingest-base] [--wipe-rpc-links] [--dry-run] [--start-from N] [--stop-before SUBSTR] [--only SUBSTR] [--no-source-guard]

Options:
    --reset-and-ai-before-10951  Run baseline ingest + wipe links + AI batch through ra_10655_2015.
    --ingest-base / --wipe-rpc-links  Baseline reset from RPC.md before the AI amendment loop.
    --dry-run      Run AI extraction and validation without writing to DB.
    --start-from N Skip the first N files in ``RPC_AMENDATORY_FILES`` (0-indexed; resume).
    --stop-before SUBSTR  Only run laws *before* the first list item matching this
                   (e.g. ``ra_10951_2017`` runs through ``ra_10655_2015`` and stops).
    --only SUBSTR  Only process files whose name contains this substring (e.g. ra_10951).
    --no-source-guard  Skip markdown anchor/snippet validation (default: guards ON).
"""

import sys
import os
import argparse
import subprocess
import time
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT   = SCRIPT_DIR.parents[1]
MD_DIR      = REPO_ROOT / "LexCode" / "Codals" / "md"

sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(REPO_ROOT / "api"))

# ── Direct textual RPC amendatory sources (chronological; same spirit as
#     scripts/reingest_rpc_pipeline.py, plus P.D./B.P./E.O. files used in full-AI path)
RPC_AMENDATORY_FILES = [
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
    "pd_942_1976.md",
    "pd_1179_1977.md",
    "bp_871_1985.md",
    "eo_272_1987.md",
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


def _files_before_token(file_list: list[str], token: str | None) -> list[str]:
    """
    Return file_list[:i] where i is the index of the first entry whose name
    contains the stop token (case-insensitive). Excludes that file and all after it.
    """
    if not token or not str(token).strip():
        return file_list
    t = str(token).strip().lower()
    for i, name in enumerate(file_list):
        if t in name.lower():
            return file_list[:i]
    print(
        f"ERROR: --stop-before {token!r} did not match any of {len(file_list)} configured files.",
        file=sys.stderr,
    )
    sys.exit(1)


def _run_rpc_base_ingest(*, dry_run: bool, wipe_links: bool) -> int:
    """Run ``ingest_rpc_base_from_md`` (clean ``rpc_codal`` + ``article_versions`` from RPC.md)."""
    base_script = REPO_ROOT / "LexCode" / "scripts" / "ingest_rpc_base_from_md.py"
    cmd = [sys.executable, "-u", str(base_script)]
    if wipe_links:
        cmd.append("--wipe-rpc-links")
    if dry_run:
        cmd.append("--dry-run")
    print("\n" + "=" * 70, flush=True)
    print("  PHASE 0: RPC baseline from RPC.md (ingest_rpc_base_from_md)", flush=True)
    print("=" * 70, flush=True)
    print(">> " + " ".join(cmd), flush=True)
    _env = os.environ.copy()
    _env["PYTHONUNBUFFERED"] = "1"
    return int(subprocess.call(cmd, cwd=str(REPO_ROOT), env=_env))


def main():
    parser = argparse.ArgumentParser(
        description="Batch full-AI ingest of RPC amendatory markdown (ai_amendment_pipeline)"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Extract and validate without writing to DB")
    parser.add_argument("--start-from", type=int, default=0, metavar="N",
                        help="Skip the first N files (0-indexed)")
    parser.add_argument(
        "--stop-before",
        type=str,
        default=None,
        metavar="FILE_OR_SUBSTR",
        help="Only run items before the first list filename matching this (e.g. ra_10951_2017 to end at ra_10655_2015)",
    )
    parser.add_argument("--only", type=str, default=None, metavar="SUBSTR",
                        help="Only process files whose name contains SUBSTR")
    parser.add_argument(
        "--no-source-guard",
        action="store_true",
        help="Disable markdown anchor/snippet checks (not recommended for clean re-ingest)",
    )
    parser.add_argument(
        "--ingest-base",
        action="store_true",
        help="Run LexCode/scripts/ingest_rpc_base_from_md.py first (reset RPC from RPC.md).",
    )
    parser.add_argument(
        "--wipe-rpc-links",
        action="store_true",
        help="With --ingest-base: delete codal_case_links for RPC before baseline insert.",
    )
    parser.add_argument(
        "--reset-and-ai-before-10951",
        action="store_true",
        help=(
            "Convenience: --ingest-base --wipe-rpc-links and --stop-before ra_10951_2017 "
            "(full-AI through ra_10655_2015, excludes RA 10951 onward)."
        ),
    )
    args = parser.parse_args()

    if args.reset_and_ai_before_10951:
        args.ingest_base = True
        args.wipe_rpc_links = True
        if not args.stop_before:
            args.stop_before = "ra_10951_2017"

    if args.ingest_base:
        rc = _run_rpc_base_ingest(dry_run=args.dry_run, wipe_links=args.wipe_rpc_links)
        if rc != 0:
            print(f"\n[FATAL] Baseline ingest failed (exit {rc}).", file=sys.stderr)
            raise SystemExit(rc)

    from process_amendment_full_ai import process_amendment_full_ai
    from lexcode_genai_client import get_amendment_primary_model, get_amendment_chunk_model

    files_to_process = _files_before_token(
        RPC_AMENDATORY_FILES[args.start_from :],
        args.stop_before,
    )
    if args.only:
        files_to_process = [f for f in files_to_process if args.only.lower() in f.lower()]

    total = len(files_to_process)
    passed, failed, skipped = [], [], []

    print("=" * 70, flush=True)
    print(f"  BATCH RPC AMENDMENT INGESTION", flush=True)
    print(f"  Mode    : {'DRY RUN' if args.dry_run else 'LIVE'}", flush=True)
    print(
        f"  Models  : primary={get_amendment_primary_model()}, "
        f"chunk={get_amendment_chunk_model()} (lexcode_genai_client.py)",
        flush=True,
    )
    print(f"  Files   : {total}", flush=True)
    print("=" * 70, flush=True)

    for idx, filename in enumerate(files_to_process, start=1):
        file_path = MD_DIR / filename
        print(f"\n[{idx}/{total}] {filename}", flush=True)

        if not file_path.exists():
            print(f"  ⚠  File not found: {file_path}  — SKIPPING")
            skipped.append(filename)
            continue

        try:
            ok = process_amendment_full_ai(
                str(file_path),
                code_short_name="RPC",
                dry_run=args.dry_run,
                skip_source_guard=args.no_source_guard,
            )
            if ok:
                passed.append(filename)
            else:
                failed.append(filename)
        except Exception as e:
            import traceback
            print(f"  [FAIL]  EXCEPTION: {e}")
            traceback.print_exc()
            failed.append(filename)

        # Polite delay between API calls to avoid rate limits
        if idx < total:
            time.sleep(2)

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 70, flush=True)
    print(f"  BATCH INGESTION COMPLETE", flush=True)
    print(f"  Passed  : {len(passed)}", flush=True)
    print(f"  Failed  : {len(failed)}", flush=True)
    print(f"  Skipped : {len(skipped)}", flush=True)
    if failed:
        print("\n  Failed files:", flush=True)
        for f in failed:
            print(f"    - {f}", flush=True)
    if skipped:
        print("\n  Skipped files (not found):", flush=True)
        for f in skipped:
            print(f"    - {f}", flush=True)
    print("=" * 70, flush=True)

    # Rebuild maps whenever at least one file succeeded (DB may have new amendments even if other files failed).
    if not args.dry_run and passed:
        # ── Post-processing: rebuild ALL structural maps from final amendments[] ──
        # Maps must be generated AFTER all laws are applied so each article's
        # amendments[] array is in its final state. Generating mid-pipeline produces
        # wrong source IDs when earlier phantom amendments corrupt the index.
        print("\n" + "=" * 70, flush=True)
        print("  POST-PROCESSING: Rebuilding structural maps for all amended RPC articles", flush=True)
        print("=" * 70, flush=True)
        try:
            from structural_mapper import generate_and_save_map
            sys.path.insert(0, str(REPO_ROOT / "api"))
            from db_pool import get_db_connection
            _conn = get_db_connection()
            _cur = _conn.cursor()
            # Only rebuild articles that actually have amendments
            _cur.execute("""
                SELECT article_num FROM rpc_codal
                WHERE amendments IS NOT NULL AND amendments != '[]'::jsonb
                ORDER BY article_num::text
            """)
            amended_arts = [r[0] for r in _cur.fetchall()]
            _cur.close()
            _conn.close()
            print(f"  Rebuilding maps for {len(amended_arts)} amended articles...", flush=True)
            for art_num in amended_arts:
                try:
                    generate_and_save_map(art_num)
                    print(f"    [MAP] Art {art_num} rebuilt", flush=True)
                except Exception as map_err:
                    print(f"    [WARN] Art {art_num} map failed: {map_err}", flush=True)
            print("  Structural map rebuild complete.", flush=True)
        except Exception as e:
            print(f"  [WARN] Post-processing map rebuild failed: {e}", flush=True)
        print("=" * 70, flush=True)

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
