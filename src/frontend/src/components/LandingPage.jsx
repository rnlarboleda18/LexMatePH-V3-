import React from 'react';
import { ArrowRight, Globe, Scale, Share2, Smartphone } from 'lucide-react';
import { SignedOut } from '@clerk/clerk-react';
import LandingPwaInstallAnimation from './LandingPwaInstallAnimation';

/** Scoped “premium glass” — see index.css `.landing-page .landing-glass*`. */
const LG = 'landing-glass rounded-2xl';
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
 * Marketing landing — pronounced glassmorphism (scoped CSS + layered highlights).
 */
const LandingPage = ({ isDarkMode, onEnterApp }) => {
    return (
        <div className="landing-page min-h-screen bg-transparent font-sans text-gray-900 dark:text-gray-100">
            <div
                className={`mx-auto flex w-full max-w-7xl flex-col gap-3 px-3 pb-20 pt-[max(1rem,env(safe-area-inset-top))] sm:gap-4 sm:px-5 sm:pb-24 sm:pt-6 lg:px-6 ${isDarkMode ? 'dark' : ''}`}
                data-lex-landing-chrome
            >
                <div className="flex w-full min-w-0 flex-col gap-3 md:gap-4">
                    <section className="relative min-w-0">
                        <div
                            className="pointer-events-none absolute -left-16 top-1/4 h-56 w-56 rounded-full bg-indigo-400/35 blur-[56px] dark:bg-indigo-500/25"
                            aria-hidden
                        />
                        <div
                            className="pointer-events-none absolute -right-12 bottom-0 h-52 w-52 rounded-full bg-violet-400/30 blur-[52px] dark:bg-violet-600/22"
                            aria-hidden
                        />
                        <div
                            className="pointer-events-none absolute left-1/3 top-0 h-40 w-72 -translate-x-1/2 rounded-full bg-amber-300/25 blur-[48px] dark:bg-amber-500/12"
                            aria-hidden
                        />
                        <div
                            className={`${LG_HERO} relative w-full min-w-0 max-w-full px-6 py-[calc(1.5rem-0.5cm)] sm:px-8 sm:py-[calc(2rem-0.5cm)] lg:grid lg:grid-cols-[minmax(0,0.82fr)_minmax(0,1.18fr)] lg:items-center lg:gap-5 lg:gap-x-6 lg:px-6 lg:py-[calc(1.5rem-0.5cm)] xl:grid-cols-[minmax(0,0.78fr)_minmax(0,1.22fr)] xl:gap-x-8 xl:px-7 xl:py-[calc(1.75rem-0.5cm)]`}
                        >
                            <div
                                className="pointer-events-none absolute inset-0 overflow-hidden rounded-[inherit]"
                                aria-hidden
                            >
                                <div className="absolute -left-1/4 -top-1/2 h-[90%] w-[70%] rounded-full bg-gradient-to-br from-white/85 via-white/35 to-transparent opacity-65 blur-2xl dark:from-indigo-300/14 dark:via-violet-400/10 dark:to-transparent dark:opacity-90" />
                                <div className="absolute -bottom-1/4 -right-1/4 h-[70%] w-[65%] rounded-full bg-gradient-to-tl from-amber-200/45 via-fuchsia-200/22 to-transparent opacity-55 blur-2xl dark:from-amber-400/14 dark:via-fuchsia-500/10 dark:to-transparent dark:opacity-85" />
                                <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/90 to-transparent dark:via-white/25" />
                            </div>
                            <div className="relative z-10 min-w-0 lg:max-w-[27rem] xl:max-w-[32rem]">
                                <div className="mb-4 flex min-w-0 items-center gap-3 sm:mb-5 sm:gap-3.5 lg:mb-4">
                                    <div
                                        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-purple-600 to-violet-600 text-white shadow-md shadow-purple-600/30 sm:h-12 sm:w-12"
                                        aria-hidden
                                    >
                                        <Scale className="h-5 w-5 sm:h-6 sm:w-6" strokeWidth={2} />
                                    </div>
                                    <div className="min-w-0">
                                        <span className="font-display block truncate text-base font-semibold tracking-tight text-gray-900 dark:text-zinc-50 sm:text-lg">
                                            LexMatePH
                                        </span>
                                        <span className="mt-0.5 block text-[10px] font-semibold uppercase tracking-[0.16em] text-gray-500 dark:text-gray-400 sm:text-[11px]">
                                            Your legal companion
                                        </span>
                                    </div>
                                </div>
                                <h1 className="font-display text-xl font-semibold leading-snug tracking-tight text-gray-900 dark:text-white sm:text-2xl md:text-[1.65rem] lg:text-xl lg:leading-snug xl:text-2xl">
                                    Master the Bar
                                    <span className="mt-1 block bg-gradient-to-r from-indigo-700 via-violet-700 to-amber-700 bg-clip-text text-base font-semibold leading-snug text-transparent dark:from-indigo-200 dark:via-violet-200 dark:to-amber-200 sm:mt-1.5 sm:text-lg md:text-[1.125rem] lg:mt-1 lg:text-base xl:text-[1.125rem]">
                                        without the burnout with your all-in-one legal companion
                                    </span>
                                </h1>
                                <p className="mt-5 max-w-xl text-base leading-relaxed text-gray-600 dark:text-gray-400 sm:text-lg lg:mt-4 lg:max-w-none lg:text-sm lg:leading-relaxed xl:text-[0.95rem]">
                                    Built for law students, bar candidates, and practitioners: past bar questions, Supreme
                                    Court decisions, evidence-grounded digests, major codals, flashcards, and LexPlay
                                    listening—together in one fast, installable workspace.
                                </p>
                                <div className="mt-8 flex flex-wrap items-center gap-3 lg:mt-5 lg:gap-2.5">
                                    <button
                                        type="button"
                                        onClick={onEnterApp}
                                        className="inline-flex max-w-full items-center justify-center gap-2 rounded-xl bg-amber-600 px-4 py-3 text-center text-sm font-bold leading-snug text-white shadow-lg shadow-amber-900/30 ring-1 ring-amber-400/50 transition-all hover:bg-amber-500 hover:shadow-[0_0_32px_-4px_rgba(245,158,11,0.55)] active:scale-[0.99] sm:px-6 sm:py-3.5 sm:text-base lg:px-5 lg:py-2.5 lg:text-sm xl:px-6 xl:py-3 xl:text-base"
                                        aria-label="Subscribe or try it for free — opens subscription plans"
                                    >
                                        Subscribe or try it for free
                                        <ArrowRight className="h-4 w-4 shrink-0 sm:h-5 sm:w-5 lg:h-4 lg:w-4 xl:h-5 xl:w-5" strokeWidth={2.25} />
                                    </button>
                                    <SignedOut>
                                        <span className="text-sm text-gray-500 dark:text-gray-400 lg:text-xs xl:text-sm">
                                            No credit card. Sign in when you&apos;re ready.
                                        </span>
                                    </SignedOut>
                                </div>
                            </div>

                            <div className="relative z-10 mt-4 min-w-0 overflow-x-hidden lg:mt-0">
                                <LandingPwaInstallAnimation compact />
                            </div>
                        </div>
                    </section>

                    <section id="install" className="scroll-mt-8 min-w-0">
                        <div className={`${LG_HERO} relative overflow-hidden p-3 sm:p-4`}>
                            <div className="pointer-events-none absolute inset-0" aria-hidden>
                                <div className="absolute -left-12 top-1/2 h-16 w-16 -translate-y-1/2 rounded-full bg-indigo-400/20 blur-xl dark:bg-indigo-500/14" />
                                <div className="absolute -right-8 bottom-0 h-14 w-14 rounded-full bg-violet-400/18 blur-xl dark:bg-violet-500/12" />
                                <div className="absolute inset-x-6 top-0 h-px bg-gradient-to-r from-transparent via-white/80 to-transparent dark:via-white/20" />
                            </div>
                            <div className="relative z-10">
                                <h2 className="font-display text-lg font-semibold text-gray-900 dark:text-white sm:text-xl">
                                    Install in three steps
                                </h2>
                                <ol className="mt-3 grid list-none gap-3 pl-0 sm:grid-cols-3 sm:gap-4">
                                    {INSTALL_STEPS.map(({ step, title, body, Icon }) => (
                                        <li key={step} className={`${LG} flex gap-3 p-3 sm:p-4`}>
                                            <div
                                                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-md dark:bg-indigo-500"
                                                aria-hidden
                                            >
                                                <Icon className="h-5 w-5" strokeWidth={2} />
                                            </div>
                                            <div className="min-w-0 flex-1">
                                                <p className="text-[11px] font-bold uppercase tracking-wide text-indigo-600 dark:text-indigo-400">
                                                    Step {step}
                                                </p>
                                                <h3 className="mt-0.5 font-display text-sm font-semibold leading-snug text-gray-900 dark:text-white sm:text-base">
                                                    {title}
                                                </h3>
                                                <p className="mt-2 text-sm leading-relaxed text-gray-700 dark:text-gray-300">
                                                    {body}
                                                </p>
                                            </div>
                                        </li>
                                    ))}
                                </ol>
                            </div>
                        </div>
                    </section>
                </div>
            </div>
        </div>
    );
};

export default LandingPage;
