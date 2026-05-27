"""
Admin-only Azure Functions blueprint.

This module contains only the core admin gate (_check_admin) and the
db-stats route.  All other admin routes have been extracted into:
  - blueprints/admin_backup.py    (pg_dump backup)
  - blueprints/admin_pipeline.py  (digest pipeline, eLib scan, gap scan)
  - blueprints/admin_metrics.py   (Azure metrics, observations)

_check_admin is deliberately kept here (not in utils/) so that every
existing test patch target — `patch("blueprints.admin.get_authenticated_user_id")`
and `patch("blueprints.admin.get_db_connection")` — continues to work
regardless of which blueprint's route calls _check_admin.
"""
import logging

import azure.functions as func
import psycopg2
from psycopg2.extras import RealDictCursor

from db_pool import get_db_connection, put_db_connection
from utils.admin_helpers import _json
from utils.clerk_auth import get_authenticated_user_id

admin_bp = func.Blueprint()


# ── Admin gate ────────────────────────────────────────────────────────────────

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


# ── DB STATS ──────────────────────────────────────────────────────────────────

@admin_bp.route(route="ops/db-stats", methods=["GET"])
def admin_db_stats(req: func.HttpRequest) -> func.HttpResponse:
    """Return PostgreSQL database health metrics: size, cache/index hit ratios, connections, table stats."""
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
