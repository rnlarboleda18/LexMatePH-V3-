import React from 'react';

const HEADER_CLASS =
  'sticky z-20 overflow-hidden border-b border-white/30 bg-white/25 shadow-[0_8px_30px_rgb(0,0,0,0.06)] backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/35 dark:shadow-[0_8px_30px_rgb(0,0,0,0.25)] md:rounded-b-2xl md:shadow-[0_12px_40px_rgb(0,0,0,0.08)] md:backdrop-blur-2xl dark:md:shadow-[0_12px_40px_rgb(0,0,0,0.22)] lg:shadow-[0_16px_48px_rgb(0,0,0,0.09)] dark:lg:shadow-[0_16px_48px_rgb(0,0,0,0.28)] top-[calc(3.5rem+env(safe-area-inset-top,0px))] md:top-[calc(5rem+env(safe-area-inset-top,0px))]';

/**
 * Shared chrome for feature areas (Bar Questions, LexCode, Flashcards, About, etc.):
 * sticky glass header + max-w-7xl main.
 */
const FeaturePageShell = ({ icon: Icon, title, subtitle, children }) => {
  return (
    <div className="min-h-screen bg-transparent font-sans text-gray-900 dark:text-gray-100">
      <header className={HEADER_CLASS} style={{ willChange: 'transform' }}>
        <div
          className="pointer-events-none absolute -left-[10%] -top-[60%] h-[280px] w-[280px] rounded-full bg-indigo-500/20 blur-[100px] dark:bg-blue-500/15 md:h-[360px] md:w-[360px] md:blur-[120px] lg:left-0 lg:h-[420px] lg:w-[420px]"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute -bottom-[80%] -right-[15%] h-[260px] w-[260px] rounded-full bg-purple-500/18 blur-[100px] dark:bg-purple-500/12 md:h-[340px] md:w-[340px] md:blur-[120px] lg:right-0 lg:bottom-[-40%] lg:h-[400px] lg:w-[400px]"
          aria-hidden
        />
        <div className="relative mx-auto flex max-w-7xl items-center gap-2 px-3 py-2 sm:gap-3 sm:px-4 sm:py-2.5 md:gap-4 md:py-3 lg:gap-4 lg:px-5 lg:py-3">
          <div
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-indigo-200/90 bg-gradient-to-br from-indigo-50/95 to-blue-50/90 text-indigo-600 shadow-[0_4px_14px_rgba(79,70,229,0.12)] dark:border-indigo-800/70 dark:from-slate-800/90 dark:to-indigo-950/50 dark:text-indigo-300 dark:shadow-[0_4px_20px_rgba(0,0,0,0.35)] sm:h-10 sm:w-10 md:h-11 md:w-11 md:rounded-xl md:shadow-[0_8px_24px_rgba(79,70,229,0.15)] lg:h-11 lg:w-11"
            aria-hidden
          >
            {Icon ? <Icon className="h-5 w-5 sm:h-5 sm:w-5 md:h-6 md:w-6 lg:h-6 lg:w-6" strokeWidth={2} /> : null}
          </div>
          <div className="min-w-0 flex-1 border-l-[3px] border-l-indigo-500 pl-2 dark:border-l-indigo-400 sm:pl-3 md:pl-4 lg:pl-4">
            <h1 className="truncate text-base font-bold tracking-tight sm:text-lg md:text-xl md:tracking-tight lg:text-[1.375rem] xl:text-[1.5rem] bg-gradient-to-r from-indigo-700 via-blue-700 to-indigo-600 bg-clip-text text-transparent dark:from-indigo-200 dark:via-blue-200 dark:to-indigo-100">
              {title}
            </h1>
            {subtitle ? (
              <p className="mt-0.5 text-[9px] font-semibold uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400 sm:text-[10px] md:mt-1 md:text-[11px] md:tracking-[0.2em] lg:text-xs lg:tracking-[0.16em]">
                {subtitle}
              </p>
            ) : null}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-3 py-4 sm:px-5 sm:py-5 lg:px-6">{children}</main>
    </div>
  );
};

export default React.memo(FeaturePageShell);
