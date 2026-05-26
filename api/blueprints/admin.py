"""
Admin-only Azure Functions blueprint.
All routes require is_admin=true in the users table.
"""
import azure.functions as func
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor

import requests

from db_pool import get_db_connection, put_db_connection
from utils.clerk_auth import get_authenticated_user_id

admin_bp = func.Blueprint()

FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://lexmateph.com").rstrip("/")

# ── In-memory backup job store ────────────────────────────────────────────────
# Persists within a single Azure Functions worker lifetime.
_backup_jobs: dict = {}
_backup_lock = threading.Lock()

# ── In-memory pipeline process state ───────────────────────────────────────────
# Persists within a single Azure Functions worker lifetime.
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

# ── In-memory eLib scan process state ───────────────────────────────────────────
_scan_lock = threading.Lock()
_scan_proc: Optional[subprocess.Popen] = None
_scan_log_path: Optional[Path] = None
_scan_state: dict = {
    "status": "idle",   # idle | running | done | failed
    "started_at": None,
    "finished_at": None,
    "last_exit_code": None,
}


def _pipeline_scripts_root() -> Path:
    """Full repo locally (scripts/ sibling to api/); bundled ``api/`` wwwroot on Azure SWA."""
    api_dir = Path(__file__).resolve().parent.parent
    # Use env vars directly — _running_on_azure_host() is defined later in the file
    # and this function is called at module-level before that definition is reached.
    if os.getenv("WEBSITE_INSTANCE_ID") or os.getenv("WEBSITE_SITE_NAME"):
        return api_dir
    sibling = api_dir.parent
    if (sibling / "scripts").is_dir() and (sibling / "api").is_dir():
        return sibling
    return api_dir


def _case_digest_pipeline_store() -> Path:
    """Directory for scan / gap JSON — repo ``admin-tools`` path or writable deploy fallback."""
    root = _pipeline_scripts_root()
    if (root / "admin-tools").is_dir():
        return root / "admin-tools" / "case-digest-pipeline"
    return root / "pipeline_runtime" / "case-digest-pipeline"


_SCAN_RESULTS_PATH = _case_digest_pipeline_store() / "scan_results.json"

# ── In-memory eLib GAP scan process state ────────────────────────────────────
_gap_scan_lock = threading.Lock()
_gap_scan_proc: Optional[subprocess.Popen] = None
_gap_scan_state: dict = {
    "status": "idle",   # idle | running | done | failed
    "started_at": None,
    "finished_at": None,
    "last_exit_code": None,
}
_GAP_RESULTS_PATH = _case_digest_pipeline_store() / "gap_results.json"

# ── In-memory eLib GAP scan log state ────────────────────────────────────────
_gap_scan_log_path: Optional[Path] = None


def _scan_subprocess_log_path() -> Path:
    return _case_digest_pipeline_store() / "scan_subprocess.log"


def _gap_scan_subprocess_log_path() -> Path:
    return _case_digest_pipeline_store() / "gap_scan_subprocess.log"


def _pipeline_progress_path() -> Path:
    """JSON snapshot written by digest pipeline subprocess (per-case stages + %)."""
    return _case_digest_pipeline_store() / "pipeline_progress.json"


def _pipeline_subprocess_log_path() -> Path:
    """Stdout/stderr from the spawned pipeline subprocess (admin triggers)."""
    return _case_digest_pipeline_store() / "pipeline_subprocess.log"


def _pipeline_progress_read_safe() -> Optional[dict]:
    p = _pipeline_progress_path()
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        logging.warning("Could not parse pipeline_progress.json: %s", exc)
        return None


def _pipeline_log_tail(max_bytes: int = 8192, path: Optional[Path] = None) -> Optional[str]:
    lp = path or _pipeline_subprocess_log_path()
    if not lp.is_file():
        return None
    try:
        data = lp.read_bytes()
        if len(data) <= max_bytes:
            return data.decode("utf-8", errors="replace")
        return data[-max_bytes:].decode("utf-8", errors="replace")
    except Exception as exc:
        logging.warning("Could not read pipeline_subprocess.log: %s", exc)
        return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _json(data, status=200):
    return func.HttpResponse(
        json.dumps(data, default=str),
        mimetype="application/json",
        status_code=status,
        headers={"Access-Control-Allow-Origin": FRONTEND_URL},
    )


def _running_on_azure_host() -> bool:
    """True when Functions runs in Azure (not local Core Tools). Local mirror restore must not run there."""
    return bool(os.getenv("WEBSITE_INSTANCE_ID") or os.getenv("WEBSITE_SITE_NAME"))


def _mirror_restore_enabled() -> bool:
    """Admin backup can pg_restore into LOCAL_DB when configured and API runs on a dev machine."""
    from config import LOCAL_DB_CONNECTION_STRING

    if _running_on_azure_host():
        return False
    return bool((LOCAL_DB_CONNECTION_STRING or "").strip())


def _check_admin(req: func.HttpRequest):
    """Returns (clerk_id, error_response). Callers must return error_response if not None."""
    clerk_id, err = get_authenticated_user_id(req)
    if err or not clerk_id:
        return None, _json({"error": "Unauthorized"}, 401)

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT is_admin FROM users WHERE clerk_id = %s", (clerk_id,))
            row = cur.fetchone()
            if not row or not row.get("is_admin"):
                return None, _json({"error": "Forbidden"}, 403)
    except Exception as exc:
        logging.error("Admin check DB error: %s", exc)
        return None, _json({"error": "Internal error"}, 500)
    finally:
        put_db_connection(conn)

    return clerk_id, None


