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

const ANON_STORAGE_KEY = 'lexmate_anonymous_usage_id';

/** @returns {boolean} */
function isUuidString(s) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(s || ''));
}

/**
 * Stable anonymous id for free-tier usage (localStorage, then sessionStorage, then in-memory).
 * @returns {string|null}
 */
export function getOrCreateAnonymousUsageId() {
  try {
    let id = localStorage.getItem(ANON_STORAGE_KEY);
    if (id && isUuidString(id)) return id;
    id = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : null;
    if (!id) return null;
    localStorage.setItem(ANON_STORAGE_KEY, id);
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
 * @returns {Promise<{ allowed: boolean, skipped?: boolean, unlimited?: boolean, degraded?: boolean, blockedByLimit?: boolean, verifyFailed?: boolean, used?: number, limit?: number, anonymous?: boolean, status?: number }>}
 */
export async function consumeFreeTierUsage({ feature, getToken, isSignedIn, canAccess }) {
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
