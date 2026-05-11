/**
 * Daily metering for case digests, bar questions, flashcards, and digest downloads.
 *
 * - **Amicus+** (`canAccess` on the matching `*_unlimited` feature): no `/api/track-usage` call.
 * - **Free (signed-out or `free` tier)**: POST `/api/track-usage` with Clerk Bearer or `anonymousId`.
 *
 * `TRACK_USAGE_FEATURE_TO_UNLIMITED` lives in `SubscriptionContext.jsx` — keep keys aligned.
 */
import { apiUrl } from './apiUrl';
import { TRACK_USAGE_FEATURE_TO_UNLIMITED } from '../context/SubscriptionContext';
import { isGuestGateGraceActive } from './guestGateGrace';

const ANON_STORAGE_KEY = 'lexmate_anonymous_usage_id';
const ANON_START_KEY   = 'lexmate_anonymous_usage_start'; // ISO timestamp of first visit

/** Duration of full-access guest window (24 h, matches GUEST_FULL_ACCESS_HOURS on the backend). */
export const GUEST_WINDOW_MS = 24 * 60 * 60 * 1000;

/** Returns true while the anonymous user is within their 24-hour free-access window. */
export function isInGuestWindow() {
  if (typeof window === 'undefined') return false;
  try {
    const startStr = localStorage.getItem(ANON_START_KEY);
    if (!startStr) return true; // Not yet set → treat as brand-new visitor still in window
    return Date.now() - new Date(startStr).getTime() < GUEST_WINDOW_MS;
  } catch (_) {
    return false;
  }
}


/**
 * Anonymous bucket resets each full page load (F5) when:
 * - production/staging: `VITE_ANON_USAGE_PER_PAGELOAD=true` at build time, or
 * - Vite dev: default on unless `VITE_DEV_ANON_USAGE_PER_RELOAD=false`.
 */
function anonIdPerPageLoad() {
  try {
    if (import.meta.env.VITE_ANON_USAGE_PER_PAGELOAD === 'true') return true;
    return import.meta.env.DEV && import.meta.env.VITE_DEV_ANON_USAGE_PER_RELOAD !== 'false';
  } catch (_) {
    return false;
  }
}

let _pageLoadAnonId = null;

/** @returns {boolean} */
function isUuidString(s) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(s || ''));
}

/**
 * Stable anonymous id for free-tier usage (localStorage, then sessionStorage, then in-memory).
 * Per-reload id when {@link anonIdPerPageLoad} is true (dev by default, or any build with
 * `VITE_ANON_USAGE_PER_PAGELOAD=true`).
 * @returns {string|null}
 */
export function getOrCreateAnonymousUsageId() {
  if (anonIdPerPageLoad()) {
    if (!_pageLoadAnonId && typeof crypto !== 'undefined' && crypto.randomUUID) {
      _pageLoadAnonId = crypto.randomUUID();
    }
    return _pageLoadAnonId;
  }
  try {
    let id = localStorage.getItem(ANON_STORAGE_KEY);
    if (id && isUuidString(id)) {
      // Ensure start timestamp exists (backfill for older sessions)
      if (!localStorage.getItem(ANON_START_KEY)) {
        localStorage.setItem(ANON_START_KEY, new Date().toISOString());
      }
      return id;
    }
    id = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : null;
    if (!id) return null;
    localStorage.setItem(ANON_STORAGE_KEY, id);
    localStorage.setItem(ANON_START_KEY, new Date().toISOString());
    return id;
  } catch (_) {
    try {
      let id = sessionStorage.getItem(ANON_STORAGE_KEY);
      if (id && isUuidString(id)) return id;
      id = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : null;
      if (!id) return null;
      sessionStorage.setItem(ANON_STORAGE_KEY, id);
      return id;
    } catch (__) {
      return null;
    }
  }
}


let _ephemeralAnonId = null;

function getEphemeralAnonymousUsageId() {
  if (!_ephemeralAnonId && typeof crypto !== 'undefined' && crypto.randomUUID) {
    _ephemeralAnonId = crypto.randomUUID();
  }
  return _ephemeralAnonId;
}

/**
 * @param {object} opts
 * @param {'case_digest'|'bar_question'|'flashcard'|'case_digest_download'} opts.feature
 * @param {() => Promise<string|null|undefined>} opts.getToken Clerk session token (Bearer)
 * @param {boolean|undefined} opts.isSignedIn — Bearer only when strictly `true`
 * @param {(feature: string) => boolean} [opts.canAccess] — when provided, Amicus+ skips the network round-trip
 * @param {boolean} [opts.subscriptionLoading] — when true with signed-in Clerk, skips metering until tier is known (avoids paid users hitting DB as “free” during cold start)
 * @param {boolean} [opts.authLoaded=true] — when false (Clerk still booting), skip the track-usage round-trip so we don’t POST as anonymous before session is known
 * @returns {Promise<{ allowed: boolean, skipped?: boolean, unlimited?: boolean, degraded?: boolean, blockedByLimit?: boolean, verifyFailed?: boolean, used?: number, limit?: number, anonymous?: boolean, status?: number, reason?: string }>}
 */
