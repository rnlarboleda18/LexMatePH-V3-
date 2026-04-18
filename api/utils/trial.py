"""
24-hour trials per paid tier (amicus, juris, barrister), stored in-app.
Uses subscription_source = 'trial' and subscription_expires_at for expiry.
PayMongo production billing after trial should be configured on each Plan in the PayMongo dashboard
(trial length / first charge timing); this module handles DB-backed trials for dev bypass and parity.

Founding promo winners use a separate path (higher priority in clerk webhook).
"""
import logging
from psycopg import errors as pg_errors

logger = logging.getLogger(__name__)

VALID_TRIAL_TIERS = frozenset({"amicus", "juris", "barrister"})


def grant_trial_for_tier(cur, clerk_id: str, tier: str) -> bool:
    """
    Grant a 24-hour trial of the given paid tier.
    Only applies to users who are still on free tier with no subscription source set.
    Returns True if a row was updated.
    """
    if not clerk_id or tier not in VALID_TRIAL_TIERS:
        return False
    try:
        cur.execute(
            """
            UPDATE users SET
                subscription_tier       = %s,
                subscription_status     = 'active',
                subscription_source     = 'trial',
                subscription_expires_at = NOW() + INTERVAL '24 hours'
            WHERE clerk_id = %s
              AND (subscription_source IS NULL OR subscription_source = '')
              AND (subscription_tier IS NULL OR subscription_tier = 'free')
            """,
            (tier, clerk_id),
        )
        granted = cur.rowcount > 0
        if granted:
            logger.info("24h %s trial granted to clerk_id=%s", tier, clerk_id)
        return granted
    except (pg_errors.UndefinedColumn, pg_errors.UndefinedTable) as e:
        logger.warning("grant_trial_for_tier skipped (columns missing): %s", e)
        return False
    except Exception:
        logger.exception("grant_trial_for_tier error for clerk_id=%s", clerk_id)
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
