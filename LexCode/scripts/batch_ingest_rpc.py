"""
batch_ingest_rpc.py
-------------------
Sequentially ingest all 24 direct RPC amendatory laws using the
full-AI pipeline (process_amendment_full_ai.py).

Primary model  : gemini-2.5-pro
Fallback model : gemini-2.5-flash-lite

Usage:
    python LexCode/scripts/batch_ingest_rpc.py [--dry-run] [--start-from N]

Options:
    --dry-run      Run AI extraction and validation without writing to DB.
    --start-from N Skip the first N laws (useful for resuming interrupted runs).
    --only NAME    Process only files matching this substring (e.g. ra_10951).
"""

import sys
import os
import argparse
import time
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT   = SCRIPT_DIR.parents[1]
MD_DIR      = REPO_ROOT / "LexCode" / "Codals" / "md"

sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(REPO_ROOT / "api"))

# ── The 24 direct textual RPC amendatory laws in chronological order ─────────
RPC_AMENDATORY_FILES = [
    "Act No. 3999, December 05, 1932.md",
    "act_4117_1933.md",
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
    "ra_10951_2017.md",
    "ra_11362_2019.md",
    "ra_11594_2021.md",
    "ra_11648_2022.md",
    "ra_11926_2022.md",
]


def main():
    parser = argparse.ArgumentParser(description="Batch ingest RPC amendatory laws")
    parser.add_argument("--dry-run", action="store_true",
                        help="Extract and validate without writing to DB")
    parser.add_argument("--start-from", type=int, default=0, metavar="N",
                        help="Skip the first N files (0-indexed)")
    parser.add_argument("--only", type=str, default=None, metavar="SUBSTR",
                        help="Only process files whose name contains SUBSTR")
    args = parser.parse_args()

    from process_amendment_full_ai import process_amendment_full_ai

    files_to_process = RPC_AMENDATORY_FILES[args.start_from:]
    if args.only:
        files_to_process = [f for f in files_to_process if args.only.lower() in f.lower()]

    total = len(files_to_process)
    passed, failed, skipped = [], [], []

    print("=" * 70)
    print(f"  BATCH RPC AMENDMENT INGESTION")
    print(f"  Mode    : {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"  Model   : gemini-2.5-pro  (fallback: gemini-2.5-flash-lite)")
    print(f"  Files   : {total}")
    print("=" * 70)

    for idx, filename in enumerate(files_to_process, start=1):
        file_path = MD_DIR / filename
        print(f"\n[{idx}/{total}] {filename}")

        if not file_path.exists():
            print(f"  ⚠  File not found: {file_path}  — SKIPPING")
            skipped.append(filename)
            continue

        try:
            result = process_amendment_full_ai(
                str(file_path),
                code_short_name="RPC",
                dry_run=args.dry_run,
            )
            passed.append(filename)
        except Exception as e:
            import traceback
            print(f"  [FAIL]  EXCEPTION: {e}")
            traceback.print_exc()
            failed.append(filename)

        # Polite delay between API calls to avoid rate limits
        if idx < total:
            time.sleep(2)

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print(f"  BATCH INGESTION COMPLETE")
    print(f"  Passed  : {len(passed)}")
    print(f"  Failed  : {len(failed)}")
    print(f"  Skipped : {len(skipped)}")
    if failed:
        print("\n  Failed files:")
        for f in failed:
            print(f"    - {f}")
    if skipped:
        print("\n  Skipped files (not found):")
        for f in skipped:
            print(f"    - {f}")
    print("=" * 70)


if __name__ == "__main__":
    main()
