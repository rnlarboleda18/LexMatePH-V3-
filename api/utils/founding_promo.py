"""
Founding promo: first N eligible signups get Barrister without PayMongo.
After FOUNDING_PROMO_DURATION_DAYS (default 30), they revert to Free unless they have an active PayMongo subscription.
"""
import logging
import os
from typing import Any, Optional

from psycopg import errors as pg_errors

logger = logging.getLogger(__name__)


def get_promo_duration_days() -> int:
    try:
        return max(1, int(os.environ.get("FOUNDING_PROMO_DURATION_DAYS", "30")))
    except ValueError:
        return 30


def get_promo_slot_limit() -> int:
    try:
        return max(0, int(os.environ.get("FOUNDING_PROMO_LIMIT", "20")))
    except ValueError:
        return 20


def get_founding_promo_slots_remaining(cur) -> Optional[int]:
    """Slots left in the founding promo pool, or None if state table is unavailable."""
    try:
        limit = get_promo_slot_limit()
        if limit <= 0:
            return 0
        cur.execute("SELECT claimed_count FROM founding_promo_state WHERE id = 1")
        row = cur.fetchone()
        if not row:
            return None
        claimed = row[0]
        return max(0, limit - int(claimed))
    except (pg_errors.UndefinedColumn, pg_errors.UndefinedTable) as e:
        logger.debug("get_founding_promo_slots_remaining: %s", e)
        return None
    except Exception:
        logger.exception("get_founding_promo_slots_remaining: unexpected")
        return None


def compute_founding_promo_pending(
    is_admin: bool,
    eligible: Optional[bool],
    founding_slot: Any,
    sub_source: Optional[str],
    tier: Optional[str],
    slots_remaining: Optional[int],
) -> bool:
    """
    True when global slots remain and this user is queued for an automatic grant
    (eligible, no slot yet, free tier, not paymongo/trial/admin).
    """
    if is_admin:
        return False
    if eligible is not True:
        return False
    if founding_slot is not None:
        return False
    if slots_remaining is None or slots_remaining <= 0:
        return False
    src = (sub_source or "").strip().lower()
    if src in ("paymongo", "admin_override", "trial"):
        return False
    t = (tier or "").strip().lower() or "free"
    if t != "free":
        return False
    return True


def try_grant_founding_promo(cur, clerk_id: str, is_admin: bool) -> None:
    """Grant Barrister promo if slots remain and user is eligible. Uses row locks; caller must commit."""
    if is_admin or not clerk_id:
        return
    try:
        # Idempotent: migration INSERT may not have run on some environments
        cur.execute(
            """
            INSERT INTO founding_promo_state (id, claimed_count, max_slots)
            VALUES (1, 0, 20)
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
            return
        claimed = row[0]
        if claimed >= limit:
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
            return
        eligible, existing_slot, db_admin = u
        if db_admin or not eligible or existing_slot is not None:
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
            return
        slot = slot_row[0]

        cur.execute(
            """
            UPDATE users SET
                subscription_tier       = 'barrister',
                subscription_status     = 'active',
                founding_promo_slot     = %s,
                founding_promo_granted_at = NOW(),
                subscription_source     = 'founding_promo',
                subscription_expires_at = NULL
            WHERE clerk_id = %s AND founding_promo_slot IS NULL
            """,
            (slot, clerk_id),
        )
        if cur.rowcount:
            logger.info("Founding promo granted slot %s to clerk_id=%s", slot, clerk_id)
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
              paymongo_subscription_id IS NULL
              OR TRIM(COALESCE(paymongo_subscription_id, '')) = ''
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
                  paymongo_subscription_id IS NULL
                  OR TRIM(COALESCE(paymongo_subscription_id, '')) = ''
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
