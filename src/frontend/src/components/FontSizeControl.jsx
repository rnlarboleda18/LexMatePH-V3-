import React from 'react';

/**
 * A- / A+ buttons for dynamic font size control.
 * Designed for modal toolbars on mobile/tablet readers.
 */
export default function FontSizeControl({ fontSize, onIncrease, onDecrease, className = '' }) {
    return (
        <div className={`flex items-center gap-0.5 ${className}`} onClick={(e) => e.stopPropagation()}>
            <button
                type="button"
                onClick={onDecrease}
                className="touch-manipulation flex h-7 items-center justify-center rounded-l-md border border-gray-200/80 bg-gray-50/90 px-1.5 text-[11px] font-bold leading-none text-gray-500 transition-all hover:bg-gray-100 active:scale-95 select-none dark:border-zinc-700 dark:bg-zinc-800/60 dark:text-zinc-400 dark:hover:bg-zinc-700/60"
                title="Decrease font size"
                aria-label="Decrease font size"
            >
                A−
            </button>
            <button
                type="button"
                onClick={onIncrease}
                className="touch-manipulation flex h-7 items-center justify-center rounded-r-md border border-l-0 border-gray-200/80 bg-gray-50/90 px-1.5 text-[13px] font-bold leading-none text-gray-500 transition-all hover:bg-gray-100 active:scale-95 select-none dark:border-zinc-700 dark:bg-zinc-800/60 dark:text-zinc-400 dark:hover:bg-zinc-700/60"
                title="Increase font size"
                aria-label="Increase font size"
            >
                A+
            </button>
        </div>
    );
}
