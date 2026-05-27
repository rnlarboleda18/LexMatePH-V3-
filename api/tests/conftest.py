import sys
import os
import json
import pytest
from unittest.mock import MagicMock

# Make api/ the root so imports like `from blueprints.xendit import ...` resolve.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import azure.functions as func


@pytest.fixture
def make_request():
    """Factory for fake Azure HttpRequest objects."""
    def _factory(method="POST", body=None, headers=None, params=None, route_params=None):
        if body is None:
            body = b""
        elif isinstance(body, dict):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        return func.HttpRequest(
            method=method,
            url="https://test.example.com/api/test",
            headers=headers or {},
            params=params or {},
            route_params=route_params or {},
            body=body,
        )
    return _factory


@pytest.fixture
def mock_conn():
    """
    Returns (conn, cur) MagicMocks that behave as psycopg context managers.

    conn.__enter__ returns conn itself so `with psycopg.connect(...) as conn:`
    and `with _get_db() as conn:` both give back the same mock object.
    """
    conn = MagicMock()
    cur = MagicMock()

    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)

    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)

    conn.cursor.return_value = cur

    # conn.transaction() must also be a context manager
    txn = MagicMock()
    txn.__enter__ = MagicMock(return_value=txn)
    txn.__exit__ = MagicMock(return_value=False)
    conn.transaction.return_value = txn

    return conn, cur
