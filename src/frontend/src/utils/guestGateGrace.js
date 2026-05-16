/** Wall-clock end of “browse without metering” after a signed-out user closes the gate modal (see App.jsx). */
let graceUntilMs = null;

export const GUEST_GATE_GRACE_MS = 4 * 60 * 1000;

export function startGuestGateGrace() {
  graceUntilMs = Date.now() + GUEST_GATE_GRACE_MS;
}

export function clearGuestGateGrace() {
  graceUntilMs = null;
}

/** True only for signed-out flows that check this before POST /api/track-usage. */
export function isGuestGateGraceActive() {
  if (graceUntilMs == null) return false;
  if (Date.now() >= graceUntilMs) {
    graceUntilMs = null;
    return false;
  }
  return true;
}
