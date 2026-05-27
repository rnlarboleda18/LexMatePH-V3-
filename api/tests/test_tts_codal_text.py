"""
Regression tests for _get_text_for_codal() in blueprints/audio_provider.py.

These tests guard against text-generation regressions while the function is
being split into per-codal helpers (T6.5).  They test *output shape* —
non-empty string, expected keywords present, no crashes — rather than exact
wording, so cosmetic text changes don't break them.

Mocking strategy:
  * blueprints.audio_provider.get_db_connection  — psycopg2-style pool
  * blueprints.audio_provider.put_db_connection  — no-op release
  * blueprints.audio_provider.get_codal_boundaries — avoids a second DB call;
      returns an empty boundary map so no structural headers are prepended.
      This does NOT affect whether the function works — it just means the first
      article of a new Book/Title will not announce the structural label, which
      is fine for a unit test.

DB row format mirrors psycopg2 RealDictCursor (plain dict with column keys).
"""
import sys
import os
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from blueprints.audio_provider import _get_text_for_codal


# ── Helpers ───────────────────────────────────────────────────────────────────

_EMPTY_BOUNDS = {
    "book_start": {},
    "title_start_book_num": {},
    "title_label": {},
    "chapter_start": {},
    "section_start": {},
}


def _mock_db(fetchone_value):
    """Return (conn, cur) where cur.fetchone() returns fetchone_value."""
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    cur.fetchone.return_value = fetchone_value
    return conn, cur


# ── Civil Code ────────────────────────────────────────────────────────────────

def test_civil_code_article_returns_non_empty_text():
    """Basic Civil Code article: returned text is a non-empty string with no error."""
    conn, cur = _mock_db({
        "id": "aaaa-1111",
        "article_num": "1",
        "article_title": "Effect and Application of Laws",
        "content_md": "Laws shall take effect after fifteen days following the completion of their publication.",
        "book": 1, "book_label": "Preliminary Title",
        "title_num": 1, "title_label": "Effect and Application of Laws",
        "chapter_num": None, "chapter_label": None, "section_label": None,
    })
    with patch("blueprints.audio_provider.get_db_connection", return_value=conn), \
         patch("blueprints.audio_provider.put_db_connection"), \
         patch("blueprints.audio_provider.get_codal_boundaries", return_value=_EMPTY_BOUNDS):
        text, err = _get_text_for_codal("1", code_id="civ")

    assert err is None
    assert isinstance(text, str)
    assert len(text) > 0


def test_civil_code_article_includes_article_number_in_text():
    """The article number must appear in the generated TTS text."""
    conn, cur = _mock_db({
        "id": "aaaa-2222",
        "article_num": "19",
        "article_title": "Abuse of Rights",
        "content_md": "Every person must, in the exercise of his rights and in the performance of his duties, act with justice.",
        "book": None, "book_label": None,
        "title_num": None, "title_label": None,
        "chapter_num": None, "chapter_label": None, "section_label": None,
    })
    with patch("blueprints.audio_provider.get_db_connection", return_value=conn), \
         patch("blueprints.audio_provider.put_db_connection"), \
         patch("blueprints.audio_provider.get_codal_boundaries", return_value=_EMPTY_BOUNDS):
        text, err = _get_text_for_codal("19", code_id="civ")

    assert err is None
    assert "19" in text


# ── Revised Penal Code ────────────────────────────────────────────────────────

def test_rpc_article_returns_non_empty_text():
    """RPC article: returned text is a non-empty string with no error."""
    conn, cur = _mock_db({
        "id": "bbbb-1111",
        "article_num": "1",
        "article_title": "Time when Act Takes Effect",
        "content_md": "This Code shall take effect on the first day of January, nineteen hundred and thirty-two.",
        "book": "One", "book_label": "General Principles Regarding Crimes",
        "title_num": 1, "title_label": "Felonies and Circumstances which Affect Criminal Liability",
        "chapter_label": None, "section_label": None,
    })
    with patch("blueprints.audio_provider.get_db_connection", return_value=conn), \
         patch("blueprints.audio_provider.put_db_connection"), \
         patch("blueprints.audio_provider.get_codal_boundaries", return_value=_EMPTY_BOUNDS):
        text, err = _get_text_for_codal("1", code_id="rpc")

    assert err is None
    assert isinstance(text, str)
    assert len(text) > 0


# ── Revised Corporation Code ──────────────────────────────────────────────────

