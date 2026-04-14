import React from 'react';

/**
 * Shared violet / purple ambient blobs for feature pages (About, Updates, Lexify, LexCode, etc.).
 * Children render above the orbs in a stacking context (`isolate`).
 */
export default function PurpleGlassAmbient({ children, className = '' }) {
  return (
    <div className={`relative isolate ${className}`.trim()}>
      <div
        className="pointer-events-none absolute -left-16 top-0 h-64 w-64 rounded-full bg-purple-500/22 blur-3xl dark:bg-zinc-600/[0.07]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute right-0 top-28 h-72 w-72 rounded-full bg-violet-500/20 blur-3xl dark:bg-zinc-500/[0.06]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute bottom-0 left-1/4 h-48 w-80 rounded-full bg-indigo-400/12 blur-3xl dark:bg-zinc-700/[0.05]"
        aria-hidden
      />
      <div className="relative">{children}</div>
    </div>
  );
}
