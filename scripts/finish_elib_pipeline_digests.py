#!/usr/bin/env python3
"""
Finish Gemini digests for rows ingested by ``elib_digest_pipeline.py`` that never completed
(stale ``PROCESSING``, empty/partial digest fields). Does **not** handle ``BLOCKED_SAFETY``
(use Grok / ``--retry-blocked`` separately).

Inputs: ``DB_CONNECTION_STRING``, ``GOOGLE_API_KEY`` (via env or ``api/local.settings.json``).

Steps:
  1. Clear stale ``digest_significance = 'PROCESSING'`` (pipeline rows by default; all rows with
     ``full_text_md`` if ``--all-sources``).
  2. Select ``sc_decided_cases.id`` with incomplete digest: same holes as Gemini ``--smart-backfill``
     (facts/issues/ruling/ratio/significance, plus keywords, legal_concepts, flashcards, spoken_script,
     cited_cases, statutes_involved when NULL/empty). Excludes ``BLOCKED_SAFETY``.
  3. Run ``generate_sc_digests_gemini.py`` per chunk: ``--force --smart-backfill`` + ``--target-ids``.

Usage:
  python scripts/finish_elib_pipeline_digests.py
  python scripts/finish_elib_pipeline_digests.py --dry-run
  python scripts/finish_elib_pipeline_digests.py --dry-run --export-ids admin-tools/case-digest-pipeline/incomplete_ids.txt
  python scripts/finish_elib_pipeline_digests.py --all-sources --dry-run
  python scripts/finish_elib_pipeline_digests.py --chunk-size 40 --model gemini-2.5-flash
  python scripts/finish_elib_pipeline_digests.py --all-sources --max-passes 3
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from load_local_settings_env import load_api_local_settings_into_environ

import psycopg2

SOURCE = "E-Library digest pipeline"

log = logging.getLogger(__name__)


def _incomplete_digest_sql_fragment() -> str:
    """
    Same field-level holes as ``generate_sc_digests_gemini.py`` when ``--smart-backfill``
    is used (core digest + extended JSON/text columns). Keeps PROCESSING out of the
    predicate here because callers clear stale PROCESSING first.
    """
    return """
          (
               digest_facts IS NULL OR btrim(digest_facts::text) = ''
            OR digest_issues IS NULL OR btrim(digest_issues::text) = ''
            OR digest_ruling IS NULL OR btrim(digest_ruling::text) = ''
            OR digest_significance IS NULL OR btrim(digest_significance) = ''
            OR digest_significance = 'Unknown'
            OR digest_ratio IS NULL OR btrim(digest_ratio::text) = ''
            OR keywords IS NULL
            OR legal_concepts IS NULL
            OR flashcards IS NULL
            OR spoken_script IS NULL OR btrim(spoken_script::text) = ''
            OR cited_cases IS NULL
            OR statutes_involved IS NULL
          )
    """


def _pending_row_ids(conn, all_sources: bool = False) -> list[int]:
    cur = conn.cursor()
    source_clause = "" if all_sources else "AND scrape_source = %s"
    params: tuple = ()
    if not all_sources:
        params = (SOURCE,)
    cur.execute(
        f"""
        SELECT id
        FROM sc_decided_cases
        WHERE full_text_md IS NOT NULL
          AND btrim(full_text_md) <> ''
          AND coalesce(digest_significance, '') <> 'BLOCKED_SAFETY'
          {source_clause}
          AND (
                digest_significance = 'PROCESSING'
             OR ({_incomplete_digest_sql_fragment().strip()})
          )
        ORDER BY id
        """,
        params,
    )
    return [int(r[0]) for r in cur.fetchall()]


def _clear_stale_processing(conn, all_sources: bool = False) -> int:
    cur = conn.cursor()
    if all_sources:
        cur.execute(
            """
            UPDATE sc_decided_cases
            SET digest_significance = NULL
            WHERE full_text_md IS NOT NULL
              AND btrim(full_text_md) <> ''
              AND digest_significance = 'PROCESSING'
            """
        )
    else:
        cur.execute(
            """
            UPDATE sc_decided_cases
            SET digest_significance = NULL
            WHERE scrape_source = %s
              AND digest_significance = 'PROCESSING'
            """,
            (SOURCE,),
        )
    n = cur.rowcount
    conn.commit()
    return int(n)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true", help="Print counts and first ids; no DB writes or digest")
    p.add_argument(
        "--all-sources",
        action="store_true",
        help="Include every sc_decided_cases row with full_text_md (not only E-Library digest pipeline).",
    )
    p.add_argument(
        "--export-ids",
        type=str,
        metavar="PATH",
        help="Write one database id per line (after optional stale-PROCESSING clear unless --dry-run).",
    )
    p.add_argument("--chunk-size", type=int, default=40, help="Target ids per Gemini subprocess (CLI length safe)")
    p.add_argument("--model", type=str, default="gemini-2.5-flash", help="Gemini model id")
    p.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Parallel workers passed to generate_sc_digests_gemini.py (capped per chunk)",
    )
    p.add_argument(
        "--max-passes",
        type=int,
        default=3,
        metavar="N",
        help="Re-query pending rows and run digest chunks up to N times (default 3). Use 1 for a single sweep.",
    )
    args = p.parse_args()

    load_api_local_settings_into_environ(_REPO_ROOT)
    db_url = os.environ.get("DB_CONNECTION_STRING")
    if not db_url:
        log.error("DB_CONNECTION_STRING is not set.")
        return 2
    if not args.dry_run and not os.environ.get("GOOGLE_API_KEY"):
        log.error("GOOGLE_API_KEY is not set; cannot run Gemini.")
        return 3

    max_passes = max(1, int(args.max_passes))
    conn = psycopg2.connect(db_url)
    try:
        all_src = bool(args.all_sources)
        scope = "all sources (full_text_md)" if all_src else SOURCE
        script = _REPO_ROOT / "scripts" / "generate_sc_digests_gemini.py"
        chunk_size = max(1, int(args.chunk_size))
        workers = max(1, int(args.workers))

        for pass_idx in range(max_passes):
            cleared = 0 if args.dry_run else _clear_stale_processing(conn, all_sources=all_src)
            if not args.dry_run:
                log.info(
                    "Pass %s/%s: cleared PROCESSING on %s row(s) (%s).",
                    pass_idx + 1,
                    max_passes,
                    cleared,
                    "all sources with full_text_md" if all_src else f"scrape_source={SOURCE!r}",
                )

            ids = _pending_row_ids(conn, all_sources=all_src)
            log.info(
                "Pending incomplete digest row(s) [%s] pass %s/%s: %s",
                scope,
                pass_idx + 1,
                max_passes,
                len(ids),
            )
            if pass_idx == 0 and args.export_ids:
                export_path = Path(args.export_ids)
                export_path.parent.mkdir(parents=True, exist_ok=True)
                export_path.write_text("\n".join(str(i) for i in ids) + ("\n" if ids else ""), encoding="utf-8")
                log.info("Wrote %s id(s) to %s", len(ids), export_path)
            if args.dry_run:
                log.info("Dry-run: first ids (up to 20): %s", ids[:20])
                return 0
            if not ids:
                log.info("Nothing to digest.")
                return 0

            for i in range(0, len(ids), chunk_size):
                chunk = ids[i : i + chunk_size]
                joined = ",".join(str(x) for x in chunk)
                w = min(workers, len(chunk))
                cmd = [
                    sys.executable,
                    str(script),
                    "--force",
                    "--smart-backfill",
                    "--target-ids",
                    joined,
                    "--model",
                    args.model,
                    "--limit",
                    str(len(chunk)),
                    "--workers",
                    str(w),
                ]
                log.info(
                    "Pass %s/%s chunk %s..%s (%s ids): workers=%s",
                    pass_idx + 1,
                    max_passes,
                    chunk[0],
                    chunk[-1],
                    len(chunk),
                    w,
                )
                subprocess.run(cmd, check=True, cwd=str(_REPO_ROOT))

            log.info(
                "Finished pass %s/%s (%s chunk(s) this pass).",
                pass_idx + 1,
                max_passes,
                (len(ids) + chunk_size - 1) // chunk_size,
            )

        remaining = _pending_row_ids(conn, all_sources=all_src)
        if remaining:
            log.warning(
                "After %s pass(es), still %s pending id(s). Re-run or increase --max-passes. First ids: %s",
                max_passes,
                len(remaining),
                remaining[:20],
            )
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
