"""
Tests for admin blueprints.

Covers:
  _check_admin gate — 401 (unauthenticated), 403 (not admin), passes for admin
  admin_db_stats  — 401 / 403 / 200 with expected response shape
  admin_backup_*  — start creates job (200), status 404 for unknown job,
                    download 404 when not ready
  admin_get_observations  — 401 / 200 list
  admin_post_observation  — 401 / 400 (missing body text) / 200
  admin_delete_observation — 401 / 200

Mocking strategy
  * blueprints.admin.get_authenticated_user_id — controls auth for _check_admin
  * blueprints.admin.get_db_connection / put_db_connection — admin gate DB calls
  * blueprints.admin_backup.threading — prevents real subprocess thread from spawning
  * blueprints.admin_metrics.get_db_connection / put_db_connection — observation route DB calls
  * psycopg2-style mock: conn.cursor(...) returns a context manager whose
    __enter__ gives back a cursor MagicMock.
"""
import json
import sys
import os
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from blueprints.admin import (
    admin_db_stats,
)
from blueprints.admin_backup import (
    admin_backup_start,
    admin_backup_status,
    admin_backup_download,
)
from blueprints.admin_metrics import (
    admin_get_observations,
    admin_post_observation,
    admin_delete_observation,
)


# ── psycopg2 mock helpers ──────────────────────────────────────────────────────

def _psycopg2_conn(fetchone_values=None, fetchall_value=None):
    """Build a psycopg2-style (conn, cur) mock pair.

    conn.cursor(...) returns a context manager whose __enter__ gives back `cur`.
    fetchone_values: single dict  → every fetchone() returns it
                     list of dicts → side_effect (one per call)
    fetchall_value:  list returned by fetchall()
    """
    conn = MagicMock()
    cur = MagicMock()
    cur_cm = MagicMock()
    cur_cm.__enter__ = MagicMock(return_value=cur)
    cur_cm.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cur_cm

    if isinstance(fetchone_values, list):
        cur.fetchone.side_effect = fetchone_values
    elif fetchone_values is not None:
        cur.fetchone.return_value = fetchone_values

    cur.fetchall.return_value = fetchall_value if fetchall_value is not None else []
    return conn, cur


def _admin_check_conn():
    """DB connection whose is_admin query returns True."""
    conn, _ = _psycopg2_conn(fetchone_values={"is_admin": True})
    return conn


def _non_admin_check_conn():
    """DB connection whose is_admin query returns False."""
    conn, _ = _psycopg2_conn(fetchone_values={"is_admin": False})
    return conn


def _stats_db_conn():
    """DB connection wired for all five admin_db_stats fetchone() calls."""
    conn, _ = _psycopg2_conn(
        fetchone_values=[
            {"db_size": "42 MB", "db_size_bytes": 44040192},
            {"cache_hit_ratio": 99.1},
            {"active": 3, "max_conn": 100},
            {"index_hit_ratio": 98.5},
            {"total_txn": 5000},
        ],
        fetchall_value=[],  # tables list
    )
    return conn


# ── Shared constants ───────────────────────────────────────────────────────────

_AUTH = {"Authorization": "Bearer fake-token"}
_AUTHED = ("user_admin", None)
_UNAUTHED = (None, "Missing Authorization Header")


# ── admin_db_stats ─────────────────────────────────────────────────────────────

def test_db_stats_returns_401_when_unauthenticated(make_request):
    req = make_request(method="GET")
    with patch("blueprints.admin.get_authenticated_user_id", return_value=_UNAUTHED):
        resp = admin_db_stats(req)
    assert resp.status_code == 401


def test_db_stats_returns_403_when_not_admin(make_request):
    req = make_request(method="GET", headers=_AUTH)
    with patch("blueprints.admin.get_authenticated_user_id", return_value=_AUTHED), \
         patch("blueprints.admin.get_db_connection", return_value=_non_admin_check_conn()), \
         patch("blueprints.admin.put_db_connection"):
        resp = admin_db_stats(req)
    assert resp.status_code == 403


