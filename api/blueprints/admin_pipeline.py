"""
Admin pipeline routes.

Covers the case-digest pipeline, eLib scan, and eLib gap-scan subprocesses.
All routes require is_admin=true in the users table.
"""
import json
import logging
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

import azure.functions as func

from db_pool import get_db_connection, put_db_connection
from psycopg2.extras import RealDictCursor
from utils.admin_helpers import (
    _json,
    _repo_root,
    _pipeline_log_tail,
    _pipeline_progress_read_safe,
    _pipeline_progress_path,
    _pipeline_subprocess_log_path,
    _case_digest_pipeline_store,
    _SCAN_RESULTS_PATH,
    _GAP_RESULTS_PATH,
    _scan_subprocess_log_path,
    _gap_scan_subprocess_log_path,
)

# Deferred import: blueprints.admin defines _check_admin which itself imports
# get_authenticated_user_id and get_db_connection.  Importing at module level is
# safe because function_app.py loads admin.py before admin_pipeline.py.
from blueprints.admin import _check_admin

pipeline_bp = func.Blueprint()

# ── In-memory pipeline process state ─────────────────────────────────────────
_pipeline_lock = threading.Lock()
_pipeline_proc: Optional[subprocess.Popen] = None
_pipeline_log_fp: Optional[object] = None
_pipeline_log_path: Optional[Path] = None

_pipeline_state: dict = {
    "mode": None,
    "status": "idle",
    "started_at": None,
    "finished_at": None,
    "last_exit_code": None,
}

# ── In-memory eLib scan process state ────────────────────────────────────────
_scan_lock = threading.Lock()
_scan_proc: Optional[subprocess.Popen] = None
_scan_log_path: Optional[Path] = None
_scan_log_fp: Optional[object] = None   # kept open while subprocess is alive; closed on finish
_scan_state: dict = {
    "status": "idle",   # idle | running | done | failed
    "started_at": None,
    "finished_at": None,
    "last_exit_code": None,
}

# ── In-memory eLib GAP scan process state ────────────────────────────────────
_gap_scan_lock = threading.Lock()
_gap_scan_proc: Optional[subprocess.Popen] = None
_gap_scan_state: dict = {
    "status": "idle",   # idle | running | done | failed
    "started_at": None,
    "finished_at": None,
    "last_exit_code": None,
}
_gap_scan_log_path: Optional[Path] = None
_gap_scan_log_fp: Optional[object] = None   # kept open while subprocess is alive; closed on finish


# ── Pipeline helpers ──────────────────────────────────────────────────────────

def _refresh_pipeline_state_locked() -> None:
    """Refresh in-memory pipeline state from subprocess status (lock must be held)."""
    global _pipeline_proc, _pipeline_log_fp
    if _pipeline_proc is None:
        return
    rc = _pipeline_proc.poll()
    if rc is None:
        return
    _pipeline_state["status"] = "done" if rc == 0 else "failed"
    _pipeline_state["finished_at"] = datetime.now(timezone.utc).isoformat()
    _pipeline_state["last_exit_code"] = int(rc)
    _pipeline_proc = None
    if _pipeline_log_fp is not None:
        try:
            _pipeline_log_fp.flush()
            _pipeline_log_fp.close()
        except Exception:
            pass
        _pipeline_log_fp = None


def _pipeline_snapshot() -> dict:
    with _pipeline_lock:
        _refresh_pipeline_state_locked()
        snap = {
            "running": _pipeline_proc is not None,
            "mode": _pipeline_state.get("mode"),
            "status": _pipeline_state.get("status"),
            "started_at": _pipeline_state.get("started_at"),
            "finished_at": _pipeline_state.get("finished_at"),
            "last_exit_code": _pipeline_state.get("last_exit_code"),
            "progress_path": str(_pipeline_progress_path()),
            "subprocess_log_path": str(_pipeline_subprocess_log_path()),
        }
        # Read log path inside the lock so we don't race with _start_pipeline
        # which updates _pipeline_log_path under the same lock.
        _snap_log_path = _pipeline_log_path

    prog = _pipeline_progress_read_safe()
    if prog:
        snap["progress"] = prog
        snap["phase"] = prog.get("phase")
        snap["progress_message"] = prog.get("message")
        snap["overall_percent"] = prog.get("overall_percent")
    snap["log_tail"] = _pipeline_log_tail(path=_snap_log_path)
    return snap


