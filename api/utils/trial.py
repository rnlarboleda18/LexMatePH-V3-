"""
24-hour trial on sign-up for paid-style exploration (tier matches Clerk unsafeMetadata).
Uses subscription_source = 'trial' and subscription_expires_at for expiry.
Founding promo (limited slots) is handled separately in the Clerk webhook and takes priority.

Override duration with TRIAL_DURATION_HOURS (default 24).
Disable trials entirely with TRIAL_ENABLED=false in app settings / local.settings.json.
"""
import logging
import os
from psycopg import errors as pg_errors

logger = logging.getLogger(__name__)

ALLOWED_TRIAL_TIERS = frozenset({"amicus", "juris", "barrister"})


def normalize_trial_tier(raw: str | None) -> str:
    """Map frontend/Clerk metadata to a subscription tier; invalid values → barrister."""
    t = (raw or "barrister").strip().lower()
    return t if t in ALLOWED_TRIAL_TIERS else "barrister"


def trial_duration_hours() -> int:
    try:
        return max(1, int(os.environ.get("TRIAL_DURATION_HOURS", "24")))
    except ValueError:
        return 24


def _trial_enabled() -> bool:
    """Returns False when TRIAL_ENABLED is explicitly set to 'false', '0', or 'no'."""
    val = os.environ.get("TRIAL_ENABLED", "true").strip().lower()
    return val not in ("false", "0", "no")


def try_grant_trial(cur, clerk_id: str, trial_tier: str | None = None) -> bool:
    """
    Grant a time-limited trial on a specific paid tier (default barrister).
    Only activates if the user has no existing subscription (source is NULL/empty).
    Skipped entirely when TRIAL_ENABLED=false.
    Returns True if the trial was granted.
    """
    if not clerk_id:
        return False
    if not _trial_enabled():
        logger.info("try_grant_trial skipped: TRIAL_ENABLED=false")
        return False
    tier = normalize_trial_tier(trial_tier)
    hours = trial_duration_hours()
    try:
        cur.execute(
            """
            UPDATE users SET
                subscription_tier      = %s,
                subscription_status    = 'active',
                subscription_source    = 'trial',
                subscription_expires_at = NOW() + make_interval(hours => %s)
            WHERE clerk_id = %s
              AND (subscription_source IS NULL OR subscription_source = '')
              AND (subscription_tier IS NULL OR subscription_tier = 'free')
            """,
            (tier, hours, clerk_id),
        )
        granted = cur.rowcount > 0
        if granted:
            logger.info("%sh %s trial granted to clerk_id=%s", hours, tier, clerk_id)
        return granted
    except (pg_errors.UndefinedColumn, pg_errors.UndefinedTable) as e:
        logger.warning("try_grant_trial skipped (columns missing): %s", e)
        return False
    except Exception:
        logger.exception("try_grant_trial error for clerk_id=%s", clerk_id)
        return False


def expire_trial_for_user(cur, clerk_id: str) -> int:
    """
    Downgrade a single user if their 24h trial has expired.
    Called on every subscription-status request.
    Returns the number of rows updated (0 or 1).
    """
    try:
        cur.execute(
            """
            UPDATE users SET
                subscription_tier       = 'free',
                subscription_status     = 'inactive',
                subscription_source     = NULL,
                subscription_expires_at = NULL
            WHERE clerk_id = %s
              AND subscription_source = 'trial'
              AND subscription_expires_at IS NOT NULL
              AND subscription_expires_at < NOW()
            """,
            (clerk_id,),
        )
        n = cur.rowcount
        if n:
            logger.info("Trial expired for clerk_id=%s", clerk_id)
        return n
    except (pg_errors.UndefinedColumn, pg_errors.UndefinedTable) as e:
        logger.debug("expire_trial_for_user skipped: %s", e)
        return 0
    except Exception:
        logger.exception("expire_trial_for_user error for clerk_id=%s", clerk_id)
        return 0


def expire_cancelled_xendit_sub(cur, clerk_id: str) -> int:
    """
    Downgrade a user whose Xendit subscription was cancelled but they still
    had paid days remaining. Once NOW() passes subscription_expires_at, this
    sets them back to Free.

    Called on every subscription-status request (same pattern as trial expiry).
    Returns the number of rows updated (0 or 1).
    """
    try:
        cur.execute(
            """
            UPDATE users SET
                subscription_tier       = 'free',
                subscription_status     = 'inactive',
                subscription_source     = NULL,
                subscription_expires_at = NULL
            WHERE clerk_id = %s
              AND subscription_status = 'cancelled'
              AND subscription_source = 'xendit'
              AND subscription_expires_at IS NOT NULL
              AND subscription_expires_at < NOW()
            """,
            (clerk_id,),
        )
        n = cur.rowcount
        if n:
            logger.info("Cancelled Xendit sub expired for clerk_id=%s", clerk_id)
        return n
    except (pg_errors.UndefinedColumn, pg_errors.UndefinedTable) as e:
        logger.debug("expire_cancelled_xendit_sub skipped: %s", e)
        return 0
    except Exception:
        logger.exception("expire_cancelled_xendit_sub error for clerk_id=%s", clerk_id)
        return 0


