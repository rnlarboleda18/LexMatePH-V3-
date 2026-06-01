"""
Shared helpers for admin blueprints.

Deliberately has NO imports of get_db_connection / get_authenticated_user_id so
that these helpers are freely importable without pulling in the DB pool at module
load time.  Route-level auth/DB work stays in each blueprint.
"""
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import azure.functions as func
import requests

import config

# ── CORS / response helper ────────────────────────────────────────────────────

_FRONTEND_ORIGIN = config.FRONTEND_URL


def _json(data, status: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(data, default=str),
        mimetype="application/json",
        status_code=status,
        headers={"Access-Control-Allow-Origin": _FRONTEND_ORIGIN},
    )


# ── Host detection ────────────────────────────────────────────────────────────

def _running_on_azure_host() -> bool:
    """True when Functions runs in Azure (not local Core Tools)."""
    return bool(os.getenv("WEBSITE_INSTANCE_ID") or os.getenv("WEBSITE_SITE_NAME"))


def _mirror_restore_enabled() -> bool:
    """Admin backup can pg_restore into LOCAL_DB when configured and API runs on a dev machine."""
    from config import LOCAL_DB_CONNECTION_STRING  # noqa: PLC0415

    if _running_on_azure_host():
        return False
    return bool((LOCAL_DB_CONNECTION_STRING or "").strip())


# ── Pipeline path helpers ─────────────────────────────────────────────────────

def _pipeline_scripts_root() -> Path:
    """Full repo locally (scripts/ sibling to api/); bundled ``api/`` wwwroot on Azure SWA."""
    api_dir = Path(__file__).resolve().parent.parent
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
    # wwwroot is read-only on Azure; /tmp is always writable on all Azure compute tiers
    if _running_on_azure_host():
        tmp = Path(os.environ.get("TEMP") or os.environ.get("TMP") or "/tmp")
        return tmp / "pipeline_runtime" / "case-digest-pipeline"
    return root / "pipeline_runtime" / "case-digest-pipeline"


_SCAN_RESULTS_PATH = _case_digest_pipeline_store() / "scan_results.json"
_GAP_RESULTS_PATH  = _case_digest_pipeline_store() / "gap_results.json"


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


def _repo_root() -> Path:
    """Filesystem root used for bundled pipeline subprocesses (matches _pipeline_scripts_root)."""
    return _pipeline_scripts_root()


# ── Azure auth / resource resolution ─────────────────────────────────────────

def _get_azure_token() -> Optional[str]:
    """Obtain an Azure management-plane bearer token.
    Tries managed identity first (works when deployed on Azure),
    then falls back to service-principal env vars, then Azure CLI.
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
                [az, "account", "get-access-token",
                 "--resource", "https://management.azure.com/",
                 "--query", "accessToken", "-o", "tsv"],
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=8,
            ).strip()
            if token:
                return token
        except Exception:
            pass

    return None


def _first_env(*names: str) -> Optional[str]:
    for name in names:
        val = (os.environ.get(name) or "").strip()
        if val:
            return val
    return None


def _az_cli_tsv(args) -> Optional[str]:
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


def _resolve_subscription_id() -> Optional[str]:
    return _first_env("AZURE_SUBSCRIPTION_ID", "AZURE_SUBSCRIPTION") or _az_cli_tsv(
        ["account", "show", "--query", "id", "-o", "tsv"]
    )


def _resolve_resource_group() -> Optional[str]:
    rg = _first_env("AZURE_RESOURCE_GROUP", "AZURE_POSTGRES_RG")
    if rg:
        return rg
    exists = _az_cli_tsv(["group", "exists", "--name", "LexMatePH"])
    return "LexMatePH" if exists == "true" else None


def _arm_list_first_name(base_url: str, headers: dict, provider_path: str) -> Optional[str]:
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
