"""
Founding promo: first N eligible signups get Barrister without Xendit.
After FOUNDING_PROMO_DURATION_DAYS (default 30), they revert to Free unless they have an active Xendit subscription.
"""
import logging
import os

from psycopg import errors as pg_errors

logger = logging.getLogger(__name__)


def get_promo_duration_days() -> int:
    try:
        return max(1, int(os.environ.get("FOUNDING_PROMO_DURATION_DAYS", "30")))
    except ValueError:
        return 30


def get_promo_slot_limit() -> int:
    try:
        return max(0, int(os.environ.get("FOUNDING_PROMO_LIMIT", "30")))
    except ValueError:
        return 30  # matches the hardcoded max_slots=30 in try_grant_founding_promo INSERT


def try_grant_founding_promo(cur, clerk_id: str, is_admin: bool) -> None:
    """Grant Barrister promo if slots remain and user is eligible. Uses row locks; caller must commit."""
    if is_admin or not clerk_id:
        logger.info("try_grant_founding_promo: skipped because is_admin=%s or clerk_id is empty", is_admin)
        return
    try:
        # Idempotent: migration INSERT may not have run on some environments
        cur.execute(
            """
            INSERT INTO founding_promo_state (id, claimed_count, max_slots)
            VALUES (1, 0, 30)
            ON CONFLICT (id) DO NOTHING
            """
        )
        cur.execute("SELECT claimed_count FROM founding_promo_state WHERE id = 1 FOR UPDATE")
        row = cur.fetchone()
        if not row:
            logger.warning("founding_promo_state missing row id=1 after ensure; skipping grant")
            return
        limit = get_promo_slot_limit()
        if limit <= 0:
            logger.info("try_grant_founding_promo: skipped because limit is %s", limit)
            return
        claimed = row[0]
        if claimed >= limit:
            logger.info("try_grant_founding_promo: skipped because claimed (%s) >= limit (%s)", claimed, limit)
            return

        cur.execute(
            """
            SELECT founding_promo_eligible, founding_promo_slot, is_admin
            FROM users WHERE clerk_id = %s FOR UPDATE
            """,
            (clerk_id,),
        )
        u = cur.fetchone()
        if not u:
            logger.info("try_grant_founding_promo: skipped because user clerk_id=%s not found in DB", clerk_id)
            return
        eligible, existing_slot, db_admin = u
        if db_admin or not eligible or existing_slot is not None:
            logger.info(
                "try_grant_founding_promo: skipped for clerk_id=%s (db_admin=%s, eligible=%s, existing_slot=%s)",
                clerk_id, db_admin, eligible, existing_slot
            )
            return

        cur.execute(
            """
            UPDATE founding_promo_state
            SET claimed_count = claimed_count + 1
            WHERE id = 1 AND claimed_count < %s
            RETURNING claimed_count
            """,
            (limit,),
        )
        slot_row = cur.fetchone()
        if not slot_row:
            logger.warning("try_grant_founding_promo: failed to increment claimed_count for clerk_id=%s", clerk_id)
            return
        slot = slot_row[0]

        days = get_promo_duration_days()
        cur.execute(
            """
            UPDATE users SET
                subscription_tier       = 'barrister',
                subscription_status     = 'active',
                founding_promo_slot     = %s,
                founding_promo_granted_at = NOW(),
                subscription_source     = 'founding_promo',
                subscription_expires_at = NOW() + make_interval(days => %s)
            WHERE clerk_id = %s AND founding_promo_slot IS NULL
            """,
            (slot, days, clerk_id),
        )
        if cur.rowcount:
            logger.info("Founding promo granted slot %s to clerk_id=%s", slot, clerk_id)
        else:
            logger.warning("try_grant_founding_promo: user UPDATE returned rowcount=0 for clerk_id=%s", clerk_id)
    except pg_errors.UndefinedColumn:
        logger.warning("Founding promo columns missing; run sql/founding_promo_migration.sql")
    except pg_errors.UndefinedTable:
        logger.warning("Founding promo tables missing; run sql/founding_promo_migration.sql")
    except Exception:
        logger.exception("try_grant_founding_promo failed for clerk_id=%s", clerk_id)


def _expire_sql():
    days = get_promo_duration_days()
    return (
        """
        UPDATE users SET
            subscription_tier = 'free',
            subscription_status = 'inactive',
            founding_promo_slot = NULL,
            founding_promo_granted_at = NULL,
            subscription_source = NULL
        WHERE subscription_source = 'founding_promo'
          AND founding_promo_granted_at IS NOT NULL
          AND founding_promo_granted_at < NOW() - make_interval(days => %s)
          AND (
              xendit_plan_id IS NULL
              OR TRIM(COALESCE(xendit_plan_id, '')) = ''
          )
        """,
        (days,),
    )


def expire_founding_promo_for_user(cur, clerk_id: str) -> int:
    """Downgrade this user if their founding promo period ended. Returns rowcount."""
    try:
        days = get_promo_duration_days()
        cur.execute(
            """
            UPDATE users SET
                subscription_tier = 'free',
                subscription_status = 'inactive',
                founding_promo_slot = NULL,
                founding_promo_granted_at = NULL,
                subscription_source = NULL
            WHERE clerk_id = %s
              AND subscription_source = 'founding_promo'
              AND founding_promo_granted_at IS NOT NULL
              AND founding_promo_granted_at < NOW() - make_interval(days => %s)
              AND (
                  xendit_plan_id IS NULL
                  OR TRIM(COALESCE(xendit_plan_id, '')) = ''
              )
            """,
            (clerk_id, days),
        )
        n = cur.rowcount
        if n:
            logger.info("Founding promo expired for clerk_id=%s", clerk_id)
        return n
    except (pg_errors.UndefinedColumn, pg_errors.UndefinedTable) as e:
        logger.debug("expire_founding_promo_for_user skipped: %s", e)
        return 0


def expire_all_founding_promo_past_due(conn) -> int:
    """Batch expiry (e.g. timer). Returns number of users updated."""
    sql, params = _expire_sql()
    try:
        with conn.cursor() as cur:
            cur.execute(sql + " RETURNING clerk_id", params)
            rows = cur.fetchall()
            conn.commit()
            n = len(rows)
            if n:
                logger.info("Founding promo batch expiry: %s users", n)
            return n
    except (pg_errors.UndefinedColumn, pg_errors.UndefinedTable) as e:
        logger.warning("expire_all_founding_promo_past_due skipped: %s", e)
        conn.rollback()
        return 0
    except Exception as e:
        logger.error("expire_all_founding_promo_past_due: %s", e)
        conn.rollback()
        return 0