def expire_past_due_xendit_sub(cur, clerk_id: str) -> int:
    """
    Downgrade a user who has been past_due for more than 30 days.
    The 30-day grace period end is stored in subscription_expires_at when
    _handle_cycle_failed fires.

    Called on every subscription-status request.
    Returns the number of rows updated (0 or 1).
    """
    try:
        cur.execute(
            """
            UPDATE users SET
                subscription_tier       = 'free',
                subscription_status     = 'inactive',
                subscription_source     = NULL,
                subscription_expires_at = NULL,
                xendit_plan_id          = NULL
            WHERE clerk_id = %s
              AND subscription_status = 'past_due'
              AND subscription_source = 'xendit'
              AND subscription_expires_at IS NOT NULL
              AND subscription_expires_at < NOW()
            """,
            (clerk_id,),
        )
        n = cur.rowcount
        if n:
            logger.info("Past-due Xendit sub expired for clerk_id=%s — downgraded to free", clerk_id)
        return n
    except (pg_errors.UndefinedColumn, pg_errors.UndefinedTable) as e:
        logger.debug("expire_past_due_xendit_sub skipped: %s", e)
        return 0
    except Exception:
        logger.exception("expire_past_due_xendit_sub error for clerk_id=%s", clerk_id)
        return 0


def expire_all_past_due_xendit_subs(conn) -> int:
    """
    Batch downgrade of all past_due users whose 30-day grace period has elapsed.
    Can be called from a nightly timer.
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users SET
                    subscription_tier       = 'free',
                    subscription_status     = 'inactive',
                    subscription_source     = NULL,
                    subscription_expires_at = NULL,
                    xendit_plan_id          = NULL
                WHERE subscription_status = 'past_due'
                  AND subscription_source = 'xendit'
                  AND subscription_expires_at IS NOT NULL
                  AND subscription_expires_at < NOW()
                RETURNING clerk_id
                """
            )
            rows = cur.fetchall()
            conn.commit()
            n = len(rows)
            if n:
                logger.info("Batch past-due expiry: %s users downgraded to free", n)
            return n
    except (pg_errors.UndefinedColumn, pg_errors.UndefinedTable) as e:
        logger.warning("expire_all_past_due_xendit_subs skipped: %s", e)
        conn.rollback()
        return 0
    except Exception as e:
        logger.error("expire_all_past_due_xendit_subs error: %s", e)
        conn.rollback()
        return 0


def expire_all_cancelled_xendit_subs(conn) -> int:
    """
    Batch expiry for all cancelled Xendit subs whose period has elapsed.
    Can be called from a nightly timer alongside expire_all_trials.
    Returns the number of users downgraded.
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users SET
                    subscription_tier       = 'free',
                    subscription_status     = 'inactive',
                    subscription_source     = NULL,
                    subscription_expires_at = NULL
                WHERE subscription_status = 'cancelled'
                  AND subscription_source = 'xendit'
                  AND subscription_expires_at IS NOT NULL
                  AND subscription_expires_at < NOW()
                RETURNING clerk_id
                """
            )
            rows = cur.fetchall()
            conn.commit()
            n = len(rows)
            if n:
                logger.info("Batch cancelled Xendit sub expiry: %s users downgraded", n)
            return n
    except (pg_errors.UndefinedColumn, pg_errors.UndefinedTable) as e:
        logger.warning("expire_all_cancelled_xendit_subs skipped: %s", e)
        conn.rollback()
        return 0
    except Exception as e:
        logger.error("expire_all_cancelled_xendit_subs error: %s", e)
        conn.rollback()
        return 0


def expire_all_trials(conn) -> int:
    """
    Batch expiry of all trials past their 24h window.
    Called by the nightly Azure Functions timer.
    Returns the number of users downgraded.
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users SET
                    subscription_tier       = 'free',
                    subscription_status     = 'inactive',
                    subscription_source     = NULL,
                    subscription_expires_at = NULL
                WHERE subscription_source = 'trial'
                  AND subscription_expires_at IS NOT NULL
                  AND subscription_expires_at < NOW()
                RETURNING clerk_id
                """
            )
            rows = cur.fetchall()
            conn.commit()
            n = len(rows)
            if n:
                logger.info("Batch trial expiry: %s users downgraded", n)
            return n
    except (pg_errors.UndefinedColumn, pg_errors.UndefinedTable) as e:
        logger.warning("expire_all_trials skipped (columns missing): %s", e)
        conn.rollback()
        return 0
    except Exception as e:
        logger.error("expire_all_trials error: %s", e)
        conn.rollback()
        return 0
