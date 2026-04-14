#!/usr/bin/env python3
"""
Unified E-Library case digest pipeline (single flow, no partial modes).

For each new Supreme Court E-Library `showdocs/1/{id}` document not yet in the DB:
  fetch HTML, convert to Markdown. Only **G.R.** dockets (case line starts with ``G.R.``)
  are written and INSERTed; A.M., A.C., etc. are skipped with outcome ``SKIP_NOT_GR``.

  For each accepted case: write HTML/MD to disk, INSERT into `sc_decided_cases`, then run
  Gemini digest on those new row IDs.

Markdown files are named from the decision header when possible:
  `{case number} - {YYYY-MM-DD}.md`
Fallback: `E-Library-{id}.md`

If a document URL already exists in the database, it is skipped (no duplicate insert).
Use `--force-reingest` with `--ids` to delete those rows first and run fetch → MD → insert → digest again.

Credentials (see `api/local.settings.sample.json`):
  • `DB_CONNECTION_STRING` — required
  • `GOOGLE_API_KEY` — required whenever at least one new row is ingested
  • `XAI_API_KEY` — optional; when Gemini marks a row `BLOCKED_SAFETY`, the pipeline runs
    `generate_sc_digests_grok.py` for those ids only (see `DIGEST_SAFETY_FALLBACK_MODEL`).

Optional tuning only: `--max-probe`, `--stop-after-consecutive-misses`, `--request-delay`,
`--html-dir`, `--md-dir`, `--digest-model`, `--start-after`, `--ids`, `--force-reingest`,
`--workers` (default 5: parallel Gemini/Grok digest subprocesses per case id)
`--no-progress` (disable live stderr progress; default is on when stderr is a TTY)

Install ``tqdm`` for a fuller progress bar (``pip install tqdm``); otherwise a simple live line is used.

Examples:
  python scripts/elib_digest_pipeline.py
  python scripts/elib_digest_pipeline.py --ids 70193,70194
  python scripts/elib_digest_pipeline.py --ids 70193 --force-reingest
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import subprocess
import sys
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, cast

import requests

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from load_local_settings_env import load_api_local_settings_into_environ

import psycopg2

from scraper.elib_html_to_markdown import elib_html_to_markdown, is_elib_error_page

ELIB_SHOWDOCS = "https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/"

log = logging.getLogger(__name__)


class _LiveBarProto(Protocol):
    def set_postfix_str(self, s: str) -> None: ...
    def update(self, n: int = 1) -> None: ...
    def close(self) -> None: ...


def _try_tqdm():
    try:
        from tqdm.auto import tqdm

        return tqdm
    except ImportError:
        return None


class _FallbackLiveBar:
    """Minimal stderr progress line when ``tqdm`` is not installed."""

    def __init__(self, desc: str, total: int | None) -> None:
        self._desc = desc[:28]
        self._total = total
        self._n = 0
        self._postfix = ""

    def set_postfix_str(self, s: str) -> None:
        self._postfix = (s or "")[:72]

    def update(self, n: int = 1) -> None:
        self._n += max(0, n)
        if not sys.stderr.isatty():
            return
        tot = self._total
        if tot:
            pct = min(100, int(100 * self._n / max(tot, 1)))
            core = f"{self._desc} {self._n}/{tot} ({pct}%)"
        else:
            core = f"{self._desc} n={self._n}"
        tail = f" | {self._postfix}" if self._postfix else ""
        line = (core + tail)[:119].ljust(119)
        print(f"\r{line}", end="", file=sys.stderr, flush=True)

    def close(self) -> None:
        if sys.stderr.isatty():
            print(file=sys.stderr, flush=True)

    def __enter__(self) -> _FallbackLiveBar:
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _tb: Any,
    ) -> None:
        self.close()


@contextmanager
def _live_progress_bar(desc: str, total: int | None, enabled: bool) -> Iterator[_LiveBarProto | None]:
    if not enabled:
        yield None
        return
    tqdm_cls = _try_tqdm()
    if tqdm_cls is not None:
        bar = tqdm_cls(
            total=total,
            desc=desc,
            unit="id" if "ingest" in desc.lower() else "case",
            dynamic_ncols=True,
            file=sys.stderr,
            leave=True,
        )
        try:
            yield cast(_LiveBarProto, bar)
        finally:
            bar.close()
    else:
        fb = _FallbackLiveBar(desc, total)
        try:
            yield fb
        finally:
            fb.close()


def _each_doc_id_with_ingest_pbar(doc_ids: list[int], bar: _LiveBarProto | None) -> Iterator[int]:
    """Yield each E-Lib id and advance the ingest progress bar once per iteration (including ``continue``)."""
    for doc_id in doc_ids:
        try:
            if bar:
                bar.set_postfix_str(f"elib id={doc_id}")
            yield doc_id
        finally:
            if bar:
                bar.update(1)


# First case line in converted MD, e.g. ## [ G.R. No. 277280, September 30, 2025 ]
_MD_CASE_HEADER = re.compile(
    r"##\s*\[\s*(.+?)\s*,\s*([A-Z][a-z]+\s+\d{1,2},?\s*\d{4})\s*\]",
    re.DOTALL,
)


def _markdown_lead_is_gr_case(md_text: str) -> bool:
    """True only if the decision's bracketed case line starts with G.R. (not A.M., A.C., etc.)."""
    head = md_text[:50000]
    m = _MD_CASE_HEADER.search(head)
    if m:
        lead = re.sub(r"\s+", " ", m.group(1).strip())
        return lead.upper().startswith("G.R.")
    # Fallback: explicit G.R. opener without matching the full date pattern
    return bool(re.search(r"##\s*\[\s*G\.R\.", head, re.IGNORECASE))