def _start_pipeline(
    mode: str,
    vertex_project: Optional[str] = None,
    vertex_location: Optional[str] = None,
    digest_model: Optional[str] = None,
) -> Tuple[Optional[dict], Optional[str]]:
    """
    Start a pipeline subprocess.
    Returns (result, error_message). Caller serializes result or error.
    """
    global _pipeline_proc, _pipeline_log_fp, _pipeline_log_path

    root = _repo_root()
    vertex_flags = []
    if vertex_project:
        vertex_flags = ["--vertex-project", vertex_project, "--vertex-location", vertex_location or "global"]

    _model = (digest_model or "").strip() or (os.environ.get("PIPELINE_DIGEST_MODEL") or "").strip() or "gemini-3.5-flash"

    if mode == "full":
        script = root / "scripts" / "elib_digest_pipeline.py"
        cmd = [sys.executable, "-u", str(script), "--digest-model", _model] + vertex_flags
    elif mode == "resume":
        script = root / "scripts" / "finish_elib_pipeline_digests.py"
        cmd = [sys.executable, "-u", str(script), "--max-passes", "1", "--model", _model] + vertex_flags
    else:
        return None, "Unsupported pipeline mode"

    if not script.exists():
        return None, f"Pipeline script not found at {script}. Run from a checkout that includes /scripts."

    digest_store = _case_digest_pipeline_store()
    digest_store.mkdir(parents=True, exist_ok=True)
    log_path = _pipeline_subprocess_log_path()
    prog_path = _pipeline_progress_path()
    cmd += ["--progress-file", str(prog_path)]

    with _pipeline_lock:
        _refresh_pipeline_state_locked()
        if _pipeline_proc is not None:
            return None, "Pipeline is already running"
        try:
            if _pipeline_log_fp is not None:
                try:
                    _pipeline_log_fp.close()
                except Exception:
                    pass
                _pipeline_log_fp = None

            _pipeline_log_path = log_path
            lf = open(log_path, "w", encoding="utf-8", buffering=1)
            _pipeline_log_fp = lf

            logging.info(
                "Starting digest pipeline subprocess mode=%s log=%s cmd=%s",
                mode,
                log_path,
                " ".join(cmd),
            )

            _pipeline_proc = subprocess.Popen(
                cmd,
                cwd=str(root),
                stdout=lf,
                stderr=subprocess.STDOUT,
                env=os.environ.copy(),
            )
            _pipeline_state["mode"] = mode
            _pipeline_state["status"] = "running"
            _pipeline_state["started_at"] = datetime.now(timezone.utc).isoformat()
            _pipeline_state["finished_at"] = None
            _pipeline_state["last_exit_code"] = None
            return {
                "ok": True,
                "mode": mode,
                "pid": int(_pipeline_proc.pid),
                "status": "running",
                "started_at": _pipeline_state["started_at"],
            }, None
        except Exception as exc:
            _pipeline_proc = None
            return None, str(exc)


def _platform_vertex_args(body: dict) -> Tuple[Optional[str], Optional[str]]:
    """Extract vertex_project and vertex_location from a pre-parsed request body dict."""
    platform = body.get("platform", "vertex")
    if platform == "vertex":
        return "gen-lang-client-0545071081", "us"
    return None, None


# ── Scan helpers ──────────────────────────────────────────────────────────────

def _refresh_scan_state_locked() -> None:
    """Poll scan subprocess and update _scan_state (lock must be held)."""
    global _scan_proc, _scan_log_fp
    if _scan_proc is None:
        return
    rc = _scan_proc.poll()
    if rc is None:
        return
    _scan_state["status"] = "done" if rc == 0 else "failed"
    _scan_state["finished_at"] = datetime.now(timezone.utc).isoformat()
    _scan_state["last_exit_code"] = int(rc)
    _scan_proc = None
    if _scan_log_fp is not None:
        try:
            _scan_log_fp.flush()
            _scan_log_fp.close()
        except Exception:
            pass
        _scan_log_fp = None


