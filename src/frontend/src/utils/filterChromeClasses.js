/**
 * App chrome: solid surfaces (no glassmorphism). Palette: white, neutral greys, black
 * in dark mode, with violet only for focus rings and the active sidebar rail.
 * Bar subject pills & digest doctrine colors stay in `colors.js`.
 *
 * Container borders use the global tokens `border-lex` / `border-lex-strong` (see
 * `index.css` --lex-border* and `tailwind.config.js` colors.lex).
 */

/** Default structural border color (use with `border`, `border-b`, etc.) */
export const LEX_BORDER = 'border-lex';

/** Slightly stronger border (inputs, nested panels) */
export const LEX_BORDER_STRONG = 'border-lex-strong';

/** Sticky filter bar */
export const FILTER_CHROME_SURFACE =
    'w-full xl:w-auto min-w-0 border-b border-lex bg-white shadow-sm dark:bg-zinc-950';

export const FILTER_SELECT =
    'box-border block h-9 w-full cursor-pointer rounded-md border border-lex-strong bg-white py-1.5 pl-2 pr-6 text-xs font-medium leading-tight text-black shadow-sm transition-colors focus:border-violet-600 focus:outline-none focus:ring-2 focus:ring-violet-500/25 dark:bg-zinc-900 dark:text-zinc-100 dark:focus:border-zinc-500 dark:focus:ring-violet-500/20 sm:text-sm';

export const FILTER_SEARCH_INPUT =
    'box-border block h-9 min-w-0 w-full max-w-full rounded-md border border-lex-strong bg-white py-1.5 pl-7 pr-8 text-xs font-medium leading-tight text-black shadow-sm placeholder:text-neutral-500 transition-colors focus:border-violet-600 focus:outline-none focus:ring-2 focus:ring-violet-500/25 dark:bg-zinc-900 dark:text-zinc-100 dark:placeholder:text-zinc-500 dark:focus:border-zinc-500 dark:focus:ring-violet-500/20 sm:text-sm';

export const FILTER_BAR_SEARCH_INPUT =
    'box-border block h-9 min-w-0 w-full max-w-full rounded-md border border-lex-strong bg-white py-1.5 pl-7 pr-3 text-xs font-medium leading-tight text-black shadow-sm placeholder:text-neutral-500 transition-colors focus:border-violet-600 focus:outline-none focus:ring-2 focus:ring-violet-500/25 dark:bg-zinc-900 dark:text-zinc-100 dark:placeholder:text-zinc-500 dark:focus:border-zinc-500 dark:focus:ring-violet-500/20 sm:text-sm';

export const FILTER_TOGGLE_BUTTON =
    'box-border flex h-9 w-full cursor-pointer items-center justify-center gap-1 rounded-md border border-lex-strong bg-white px-2 text-xs font-semibold uppercase leading-tight tracking-wide text-black shadow-sm transition-colors hover:bg-neutral-100 focus:border-violet-600 focus:outline-none focus:ring-2 focus:ring-violet-500/25 dark:bg-zinc-900 dark:text-zinc-200 dark:hover:bg-zinc-800 dark:focus:border-zinc-500 dark:focus:ring-violet-500/20 sm:text-sm';

export const FILTER_CHROME_DIVIDER =
    'border-t border-lex pt-3';

export const FILTER_SEARCH_ICON_CLASS =
    'h-3.5 w-3.5 shrink-0 text-neutral-500 dark:text-zinc-400';

export const FILTER_FIELD_LABEL =
    'mb-0.5 block text-[10px] font-semibold uppercase tracking-wide text-neutral-600 dark:text-zinc-500';

export const APP_HEADER_SURFACE =
    'isolate border-b border-lex bg-white shadow-sm dark:bg-zinc-950';

export const SIDEBAR_ASIDE_SURFACE =
    'isolate border-r border-lex bg-neutral-50 shadow-sm dark:bg-zinc-950';

/** Active row: solid fill + violet left rail (only strong brand tint) */
export const SIDEBAR_NAV_ACTIVE =
    'border border-lex !border-l-[3px] !border-l-violet-600 bg-white text-black shadow-sm dark:bg-zinc-900 dark:!border-l-violet-500 dark:text-zinc-50';

export const SIDEBAR_NAV_IDLE =
    'border border-transparent !border-l-[3px] !border-l-transparent text-black hover:border-lex hover:!border-l-lex-strong hover:bg-neutral-100 dark:border-transparent dark:text-zinc-300 dark:hover:border-lex dark:hover:!border-l-lex-strong dark:hover:bg-zinc-900';

export const SIDEBAR_MOBILE_AUTH_CARD =
    'rounded-xl border border-lex bg-white p-4 shadow-sm dark:bg-zinc-900';
