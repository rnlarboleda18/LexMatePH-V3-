/**
 * Chrome styling: light mode keeps violet / purple glass brand.
 * Dark mode uses neutral zinc (simple dark UI); violet is not a foundation fill.
 */

/** Sticky filter bar */
export const FILTER_CHROME_SURFACE =
    'w-full xl:w-auto min-w-0 border-b-[3px] border-violet-400/75 bg-gradient-to-b from-white/98 via-violet-100/65 to-purple-100/55 shadow-[0_10px_36px_-6px_rgba(91,33,182,0.38)] backdrop-blur-xl dark:border-b dark:border-zinc-800 dark:bg-zinc-950/90 dark:shadow-[0_8px_32px_-8px_rgba(0,0,0,0.55)] dark:backdrop-blur-xl dark:ring-1 dark:ring-inset dark:ring-white/[0.05]';

export const FILTER_SELECT =
    'box-border block h-9 w-full cursor-pointer rounded-lg border-2 border-violet-300/90 bg-white/95 py-1.5 pl-2 pr-6 text-xs font-medium leading-tight text-gray-900 shadow-md shadow-violet-200/30 backdrop-blur-sm transition-colors focus:border-violet-600 focus:outline-none focus:ring-2 focus:ring-violet-500/45 dark:border-zinc-600 dark:bg-zinc-900 dark:text-zinc-100 dark:shadow-none focus:dark:border-zinc-500 focus:dark:ring-zinc-600/50 sm:text-sm';

export const FILTER_SEARCH_INPUT =
    'box-border block h-9 min-w-0 w-full max-w-full rounded-lg border-2 border-violet-300/90 bg-white/95 py-1.5 pl-7 pr-8 text-xs font-medium leading-tight text-gray-900 shadow-md shadow-violet-200/30 backdrop-blur-sm placeholder:text-slate-500 transition-colors focus:border-violet-600 focus:outline-none focus:ring-2 focus:ring-violet-500/45 dark:border-zinc-600 dark:bg-zinc-900 dark:text-zinc-100 dark:placeholder:text-zinc-500 dark:shadow-none focus:dark:border-zinc-500 focus:dark:ring-zinc-600/50 sm:text-sm';

/** Bar browse search — no trailing clear control, tighter right padding */
export const FILTER_BAR_SEARCH_INPUT =
    'box-border block h-9 min-w-0 w-full max-w-full rounded-lg border-2 border-violet-300/90 bg-white/95 py-1.5 pl-7 pr-3 text-xs font-medium leading-tight text-gray-900 shadow-md shadow-violet-200/30 backdrop-blur-sm placeholder:text-slate-500 transition-colors focus:border-violet-600 focus:outline-none focus:ring-2 focus:ring-violet-500/45 dark:border-zinc-600 dark:bg-zinc-900 dark:text-zinc-100 dark:placeholder:text-zinc-500 dark:shadow-none focus:dark:border-zinc-500 focus:dark:ring-zinc-600/50 sm:text-sm';

export const FILTER_TOGGLE_BUTTON =
    'box-border flex h-9 w-full cursor-pointer items-center justify-center gap-1 rounded-lg border-2 border-violet-300/90 bg-white/95 px-2 text-xs font-semibold uppercase leading-tight tracking-wide text-violet-900 shadow-md shadow-violet-200/30 backdrop-blur-sm transition-colors hover:bg-violet-100 hover:shadow-sm focus:border-violet-600 focus:outline-none focus:ring-2 focus:ring-violet-500/45 dark:border-zinc-600 dark:bg-zinc-900 dark:text-zinc-200 dark:shadow-none dark:hover:bg-zinc-800 focus:dark:border-zinc-500 focus:dark:ring-zinc-600/50 sm:text-sm';

export const FILTER_CHROME_DIVIDER =
    'border-t-2 border-violet-300/60 pt-3 dark:border-zinc-700';

/** Leading search icon inside inputs */
export const FILTER_SEARCH_ICON_CLASS =
    'h-3.5 w-3.5 shrink-0 text-violet-700 dark:text-zinc-400';

/** Small uppercase labels above selects */
export const FILTER_FIELD_LABEL =
    'mb-0.5 block text-[10px] font-semibold uppercase tracking-wide text-violet-900 dark:text-zinc-500';

// --- Main app sidebar (Layout aside + nav affordances) ---

/** Fixed app header — dark: neutral bar (not purple-tinted) */
export const APP_HEADER_SURFACE =
    'isolate border-b-[3px] border-violet-400/70 bg-gradient-to-b from-white/68 via-violet-50/38 to-purple-100/32 backdrop-blur-2xl shadow-[0_20px_56px_-20px_rgba(109,40,217,0.3)] ring-1 ring-inset ring-white/55 dark:border-b dark:border-zinc-800 dark:bg-zinc-950/92 dark:shadow-[0_12px_40px_-12px_rgba(0,0,0,0.55)] dark:backdrop-blur-xl dark:ring-1 dark:ring-inset dark:ring-white/[0.05]';

/** Fixed left navigation — dark: matches header (zinc) */
export const SIDEBAR_ASIDE_SURFACE =
    'isolate border-r-[3px] border-violet-400/70 bg-gradient-to-br from-white/66 via-violet-50/36 to-purple-100/30 backdrop-blur-2xl shadow-[8px_0_44px_-18px_rgba(109,40,217,0.28)] ring-1 ring-inset ring-white/45 dark:border-r dark:border-zinc-800 dark:bg-zinc-950/94 dark:shadow-[6px_0_32px_-12px_rgba(0,0,0,0.5)] dark:backdrop-blur-xl dark:ring-1 dark:ring-inset dark:ring-white/[0.04]';

/** Sidebar nav row — selected */
export const SIDEBAR_NAV_ACTIVE =
    'border border-violet-200/55 !border-l-[3px] !border-l-violet-600 bg-white/52 text-violet-950 shadow-md shadow-violet-300/25 backdrop-blur-md ring-1 ring-violet-200/45 dark:border-zinc-700/90 dark:!border-l-zinc-400 dark:bg-white/[0.07] dark:text-zinc-100 dark:shadow-none dark:backdrop-blur-md dark:ring-1 dark:ring-zinc-600/40';

/** Sidebar nav row — default + hover */
export const SIDEBAR_NAV_IDLE =
    'border border-transparent !border-l-[3px] !border-l-transparent text-violet-950/92 hover:border-violet-200/70 hover:!border-l-violet-400/80 hover:bg-white/42 dark:border-transparent dark:text-zinc-300 dark:hover:bg-white/[0.05] dark:hover:border-zinc-700 dark:hover:!border-l-zinc-500';

/** Mobile-only auth block at top of sidebar */
export const SIDEBAR_MOBILE_AUTH_CARD =
    'rounded-[1.25rem] border-2 border-violet-200/70 bg-gradient-to-br from-white/64 via-violet-50/36 to-purple-100/30 p-4 shadow-[0_18px_48px_-16px_rgba(109,40,217,0.26)] backdrop-blur-2xl ring-1 ring-inset ring-white/40 dark:border-zinc-700 dark:bg-zinc-900/85 dark:backdrop-blur-xl dark:shadow-lg dark:ring-white/[0.04]';