def _scan_snapshot() -> dict:
    with _scan_lock:
        _refresh_scan_state_locked()
        return {
            "running":        _scan_proc is not None,
            "status":         _scan_state.get("status"),
            "started_at":     _scan_state.get("started_at"),
            "finished_at":    _scan_state.get("finished_at"),
            "last_exit_code": _scan_state.get("last_exit_code"),
        }


# ── Gap scan helpers ──────────────────────────────────────────────────────────

def _refresh_gap_scan_state_locked() -> None:
    """Poll gap scan subprocess and update _gap_scan_state (lock must be held)."""
    global _gap_scan_proc, _gap_scan_log_fp
    if _gap_scan_proc is None:
        return
    rc = _gap_scan_proc.poll()
    if rc is None:
        return
    _gap_scan_state["status"] = "done" if rc == 0 else "failed"
    _gap_scan_state["finished_at"] = datetime.now(timezone.utc).isoformat()
    _gap_scan_state["last_exit_code"] = int(rc)
    _gap_scan_proc = None
    if _gap_scan_log_fp is not None:
        try:
            _gap_scan_log_fp.flush()
            _gap_scan_log_fp.close()
        except Exception:
            pass
        _gap_scan_log_fp = None


def _gap_scan_snapshot() -> dict:
    with _gap_scan_lock:
        _refresh_gap_scan_state_locked()
        return {
            "running":        _gap_scan_proc is not None,
            "status":         _gap_scan_state.get("status"),
            "started_at":     _gap_scan_state.get("started_at"),
            "finished_at":    _gap_scan_state.get("finished_at"),
            "last_exit_code": _gap_scan_state.get("last_exit_code"),
        }


# ── Routes ────────────────────────────────────────────────────────────────────

