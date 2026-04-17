
import os
import json
import psycopg2
from pathlib import Path

def get_repo_root() -> Path:
    """Returns the root LexMatePH V3 directory."""
    return Path(__file__).resolve().parents[2]

def get_lexcode_root() -> Path:
    """Returns the LexCode directory."""
    return Path(__file__).resolve().parents[1]

def get_db_connection():
    """Returns a psycopg2 connection using local.settings.json or Environment Variables."""
    conn_str = os.environ.get("DB_CONNECTION_STRING", "").strip()
    if conn_str:
        return psycopg2.connect(conn_str)
    
    root = get_repo_root()
    # Try both common locations for local.settings.json
    for p in [root / "api" / "local.settings.json", root / "local.settings.json"]:
        if p.exists():
            try:
                with open(p, encoding="utf-8") as f:
                    settings = json.load(f)
                    return psycopg2.connect(settings['Values']['DB_CONNECTION_STRING'])
            except Exception:
                continue
    
    # Final hardcoded fallback for local development if all else fails
    fallback = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@127.0.0.1:5432/lexmateph-ea-db"
    return psycopg2.connect(fallback)

def resolve_codal_path(relative_path: str) -> Path:
    """Resolves a path relative to LexCode/Codals."""
    return get_lexcode_root() / "Codals" / relative_path