def _get_azure_token():
    """Obtain an Azure management-plane bearer token.
    Tries managed identity first (works when deployed on Azure),
    then falls back to service-principal env vars.
    """
    try:
        resp = requests.get(
            "http://169.254.169.254/metadata/identity/oauth2/token",
            params={"api-version": "2019-08-01", "resource": "https://management.azure.com/"},
            headers={"Metadata": "true"},
            timeout=3,
        )
        if resp.ok:
            return resp.json().get("access_token")
    except Exception:
        pass

    tenant = os.environ.get("AZURE_TENANT_ID")
    client_id = os.environ.get("AZURE_CLIENT_ID")
    client_secret = os.environ.get("AZURE_CLIENT_SECRET")
    if tenant and client_id and client_secret:
        try:
            resp = requests.post(
                f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scope": "https://management.azure.com/.default",
                },
                timeout=10,
            )
            if resp.ok:
                return resp.json().get("access_token")
        except Exception as exc:
            logging.warning("Azure SP auth failed: %s", exc)

    # Local dev fallback: use Azure CLI signed-in session.
    az = shutil.which("az")
    if az:
        try:
            token = subprocess.check_output(
                [
                    az,
                    "account",
                    "get-access-token",
                    "--resource",
                    "https://management.azure.com/",
                    "--query",
                    "accessToken",
                    "-o",
                    "tsv",
                ],
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=8,
            ).strip()
            if token:
                return token
        except Exception:
            pass

    return None


def _repo_root() -> Path:
    """Filesystem root used for bundled pipeline subprocesses (matches _pipeline_scripts_root)."""
    return _pipeline_scripts_root()


def _first_env(*names):
    for name in names:
        val = (os.environ.get(name) or "").strip()
        if val:
            return val
    return None


def _az_cli_tsv(args):
    az = shutil.which("az")
    if not az:
        return None
    try:
        out = subprocess.check_output(
            [az] + args,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=8,
        ).strip()
        return out or None
    except Exception:
        return None


def _resolve_subscription_id():
    return _first_env("AZURE_SUBSCRIPTION_ID", "AZURE_SUBSCRIPTION") or _az_cli_tsv(
        ["account", "show", "--query", "id", "-o", "tsv"]
    )


def _resolve_resource_group():
    rg = _first_env("AZURE_RESOURCE_GROUP", "AZURE_POSTGRES_RG")
    if rg:
        return rg
    # Practical local default in this workspace.
    exists = _az_cli_tsv(["group", "exists", "--name", "LexMatePH"])
    return "LexMatePH" if exists == "true" else None


def _arm_list_first_name(base_url, headers, provider_path):
    try:
        r = requests.get(f"{base_url}/{provider_path}", headers=headers, timeout=10)
        if not r.ok:
            return None
        values = r.json().get("value", [])
        if not values:
            return None
        return values[0].get("name")
    except Exception:
        return None


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

    prog = _pipeline_progress_read_safe()
    if prog:
        snap["progress"] = prog
        # Helpful UX: last line mirrors human-readable headline.
        snap["phase"] = prog.get("phase")
        snap["progress_message"] = prog.get("message")
        snap["overall_percent"] = prog.get("overall_percent")
    snap["log_tail"] = _pipeline_log_tail(path=_pipeline_log_path)
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

    # Determine which model to use — explicit arg wins, then env var, then hardcoded fallback.
    # We pass --digest-model explicitly so GEMINI_DIGEST_MODEL in the child env doesn't override
    # the intended model (the env var is evaluated at argparse construction time, before
    # load_api_local_settings_into_environ runs in the subprocess).
    _model = (digest_model or "").strip() or (os.environ.get("PIPELINE_DIGEST_MODEL") or "").strip() or "gemini-3-flash-preview"

    if mode == "full":
        script = root / "scripts" / "elib_digest_pipeline.py"
        cmd = [sys.executable, "-u", str(script), "--digest-model", _model] + vertex_flags
    elif mode == "resume":
        # Resume mode: continue pending digest work on already-ingested rows.
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


# ── DB STATS ──────────────────────────────────────────────────────────────────

