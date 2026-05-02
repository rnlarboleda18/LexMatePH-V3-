import React from 'react';

/** Shown while lazy-loaded feature chunks download. */
export default function PageLoadingFallback({
  label = 'Loading…',
  /** When 'lg', label is hidden on narrow viewports; parent keeps aria-label for screen readers. */
  labelVisibility = 'always',
}) {
  const labelClass =
    labelVisibility === 'lgAndUp'
      ? 'hidden text-sm font-medium text-gray-500 dark:text-gray-400 lg:block'
      : 'text-sm font-medium text-gray-500 dark:text-gray-400';
  return (
    <div
      className="flex min-h-[40vh] flex-col items-center justify-center gap-3 text-gray-500 dark:text-gray-400"
      role="status"
      aria-live="polite"
      aria-busy="true"
      aria-label={label}
    >
      <div
        className="h-10 w-10 shrink-0 animate-spin rounded-full border-2 border-amber-500/30 border-t-amber-600 dark:border-amber-400/20 dark:border-t-amber-400"
        aria-hidden
      />
      <p className={labelClass}>{label}</p>
    </div>
  );
}