def test_db_stats_returns_200_with_expected_keys(make_request):
    req = make_request(method="GET", headers=_AUTH)
    with patch("blueprints.admin.get_authenticated_user_id", return_value=_AUTHED), \
         patch("blueprints.admin.get_db_connection",
               side_effect=[_admin_check_conn(), _stats_db_conn()]), \
         patch("blueprints.admin.put_db_connection"):
        resp = admin_db_stats(req)
    assert resp.status_code == 200
    body = json.loads(resp.get_body())
    for key in ("db_size", "db_size_bytes", "cache_hit_ratio",
                "index_hit_ratio", "active_connections", "tables"):
        assert key in body, f"Expected key '{key}' missing from response"


# ── admin_backup_start ────────────────────────────────────────────────────────

def test_backup_start_returns_401_when_unauthenticated(make_request):
    req = make_request(method="POST")
    with patch("blueprints.admin.get_authenticated_user_id", return_value=_UNAUTHED):
        resp = admin_backup_start(req)
    assert resp.status_code == 401


def test_backup_start_returns_403_when_not_admin(make_request):
    req = make_request(method="POST", headers=_AUTH)
    with patch("blueprints.admin.get_authenticated_user_id", return_value=_AUTHED), \
         patch("blueprints.admin.get_db_connection", return_value=_non_admin_check_conn()), \
         patch("blueprints.admin.put_db_connection"):
        resp = admin_backup_start(req)
    assert resp.status_code == 403


def test_backup_start_creates_job_and_returns_job_id(make_request):
    req = make_request(method="POST", headers=_AUTH)
    with patch("blueprints.admin.get_authenticated_user_id", return_value=_AUTHED), \
         patch("blueprints.admin.get_db_connection", return_value=_admin_check_conn()), \
         patch("blueprints.admin.put_db_connection"), \
         patch("blueprints.admin_backup.threading.Thread") as mock_thread:
        mock_thread.return_value.start = MagicMock()
        resp = admin_backup_start(req)
    assert resp.status_code == 200
    body = json.loads(resp.get_body())
    assert "job_id" in body
    assert len(body["job_id"]) == 8  # uuid4 first 8 chars


# ── admin_backup_status ───────────────────────────────────────────────────────

def test_backup_status_returns_401_when_unauthenticated(make_request):
    req = make_request(method="GET", params={"job_id": "abc"})
    with patch("blueprints.admin.get_authenticated_user_id", return_value=_UNAUTHED):
        resp = admin_backup_status(req)
    assert resp.status_code == 401


def test_backup_status_returns_404_for_unknown_job(make_request):
    req = make_request(method="GET", headers=_AUTH, params={"job_id": "no-such-job"})
    with patch("blueprints.admin.get_authenticated_user_id", return_value=_AUTHED), \
         patch("blueprints.admin.get_db_connection", return_value=_admin_check_conn()), \
         patch("blueprints.admin.put_db_connection"):
        resp = admin_backup_status(req)
    assert resp.status_code == 404


def test_backup_status_returns_200_for_known_job(make_request):
    """Inject a job directly into _backup_jobs so cross-test state doesn't interfere."""
    from blueprints.admin_backup import _backup_jobs, _backup_lock

    job_id = "testjob1"
    with _backup_lock:
        _backup_jobs[job_id] = {"status": "running", "pct": 10}

    try:
        req = make_request(method="GET", headers=_AUTH, params={"job_id": job_id})
        with patch("blueprints.admin.get_authenticated_user_id", return_value=_AUTHED), \
             patch("blueprints.admin.get_db_connection", return_value=_admin_check_conn()), \
             patch("blueprints.admin.put_db_connection"):
            resp = admin_backup_status(req)
        assert resp.status_code == 200
        body = json.loads(resp.get_body())
        assert body["status"] == "running"
    finally:
        with _backup_lock:
            _backup_jobs.pop(job_id, None)


# ── admin_backup_download ─────────────────────────────────────────────────────

def test_backup_download_returns_404_when_job_not_ready(make_request):
    req = make_request(method="GET", headers=_AUTH, params={"job_id": "not-real"})
    with patch("blueprints.admin.get_authenticated_user_id", return_value=_AUTHED), \
         patch("blueprints.admin.get_db_connection", return_value=_admin_check_conn()), \
         patch("blueprints.admin.put_db_connection"):
        resp = admin_backup_download(req)
    assert resp.status_code == 404