@admin_bp.route(route="ops/db-stats", methods=["GET"])
def admin_db_stats(req: func.HttpRequest) -> func.HttpResponse:
    _, err = _check_admin(req)
    if err:
        return err

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT pg_size_pretty(pg_database_size(current_database())) AS db_size,"
                "       pg_database_size(current_database()) AS db_size_bytes"
            )
            size_row = cur.fetchone()

            cur.execute("""
                SELECT
                    t.relname                                       AS table_name,
                    s.n_live_tup                                    AS live_rows,
                    s.n_dead_tup                                    AS dead_rows,
                    pg_size_pretty(pg_total_relation_size(t.oid))   AS total_size,
                    pg_total_relation_size(t.oid)                   AS total_size_bytes,
                    pg_size_pretty(pg_relation_size(t.oid))         AS table_size,
                    pg_size_pretty(pg_indexes_size(t.oid))          AS index_size,
                    s.last_autovacuum,
                    s.last_autoanalyze
                FROM pg_class t
                JOIN pg_stat_user_tables s ON t.oid = s.relid
                WHERE t.relkind = 'r'
                ORDER BY pg_total_relation_size(t.oid) DESC
            """)
            tables = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT ROUND(
                    100.0 * sum(heap_blks_hit) /
                    NULLIF(sum(heap_blks_hit) + sum(heap_blks_read), 0),
                    2
                ) AS cache_hit_ratio
                FROM pg_statio_user_tables
            """)
            cache_row = cur.fetchone()

            cur.execute("""
                SELECT count(*) AS active,
                       (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') AS max_conn
                FROM pg_stat_activity
                WHERE state = 'active'
            """)
            conn_row = cur.fetchone()

            cur.execute("""
                SELECT ROUND(
                    100.0 * sum(idx_blks_hit) /
                    NULLIF(sum(idx_blks_hit) + sum(idx_blks_read), 0),
                    2
                ) AS index_hit_ratio
                FROM pg_statio_user_indexes
            """)
            idx_row = cur.fetchone()

            cur.execute(
                "SELECT xact_commit + xact_rollback AS total_txn"
                " FROM pg_stat_database WHERE datname = current_database()"
            )
            txn_row = cur.fetchone()

        total_dead = sum(int(t.get("dead_rows") or 0) for t in tables)

        return _json({
            "db_size":            size_row["db_size"],
            "db_size_bytes":      int(size_row["db_size_bytes"] or 0),
            "cache_hit_ratio":    float(cache_row["cache_hit_ratio"] or 0),
            "index_hit_ratio":    float(idx_row["index_hit_ratio"] or 0),
            "active_connections": int(conn_row["active"] or 0),
            "max_connections":    int(conn_row["max_conn"] or 100),
            "total_dead_tuples":  total_dead,
            "total_transactions": int(txn_row["total_txn"] or 0),
            "tables":             tables,
        })
    except Exception as exc:
        logging.error("admin/db-stats: %s", exc)
        return _json({"error": str(exc)}, 500)
    finally:
        put_db_connection(conn)


# ── BACKUP (pg_dump custom format) ───────────────────────────────────────────

def _run_pg_restore_mirror(job_id: str, dump_path: str, local_uri: str) -> None:
    """Restore custom-format dump into local Postgres (same flags as tools/pg_restore_local_mirror.py)."""
    pg_restore_bin = shutil.which("pg_restore")
    if not pg_restore_bin:
        raise RuntimeError(
            "pg_restore was not found on PATH. Install PostgreSQL client tools, or run "
            "`python tools/pg_restore_local_mirror.py` manually with your downloaded .dump file."
        )
    cmd = [
        pg_restore_bin,
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-acl",
        f"--dbname={local_uri}",
        dump_path,
    ]
    with _backup_lock:
        _backup_jobs[job_id].update({
            "pct":           55,
            "current_table": "pg_restore · LOCAL_DB_CONNECTION_STRING",
        })
    logging.info("Backup job %s: invoking pg_restore into local mirror", job_id)
    proc = subprocess.run(cmd, capture_output=True, timeout=7200, text=False)
    if proc.returncode != 0:
        tail = (proc.stderr or b"").decode("utf-8", errors="replace")[-4000:]
        raise RuntimeError(f"pg_restore failed (exit {proc.returncode}): {tail.strip() or 'no stderr'}")


def _run_pg_dump_backup(job_id: str):
    """Background thread: pg_dump cloud DB (-Fc), optional pg_restore to LOCAL_DB, then expose dump for download."""
    tmp_path = None
    try:
        from config import DB_CONNECTION_STRING, LOCAL_DB_CONNECTION_STRING

        uri = (DB_CONNECTION_STRING or "").strip()
        if not uri:
            raise RuntimeError("DB_CONNECTION_STRING is not configured")

        local_uri = (LOCAL_DB_CONNECTION_STRING or "").strip()
        run_mirror = bool(local_uri) and not _running_on_azure_host()

        if local_uri and _running_on_azure_host():
            logging.info(
                "Backup job %s: LOCAL_DB_CONNECTION_STRING is set but mirror restore is skipped "
                "(hosted API cannot reach your workstation Postgres).",
                job_id,
            )

        pg_dump_bin = shutil.which("pg_dump")
        if not pg_dump_bin:
            raise RuntimeError(
                "pg_dump was not found on PATH. Install PostgreSQL client tools on this machine, "
                "or from the api/ folder run: python tools/pg_dump_cloud.py --output … "
                "(same dump format, runs where pg_dump is installed)."
            )

        with _backup_lock:
            _backup_jobs[job_id].update({
                "pct":           5,
                "current_table": "pg_dump · cloud database (-Fc)",
                "done_tables":   0,
                "total_tables":  0,
            })

        fd, tmp_path = tempfile.mkstemp(suffix=".dump")
        os.close(fd)

        cmd = [
            pg_dump_bin,
            "--format=custom",
            "--no-owner",
            "--no-acl",
            f"--file={tmp_path}",
            f"--dbname={uri}",
        ]
        logging.info("Backup job %s: invoking pg_dump", job_id)
        proc = subprocess.run(
            cmd,
            capture_output=True,
            timeout=7200,
            text=False,
        )
        if proc.returncode != 0:
            tail = (proc.stderr or b"").decode("utf-8", errors="replace")[-4000:]
            raise RuntimeError(f"pg_dump failed (exit {proc.returncode}): {tail.strip() or 'no stderr'}")

        with open(tmp_path, "rb") as f:
            dump_bytes = f.read()

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
        filename = f"lexmate_pg_backup_{ts}.dump"

        mirror_restored = False
        mirror_error = None
        if run_mirror:
            try:
                with _backup_lock:
                    _backup_jobs[job_id].update({
                        "pct":           45,
                        "current_table": "pg_restore · local PostgreSQL mirror",
                    })
                _run_pg_restore_mirror(job_id, tmp_path, local_uri)
                mirror_restored = True
                logging.info("Backup job %s: pg_restore finished", job_id)
            except Exception as rex:
                mirror_error = str(rex)
                logging.error("Backup job %s: pg_restore failed: %s", job_id, rex)

        finished = {
            "pct":             100,
            "done":            True,
            "filename":        filename,
            "data":            dump_bytes,
            "size_bytes":      len(dump_bytes),
            "current_table":   None,
            "finished_at":     datetime.now(timezone.utc).isoformat(),
            "mirror_restored": mirror_restored,
            "dump_ok":         True,
        }

        if mirror_error:
            finished.update({
                "status":        "error",
                "error":         mirror_error,
                "mirror_failed": True,
            })
        else:
            finished["status"] = "done"
            finished["error"] = None
            finished["mirror_failed"] = False

        with _backup_lock:
            _backup_jobs[job_id].update(finished)
        logging.info(
            "Backup job %s: pg_dump finished (%s bytes), mirror_restored=%s",
            job_id,
            len(dump_bytes),
            mirror_restored,
        )

    except subprocess.TimeoutExpired:
        logging.error("Backup job %s: pg_dump timed out", job_id)
        with _backup_lock:
            _backup_jobs[job_id].update({
                "status": "error",
                "done":   True,
                "error": (
                    "pg_dump exceeded the 2 hour limit. Run "
                    "`python tools/pg_dump_cloud.py --output …` from api/ on your workstation instead."
                ),
            })
    except Exception as exc:
        logging.error("Backup job %s failed: %s", job_id, exc)
        with _backup_lock:
            _backup_jobs[job_id].update({
                "status": "error",
                "done":   True,
                "error":  str(exc),
            })
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


@admin_bp.route(route="ops/backup/start", methods=["POST"])
def admin_backup_start(req: func.HttpRequest) -> func.HttpResponse:
    _, err = _check_admin(req)
    if err:
        return err

    with _backup_lock:
        running = [j for j in _backup_jobs.values() if j.get("status") == "running"]
        if running:
            return _json({"error": "A backup is already in progress"}, 409)

        job_id = str(uuid.uuid4())[:8]
        _backup_jobs[job_id] = {
            "status":                  "running",
            "pct":                     0,
            "current_table":           None,
            "done_tables":             0,
            "total_tables":            0,
            "done":                    False,
            "error":                   None,
            "started_at":              datetime.now(timezone.utc).isoformat(),
            "mirror_restore_planned":  _mirror_restore_enabled(),
        }

    threading.Thread(target=_run_pg_dump_backup, args=(job_id,), daemon=True).start()
    return _json({"job_id": job_id})


@admin_bp.route(route="ops/backup/status", methods=["GET"])
def admin_backup_status(req: func.HttpRequest) -> func.HttpResponse:
    _, err = _check_admin(req)
    if err:
        return err

    job_id = req.params.get("job_id", "")
    with _backup_lock:
        job = _backup_jobs.get(job_id)

    if not job:
        return _json({"error": "Job not found"}, 404)

    return _json({k: v for k, v in job.items() if k != "data"})


@admin_bp.route(route="ops/backup/download", methods=["GET"])
def admin_backup_download(req: func.HttpRequest) -> func.HttpResponse:
    _, err = _check_admin(req)
    if err:
        return err

    job_id = req.params.get("job_id", "")
    with _backup_lock:
        job = _backup_jobs.get(job_id)

    if not job or not job.get("data"):
        return _json({"error": "Backup not ready"}, 404)
    if job.get("status") == "done":
        pass
    elif job.get("status") == "error" and job.get("dump_ok"):
        pass
    else:
        return _json({"error": "Backup not ready"}, 404)

    return func.HttpResponse(
        body=job["data"],
        status_code=200,
        headers={
            "Content-Type": "application/octet-stream",
            "Content-Disposition": f'attachment; filename="{job.get("filename", "lexmate_pg_backup.dump")}"',
        },
    )


# ── PIPELINE STATS ────────────────────────────────────────────────────────────

@admin_bp.route(route="ops/pipeline-stats", methods=["GET"])
def admin_pipeline_stats(req: func.HttpRequest) -> func.HttpResponse:
    _, err = _check_admin(req)
    if err:
        return err

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*) AS total FROM sc_decided_cases")
            total = int(cur.fetchone()["total"] or 0)

            # 'digest' is split into digest_facts/digest_ruling/etc. — a case is
            # considered digested when digest_ruling is populated (core field).
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
                # The date column is called 'date', not 'date_decided'
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
                # Codal link coverage — how many distinct cases have at least one link
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
                # Per-statute breakdown — total links and distinct linked cases
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

            # ── Last eLib case in DB — the scan anchor ────────────────────────
            # The scan script probes from (elib_id + 1) onwards. Surfaced in the
            # UI so admins can confirm the exact starting point before scanning.
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
            # Codal linking metrics
            "linked_cases":             n_linked,
            "total_links":              n_links,
            "link_coverage_pct":        round(100 * n_linked / max(total, 1), 1),
            "links_by_statute":         links_by_statute,
            "linked_cases_by_statute":  linked_cases_by_statute,
            # eLib scan anchor — where the next scan starts from
            "last_elib_case":      last_elib_case,
        })
    except Exception as exc:
        logging.error("admin/pipeline-stats: %s", exc)
        return _json({"error": str(exc)}, 500)
    finally:
        put_db_connection(conn)


def _platform_vertex_args(req: func.HttpRequest) -> Tuple[Optional[str], Optional[str]]:
    """Extract vertex_project and vertex_location from the request body platform field."""
    try:
        body = req.get_json() or {}
    except Exception:
        body = {}
    platform = body.get("platform", "vertex")
    if platform == "vertex":
        return "gen-lang-client-0176283199", "global"
    return None, None


@admin_bp.route(route="ops/pipeline/start", methods=["POST"])
def admin_pipeline_start(req: func.HttpRequest) -> func.HttpResponse:
    _, err = _check_admin(req)
    if err:
        return err
    try:
        body = req.get_json(silent=True) or {}
    except Exception:
        body = {}
    v_project, v_location = _platform_vertex_args(req)
    digest_model = (body.get("digest_model") or "").strip() or None
    result, start_err = _start_pipeline("full", vertex_project=v_project, vertex_location=v_location, digest_model=digest_model)
    if start_err:
        status = 409 if "already running" in start_err.lower() else 500
        return _json({"error": start_err}, status)
    return _json(result, 200)


@admin_bp.route(route="ops/pipeline/resume", methods=["POST"])
def admin_pipeline_resume(req: func.HttpRequest) -> func.HttpResponse:
    _, err = _check_admin(req)
    if err:
        return err
    v_project, v_location = _platform_vertex_args(req)
    result, start_err = _start_pipeline("resume", vertex_project=v_project, vertex_location=v_location)
    if start_err:
        status = 409 if "already running" in start_err.lower() else 500
        return _json({"error": start_err}, status)
    return _json(result, 200)


@admin_bp.route(route="ops/pipeline/stop", methods=["POST"])
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


@admin_bp.route(route="ops/pipeline/status", methods=["GET"])
def admin_pipeline_status(req: func.HttpRequest) -> func.HttpResponse:
    _, err = _check_admin(req)
    if err:
        return err
    return _json(_pipeline_snapshot(), 200)


# ── eLib Scan ─────────────────────────────────────────────────────────────────

def _refresh_scan_state_locked() -> None:
    """Poll scan subprocess and update _scan_state (lock must be held)."""
    global _scan_proc
    if _scan_proc is None:
        return
    rc = _scan_proc.poll()
    if rc is None:
        return
    _scan_state["status"] = "done" if rc == 0 else "failed"
    _scan_state["finished_at"] = datetime.now(timezone.utc).isoformat()
    _scan_state["last_exit_code"] = int(rc)
    _scan_proc = None


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


@admin_bp.route(route="ops/pipeline/scan", methods=["POST"])
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

    # Parse optional overrides from request body
    try:
        body = req.get_json(silent=True) or {}
    except Exception:
        body = {}
    max_probe  = int(body.get("max_probe",  400))
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
        global _scan_log_path
        try:
            _SCAN_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
            _scan_log_path = _scan_subprocess_log_path()
            scan_log_fp = open(_scan_log_path, "w", encoding="utf-8", buffering=1)
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


@admin_bp.route(route="ops/pipeline/scan-results", methods=["GET"])
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


# ── eLib GAP Scan ─────────────────────────────────────────────────────────────

def _refresh_gap_scan_state_locked() -> None:
    """Poll gap scan subprocess and update _gap_scan_state (lock must be held)."""
    global _gap_scan_proc
    if _gap_scan_proc is None:
        return
    rc = _gap_scan_proc.poll()
    if rc is None:
        return
    _gap_scan_state["status"] = "done" if rc == 0 else "failed"
    _gap_scan_state["finished_at"] = datetime.now(timezone.utc).isoformat()
    _gap_scan_state["last_exit_code"] = int(rc)
    _gap_scan_proc = None


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


@admin_bp.route(route="ops/pipeline/scan-gaps", methods=["POST"])
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

    max_probe  = body.get("max_probe")    # None = scan all gaps
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
        global _gap_scan_log_path
        try:
            _GAP_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
            _gap_scan_log_path = _gap_scan_subprocess_log_path()
            gap_log_fp = open(_gap_scan_log_path, "w", encoding="utf-8", buffering=1)
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


@admin_bp.route(route="ops/pipeline/gap-results", methods=["GET"])
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


@admin_bp.route(route="ops/pipeline/stop-gap-scan", methods=["POST"])
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


# ── AZURE METRICS + COST ──────────────────────────────────────────────────────

@admin_bp.route(route="ops/azure-metrics", methods=["GET"])
def admin_azure_metrics(req: func.HttpRequest) -> func.HttpResponse:
    _, err = _check_admin(req)
    if err:
        return err

    sub_id = _resolve_subscription_id()
    rg = _resolve_resource_group()

    if not sub_id or not rg:
        return _json({
            "configured": False,
            "message": (
                "Set AZURE_SUBSCRIPTION_ID and AZURE_RESOURCE_GROUP in your "
                "Function App Application Settings (or sign in with Azure CLI locally) "
                "to enable Azure metrics."
            ),
        })

    token = _get_azure_token()
    if not token:
        return _json({
            "configured": False,
            "message": (
                "Azure credentials not found. Add AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, "
                "and AZURE_TENANT_ID to your Application Settings, or enable Managed Identity."
            ),
        })

    hdrs = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    base = f"https://management.azure.com/subscriptions/{sub_id}"
    now  = datetime.now(timezone.utc)

    # 24-hour window for metrics (DB, Functions)
    timespan = (
        f"{(now - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%SZ')}/"
        f"{now.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    )
    # Billing-period window (start of month → now) for SWA bandwidth and Speech usage
    billing_start_ts = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_timespan = (
        f"{billing_start_ts.strftime('%Y-%m-%dT%H:%M:%SZ')}/"
        f"{now.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    )

    result: dict = {"configured": True, "resources": {}, "skus": {}}

    # ── PostgreSQL Flexible Server ────────────────────────────────────────────
    pg_name = _first_env("AZURE_POSTGRES_SERVER_NAME", "AZURE_POSTGRES_SERVER")
    if not pg_name:
        pg_name = _arm_list_first_name(
            base,
            hdrs,
            f"resourceGroups/{rg}/providers/Microsoft.DBforPostgreSQL/flexibleServers?api-version=2023-06-01-preview",
        )
    if pg_name:
        pg_rid = (
            f"{base}/resourceGroups/{rg}"
            f"/providers/Microsoft.DBforPostgreSQL/flexibleServers/{pg_name}"
        )
        try:
            r = requests.get(f"{pg_rid}?api-version=2023-06-01-preview", headers=hdrs, timeout=10)
            pg_meta = r.json() if r.ok else {}
            sku = pg_meta.get("sku", {})
            props = pg_meta.get("properties", {})
            storage = props.get("storage", {})
        except Exception:
            sku = props = storage = {}

        metric_names = "cpu_percent,memory_percent,storage_percent,active_connections,iops"
        try:
            r = requests.get(
                f"{pg_rid}/providers/microsoft.insights/metrics",
                params={
                    "api-version":  "2018-01-01",
                    "metricnames":  metric_names,
                    "timespan":     timespan,
                    "interval":     "PT1H",
                    "aggregation":  "Average",
                },
                headers=hdrs,
                timeout=15,
            )
            pg_metrics = r.json().get("value", []) if r.ok else []
        except Exception:
            pg_metrics = []

        result["resources"]["postgresql"] = {
            "name":         pg_name,
            "sku":          sku,
            "storage_mb":   storage.get("storageSizeGB", 0) * 1024 if storage else 0,
            "storage_gb":   storage.get("storageSizeGB", 0),
            "tier":         sku.get("tier", "Unknown"),
            "metrics":      pg_metrics,
        }
        result["skus"]["postgresql"] = {
            "name":        sku.get("name", "Unknown"),
            "tier":        sku.get("tier", "Unknown"),
            # Free tier limits
            "max_storage_gb":     32 if sku.get("tier") == "Burstable" else 1024,
            "max_connections":    50  if sku.get("tier") == "Burstable" else 500,
            "free_compute_hours": 750,
        }

    # ── Function App ──────────────────────────────────────────────────────────
    func_name = _first_env("AZURE_FUNCTION_APP_NAME")
    if not func_name:
        func_name = _arm_list_first_name(
            base,
            hdrs,
            f"resourceGroups/{rg}/providers/Microsoft.Web/sites?api-version=2023-01-01",
        )
    if func_name:
        func_rid = (
            f"{base}/resourceGroups/{rg}"
            f"/providers/Microsoft.Web/sites/{func_name}"
        )
        try:
            r = requests.get(f"{func_rid}?api-version=2023-01-01", headers=hdrs, timeout=10)
            func_meta = r.json() if r.ok else {}
        except Exception:
            func_meta = {}

        metric_names = "FunctionExecutionCount,FunctionExecutionUnits,Http5xx,Http4xx,AverageResponseTime,MemoryWorkingSet"
        try:
            r = requests.get(
                f"{func_rid}/providers/microsoft.insights/metrics",
                params={
                    "api-version": "2018-01-01",
                    "metricnames": metric_names,
                    "timespan":    timespan,
                    "interval":    "PT1H",
                    "aggregation": "Total,Average",
                },
                headers=hdrs,
                timeout=15,
            )
            func_metrics = r.json().get("value", []) if r.ok else []
        except Exception:
            func_metrics = []

        result["resources"]["function_app"] = {
            "name":    func_name,
            "kind":    func_meta.get("kind", ""),
            "metrics": func_metrics,
        }
        result["skus"]["function_app"] = {
            "plan": "Consumption",
            "free_executions_per_month": 1_000_000,
            "free_gb_seconds_per_month": 400_000,
        }

    # ── Static Web App ────────────────────────────────────────────────────────
    swa_name = _first_env("AZURE_STATIC_WEB_APP_NAME")
    if not swa_name:
        swa_name = _arm_list_first_name(
            base,
            hdrs,
            f"resourceGroups/{rg}/providers/Microsoft.Web/staticSites?api-version=2023-01-01",
        )
    if swa_name:
        swa_rid = (
            f"{base}/resourceGroups/{rg}"
            f"/providers/Microsoft.Web/staticSites/{swa_name}"
        )
        try:
            r = requests.get(f"{swa_rid}?api-version=2023-01-01", headers=hdrs, timeout=10)
            swa_meta = r.json() if r.ok else {}
            swa_sku = swa_meta.get("sku", {})
        except Exception:
            swa_sku = {}

        # SWA valid metrics: BytesSent, SiteHits, SiteErrors, CdnRequestCount, CdnResponseSize, CdnTotalLatency
        swa_metric_names = "BytesSent,SiteHits,SiteErrors,CdnRequestCount,CdnResponseSize,CdnTotalLatency"
        try:
            r = requests.get(
                f"{swa_rid}/providers/microsoft.insights/metrics",
                params={
                    "api-version": "2018-01-01",
                    "metricnames": swa_metric_names,
                    "timespan":    monthly_timespan,
                    "interval":    "PT1H",
                    "aggregation": "Total,Average",
                },
                headers=hdrs,
                timeout=15,
            )
            swa_metrics = r.json().get("value", []) if r.ok else []
        except Exception:
            swa_metrics = []

        result["resources"]["static_web_app"] = {
            "name":    swa_name,
            "sku":     swa_sku,
            "metrics": swa_metrics,
        }
        result["skus"]["static_web_app"] = {
            "tier":                  swa_sku.get("tier", "Free"),
            "free_bandwidth_gb":     100,
            "free_builds_per_month": 2,
        }

    # ── LexPlay Speech (Azure Cognitive Services – Speech) ─────────────────
    # Correct metric names verified from Azure Monitor API error response
    _cog_metrics = "TotalCalls,SuccessfulCalls,TotalErrors,BlockedCalls,Latency,SynthesizedCharacters,TotalTokenCalls"

    def _fetch_cog(name, env_var):
        res_name = _first_env(env_var) or name
        rid = f"{base}/resourceGroups/{rg}/providers/Microsoft.CognitiveServices/accounts/{res_name}"
        try:
            rm = requests.get(f"{rid}?api-version=2023-05-01", headers=hdrs, timeout=10)
            meta = rm.json() if rm.ok else {}
            meta_ok = rm.ok
        except Exception:
            meta = {}; meta_ok = False
        sku_raw = meta.get("sku", {})
        try:
            rr = requests.get(
                f"{rid}/providers/microsoft.insights/metrics",
                params={
                    "api-version": "2018-01-01",
                    "metricnames": _cog_metrics,
                    "timespan":    monthly_timespan,
                    "interval":    "PT1H",
                    "aggregation": "Total,Average",
                },
                headers=hdrs,
                timeout=15,
            )
            met = rr.json().get("value", []) if rr.ok else []
        except Exception:
            met = []
        is_free = sku_raw.get("name", "F0") in ("F0", "Free")
        return {
            "resource": {
                "name":    res_name,
                "kind":    meta.get("kind", "SpeechServices"),
                "sku":     sku_raw,
                "metrics": met,
                "meta_ok":    meta_ok,
            },
            "sku": {
                "name": sku_raw.get("name", "F0"),
                "tier": sku_raw.get("tier", "Free"),
                "is_free": is_free,
                "free_tts_chars_per_month":     500_000,
                "free_stt_hours_per_month":     5,
                "free_tts_audio_minutes_month": 30,
            },
        }

    sp = _fetch_cog("lexplayspeech",  "AZURE_LEXPLAYSPEECH_NAME")
    result["resources"]["lexplay_speech"]  = sp["resource"]
    result["skus"]["lexplay_speech"]       = sp["sku"]

    # ── LexPlay Audio18 (Azure Blob Storage – StorageV2) ─────────────────────
    audio18_name = _first_env("AZURE_LEXPLAYAUDIO18_NAME") or "lexplayaudio18"
    audio18_rid  = f"{base}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{audio18_name}"
    try:
        ra = requests.get(f"{audio18_rid}?api-version=2023-01-01", headers=hdrs, timeout=10)
        audio18_meta = ra.json() if ra.ok else {}
    except Exception:
        audio18_meta = {}
    audio18_sku_raw = audio18_meta.get("sku", {})

    # Account-level metrics (transactions, ingress, egress, latency, availability)
    try:
        r_acct = requests.get(
            f"{audio18_rid}/providers/microsoft.insights/metrics",
            params={
                "api-version": "2018-01-01",
                "metricnames": "Transactions,Ingress,Egress,SuccessServerLatency,Availability",
                "timespan":    timespan,
                "interval":    "PT1H",
                "aggregation": "Total,Average",
            },
            headers=hdrs,
            timeout=15,
        )
        audio18_acct_met = r_acct.json().get("value", []) if r_acct.ok else []
    except Exception:
        audio18_acct_met = []

    # Blob-service-level metrics (capacity, count, containers)
    try:
        r_blob = requests.get(
            f"{audio18_rid}/blobServices/default/providers/microsoft.insights/metrics",
            params={
                "api-version": "2018-01-01",
                "metricnames": "BlobCapacity,BlobCount,ContainerCount",
                "timespan":    timespan,
                "interval":    "PT1H",
                "aggregation": "Average",
            },
            headers=hdrs,
            timeout=15,
        )
        audio18_blob_met = r_blob.json().get("value", []) if r_blob.ok else []
    except Exception:
        audio18_blob_met = []

    result["resources"]["lexplay_audio18"] = {
        "name":    audio18_name,
        "kind":    audio18_meta.get("kind", "StorageV2"),
        "sku":     audio18_sku_raw,
        "metrics": audio18_acct_met + audio18_blob_met,
    }
    result["skus"]["lexplay_audio18"] = {
        "name":               audio18_sku_raw.get("name", "Standard_LRS"),
        "tier":               audio18_sku_raw.get("tier", "Standard"),
        "kind":               audio18_meta.get("kind", "StorageV2"),
        "free_storage_gb":    5,
        "hot_per_gb_usd":     0.018,
        "free_egress_gb":     100,
    }

    # ── Cost Management ───────────────────────────────────────────────────────
    billing_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    days_elapsed  = now.day
    # last day of current month
    next_month    = (billing_start + timedelta(days=32)).replace(day=1)
    billing_end   = next_month - timedelta(days=1)
    days_in_month = billing_end.day

    try:
        r = requests.post(
            f"{base}/providers/Microsoft.CostManagement/query?api-version=2023-11-01",
            headers=hdrs,
            json={
                "type":       "ActualCost",
                "timeframe":  "Custom",
                "timePeriod": {
                    "from": billing_start.strftime("%Y-%m-%dT00:00:00Z"),
                    "to":   now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
                "dataset": {
                    "granularity": "Daily",
                    "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
                    "grouping": [{"type": "Dimension", "name": "ServiceName"}],
                },
            },
            timeout=20,
        )
        cost_data = r.json() if r.ok else {"error": r.text[:300]}
    except Exception as exc:
        cost_data = {"error": str(exc)}

    result["cost"] = cost_data
    result["billing"] = {
        "period_start":  billing_start.strftime("%Y-%m-%d"),
        "period_end":    billing_end.strftime("%Y-%m-%d"),
        "days_elapsed":  days_elapsed,
        "days_in_month": days_in_month,
        "days_remaining": days_in_month - days_elapsed,
    }

    return _json(result)


# ── OBSERVATIONS ──────────────────────────────────────────────────────────────

def _ensure_obs_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_observations (
            id              SERIAL PRIMARY KEY,
            resource        VARCHAR(100)  NOT NULL DEFAULT 'general',
            body            TEXT          NOT NULL,
            author_clerk_id VARCHAR(100),
            created_at      TIMESTAMPTZ   DEFAULT NOW()
        )
    """)


