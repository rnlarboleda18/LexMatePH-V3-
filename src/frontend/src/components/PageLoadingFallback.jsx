import React from 'react';

/** Shown while lazy-loaded feature chunks download. */
export default function PageLoadingFallback({ label = 'Loading…' }) {
  return (
    <div
      className="flex min-h-[40vh] flex-col items-center justify-center gap-3 text-gray-500 dark:text-gray-400"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="h-10 w-10 animate-spin rounded-full border-2 border-amber-500/30 border-t-amber-600 dark:border-amber-400/20 dark:border-t-amber-400" />
      <p className="text-sm font-medium">{label}</p>
    </div>
  );
}
