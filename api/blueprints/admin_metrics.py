"""
Admin metrics and observations routes.

All routes require is_admin=true in the users table.
"""
import logging
from datetime import datetime, timedelta, timezone

import azure.functions as func
import requests
from psycopg2.extras import RealDictCursor

from db_pool import get_db_connection, put_db_connection
from utils.admin_helpers import (
    _json,
    _first_env,
    _arm_list_first_name,
    _get_azure_token,
    _resolve_resource_group,
    _resolve_subscription_id,
)
from blueprints.admin import _check_admin

metrics_bp = func.Blueprint()


# ── AZURE METRICS ─────────────────────────────────────────────────────────────

@metrics_bp.route(route="ops/azure-metrics", methods=["GET"])
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

    # ── LexPlay Speech (Azure Cognitive Services – Speech) ───────────────────
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
                "meta_ok": meta_ok,
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

    sp = _fetch_cog("lexplayspeech", "AZURE_LEXPLAYSPEECH_NAME")
    result["resources"]["lexplay_speech"] = sp["resource"]
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
        if r.ok:
            cost_data = r.json()
        else:
            try:
                err_body = r.json()
                err_msg = (err_body.get("error") or {}).get("message") or f"HTTP {r.status_code}"
            except Exception:
                err_msg = r.text[:200] or f"HTTP {r.status_code}"
            cost_data = {"error": f"Azure Cost API ({r.status_code}): {err_msg}"}
    except Exception as exc:
        cost_data = {"error": str(exc)}

    result["cost"] = cost_data
    result["billing"] = {
        "period_start":   billing_start.strftime("%Y-%m-%d"),
        "period_end":     billing_end.strftime("%Y-%m-%d"),
        "days_elapsed":   days_elapsed,
        "days_in_month":  days_in_month,
        "days_remaining": days_in_month - days_elapsed,
    }

    return _json(result)


# ── OBSERVATIONS ──────────────────────────────────────────────────────────────

def _ensure_obs_table(cur) -> None:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_observations (
            id              SERIAL PRIMARY KEY,
            resource        VARCHAR(100)  NOT NULL DEFAULT 'general',
            body            TEXT          NOT NULL,
            author_clerk_id VARCHAR(100),
            created_at      TIMESTAMPTZ   DEFAULT NOW()
        )
    """)


@metrics_bp.route(route="ops/observations", methods=["GET"])
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


@metrics_bp.route(route="ops/observations", methods=["POST"])
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


@metrics_bp.route(route="ops/observations/{obs_id}", methods=["DELETE"])
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
