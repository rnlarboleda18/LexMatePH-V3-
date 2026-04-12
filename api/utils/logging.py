"""
Structured logging helpers for LexMatePH Azure Functions.

Usage:
    from utils.logging import get_logger
    log = get_logger(__name__)
    log.info("Fetched decisions", extra={"count": 12, "duration_ms": 45})

The correlation_id is derived from the Azure Functions invocation ID when
available, or generated per-process otherwise.  Including it in every log line
lets you filter all logs for a single request in Azure Log Analytics:

    traces | where customDimensions.correlation_id == "<id>"
"""
import logging
import os
import uuid

# Module-level fallback ID for non-Functions execution (e.g. local scripts).
_FALLBACK_CORRELATION_ID = str(uuid.uuid4())


def get_correlation_id(req=None) -> str:
    """
    Returns a correlation ID for the current request.

    Priority:
    1. Azure Functions invocation ID (x-ms-invocation-id header)
    2. Client-supplied X-Correlation-ID / X-Request-ID header
    3. Process-level fallback UUID
    """
    if req is not None:
        inv_id = (req.headers.get("x-ms-invocation-id") or "").strip()
        if inv_id:
            return inv_id
        for header in ("x-correlation-id", "x-request-id"):
            val = (req.headers.get(header) or "").strip()
            if val:
                return val
    return _FALLBACK_CORRELATION_ID


class _CorrelationFilter(logging.Filter):
    """Injects correlation_id into every LogRecord produced by this logger."""

    def __init__(self, correlation_id: str):
        super().__init__()
        self._cid = correlation_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = self._cid
        return True


def get_logger(name: str, req=None) -> logging.Logger:
    """
    Return a standard Logger augmented with a correlation_id filter.

    Example::

        log = get_logger(__name__, req)
        log.info("handler called")
        # Azure Log Analytics: customDimensions.correlation_id = "<invocation-id>"
    """
    logger = logging.getLogger(name)
    cid = get_correlation_id(req)
    # Avoid duplicate filters on re-use
    logger.filters = [f for f in logger.filters if not isinstance(f, _CorrelationFilter)]
    logger.addFilter(_CorrelationFilter(cid))
    return logger