def _parse_decision_date(date_raw: str) -> str | None:
    s = re.sub(r",\s*", " ", date_raw.strip())
    s = re.sub(r"\s+", " ", s).strip()
    try:
        return datetime.strptime(s, "%B %d %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def _sanitize_windows_filename(stem: str, max_len: int = 180) -> str:
    stem = re.sub(r'[\n\r\t\x00-\x1f]', " ", stem)
    for ch in '<>:"/\\|?*':
        stem = stem.replace(ch, "-")
    stem = re.sub(r"\s+", " ", stem).strip().rstrip(". ")
    if not stem:
        stem = "case"
    return stem[:max_len]


def _markdown_save_path(md_dir: Path, md_text: str, elib_doc_id: int) -> Path:
    m = _MD_CASE_HEADER.search(md_text[:20000])
    if m:
        raw_case = re.sub(r"\s+", " ", m.group(1).strip())[:200]
        date_raw = m.group(2).strip()
        date_iso = _parse_decision_date(date_raw) or _sanitize_windows_filename(date_raw, 40)
        stem = _sanitize_windows_filename(f"{raw_case} - {date_iso}")
    else:
        stem = _sanitize_windows_filename(f"E-Library-{elib_doc_id}")

    base = md_dir / f"{stem}.md"
    if not base.exists():
        return base
    alt_stem = _sanitize_windows_filename(f"{stem} (elib {elib_doc_id})")
    alt = md_dir / f"{alt_stem}.md"
    if not alt.exists():
        return alt
    n = 2
    while True:
        p = md_dir / f"{_sanitize_windows_filename(f'{stem} (elib {elib_doc_id}) {n}')}.md"
        if not p.exists():
            return p
        n += 1


@dataclass
class PipelineReport:
    started_at: datetime = field(default_factory=datetime.now)
    scan_mode: bool = False
    max_elib_before: int | None = None
    html_dir: Path | None = None
    md_dir: Path | None = None
    digest_model: str = ""
    rows: list[dict] = field(default_factory=list)
    digest_row_ids: list[int] = field(default_factory=list)
    digest_ok: bool | None = None
    digest_error: str | None = None
    fatal_error: str | None = None

    def add(
        self,
        *,
        elib_id: int,
        outcome: str,
        detail: str = "",
        sc_url: str = "",
        md_file: str = "",
        html_file: str = "",
        db_row_id: int | None = None,
        case_label: str = "",
    ) -> None:
        self.rows.append(
            {
                "elib_id": elib_id,
                "outcome": outcome,
                "detail": detail,
                "sc_url": sc_url,
                "md_file": md_file,
                "html_file": html_file,
                "db_row_id": db_row_id,
                "case_label": case_label,
            }
        )

    def emit(self) -> None:
        lines: list[str] = []
        lines.append("")
        lines.append("=" * 64)
        lines.append("E-LIBRARY CASE DIGEST PIPELINE - RUN REPORT")
        lines.append("=" * 64)
        lines.append(f"Finished (local time): {datetime.now().isoformat(timespec='seconds')}")
        lines.append(f"Started (local time):  {self.started_at.isoformat(timespec='seconds')}")
        if self.scan_mode and self.max_elib_before is not None:
            lines.append(f"Scan mode: yes | Max E-Lib id in DB before run: {self.max_elib_before}")
        else:
            lines.append("Scan mode: no (--ids)")
        if self.html_dir is not None:
            lines.append(f"HTML directory: {self.html_dir}")
        if self.md_dir is not None:
            lines.append(f"MD directory:   {self.md_dir}")
        lines.append("")

        ingested = 0
        for r in self.rows:
            oid = r["elib_id"]
            oc = r["outcome"]
            extra = []
            if r.get("case_label"):
                extra.append(f"case={r['case_label'][:80]}")
            if r.get("db_row_id"):
                extra.append(f"db_id={r['db_row_id']}")
            if r.get("md_file"):
                extra.append(f"md={r['md_file']}")
            if r.get("html_file"):
                extra.append(f"html={r['html_file']}")
            if r.get("detail"):
                extra.append(r["detail"])
            tail = (" | " + " ".join(extra)) if extra else ""
            lines.append(f"  [{oid}] {oc}{tail}")
            if oc == "INGESTED":
                ingested += 1

        lines.append("")
        lines.append(f"Summary: {ingested} new row(s) inserted.")
        if self.digest_row_ids:
            lines.append(
                f"Digest: model={self.digest_model!r} | row id(s)={self.digest_row_ids}"
            )
            if self.digest_ok is True:
                lines.append("Digest subprocess: completed OK.")
            elif self.digest_ok is False and self.digest_error:
                lines.append(f"Digest subprocess: FAILED - {self.digest_error}")
            else:
                lines.append("Digest subprocess: not run.")
        else:
            lines.append("Digest: not run (no new rows).")
        if self.fatal_error:
            lines.append(f"Fatal: {self.fatal_error}")
        lines.append("=" * 64)
        block = "\n".join(lines)
        print(block, flush=True)
        log.info("Run report:\n%s", block)


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://elibrary.judiciary.gov.ph/",
        }
    )
    return s