@pipeline_bp.route(route="ops/pipeline-stats", methods=["GET"])
def admin_pipeline_stats(req: func.HttpRequest) -> func.HttpResponse:
    _, err = _check_admin(req)
    if err:
        return err

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*) AS total FROM sc_decided_cases")
            total = int(cur.fetchone()["total"] or 0)

            cur.execute(
                "SELECT COUNT(*) AS n FROM sc_decided_cases"
                " WHERE digest_ruling IS NOT NULL AND digest_ruling != ''"
            )
            with_digest = int(cur.fetchone()["n"] or 0)

            cur.execute(
                "SELECT COUNT(*) AS n FROM sc_decided_cases"
                " WHERE full_text_md IS NOT NULL AND full_text_md != ''"
            )
            with_md = int(cur.fetchone()["n"] or 0)

            try:
                cur.execute("SELECT COUNT(*) AS n FROM legal_concepts")
                concepts = int(cur.fetchone()["n"] or 0)
            except Exception:
                concepts = None

            try:
                cur.execute(
                    "SELECT MIN(date) AS oldest, MAX(date) AS latest"
                    " FROM sc_decided_cases WHERE date IS NOT NULL"
                )
                date_row = cur.fetchone()
                oldest_date = str(date_row["oldest"]) if date_row["oldest"] else None
                latest_date = str(date_row["latest"]) if date_row["latest"] else None
            except Exception:
                oldest_date = latest_date = None

            try:
                cur.execute(
                    """
                    SELECT
                        COUNT(DISTINCT case_id) AS linked_cases,
                        COUNT(*)                AS total_links
                    FROM codal_case_links
                    """
                )
                link_row = cur.fetchone()
                n_linked = int(link_row["linked_cases"] or 0)
                n_links  = int(link_row["total_links"]  or 0)
                cur.execute(
                    """
                    SELECT
                        statute_id,
                        COUNT(*)                AS total_links,
                        COUNT(DISTINCT case_id) AS linked_cases
                    FROM codal_case_links
                    GROUP BY statute_id
                    ORDER BY statute_id
                    """
                )
                links_by_statute        = {}
                linked_cases_by_statute = {}
                for r in cur.fetchall():
                    sid = r["statute_id"]
                    links_by_statute[sid]        = int(r["total_links"])
                    linked_cases_by_statute[sid] = int(r["linked_cases"])
            except Exception as _link_exc:
                logging.warning("pipeline-stats: codal_case_links query failed: %s", _link_exc)
                n_linked = n_links = 0
                links_by_statute        = {}
                linked_cases_by_statute = {}

            last_elib_case = None
            try:
                cur.execute(
                    """
                    SELECT
                        sc_url,
                        CAST(SUBSTRING(sc_url FROM '/showdocs/1/([0-9]+)') AS INTEGER) AS elib_id,
                        COALESCE(NULLIF(TRIM(case_number),''), NULLIF(TRIM(short_title),''), '') AS case_label,
                        date
                    FROM sc_decided_cases
                    WHERE sc_url ILIKE %s
                      AND sc_url ~ %s
                    ORDER BY
                        CAST(SUBSTRING(sc_url FROM '/showdocs/1/([0-9]+)') AS INTEGER) DESC
                    LIMIT 1
                    """,
                    (
                        "%elibrary.judiciary.gov.ph%thebookshelf/showdocs/1/%",
                        r"/showdocs/1/[0-9]+",
                    ),
                )
                erow = cur.fetchone()
                if erow and erow["elib_id"]:
                    last_elib_case = {
                        "elib_id":      int(erow["elib_id"]),
                        "sc_url":       erow["sc_url"],
                        "case_label":   (erow["case_label"] or "").strip(),
                        "date":         str(erow["date"]) if erow["date"] else None,
                        "next_scan_id": int(erow["elib_id"]) + 1,
                    }
            except Exception as _exc:
                logging.warning("Could not fetch last eLib case: %s", _exc)

        return _json({
            "total_cases":         total,
            "with_digest":         with_digest,
            "without_digest":      total - with_digest,
            "with_full_text_md":   with_md,
            "legal_concepts":      concepts,
            "oldest_case_date":    oldest_date,
            "latest_case_date":    latest_date,
            "digest_coverage_pct": round(100 * with_digest / max(total, 1), 1),
            "md_coverage_pct":     round(100 * with_md / max(total, 1), 1),
            "linked_cases":             n_linked,
            "total_links":              n_links,
            "link_coverage_pct":        round(100 * n_linked / max(total, 1), 1),
            "links_by_statute":         links_by_statute,
            "linked_cases_by_statute":  linked_cases_by_statute,
            "last_elib_case":      last_elib_case,
        })
    except Exception as exc:
        logging.error("admin/pipeline-stats: %s", exc)
        return _json({"error": str(exc)}, 500)
    finally:
        put_db_connection(conn)


@pipeline_bp.route(route="ops/pipeline/start", methods=["POST"])
def admin_pipeline_start(req: func.HttpRequest) -> func.HttpResponse:
    _, err = _check_admin(req)
    if err:
        return err
    try:
        body = req.get_json(silent=True) or {}
    except Exception:
        body = {}
    v_project, v_location = _platform_vertex_args(body)
    digest_model = (body.get("digest_model") or "").strip() or None
    result, start_err = _start_pipeline("full", vertex_project=v_project, vertex_location=v_location, digest_model=digest_model)
    if start_err:
        status = 409 if "already running" in start_err.lower() else 500
        return _json({"error": start_err}, status)
    return _json(result, 200)


@pipeline_bp.route(route="ops/pipeline/resume", methods=["POST"])
def admin_pipeline_resume(req: func.HttpRequest) -> func.HttpResponse:
    _, err = _check_admin(req)
    if err:
        return err
    try:
        body = req.get_json(silent=True) or {}
    except Exception:
        body = {}
    v_project, v_location = _platform_vertex_args(body)
    result, start_err = _start_pipeline("resume", vertex_project=v_project, vertex_location=v_location)
    if start_err:
        status = 409 if "already running" in start_err.lower() else 500
        return _json({"error": start_err}, status)
    return _json(result, 200)