# ── admin_get_observations ────────────────────────────────────────────────────

def test_get_observations_returns_401_when_unauthenticated(make_request):
    req = make_request(method="GET")
    with patch("blueprints.admin.get_authenticated_user_id", return_value=_UNAUTHED):
        resp = admin_get_observations(req)
    assert resp.status_code == 401


def test_get_observations_returns_list(make_request):
    req = make_request(method="GET", headers=_AUTH, params={"resource": "general"})
    obs_conn, _ = _psycopg2_conn(fetchall_value=[])
    with patch("blueprints.admin.get_authenticated_user_id", return_value=_AUTHED), \
         patch("blueprints.admin.get_db_connection", return_value=_admin_check_conn()), \
         patch("blueprints.admin.put_db_connection"), \
         patch("blueprints.admin_metrics.get_db_connection", return_value=obs_conn), \
         patch("blueprints.admin_metrics.put_db_connection"):
        resp = admin_get_observations(req)
    assert resp.status_code == 200
    assert isinstance(json.loads(resp.get_body()), list)


# ── admin_post_observation ────────────────────────────────────────────────────

def test_post_observation_returns_401_when_unauthenticated(make_request):
    req = make_request(method="POST", body={"resource": "general", "body": "Note"})
    with patch("blueprints.admin.get_authenticated_user_id", return_value=_UNAUTHED):
        resp = admin_post_observation(req)
    assert resp.status_code == 401


def test_post_observation_returns_400_when_body_text_missing(make_request):
    req = make_request(method="POST", headers=_AUTH, body={"resource": "general"})
    with patch("blueprints.admin.get_authenticated_user_id", return_value=_AUTHED), \
         patch("blueprints.admin.get_db_connection", return_value=_admin_check_conn()), \
         patch("blueprints.admin.put_db_connection"):
        resp = admin_post_observation(req)
    assert resp.status_code == 400
    assert "body is required" in json.loads(resp.get_body())["error"]


def test_post_observation_creates_record(make_request):
    req = make_request(method="POST", headers=_AUTH,
                       body={"resource": "general", "body": "Test observation"})
    obs_conn, _ = _psycopg2_conn(
        fetchone_values={"id": 7, "created_at": "2026-05-27T00:00:00+00:00"}
    )
    with patch("blueprints.admin.get_authenticated_user_id", return_value=_AUTHED), \
         patch("blueprints.admin.get_db_connection", return_value=_admin_check_conn()), \
         patch("blueprints.admin.put_db_connection"), \
         patch("blueprints.admin_metrics.get_db_connection", return_value=obs_conn), \
         patch("blueprints.admin_metrics.put_db_connection"):
        resp = admin_post_observation(req)
    assert resp.status_code == 200
    body = json.loads(resp.get_body())
    assert body["ok"] is True
    assert body["id"] == 7


# ── admin_delete_observation ──────────────────────────────────────────────────

def test_delete_observation_returns_401_when_unauthenticated(make_request):
    req = make_request(method="DELETE", route_params={"obs_id": "5"})
    with patch("blueprints.admin.get_authenticated_user_id", return_value=_UNAUTHED):
        resp = admin_delete_observation(req)
    assert resp.status_code == 401


def test_delete_observation_returns_200(make_request):
    req = make_request(method="DELETE", headers=_AUTH, route_params={"obs_id": "5"})
    del_conn, _ = _psycopg2_conn()
    with patch("blueprints.admin.get_authenticated_user_id", return_value=_AUTHED), \
         patch("blueprints.admin.get_db_connection", return_value=_admin_check_conn()), \
         patch("blueprints.admin.put_db_connection"), \
         patch("blueprints.admin_metrics.get_db_connection", return_value=del_conn), \
         patch("blueprints.admin_metrics.put_db_connection"):
        resp = admin_delete_observation(req)
    assert resp.status_code == 200
    assert json.loads(resp.get_body())["ok"] is True