def get_max_elib_showdocs_id(conn) -> int:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COALESCE(
            MAX(
                CAST(
                    SUBSTRING(sc_url FROM '/showdocs/1/([0-9]+)') AS INTEGER
                )
            ),
            0
        )
        FROM sc_decided_cases
        WHERE sc_url ILIKE %s
          AND sc_url ~ %s
        """,
        ("%elibrary.judiciary.gov.ph%thebookshelf/showdocs/1/%", r"/showdocs/1/[0-9]+"),
    )
    row = cur.fetchone()
    return int(row[0] or 0)


def sc_url_for_elib_id(doc_id: int) -> str:
    return f"{ELIB_SHOWDOCS}{doc_id}"


def row_exists_for_url(conn, sc_url: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM sc_decided_cases WHERE sc_url = %s LIMIT 1", (sc_url,))
    return cur.fetchone() is not None


def delete_sc_cases_for_elib_ids(conn, doc_ids: list[int]) -> list[int]:
    """Delete rows for the given E-Lib showdocs IDs (by exact sc_url) so they can be re-inserted."""
    deleted: list[int] = []
    cur = conn.cursor()
    for doc_id in doc_ids:
        sc_url = sc_url_for_elib_id(doc_id)
        cur.execute(
            "DELETE FROM sc_decided_cases WHERE sc_url = %s RETURNING id",
            (sc_url,),
        )
        for row in cur.fetchall():
            deleted.append(int(row[0]))
    conn.commit()
    return deleted


def insert_decision(conn, sc_url: str, full_text_md: str) -> int:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO sc_decided_cases (full_text_md, scrape_source, sc_url, created_at, updated_at)
        VALUES (%s, %s, %s, NOW(), NOW())
        RETURNING id
        """,
        (full_text_md, "E-Library digest pipeline", sc_url),
    )
    row = cur.fetchone()
    conn.commit()
    return int(row[0])


