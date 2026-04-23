import React from 'react';
import { ArrowRight, Globe, Share2, Smartphone, Moon, Sun } from 'lucide-react';
import { SignedIn, SignedOut, SignInButton, SignUpButton, UserButton } from '@clerk/clerk-react';
import LandingPwaInstallAnimation from './LandingPwaInstallAnimation';

/** Hero + device mockups — same glass treatment as before */
const LG_HERO = 'landing-glass-hero';

const INSTALL_STEPS = [
    {
        step: '1',
        title: 'Open LexMatePH',
        body: 'Use Safari on iPhone and iPad. Use Chrome on Android tablets, phones, and desktop.',
        Icon: Globe,
    },
    {
        step: '2',
        title: 'Install the app',
        body: 'iPhone: Share (↑), then Add to Home Screen. Android or desktop: tap Install, or ⋮ → Install app.',
        Icon: Share2,
    },
    {
        step: '3',
        title: 'Open from your home screen',
        body: 'Tap the LexMatePH icon. On iPhone, turn on Open as Web App if you see that option.',
        Icon: Smartphone,
    },
];

/**
 * Minimal marketing landing: install steps + hero only.
 * Layout is compressed so both blocks fit one viewport on typical laptops (scroll on very small heights).
 */
const LandingPage = ({ isDarkMode, toggleTheme, onEnterApp }) => {
    return (
        <div className="landing-page flex min-h-[100dvh] flex-col bg-transparent font-sans text-gray-900 dark:text-gray-100 lg:h-[100dvh] lg:overflow-hidden">
            {/* Floating chrome — no glass tile */}
            <div
                className="fixed right-0 top-0 z-50 flex items-center gap-1.5 p-3 pr-[max(0.75rem,env(safe-area-inset-right))] pt-[max(0.75rem,env(safe-area-inset-top))] sm:gap-2 sm:p-4"
                data-lex-landing-chrome
            >
                <button
                    type="button"
                    onClick={toggleTheme}
                    className="flex h-10 w-10 items-center justify-center rounded-full border border-gray-200/90 bg-white/90 text-gray-700 shadow-sm backdrop-blur-sm transition-colors hover:bg-gray-50 dark:border-white/15 dark:bg-slate-900/80 dark:text-gray-200 dark:hover:bg-slate-800/90"
                    aria-label={isDarkMode ? 'Light mode' : 'Dark mode'}
                >
                    {isDarkMode ? <Sun className="h-4 w-4 text-amber-400" /> : <Moon className="h-4 w-4 text-violet-600" />}
                </button>
                <div className="flex items-center gap-1 rounded-full border border-gray-200/90 bg-white/90 px-1 py-1 shadow-sm backdrop-blur-sm dark:border-white/15 dark:bg-slate-900/80">
                    <SignedIn>
                        <UserButton appearance={{ elements: { userButtonAvatarBox: 'w-9 h-9' } }} />
                    </SignedIn>
                    <SignedOut>
                        <SignInButton mode="modal">
                            <button
                                type="button"
                                className="rounded-full px-3 py-1.5 text-sm font-medium text-gray-800 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-white/10"
                            >
                                Log in
                            </button>
                        </SignInButton>
                        <SignUpButton mode="modal">
                            <button
                                type="button"
                                className="rounded-full bg-amber-600 px-3 py-1.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-amber-500"
                            >
                                Sign up
                            </button>
                        </SignUpButton>
                    </SignedOut>
                </div>
            </div>

            <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-2 overflow-y-auto px-3 pb-3 pt-[3.25rem] sm:gap-2.5 sm:px-4 sm:pt-14 lg:min-h-0 lg:justify-center lg:gap-3 lg:overflow-y-auto lg:px-6 lg:pb-4 lg:pt-16">
                <section id="install" className="scroll-mt-6 shrink-0">
                    <div className="rounded-xl border border-slate-200/90 bg-white/75 px-3 py-3 shadow-sm backdrop-blur-md dark:border-white/10 dark:bg-slate-950/50 sm:px-4 sm:py-3.5">
                        <h2 className="font-display text-base font-semibold tracking-tight text-slate-900 dark:text-white sm:text-lg">
                            Install in three steps
                        </h2>
                        <p className="mt-0.5 max-w-2xl text-xs text-slate-600 dark:text-slate-400 sm:text-[13px]">
                            Add LexMatePH to your home screen for a focused, app-like experience.
                        </p>
                        <ol className="mt-2.5 grid list-none gap-2 pl-0 sm:mt-3 sm:grid-cols-3 sm:gap-2.5 lg:gap-3">
                            {INSTALL_STEPS.map(({ step, title, body, Icon }) => (
                                <li
                                    key={step}
                                    className="flex gap-2.5 rounded-lg border border-slate-200/80 bg-white/90 p-2.5 shadow-[0_1px_2px_rgba(15,23,42,0.04)] dark:border-white/10 dark:bg-slate-900/40 sm:gap-3 sm:p-3"
                                >
                                    <div
                                        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-violet-600 to-indigo-700 text-white shadow-md shadow-indigo-900/20 sm:h-10 sm:w-10"
                                        aria-hidden
                                    >
                                        <Icon className="h-4 w-4 sm:h-[18px] sm:w-[18px]" strokeWidth={2} />
                                    </div>
                                    <div className="min-w-0 flex-1">
                                        <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-indigo-600 dark:text-indigo-400">
                                            Step {step}
                                        </p>
                                        <h3 className="mt-0.5 font-display text-sm font-semibold leading-snug text-slate-900 dark:text-white">
                                            {title}
                                        </h3>
                                        <p className="mt-1 text-xs leading-snug text-slate-600 dark:text-slate-400 sm:mt-1.5 sm:text-[13px] sm:leading-relaxed">
                                            {body}
                                        </p>
                                    </div>
                                </li>
                            ))}
                        </ol>
                    </div>
                </section>

                <section className="relative min-h-0 min-w-0 shrink-0 lg:shrink">
                    <div
                        className="pointer-events-none absolute -left-12 top-1/4 h-40 w-40 rounded-full bg-indigo-400/30 blur-[48px] dark:bg-indigo-500/20 lg:h-32 lg:w-32"
                        aria-hidden
                    />
                    <div
                        className="pointer-events-none absolute -right-8 bottom-0 h-36 w-36 rounded-full bg-violet-400/25 blur-[44px] dark:bg-violet-600/18 lg:h-28 lg:w-28"
                        aria-hidden
                    />
                    <div
                        className="pointer-events-none absolute left-1/3 top-0 h-28 w-56 -translate-x-1/2 rounded-full bg-amber-300/20 blur-[40px] dark:bg-amber-500/10"
                        aria-hidden
                    />
                    <div
                        className={`${LG_HERO} relative w-full min-w-0 max-w-full px-4 py-3 sm:px-5 sm:py-4 lg:grid lg:grid-cols-[minmax(0,0.88fr)_minmax(0,1.12fr)] lg:items-center lg:gap-5 lg:px-5 lg:py-3 xl:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] xl:gap-6`}
                    >
                        <div
                            className="pointer-events-none absolute inset-0 overflow-hidden rounded-[inherit]"
                            aria-hidden
                        >
                            <div className="absolute -left-1/4 -top-1/2 h-[90%] w-[70%] rounded-full bg-gradient-to-br from-white/85 via-white/35 to-transparent opacity-65 blur-2xl dark:from-indigo-300/14 dark:via-violet-400/10 dark:to-transparent dark:opacity-90" />
                            <div className="absolute -bottom-1/4 -right-1/4 h-[70%] w-[65%] rounded-full bg-gradient-to-tl from-amber-200/45 via-fuchsia-200/22 to-transparent opacity-55 blur-2xl dark:from-amber-400/14 dark:via-fuchsia-500/10 dark:to-transparent dark:opacity-85" />
                            <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/90 to-transparent dark:via-white/25" />
                        </div>
                        <div className="relative z-10 min-w-0 lg:max-w-none">
                            <h1 className="font-display text-2xl font-semibold leading-[1.12] tracking-tight text-gray-900 dark:text-white sm:text-3xl lg:text-[1.65rem] lg:leading-snug xl:text-3xl">
                                Master the Bar
                                <span className="mt-1 block bg-gradient-to-r from-indigo-700 via-violet-700 to-amber-700 bg-clip-text text-transparent dark:from-indigo-200 dark:via-violet-200 dark:to-amber-200 sm:mt-1.5 lg:mt-1 lg:text-[1.05em]">
                                    without the burnout with your all-in-one legal companion
                                </span>
                            </h1>
                            <p className="mt-3 max-w-xl text-sm leading-relaxed text-gray-600 dark:text-gray-400 sm:text-[0.95rem] lg:mt-2.5 lg:text-sm xl:text-[0.95rem]">
                                Built for law students, bar candidates, and practitioners: past bar questions, Supreme
                                Court decisions, evidence-grounded digests, major codals, flashcards, and LexPlay
                                listening—together in one fast, installable workspace.
                            </p>
                            <div className="mt-4 flex flex-wrap items-center gap-2 sm:mt-5 lg:mt-4">
                                <button
                                    type="button"
                                    onClick={onEnterApp}
                                    className="inline-flex items-center justify-center gap-2 rounded-xl bg-amber-600 px-5 py-2.5 text-sm font-bold text-white shadow-lg shadow-amber-900/30 ring-1 ring-amber-400/50 transition-all hover:bg-amber-500 hover:shadow-[0_0_28px_-4px_rgba(245,158,11,0.5)] active:scale-[0.99] sm:px-6 sm:py-3 sm:text-base lg:px-5 lg:py-2.5 lg:text-sm xl:text-base"
                                >
                                    Start reviewing — it&apos;s free
                                    <ArrowRight className="h-4 w-4 shrink-0 sm:h-5 sm:w-5 lg:h-4 lg:w-4 xl:h-5 xl:w-5" strokeWidth={2.25} />
                                </button>
                                <SignedOut>
                                    <span className="text-xs text-gray-500 dark:text-gray-400 sm:text-sm lg:text-xs xl:text-sm">
                                        No credit card. Sign in when you&apos;re ready.
                                    </span>
                                </SignedOut>
                            </div>
                        </div>
                        <div className="relative z-10 mt-3 min-w-0 overflow-x-hidden sm:mt-4 lg:mt-0">
                            <LandingPwaInstallAnimation compact dense />
                        </div>
                    </div>
                </section>
            </div>
        </div>
    );
};

export default LandingPage;
