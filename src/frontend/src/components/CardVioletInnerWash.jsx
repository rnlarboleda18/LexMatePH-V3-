import React from 'react';

/**
 * Soft violet/purple corner glow inside bordered cards (matches About / Updates hero).
 * Parent must be `relative overflow-hidden` with a matching `rounded-*`.
 */
export default function CardVioletInnerWash() {
    return (
        <div
            className="pointer-events-none absolute inset-0 overflow-hidden rounded-[inherit]"
            aria-hidden
        >
            <div className="absolute -right-8 -top-16 h-36 w-36 rounded-full bg-gradient-to-br from-purple-400/22 to-fuchsia-500/14 blur-2xl dark:from-purple-500/14 dark:to-fuchsia-600/10" />
            <div className="absolute -bottom-10 left-0 h-32 w-48 rounded-full bg-violet-400/16 blur-2xl dark:bg-violet-500/12" />
            <div className="absolute right-1/3 top-1/2 h-20 w-20 -translate-y-1/2 rounded-full bg-indigo-400/12 blur-xl dark:bg-indigo-500/10" />
        </div>
    );
}