def fetch_showdocs_html(session: requests.Session, doc_id: int) -> tuple[str | None, str]:
    url = sc_url_for_elib_id(doc_id)
    try:
        r = session.get(url, timeout=45)
    except requests.RequestException as e:
        log.warning("Request failed for %s: %s", url, e)
        return None, "http_error"

    if r.status_code != 200:
        return None, "http_error"

    text = r.text
    if is_elib_error_page(text):
        return None, "error_page"

    if not re.search(
        r"D\s*E\s*C\s*I\s*S\s*I\s*O\s*N|R\s*E\s*S\s*O\s*L\s*U\s*T\s*I\s*O\s*N",
        text,
        re.I,
    ):
        return None, "invalid_content"

    return text, "ok"


def run_digest_subprocess(
    new_case_ids: list[int],
    *,
    model: str,
    workers: int = 5,
    live_bar: _LiveBarProto | None = None,
) -> None:
    if not new_case_ids:
        return
    script = _REPO_ROOT / "scripts" / "generate_sc_digests_gemini.py"
    workers = max(1, min(int(workers), len(new_case_ids)))

    def _run_one(case_id: int) -> None:
        cmd = [
            sys.executable,
            str(script),
            "--target-ids",
            str(case_id),
            "--model",
            model,
            "--limit",
            "1",
            "--workers",
            "1",
        ]
        log.info("Running digest subprocess: %s", " ".join(cmd))
        if live_bar:
            live_bar.set_postfix_str(f"Gemini db row {case_id}")
        proc = subprocess.run(cmd, cwd=str(_REPO_ROOT))
        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, cmd)
        if live_bar:
            live_bar.update(1)

    if workers == 1:
        joined = ",".join(str(i) for i in new_case_ids)
        cmd = [
            sys.executable,
            str(script),
            "--target-ids",
            joined,
            "--model",
            model,
            "--limit",
            str(len(new_case_ids)),
            "--workers",
            "1",
        ]
        log.info("Running digest subprocess: %s", " ".join(cmd))
        if live_bar:
            live_bar.set_postfix_str(f"Gemini batch n={len(new_case_ids)}")
        proc = subprocess.run(cmd, cwd=str(_REPO_ROOT))
        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, cmd)
        if live_bar:
            live_bar.update(len(new_case_ids))
        return

    log.info("Running digest with %s parallel workers for %s case(s).", workers, len(new_case_ids))
    errors: list[BaseException] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_run_one, cid) for cid in new_case_ids]
        for fut in as_completed(futures):
            try:
                fut.result()
            except BaseException as e:  # noqa: BLE001
                errors.append(e)
    if errors:
        for extra in errors[1:]:
            if isinstance(extra, subprocess.CalledProcessError):
                log.error(
                    "Additional parallel digest failure (returncode=%s cmd=%s)",
                    extra.returncode,
                    extra.cmd,
                )
            else:
                log.error("Additional parallel digest failure: %s", extra)
        raise errors[0]


