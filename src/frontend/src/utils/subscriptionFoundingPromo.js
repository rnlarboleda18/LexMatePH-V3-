/**
 * Founding promo users are granted Barrister automatically; UI uses this to
 * gray out lower tiers and label the Barrister card.
 */
export function isFoundingPromoBarrister(tier, subscriptionSource, foundingPromoSlot) {
  if (tier !== 'barrister') return false;
  if (subscriptionSource === 'founding_promo') return true;
  return foundingPromoSlot != null && foundingPromoSlot !== '';
}

/**
 * True when the subscription modal should show founding promo framing: either
 * Barrister already granted via founding promo, or the user is eligible with
 * slots remaining while the automatic grant is still pending (e.g. right after sign-up).
 */
export function isFoundingPromoModalActive(foundingPromoPending, isFoundingPromoBarristerResult) {
  return !!foundingPromoPending || isFoundingPromoBarristerResult;
}