export async function consumeFreeTierUsage({
  feature,
  getToken,
  isSignedIn,
  canAccess,
  subscriptionLoading = false,
  authLoaded = true,
}) {
  try {
    const skipDev =
      import.meta.env.DEV && import.meta.env.VITE_DEV_SKIP_FREE_TIER_TRACKING === 'true';
    const skipAny = import.meta.env.VITE_SKIP_FREE_TIER_TRACKING === 'true';
    if (skipDev || skipAny) {
      return {
        allowed: true,
        skipped: true,
        unlimited: true,
        reason: skipAny ? 'skip_free_tier_tracking' : 'dev_skip_tracking',
      };
    }
  } catch (_) {
    /* ignore */
  }

  if (authLoaded === false) {
    return { allowed: true, skipped: true, reason: 'auth_loading' };
  }

  // Signed-out user just closed the subscription gate modal: browse without consuming daily caps
  // (same 5-minute window before the gate modal can show again — see guestGateGrace.js).
  if (isSignedIn !== true && isGuestGateGraceActive()) {
    return { allowed: true, skipped: true, reason: 'guest_gate_grace' };
  }

  // ── 24-hour full-access guest window ─────────────────────────────────────
  // Unregistered (anonymous) users get full, unlimited access for the first
  // 24 hours from when their anonymous ID was created.  After that, normal
  // per-feature daily caps apply.  Mirrors GUEST_FULL_ACCESS_HOURS on the backend.
  if (isSignedIn !== true) {
    try {
      const startStr = localStorage.getItem(ANON_START_KEY);
      if (startStr) {
        const elapsed = Date.now() - new Date(startStr).getTime();
        if (elapsed < GUEST_WINDOW_MS) {
          return { allowed: true, skipped: true, unlimited: true, reason: 'guest_window' };
        }
      } else {
        // No timestamp yet — this will be set when getOrCreateAnonymousUsageId() runs;
        // treat as in-window for this call.
        return { allowed: true, skipped: true, unlimited: true, reason: 'guest_window_new' };
      }
    } catch (_) {
      /* localStorage unavailable — fall through to network check */
    }
  }
  // ─────────────────────────────────────────────────────────────────────────

  if (isSignedIn === true && subscriptionLoading) {
    return { allowed: true, skipped: true, reason: 'subscription_loading' };
  }

  const unlimitedKey = TRACK_USAGE_FEATURE_TO_UNLIMITED[feature];
  if (typeof canAccess === 'function' && unlimitedKey && canAccess(unlimitedKey)) {
    return { allowed: true, skipped: true, unlimited: true };
  }

  const useClerkSession = isSignedIn === true;

  let token = null;
  if (useClerkSession) {
    try {
      token = typeof getToken === 'function' ? await getToken() : null;
    } catch (_) {
      token = null;
    }
  }

  const headers = { 'Content-Type': 'application/json' };
  const body = { feature };

  if (token) {
    headers['X-Clerk-Authorization'] = `Bearer ${token}`;
  } else {
    const anonId = getOrCreateAnonymousUsageId() || getEphemeralAnonymousUsageId();
    if (!anonId) {
      return { allowed: false, verifyFailed: true, reason: 'no_anonymous_id' };
    }
    body.anonymousId = anonId;
  }

  try {
    const res = await fetch(apiUrl('/api/track-usage'), {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });

    let data = {};
    try {
      data = await res.json();
    } catch (_) {
      /* ignore */
    }

    if (!res.ok) {
      console.error('[freeTierUsage] track-usage HTTP error', res.status, data);
      return {
        allowed: false,
        verifyFailed: true,
        status: res.status,
        message: typeof data?.error === 'string' ? data.error : undefined,
      };
    }

    if (data.allowed === false) {
      return {
        allowed: false,
        used: data.used,
        limit: data.limit,
        anonymous: Boolean(data.anonymous),
        blockedByLimit: true,
      };
    }
    return {
      allowed: true,
      used: data.used,
      limit: data.limit,
      anonymous: Boolean(data.anonymous),
    };
  } catch (e) {
    console.error('[freeTierUsage] network error', e);
    return { allowed: false, verifyFailed: true, reason: 'network' };
  }
}

/**
 * After `consumeFreeTierUsage` returns `allowed: false`, either open the upgrade modal
 * (daily cap hit) or alert on verification/network failure.
 */
export function notifyUsageBlocked(usage, openUpgradeModal, upgradeFeatureKey) {
  if (usage?.blockedByLimit && upgradeFeatureKey) {
    openUpgradeModal(upgradeFeatureKey);
    return;
  }
  if (typeof window !== 'undefined' && typeof window.alert === 'function') {
    const dev =
      typeof import.meta !== 'undefined' && import.meta.env?.DEV
        ? '\n\nDev: ensure Azure Functions is running (e.g. port 7071) so POST /api/track-usage succeeds.'
        : '';
    window.alert(
      "We couldn't verify your daily usage limit. Check your connection, or try again in a moment." + dev,
    );
  }
}
