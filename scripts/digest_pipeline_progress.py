"""
JSON progress file for digest pipeline subprocesses (written from ``elib_digest_pipeline.py``).

The admin API exposes this payload via ``GET /api/ops/pipeline/status`` so the Ops UI can
render per-case stage + percentage while a run is active.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


# Rough progress within one case (plain labels for Ops UI).
STAGE_ORDER = [
    "queued",
    "fetch_html",
    "to_markdown",
    "db_insert",
    "ai_digest",
    "grok_fallback",
    "codal_link",
    "done",
    "skipped",
    "failed",
]


def stage_index(stage: str) -> int:
    try:
        return STAGE_ORDER.index(stage)
    except ValueError:
        return 0


def stage_percent(stage: str) -> int:
    """Map coarse stage → 0–100 for a single-case progress bar."""
    table = {
        "queued": 0,
        "fetch_html": 12,
        "to_markdown": 24,
        "db_insert": 36,
        "ai_digest": 72,
        "grok_fallback": 82,
        "codal_link": 93,
        "done": 100,
        "skipped": 100,
        "failed": 100,
    }
    return table.get(stage, 5)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class CaseSlice:
    elib_id: int | None
    db_row_id: int | None
    label: str
    stage: str
    detail: str = ""
    outcome: str = ""  # e.g. INGESTED, SKIP_ALREADY_IN_DB
    updated_at: str = field(default_factory=_utc_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "elib_id": self.elib_id,
            "db_row_id": self.db_row_id,
            "label": (self.label or "")[:280],
            "stage": self.stage,
            "stage_label": stage_display_label(self.stage),
            "percent": stage_percent(self.stage),
            "detail": (self.detail or "")[:500],
            "outcome": self.outcome,
            "updated_at": self.updated_at,
        }


def stage_display_label(stage: str) -> str:
    return {
        "queued": "Waiting",
        "fetch_html": "Downloading HTML",
        "to_markdown": "Convert to Markdown",
        "db_insert": "Saving to database",
        "ai_digest": "AI digest (Gemini)",
        "grok_fallback": "AI digest (Grok fallback)",
        "codal_link": "Codal linking",
        "done": "Complete",
        "skipped": "Skipped",
        "failed": "Failed",
    }.get(stage, stage.replace("_", " ").title())


class DigestPipelineProgressWriter:
    """Thread-safe JSON writer with atomic replace."""

    def __init__(self, path: Path | None, mode: str, *, lock: threading.Lock | None = None):
        self.path = path
        self.mode = mode
        self._lock = lock or threading.Lock()
        self.run_id = uuid4().hex[:12]
        self._cases: dict[str, CaseSlice] = {}
        self._order: list[str] = []
        self._max_cases = 40
        self._finalized = False

    def disabled(self) -> bool:
        return self.path is None

    def _key(self, elib_id: int | None, db_row_id: int | None) -> str:
        if db_row_id is not None:
            return f"db:{db_row_id}"
        if elib_id is not None:
            return f"elib:{elib_id}"
        return f"anon:{len(self._order)}"

    def start(self, message: str = "") -> None:
        payload = self._payload("running", "starting", message, overall_percent=0)
        self._atomic_write(payload)

    def heartbeat(self, phase: str, message: str, *, overall_percent: float | None = None) -> None:
        payload = self._payload("running", phase, message, overall_percent=overall_percent)
        self._atomic_write(payload)

    def done(self, summary: str, *, ok: bool = True) -> None:
        self._finalized = True
        payload = self._payload("done" if ok else "failed", "done", summary, overall_percent=100.0 if ok else None)
        self._atomic_write(payload)

    def finalize_if_needed(self, summary: str, *, ok: bool) -> None:
        """Idempotent terminal write when ``done()`` was not invoked earlier."""
        if self.disabled() or self._finalized:
            return
        self.done(summary, ok=ok)

    def finalize_interrupted(self, summary: str) -> None:
        """Terminal state if ``done()`` was never reached (crash / stray return)."""
        if self.disabled() or self._finalized:
            return
        self.done(summary, ok=False)

    def note_case(
        self,
        *,
        elib_id: int | None,
        db_row_id: int | None,
        label: str = "",
        stage: str,
        detail: str = "",
        outcome: str = "",
    ) -> None:
        key = self._key(elib_id, db_row_id)
        if key not in self._cases:
            if len(self._order) >= self._max_cases:
                stale = self._order.pop(0)
                self._cases.pop(stale, None)
            self._order.append(key)
        self._cases[key] = CaseSlice(
            elib_id=elib_id,
            db_row_id=db_row_id,
            label=label,
            stage=stage,
            detail=detail,
            outcome=outcome,
            updated_at=_utc_iso(),
        )
        pct = sum(stage_percent(cs.stage) for cs in self._cases.values()) / max(len(self._cases), 1)
        self._atomic_write(
            self._payload(
                "running",
                phase_from_stage(stage),
                detail or "",
                overall_percent=min(99.9, pct),
            )
        )

    def phase_snapshot(self, phase: str, message: str, *, overall_percent: float | None = None) -> None:
        self._atomic_write(self._payload("running", phase, message, overall_percent=overall_percent))

    def _payload(self, status: str, phase: str, message: str, *, overall_percent: float | None) -> dict[str, Any]:
        cases_out = []
        seen: set[str] = set()
        for k in reversed(self._order):
            if k in seen:
                continue
            seen.add(k)
            c = self._cases.get(k)
            if c:
                cases_out.append(c.to_dict())
        cases_out.reverse()
        od = {}
        od["run_id"] = self.run_id
        od["mode"] = self.mode
        od["status"] = status
        od["phase"] = phase
        od["message"] = (message or "")[:1200]
        od["overall_percent"] = (
            round(overall_percent, 1)
            if overall_percent is not None
            else (round(sum(x["percent"] for x in cases_out) / max(len(cases_out), 1), 1) if cases_out else 0)
        )
        od["started_at"] = getattr(self, "_started_at", _utc_iso())
        od["updated_at"] = _utc_iso()
        od["cases"] = cases_out
        return od

    def _atomic_write(self, data: dict[str, Any]) -> None:
        if self.disabled():
            return
        assert self.path is not None
        with self._lock:
            if not hasattr(self, "_started_at"):
                self._started_at = data.get("started_at") or _utc_iso()
            data.setdefault("started_at", self._started_at)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            tmp.replace(self.path)


def phase_from_stage(stage: str) -> str:
    if stage in ("fetch_html", "to_markdown", "db_insert"):
        return "ingest"
    if stage.startswith("ai") or stage == "grok_fallback":
        return "digest"
    if stage == "codal_link":
        return "link"
    return "digest"
