"""
Admin backup routes.

Provides pg_dump cloud backup (custom format) with optional pg_restore into a
local PostgreSQL mirror.  All routes require is_admin=true in the users table.
"""
import logging
import os
import shutil
import subprocess
import tempfile
import threading
import uuid
from datetime import datetime, timezone

import azure.functions as func

from db_pool import get_db_connection, put_db_connection
from utils.admin_helpers import _json, _mirror_restore_enabled, _running_on_azure_host

# Deferred import: blueprints.admin defines _check_admin which itself imports
# get_authenticated_user_id and get_db_connection.  Importing at module level is
# safe because function_app.py loads admin.py before admin_backup.py.
from blueprints.admin import _check_admin

backup_bp = func.Blueprint()

# ── In-memory backup job store ────────────────────────────────────────────────
# Persists within a single Azure Functions worker lifetime.
_backup_jobs: dict = {}
_backup_lock = threading.Lock()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run_pg_restore_mirror(job_id: str, dump_path: str, local_uri: str) -> None:
    """Restore custom-format dump into local Postgres."""
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


def _run_pg_dump_backup(job_id: str) -> None:
    """Background thread: pg_dump cloud DB (-Fc), optional pg_restore to LOCAL_DB, then expose dump for download."""
    tmp_path = None
    try:
        from config import DB_CONNECTION_STRING, LOCAL_DB_CONNECTION_STRING  # noqa: PLC0415

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
        proc = subprocess.run(cmd, capture_output=True, timeout=7200, text=False)
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

        finished: dict = {
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
            job_id, len(dump_bytes), mirror_restored,
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


# ── Routes ────────────────────────────────────────────────────────────────────

@backup_bp.route(route="ops/backup/start", methods=["POST"])
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


@backup_bp.route(route="ops/backup/status", methods=["GET"])
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


@backup_bp.route(route="ops/backup/download", methods=["GET"])
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
