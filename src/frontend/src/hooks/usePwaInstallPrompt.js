import { useCallback, useEffect, useRef, useState } from 'react';

function getIsStandalone() {
  if (typeof window === 'undefined') return true;
  if (window.matchMedia('(display-mode: standalone)').matches) return true;
  if (window.matchMedia('(display-mode: fullscreen)').matches) return true;
  // iOS Safari PWA
  if (typeof navigator !== 'undefined' && navigator.standalone === true) return true;
  return false;
}

function getIsIos() {
  if (typeof navigator === 'undefined') return false;
  const ua = navigator.userAgent || '';
  if (/iPad|iPhone|iPod/.test(ua)) return true;
  return navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1;
}

/**
 * When `active` (e.g. user is past the marketing landing route), surface install UX.
 * Chromium exposes `beforeinstallprompt`; iOS has no API — caller shows Add-to-Home guidance.
 * Browsers cannot show the install dialog without a user gesture; use the returned `install` from a button.
 */
export function usePwaInstallPrompt(active) {
  const deferredRef = useRef(null);
  const [canPrompt, setCanPrompt] = useState(false);
  const [showBanner, setShowBanner] = useState(false);

  useEffect(() => {
    const onBip = (e) => {
      e.preventDefault();
      deferredRef.current = e;
      setCanPrompt(true);
    };
    window.addEventListener('beforeinstallprompt', onBip);
    return () => window.removeEventListener('beforeinstallprompt', onBip);
  }, []);

  useEffect(() => {
    if (!active) {
      setShowBanner(false);
      return;
    }
    if (getIsStandalone()) {
      setShowBanner(false);
      return;
    }
    setShowBanner(true);
  }, [active]);

  const install = useCallback(async () => {
    const ev = deferredRef.current;
    if (!ev || typeof ev.prompt !== 'function') return { outcome: 'unavailable' };
    await ev.prompt();
    const choice = await ev.userChoice;
    deferredRef.current = null;
    setCanPrompt(false);
    return { outcome: choice?.outcome ?? 'dismissed' };
  }, []);

  const dismiss = useCallback(() => {
    setShowBanner(false);
  }, []);

  return {
    showBanner,
    canPrompt,
    isIos: getIsIos(),
    isStandalone: getIsStandalone(),
    install,
    dismiss,
  };
}
