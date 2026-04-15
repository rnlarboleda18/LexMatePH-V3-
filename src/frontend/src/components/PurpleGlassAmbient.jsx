import React from 'react';

/**
 * Page wrapper with optional violet/purple ambient (same vocabulary as Updates / Lexify hero).
 * Use showAmbient on study surfaces (Bar, LexCode, Case Digest) so they align with About / Updates.
 */
export default function PurpleGlassAmbient({ children, className = '', showAmbient = false }) {
  const wash = showAmbient
    ? 'bg-gradient-to-br from-violet-50/45 via-white/70 to-purple-50/35 dark:from-violet-950/35 dark:via-zinc-950 dark:to-purple-950/30'
    : '';
  return (
    <div className={`relative ${wash} ${className}`.trim()}>
      {showAmbient && (
        <>
          <div
            className="pointer-events-none absolute -left-24 top-0 h-72 w-72 rounded-full bg-violet-500/20 blur-3xl dark:bg-violet-600/15"
            aria-hidden
          />
          <div
            className="pointer-events-none absolute right-0 top-32 h-80 w-80 rounded-full bg-purple-500/18 blur-3xl dark:bg-purple-500/12 md:top-44"
            aria-hidden
          />
          <div
            className="pointer-events-none absolute bottom-16 left-1/4 h-56 w-[min(100%,24rem)] rounded-full bg-indigo-400/14 blur-3xl dark:bg-indigo-500/10"
            aria-hidden
          />
        </>
      )}
      {showAmbient ? <div className="relative z-[1] min-h-0">{children}</div> : children}
    </div>
  );
}