@admin_bp.route(route="ops/observations", methods=["GET"])
def admin_get_observations(req: func.HttpRequest) -> func.HttpResponse:
    _, err = _check_admin(req)
    if err:
        return err

    resource = req.params.get("resource", "general")
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _ensure_obs_table(cur)
            conn.commit()
            cur.execute(
                "SELECT id, resource, body, author_clerk_id, created_at"
                " FROM admin_observations WHERE resource = %s ORDER BY created_at DESC LIMIT 50",
                (resource,),
            )
            rows = [dict(r) for r in cur.fetchall()]
        return _json(rows)
    except Exception as exc:
        logging.error("observations GET: %s", exc)
        conn.rollback()
        return _json({"error": str(exc)}, 500)
    finally:
        put_db_connection(conn)


@admin_bp.route(route="ops/observations", methods=["POST"])
def admin_post_observation(req: func.HttpRequest) -> func.HttpResponse:
    clerk_id, err = _check_admin(req)
    if err:
        return err

    try:
        body = req.get_json()
    except Exception:
        return _json({"error": "Invalid JSON"}, 400)

    resource = (body.get("resource") or "general").strip()
    text     = (body.get("body") or "").strip()
    if not text:
        return _json({"error": "body is required"}, 400)

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _ensure_obs_table(cur)
            cur.execute(
                "INSERT INTO admin_observations (resource, body, author_clerk_id)"
                " VALUES (%s, %s, %s) RETURNING id, created_at",
                (resource, text, clerk_id),
            )
            row = cur.fetchone()
            conn.commit()
        return _json({"ok": True, "id": row["id"], "created_at": row["created_at"]})
    except Exception as exc:
        logging.error("observations POST: %s", exc)
        conn.rollback()
        return _json({"error": str(exc)}, 500)
    finally:
        put_db_connection(conn)


@admin_bp.route(route="ops/observations/{obs_id}", methods=["DELETE"])
def admin_delete_observation(req: func.HttpRequest) -> func.HttpResponse:
    _, err = _check_admin(req)
    if err:
        return err

    obs_id = req.route_params.get("obs_id")
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM admin_observations WHERE id = %s", (obs_id,))
            conn.commit()
        return _json({"ok": True})
    except Exception as exc:
        conn.rollback()
        return _json({"error": str(exc)}, 500)
    finally:
        put_db_connection(conn)