@pipeline_bp.route(route="ops/pipeline/stop", methods=["POST"])
def admin_pipeline_stop(req: func.HttpRequest) -> func.HttpResponse:
    _, err = _check_admin(req)
    if err:
        return err

    global _pipeline_proc
    with _pipeline_lock:
        _refresh_pipeline_state_locked()
        if _pipeline_proc is None:
            return _json({"error": "Pipeline is not running"}, 409)
        try:
            _pipeline_proc.terminate()
            _pipeline_state["status"] = "stopping"
            return _json({"ok": True, "status": "stopping"}, 200)
        except Exception as exc:
            return _json({"error": str(exc)}, 500)


@pipeline_bp.route(route="ops/pipeline/status", methods=["GET"])
def admin_pipeline_status(req: func.HttpRequest) -> func.HttpResponse:
    _, err = _check_admin(req)
    if err:
        return err
    return _json(_pipeline_snapshot(), 200)


@pipeline_bp.route(route="ops/pipeline/scan", methods=["POST"])
def admin_pipeline_scan(req: func.HttpRequest) -> func.HttpResponse:
    """Start the eLib scan subprocess (read-only — no DB writes)."""
    _, err = _check_admin(req)
    if err:
        return err

    global _scan_proc
    root = _repo_root()
    script = root / "scripts" / "scan_elib_new_cases.py"
    if not script.exists():
        return _json({"error": f"Scan script not found: {script}"}, 500)

    try:
        body = req.get_json(silent=True) or {}
    except Exception:
        body = {}
    max_probe   = int(body.get("max_probe", 400))
    start_after = body.get("start_after")  # None means auto-detect from DB

    cmd = [
        sys.executable, "-u", str(script),
        "--max-probe", str(max_probe),
        "--output", str(_SCAN_RESULTS_PATH),
    ]
    if start_after is not None:
        cmd += ["--start-after", str(int(start_after))]

    with _scan_lock:
        _refresh_scan_state_locked()
        if _scan_proc is not None:
            return _json({"error": "Scan is already running"}, 409)
        global _scan_log_path, _scan_log_fp
        try:
            _SCAN_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
            _scan_log_path = _scan_subprocess_log_path()
            scan_log_fp = open(_scan_log_path, "w", encoding="utf-8", buffering=1)
            _scan_log_fp = scan_log_fp
            _scan_proc = subprocess.Popen(
                cmd,
                cwd=str(root),
                stdout=scan_log_fp,
                stderr=subprocess.STDOUT,
                env=os.environ.copy(),
            )
            _scan_state["status"] = "running"
            _scan_state["started_at"] = datetime.now(timezone.utc).isoformat()
            _scan_state["finished_at"] = None
            _scan_state["last_exit_code"] = None
            return _json({
                "ok": True,
                "pid": int(_scan_proc.pid),
                "status": "running",
                "started_at": _scan_state["started_at"],
                "max_probe": max_probe,
            }, 200)
        except Exception as exc:
            _scan_proc = None
            return _json({"error": str(exc)}, 500)