def test_rcc_article_returns_non_empty_text():
    """RCC article: no crash, non-empty text."""
    conn, cur = _mock_db({
        "id": "cccc-1111",
        "article_num": "1",
        "article_title": "Title of the Code",
        "content_md": "This Code shall be known as the Revised Corporation Code of the Philippines.",
        "book": None, "book_label": None,
        "title_num": None, "title_label": None,
        "chapter_num": None, "chapter_label": None, "section_label": None,
    })
    with patch("blueprints.audio_provider.get_db_connection", return_value=conn), \
         patch("blueprints.audio_provider.put_db_connection"), \
         patch("blueprints.audio_provider.get_codal_boundaries", return_value=_EMPTY_BOUNDS):
        text, err = _get_text_for_codal("1", code_id="rcc")

    assert err is None
    assert isinstance(text, str)
    assert len(text) > 0


# ── Labor Code ────────────────────────────────────────────────────────────────

def test_labor_code_article_returns_non_empty_text():
    conn, cur = _mock_db({
        "id": "dddd-1111",
        "article_num": "1",
        "article_title": "Name of Decree",
        "content_md": "This Decree shall be known as the Labor Code of the Philippines.",
        "book": 1, "book_label": "Pre-Employment",
        "title_num": 1, "title_label": "Recruitment and Placement of Workers",
        "chapter_num": 1, "chapter_label": "General Provisions",
    })
    with patch("blueprints.audio_provider.get_db_connection", return_value=conn), \
         patch("blueprints.audio_provider.put_db_connection"), \
         patch("blueprints.audio_provider.get_codal_boundaries", return_value=_EMPTY_BOUNDS):
        text, err = _get_text_for_codal("1", code_id="labor")

    assert err is None
    assert isinstance(text, str)
    assert len(text) > 0


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_article_with_empty_body_does_not_crash():
    """An article with no body text should return a text string (just the header), not crash."""
    conn, cur = _mock_db({
        "id": "eeee-1111",
        "article_num": "999",
        "article_title": "Some Article Title",
        "content_md": "",
        "book": None, "book_label": None,
        "title_num": None, "title_label": None,
        "chapter_num": None, "chapter_label": None, "section_label": None,
    })
    with patch("blueprints.audio_provider.get_db_connection", return_value=conn), \
         patch("blueprints.audio_provider.put_db_connection"), \
         patch("blueprints.audio_provider.get_codal_boundaries", return_value=_EMPTY_BOUNDS):
        text, err = _get_text_for_codal("999", code_id="civ")

    assert err is None
    assert isinstance(text, str)


def test_article_not_found_returns_none_with_error_string():
    """When no row is found for a given content_id, returns (None, error_str)."""
    conn, cur = _mock_db(None)  # fetchone returns None → article not found
    with patch("blueprints.audio_provider.get_db_connection", return_value=conn), \
         patch("blueprints.audio_provider.put_db_connection"), \
         patch("blueprints.audio_provider.get_codal_boundaries", return_value=_EMPTY_BOUNDS):
        text, err = _get_text_for_codal("999999", code_id="civ")

    assert text is None
    assert isinstance(err, str)
    assert len(err) > 0


def test_article_versions_fallback_returns_text():
    """When code_id is None (UUID path), falls through to article_versions table."""
    conn, cur = _mock_db({
        "article_number": "3",
        "content": "Every person is bound to observe good faith in the exercise of his rights.",
    })
    with patch("blueprints.audio_provider.get_db_connection", return_value=conn), \
         patch("blueprints.audio_provider.put_db_connection"):
        text, err = _get_text_for_codal("some-uuid-1234", code_id=None)

    assert err is None
    assert isinstance(text, str)
    assert len(text) > 0


def test_sc_issuance_section_returns_text():
    """SC Issuance path: CPRA section returns non-empty text."""
    conn, cur = _mock_db({
        "id": "ffff-1111",
        "statute_id": "CPRA",
        "statute_label": "Code of Professional Responsibility and Accountability",
        "group_type": "CANON",
        "group_num": "I",
        "group_label": "Propriety",
        "part_num": None, "part_label": None,
        "section_num": "1",
        "section_title": "Proper conduct at all times",
        "content_md": "A lawyer shall not engage in unlawful, dishonest, immoral, or deceitful conduct.",
    })
    with patch("blueprints.audio_provider.get_db_connection", return_value=conn), \
         patch("blueprints.audio_provider.put_db_connection"):
        text, err = _get_text_for_codal("1", code_id="cpra")

    assert err is None
    assert isinstance(text, str)
    assert len(text) > 0