def _digest_blocked_safety_row_ids(db_url: str, row_ids: list[int]) -> list[int]:
    """Row ids among ``row_ids`` still marked BLOCKED_SAFETY (Gemini safety / empty response)."""
    if not row_ids:
        return []
    conn = psycopg2.connect(db_url)
    try:
        cur = conn.cursor()
        ph = ",".join(["%s"] * len(row_ids))
        cur.execute(
            f"""
            SELECT id FROM sc_decided_cases
            WHERE id IN ({ph})
              AND digest_significance = 'BLOCKED_SAFETY'
            ORDER BY id
            """,
            tuple(row_ids),
        )
        return [int(r[0]) for r in cur.fetchall()]
    finally:
        conn.close()


def _latest_non_gemini_ai_model(db_url: str) -> str | None:
    """Most recently updated non-Gemini ``ai_model`` (hint for which provider last digested cases)."""
    conn = psycopg2.connect(db_url)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT ai_model FROM sc_decided_cases
            WHERE ai_model IS NOT NULL AND BTRIM(ai_model) <> ''
              AND ai_model NOT ILIKE %s
            ORDER BY updated_at DESC NULLS LAST, id DESC
            LIMIT 1
            """,
            ("%gemini%",),
        )
        row = cur.fetchone()
        return (row[0] or "").strip() if row else None
    finally:
        conn.close()


def _grok_model_for_safety_fallback(db_url: str) -> str:
    """
    Grok model id for safety fallback: env ``DIGEST_SAFETY_FALLBACK_MODEL``,
    else first token of latest DB model if it looks like Grok, else ``grok-beta``
    (matches ``generate_sc_digests_grok.py`` default).
    """
    override = (os.environ.get("DIGEST_SAFETY_FALLBACK_MODEL") or "").strip()
    if override:
        return override
    latest = _latest_non_gemini_ai_model(db_url)
    if latest and "grok" in latest.lower():
        for token in latest.split():
            if "grok" in token.lower():
                return token.strip()
        return latest.strip()
    return (os.environ.get("GROK_DIGEST_MODEL") or "grok-beta").strip()


def run_grok_digest_fallback_subprocess(
    case_ids: list[int],
    *,
    model: str,
    workers: int = 5,
    live_bar: _LiveBarProto | None = None,
) -> int:
    """Full digest via Grok for blocked ids; uses ``--force`` so BLOCKED_SAFETY rows are claimable."""
    if not case_ids:
        return 0
    script = _REPO_ROOT / "scripts" / "generate_sc_digests_grok.py"
    workers = max(1, min(int(workers), len(case_ids)))

    def _run_grok_one(case_id: int) -> int:
        cmd = [
            sys.executable,
            str(script),
            "--force",
            "--target-ids",
            str(case_id),
            "--model",
            model,
            "--limit",
            "1",
            "--workers",
            "1",
        ]
        log.info("Running Grok digest fallback subprocess: %s", " ".join(cmd))
        if live_bar:
            live_bar.set_postfix_str(f"Grok db row {case_id}")
        rc = int(subprocess.run(cmd, cwd=str(_REPO_ROOT)).returncode)
        if live_bar and rc == 0:
            live_bar.update(1)
        return rc

    if workers == 1:
        joined = ",".join(str(i) for i in case_ids)
        cmd = [
            sys.executable,
            str(script),
            "--force",
            "--target-ids",
            joined,
            "--model",
            model,
            "--limit",
            str(len(case_ids)),
            "--workers",
            "1",
        ]
        log.info("Running Grok digest fallback subprocess: %s", " ".join(cmd))
        if live_bar:
            live_bar.set_postfix_str(f"Grok batch n={len(case_ids)}")
        proc = subprocess.run(cmd, cwd=str(_REPO_ROOT))
        if proc.returncode != 0:
            log.warning("Grok digest fallback exited with code %s", proc.returncode)
        if live_bar and proc.returncode == 0:
            live_bar.update(len(case_ids))
        return proc.returncode

    log.info("Running Grok fallback with %s parallel workers for %s case(s).", workers, len(case_ids))
    codes: list[int] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_run_grok_one, cid) for cid in case_ids]
        for fut in as_completed(futures):
            codes.append(int(fut.result()))
    worst = max(codes) if codes else 0
    if worst != 0:
        log.warning("Grok digest fallback had non-zero exit code(s): %s", codes)
    return worst


def _run_grok_safety_fallback_if_needed(
    db_url: str,
    blocked_ids: list[int],
    *,
    workers: int = 5,
    live_bar: _LiveBarProto | None = None,
) -> None:
    """Run Grok digest on ``blocked_ids`` (must be non-empty; caller checks XAI_API_KEY)."""
    fb_model = _grok_model_for_safety_fallback(db_url)
    latest = _latest_non_gemini_ai_model(db_url)
    log.info(
        "Gemini blocked id(s) %s; running Grok fallback with model %r (latest non-Gemini ai_model in DB: %r).",
        blocked_ids,
        fb_model,
        latest,
    )
    run_grok_digest_fallback_subprocess(
        blocked_ids, model=fb_model, workers=workers, live_bar=live_bar
    )


def _case_label_from_md(md_text: str) -> str:
    m = _MD_CASE_HEADER.search(md_text[:20000])
    if not m:
        return ""
    case_part = re.sub(r"\s+", " ", m.group(1).strip())
    date_raw = m.group(2).strip()
    d = _parse_decision_date(date_raw)
    if d:
        return f"{case_part} | {d}"
    return f"{case_part} | {date_raw}"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(
        description="Unified E-Library pipeline: fetch, MD, DB insert, Gemini digest (single flow).",
    )
    parser.add_argument(
        "--html-dir",
        type=Path,
        default=_REPO_ROOT / "admin-tools" / "case-digest-pipeline" / "html",
        help="Directory for downloaded HTML (default: admin-tools/case-digest-pipeline/html)",
    )
    parser.add_argument(
        "--md-dir",
        type=Path,
        default=_REPO_ROOT / "admin-tools" / "case-digest-pipeline" / "md",
        help="Directory for generated Markdown",
    )
    parser.add_argument(
        "--max-probe",
        type=int,
        default=400,
        help="Max successive numeric IDs to try after DB max (scan mode only)",
    )
    parser.add_argument(
        "--stop-after-consecutive-misses",
        type=int,
        default=35,
        help="Stop scan after this many consecutive blank/error responses",
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=1.0,
        help="Seconds between HTTP requests",
    )
    parser.add_argument(
        "--digest-model",
        type=str,
        default="gemini-2.5-flash",
        help="Gemini model id for generate_sc_digests_gemini.py",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Parallel digest worker processes (Gemini + Grok fallback); default 5",
    )
    parser.add_argument(
        "--start-after",
        type=int,
        default=None,
        help="Override last stored E-Lib id; first probed id is start-after + 1 (scan mode only)",
    )
    parser.add_argument(
        "--ids",
        type=str,
        default=None,
        help="Comma-separated E-Lib ids only (e.g. 70193). Each new URL runs full ingest + digest.",
    )
    parser.add_argument(
        "--force-reingest",
        action="store_true",
        help="With --ids only: DELETE existing sc_decided_cases for those URLs, then full pipeline.",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable live progress on stderr (default: show when stderr is a terminal)",
    )
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be >= 1")

    use_progress = not args.no_progress and sys.stderr.isatty()

    rep = PipelineReport(
        html_dir=args.html_dir.resolve(),
        md_dir=args.md_dir.resolve(),
        digest_model=args.digest_model,
    )
    exit_code = 0

    id_list: list[int] | None = None
    if args.ids:
        id_list = []
        for part in args.ids.replace(" ", "").split(","):
            if not part:
                continue
            id_list.append(int(part))
        if not id_list:
            rep.fatal_error = "--ids was empty after parsing."
            rep.emit()
            return 2

    if args.force_reingest and not id_list:
        rep.fatal_error = "--force-reingest requires --ids (not compatible with scan mode)."
        rep.emit()
        return 2

    try:
        load_api_local_settings_into_environ(_REPO_ROOT)

        db_url = os.environ.get("DB_CONNECTION_STRING")
        if not db_url:
            rep.fatal_error = "DB_CONNECTION_STRING is not set."
            exit_code = 2
        else:
            conn = psycopg2.connect(db_url)
            new_db_ids: list[int] = []
            try:
                rep.scan_mode = id_list is None
                if id_list is None:
                    base_id = (
                        args.start_after
                        if args.start_after is not None
                        else get_max_elib_showdocs_id(conn)
                    )
                    rep.max_elib_before = base_id
                else:
                    base_id = None

                args.html_dir.mkdir(parents=True, exist_ok=True)
                args.md_dir.mkdir(parents=True, exist_ok=True)

                if id_list is not None and args.force_reingest:
                    removed = delete_sc_cases_for_elib_ids(conn, id_list)
                    log.info(
                        "Force re-ingest: deleted %s existing sc_decided_cases row(s): %s",
                        len(removed),
                        removed,
                    )

                session = _session()
                consecutive_misses = 0
                scan_mode = id_list is None
                if id_list is not None:
                    doc_iter = list(id_list)
                else:
                    assert base_id is not None
                    doc_iter = [base_id + offset for offset in range(1, args.max_probe + 1)]

                with _live_progress_bar("E-Lib ingest", len(doc_iter), use_progress) as ingest_bar:
                    for doc_id in _each_doc_id_with_ingest_pbar(doc_iter, ingest_bar):
                        sc_url = sc_url_for_elib_id(doc_id)

                        if row_exists_for_url(conn, sc_url):
                            log.info("Already in DB, skip id=%s", doc_id)
                            rep.add(
                                elib_id=doc_id,
                                outcome="SKIP_ALREADY_IN_DB",
                                sc_url=sc_url,
                            )
                            consecutive_misses = 0
                            time.sleep(args.request_delay)
                            continue

                        time.sleep(args.request_delay)
                        html, status = fetch_showdocs_html(session, doc_id)

                        if status != "ok" or not html:
                            log.info("Miss id=%s (%s)", doc_id, status)
                            rep.add(
                                elib_id=doc_id,
                                outcome="MISS",
                                detail=status,
                                sc_url=sc_url,
                            )
                            if scan_mode:
                                consecutive_misses += 1
                                if consecutive_misses >= args.stop_after_consecutive_misses:
                                    log.info(
                                        "Stopping after %s consecutive misses (last tried id=%s).",
                                        consecutive_misses,
                                        doc_id,
                                    )
                                    break
                            continue

                        consecutive_misses = 0
                        md_text, conv_err = elib_html_to_markdown(
                            html, source_url=sc_url, elib_doc_id=doc_id
                        )
                        if conv_err or not md_text:
                            log.warning("Convert failed id=%s (%s)", doc_id, conv_err)
                            rep.add(
                                elib_id=doc_id,
                                outcome="CONVERT_FAIL",
                                detail=conv_err or "empty",
                                sc_url=sc_url,
                            )
                            if scan_mode:
                                consecutive_misses += 1
                                if consecutive_misses >= args.stop_after_consecutive_misses:
                                    break
                            continue

                        if not _markdown_lead_is_gr_case(md_text):
                            log.info(
                                "Skip id=%s: not a G.R. case (ingest only G.R. dockets).",
                                doc_id,
                            )
                            rep.add(
                                elib_id=doc_id,
                                outcome="SKIP_NOT_GR",
                                detail="case header is not G.R.",
                                sc_url=sc_url,
                                case_label=_case_label_from_md(md_text) or "",
                            )
                            consecutive_misses = 0
                            time.sleep(args.request_delay)
                            continue

                        html_path = args.html_dir / f"{doc_id}.html"
                        md_path = _markdown_save_path(args.md_dir, md_text, doc_id)
                        html_path.write_text(html, encoding="utf-8")
                        md_path.write_text(md_text, encoding="utf-8")

                        case_id = insert_decision(conn, sc_url, md_text)
                        new_db_ids.append(case_id)
                        log.info("Ingested E-Lib id=%s -> sc_decided_cases.id=%s", doc_id, case_id)
                        rep.add(
                            elib_id=doc_id,
                            outcome="INGESTED",
                            sc_url=sc_url,
                            md_file=md_path.name,
                            html_file=html_path.name,
                            db_row_id=case_id,
                            case_label=_case_label_from_md(md_text),
                        )

            finally:
                conn.close()

            rep.digest_row_ids = list(new_db_ids)
            if new_db_ids:
                if not os.environ.get("GOOGLE_API_KEY"):
                    rep.fatal_error = (
                        f"GOOGLE_API_KEY is not set; required to digest {len(new_db_ids)} new row(s)."
                    )
                    exit_code = 3
                else:
                    gemini_exc: str | None = None
                    with _live_progress_bar(
                        "Gemini digest", len(new_db_ids), use_progress
                    ) as digest_bar:
                        try:
                            run_digest_subprocess(
                                new_db_ids,
                                model=args.digest_model,
                                workers=args.workers,
                                live_bar=digest_bar,
                            )
                        except subprocess.CalledProcessError as e:
                            if e.returncode == 100:
                                gemini_exc = (
                                    "Digest child exited with code 100 (no case processed in that process). "
                                    "Check fleet_debug.log / child logs; common causes: row not claimable "
                                    "(SKIP LOCKED), filters excluding the row, or missing full_text_md."
                                )
                                log.error("Gemini digest subprocess exit 100 for command: %s", e.cmd)
                            else:
                                gemini_exc = str(e)
                                log.error("Gemini digest subprocess failed: %s", e)

                    blocked = _digest_blocked_safety_row_ids(db_url, new_db_ids)
                    if blocked and os.environ.get("XAI_API_KEY"):
                        try:
                            with _live_progress_bar(
                                "Grok fallback", len(blocked), use_progress
                            ) as grok_bar:
                                _run_grok_safety_fallback_if_needed(
                                    db_url,
                                    blocked,
                                    workers=args.workers,
                                    live_bar=grok_bar,
                                )
                        except OSError as e:
                            log.exception("Grok fallback failed to start: %s", e)
                        blocked = _digest_blocked_safety_row_ids(db_url, new_db_ids)
                    elif blocked:
                        log.warning(
                            "Gemini safety block on id(s) %s; set XAI_API_KEY for Grok fallback.",
                            blocked,
                        )

                    if blocked:
                        rep.digest_ok = False
                        parts = [f"BLOCKED_SAFETY on id(s): {blocked}"]
                        if gemini_exc:
                            parts.append(f"Gemini subprocess: {gemini_exc}")
                        rep.digest_error = "; ".join(parts)
                        exit_code = 1
                    elif gemini_exc:
                        rep.digest_ok = False
                        rep.digest_error = gemini_exc
                        exit_code = 1
                    else:
                        rep.digest_ok = True
                        rep.digest_error = None
                        exit_code = 0
            else:
                rep.digest_ok = None

    except Exception as e:
        rep.fatal_error = str(e)
        exit_code = 1
        log.exception("Pipeline failed")
    finally:
        rep.emit()

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
