/**
 * Runs onClose and blocks pointer events briefly so the same touch/click on mobile
 * cannot "fall through" to the list item underneath and reopen the modal.
 */
export function closeModalAbsorbingGhostTap(onClose) {
    const shield = document.createElement('div');
    shield.setAttribute('aria-hidden', 'true');
    shield.style.cssText =
        'position:fixed;inset:0;z-index:2147483646;pointer-events:auto;touch-action:none;cursor:default';
    document.body.appendChild(shield);
    onClose();
    window.setTimeout(() => shield.remove(), 750);
}
