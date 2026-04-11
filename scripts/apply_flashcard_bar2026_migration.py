"""Apply sql/flashcard_bar2026_migration.sql to DB (uses DB_CONNECTION_STRING or api/local.settings.json)."""
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_API = _ROOT / "api"


def main() -> None:
    cs = os.environ.get("DB_CONNECTION_STRING", "").strip()
    if not cs and (_API / "local.settings.json").is_file():
        data = json.loads((_API / "local.settings.json").read_text(encoding="utf-8"))
        cs = (data.get("Values") or {}).get("DB_CONNECTION_STRING", "").strip()
    if not cs:
        print("No DB_CONNECTION_STRING", file=sys.stderr)
        sys.exit(1)
    if ":5432/" in cs:
        cs = cs.replace(":5432/", ":5432/")
    import psycopg2

    stmts = [
        """ALTER TABLE flashcard_concepts
  ADD COLUMN IF NOT EXISTS bar_2026_aligned boolean NULL""",
        """ALTER TABLE flashcard_concepts
  ADD COLUMN IF NOT EXISTS bar_2026_labeled_at timestamptz NULL""",
        """COMMENT ON COLUMN flashcard_concepts.bar_2026_aligned IS
  'True if concept is aligned with 2026 Bar syllabi (Gemini batch labeler). NULL = not labeled yet.'""",
        """CREATE INDEX IF NOT EXISTS idx_flashcard_concepts_bar_2026_aligned
  ON flashcard_concepts (bar_2026_aligned)
  WHERE bar_2026_aligned IS NOT NULL""",
    ]
    conn = psycopg2.connect(cs, connect_timeout=120)
    conn.autocommit = True
    cur = conn.cursor()
    for s in stmts:
        cur.execute(s)
    cur.close()
    conn.close()
    print("Applied flashcard_bar2026_migration.sql")


if __name__ == "__main__":
    main()
