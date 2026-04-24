import React from 'react';
import { ArrowRight, Globe, Share2, Smartphone } from 'lucide-react';
import { SignedOut } from '@clerk/clerk-react';
import LandingPwaInstallAnimation from './LandingPwaInstallAnimation';

/** Panels use scoped landing glass + global `--lex-border` / `--lex-ui-border-width` from index.css */
const LG = 'landing-glass';
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

/** Install steps + hero; on lg the two glass panels are vertically centered in the viewport (scroll if content is taller). */
const LandingPage = ({ onEnterApp }) => {
    return (
        <div className="landing-page flex min-h-[100dvh] flex-col bg-transparent font-sans text-gray-900 dark:text-gray-100 lg:h-[100dvh] lg:overflow-hidden">
            <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-2 overflow-y-auto px-3 pb-3 pt-[max(0.75rem,env(safe-area-inset-top))] sm:gap-2.5 sm:px-4 sm:pb-4 sm:pt-4 lg:min-h-0 lg:justify-center lg:gap-4 lg:overflow-y-auto lg:px-6 lg:py-3">
                <section id="install" className="scroll-mt-4 shrink-0">
                    <div className={`${LG} px-3 py-3 sm:px-4 sm:py-3.5 lg:px-5 lg:py-4`}>
                        <h2 className="font-display text-base font-semibold tracking-tight text-gray-900 dark:text-white sm:text-lg">
                            Install in three steps
                        </h2>
                        <p className="mt-0.5 max-w-2xl font-sans text-xs leading-snug text-slate-800 dark:text-zinc-200 sm:text-[13px]">
                            Add LexMatePH to your home screen for a focused, app-like experience.
                        </p>
                        <ol className="mt-2 grid list-none gap-2 pl-0 sm:mt-2.5 sm:grid-cols-3 sm:gap-2.5 lg:gap-3">
                            {INSTALL_STEPS.map(({ step, title, body, Icon }) => (
                                <li
                                    key={step}
                                    className="flex gap-2 rounded-lg border border-lex bg-white/95 p-2 dark:bg-slate-900/65 sm:gap-2.5 sm:p-2.5"
                                >
                                    <div
                                        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-gradient-to-br from-violet-600 to-indigo-700 text-white shadow-md shadow-indigo-900/25 ring-1 ring-indigo-900/20 dark:ring-white/10 sm:h-9 sm:w-9"
                                        aria-hidden
                                    >
                                        <Icon className="h-3.5 w-3.5 sm:h-4 sm:w-4" strokeWidth={2} />
                                    </div>
                                    <div className="min-w-0 flex-1">
                                        <p className="font-sans text-[10px] font-bold uppercase tracking-[0.14em] text-indigo-700 dark:text-indigo-300">
                                            Step {step}
                                        </p>
                                        <h3 className="mt-0.5 font-display text-xs font-semibold leading-snug text-gray-900 dark:text-white sm:text-sm">
                                            {title}
                                        </h3>
                                        <p className="mt-1 font-sans text-xs font-normal leading-snug text-slate-800 dark:text-zinc-200 sm:text-[13px] sm:leading-relaxed">
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
                        className="pointer-events-none absolute -right-8 bottom-0 h-36 w-36 rounded-full bg-violet-400/25 blur-[44px] dark:bg-violet-600/18"
                        aria-hidden
                    />
                    <div
                        className="pointer-events-none absolute left-1/3 top-0 h-24 w-56 -translate-x-1/2 rounded-full bg-amber-300/20 blur-[36px] dark:bg-amber-500/10"
                        aria-hidden
                    />
                    <div
                        className={`${LG_HERO} relative flex w-full min-w-0 max-w-full flex-col gap-3 px-3 py-3 max-lg:flex-col max-lg:items-center max-lg:gap-4 sm:max-lg:gap-4 sm:px-4 sm:py-4 lg:grid lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:items-center lg:gap-5 lg:px-6 lg:py-6 xl:grid-cols-[minmax(0,0.82fr)_minmax(0,1.18fr)] xl:gap-6 xl:px-7 xl:py-7`}
                    >
                        <div
                            className="pointer-events-none absolute inset-0 overflow-hidden rounded-[inherit]"
                            aria-hidden
                        >
                            <div className="absolute -left-1/4 -top-1/2 h-[90%] w-[70%] rounded-full bg-gradient-to-br from-white/85 via-white/35 to-transparent opacity-65 blur-2xl dark:from-indigo-300/14 dark:via-violet-400/10 dark:to-transparent dark:opacity-90" />
                            <div className="absolute -bottom-1/4 -right-1/4 h-[70%] w-[65%] rounded-full bg-gradient-to-tl from-amber-200/45 via-fuchsia-200/22 to-transparent opacity-55 blur-2xl dark:from-amber-400/14 dark:via-fuchsia-500/10 dark:to-transparent dark:opacity-85" />
                            <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/90 to-transparent dark:via-white/25" />
                        </div>
                        <div className="relative z-10 min-w-0 w-full max-lg:flex-1 max-lg:min-w-0 lg:max-w-[26rem] xl:max-w-[28rem]">
                            <h1 className="font-display text-xl font-semibold leading-[1.12] tracking-tight text-gray-900 dark:text-white max-lg:leading-snug sm:max-lg:text-2xl lg:text-[1.55rem] lg:leading-snug xl:text-2xl 2xl:text-3xl">
                                Master the Bar
                                <span className="mt-1 block bg-gradient-to-r from-indigo-700 via-violet-700 to-amber-700 bg-clip-text text-transparent dark:from-indigo-200 dark:via-violet-200 dark:to-amber-200 sm:mt-1.5 lg:mt-1">
                                    without the burnout with your all-in-one legal companion
                                </span>
                            </h1>
                            <p className="mt-2 max-w-xl text-xs leading-relaxed text-gray-700 dark:text-gray-300 max-lg:max-w-none sm:mt-3 sm:max-lg:text-sm lg:mt-2.5 lg:text-sm xl:text-[0.95rem]">
                                Built for law students, bar candidates, and practitioners: past bar questions, Supreme
                                Court decisions, evidence-grounded digests, major codals, flashcards, and LexPlay
                                listening—together in one fast, installable workspace.
                            </p>
                            <div className="mt-3 flex flex-wrap items-center gap-1.5 sm:mt-5 sm:gap-2 lg:mt-3.5 lg:gap-2.5">
                                <button
                                    type="button"
                                    onClick={onEnterApp}
                                    className="inline-flex max-w-full items-center justify-center gap-1.5 rounded-xl bg-amber-600 px-3 py-2 text-xs font-bold text-white shadow-lg shadow-amber-900/30 ring-1 ring-amber-400/50 transition-all hover:bg-amber-500 hover:shadow-[0_0_28px_-4px_rgba(245,158,11,0.5)] active:scale-[0.99] sm:gap-2 sm:px-6 sm:py-3 sm:text-base lg:px-5 lg:py-2.5 lg:text-sm xl:px-6 xl:py-3 xl:text-base"
                                >
                                    <span className="min-w-0 text-left leading-tight max-lg:max-w-[11rem] sm:max-lg:max-w-none">
                                        Start reviewing — it&apos;s free
                                    </span>
                                    <ArrowRight className="h-3.5 w-3.5 shrink-0 sm:h-5 sm:w-5 lg:h-4 lg:w-4 xl:h-5 xl:w-5" strokeWidth={2.25} />
                                </button>
                                <SignedOut>
                                    <span className="basis-full text-[10px] leading-snug text-gray-600 dark:text-gray-400 sm:text-sm lg:basis-auto lg:text-xs xl:text-sm">
                                        No credit card. Sign in when you&apos;re ready.
                                    </span>
                                </SignedOut>
                            </div>
                        </div>
                        <div className="relative z-10 mt-0 flex shrink-0 items-center justify-center max-lg:w-[min(7.25rem,28vw)] max-lg:self-center min-[480px]:max-lg:w-[min(8rem,30vw)] lg:mt-0 lg:block lg:min-w-0 lg:w-auto lg:overflow-x-hidden">
                            <LandingPwaInstallAnimation compact dense heroMobile />
                        </div>
                    </div>
                </section>
            </div>
        </div>
    );
};

export default LandingPage;