@pipeline_bp.route(route="ops/pipeline/scan-results", methods=["GET"])
def admin_pipeline_scan_results(req: func.HttpRequest) -> func.HttpResponse:
    """Return the latest scan results JSON + current scan process status."""
    _, err = _check_admin(req)
    if err:
        return err

    state = _scan_snapshot()
    results = None
    if _SCAN_RESULTS_PATH.exists():
        try:
            results = json.loads(_SCAN_RESULTS_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            logging.warning("Could not read scan results: %s", exc)

    return _json({"scan": state, "results": results, "log_tail": _pipeline_log_tail(path=_scan_log_path)}, 200)


@pipeline_bp.route(route="ops/pipeline/scan-gaps", methods=["POST"])
def admin_pipeline_scan_gaps(req: func.HttpRequest) -> func.HttpResponse:
    """Start the eLib gap scan subprocess (read-only — finds missing G.R. cases)."""
    _, err = _check_admin(req)
    if err:
        return err

    global _gap_scan_proc
    root = _repo_root()
    script = root / "scripts" / "scan_elib_gaps.py"
    if not script.exists():
        return _json({"error": f"Gap scan script not found: {script}"}, 500)

    try:
        body = req.get_json(silent=True) or {}
    except Exception:
        body = {}

    max_probe  = body.get("max_probe")
    resume     = bool(body.get("resume", False))
    fresh      = bool(body.get("fresh",  False))
    range_from = body.get("range_from")
    range_to   = body.get("range_to")

    cmd = [
        sys.executable, "-u", str(script),
        "--output", str(_GAP_RESULTS_PATH),
    ]
    if max_probe is not None:
        cmd += ["--max-probe", str(int(max_probe))]
    if resume:
        cmd += ["--resume"]
    if range_from is not None:
        cmd += ["--range-from", str(int(range_from))]
    if range_to is not None:
        cmd += ["--range-to", str(int(range_to))]

    with _gap_scan_lock:
        _refresh_gap_scan_state_locked()
        if _gap_scan_proc is not None:
            if fresh:
                try:
                    _gap_scan_proc.terminate()
                except Exception:
                    pass
                _gap_scan_proc = None
            else:
                return _json({"error": "Gap scan is already running"}, 409)
        if fresh and _GAP_RESULTS_PATH.exists():
            try:
                _GAP_RESULTS_PATH.unlink()
            except Exception:
                pass
        global _gap_scan_log_path, _gap_scan_log_fp
        try:
            _GAP_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
            _gap_scan_log_path = _gap_scan_subprocess_log_path()
            gap_log_fp = open(_gap_scan_log_path, "w", encoding="utf-8", buffering=1)
            _gap_scan_log_fp = gap_log_fp
            _gap_scan_proc = subprocess.Popen(
                cmd,
                cwd=str(root),
                stdout=gap_log_fp,
                stderr=subprocess.STDOUT,
                env=os.environ.copy(),
            )
            _gap_scan_state["status"] = "running"
            _gap_scan_state["started_at"] = datetime.now(timezone.utc).isoformat()
            _gap_scan_state["finished_at"] = None
            _gap_scan_state["last_exit_code"] = None
            return _json({
                "ok": True,
                "pid": int(_gap_scan_proc.pid),
                "status": "running",
                "started_at": _gap_scan_state["started_at"],
            }, 200)
        except Exception as exc:
            _gap_scan_proc = None
            return _json({"error": str(exc)}, 500)


@pipeline_bp.route(route="ops/pipeline/gap-results", methods=["GET"])
def admin_pipeline_gap_results(req: func.HttpRequest) -> func.HttpResponse:
    """Return the latest gap scan results JSON + current process status."""
    _, err = _check_admin(req)
    if err:
        return err

    state = _gap_scan_snapshot()
    results = None
    if _GAP_RESULTS_PATH.exists():
        try:
            results = json.loads(_GAP_RESULTS_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            logging.warning("Could not read gap results: %s", exc)

    return _json({"scan": state, "results": results, "log_tail": _pipeline_log_tail(path=_gap_scan_log_path)}, 200)


@pipeline_bp.route(route="ops/pipeline/stop-gap-scan", methods=["POST"])
def admin_pipeline_stop_gap_scan(req: func.HttpRequest) -> func.HttpResponse:
    """Terminate the running gap scan subprocess."""
    _, err = _check_admin(req)
    if err:
        return err
    global _gap_scan_proc
    with _gap_scan_lock:
        _refresh_gap_scan_state_locked()
        if _gap_scan_proc is None:
            return _json({"ok": True, "stopped": False}, 200)
        try:
            _gap_scan_proc.terminate()
        except Exception:
            pass
        _gap_scan_proc = None
        _gap_scan_state["status"] = "idle"
        _gap_scan_state["finished_at"] = datetime.now(timezone.utc).isoformat()
    return _json({"ok": True, "stopped": True}, 200)
