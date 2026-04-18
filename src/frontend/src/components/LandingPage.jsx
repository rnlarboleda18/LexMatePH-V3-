import React from 'react';
import {
    ArrowRight,
    BookOpen,
    Gavel,
    Globe,
    Headphones,
    Library,
    Moon,
    Scale,
    Share2,
    Shield,
    Smartphone,
    Sun,
    Zap,
} from 'lucide-react';
import { SignedIn, SignedOut, SignInButton, SignUpButton, UserButton } from '@clerk/clerk-react';
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
 * Copy echoes About: one workspace, engineered digests, verify primary sources.
 */
const LandingPage = ({ isDarkMode, toggleTheme, onEnterApp }) => {
    return (
        <div className="landing-page min-h-screen bg-transparent font-sans text-gray-900 dark:text-gray-100">
            <div className="mx-auto flex w-full max-w-7xl flex-col gap-3 px-3 pb-20 pt-[max(1rem,env(safe-area-inset-top))] sm:gap-4 sm:px-5 sm:pb-24 sm:pt-6 lg:px-6">
                <div className={isDarkMode ? 'dark' : ''} data-lex-landing-chrome>
                    <header className="landing-page relative w-full">
                        <div
                            className={`${LG} landing-glass-header flex w-full items-center justify-between gap-3 px-4 py-2.5 sm:px-5 sm:py-3 lg:px-6`}
                        >
                            <div className="flex min-w-0 items-center gap-2.5">
                                <div
                                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-purple-600 to-violet-600 text-white shadow-md shadow-purple-600/30"
                                    aria-hidden
                                >
                                    <Scale className="h-5 w-5" strokeWidth={2} />
                                </div>
                                <div className="min-w-0">
                                    <span className="font-display block truncate text-lg font-semibold tracking-tight sm:text-xl">
                                        LexMatePH
                                    </span>
                                    <span className="hidden text-[10px] font-semibold uppercase tracking-[0.16em] text-gray-500 dark:text-gray-400 sm:block">
                                        Your legal companion
                                    </span>
                                </div>
                            </div>
                            <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
                                <button
                                    type="button"
                                    onClick={toggleTheme}
                                    className="flex h-9 w-9 items-center justify-center rounded-xl border-2 border-transparent text-gray-700 transition-colors hover:border-amber-300/90 hover:bg-amber-50 hover:text-amber-900 dark:text-gray-300 dark:hover:border-amber-800/40 dark:hover:bg-amber-900/20 dark:hover:text-amber-300"
                                    aria-label={isDarkMode ? 'Light mode' : 'Dark mode'}
                                >
                                    {isDarkMode ? <Sun className="h-4 w-4 text-amber-400" /> : <Moon className="h-4 w-4 text-violet-600" />}
                                </button>
                                <div className="flex items-center gap-1">
                                    <SignedIn>
                                        <UserButton appearance={{ elements: { userButtonAvatarBox: 'w-9 h-9' } }} />
                                    </SignedIn>
                                    <SignedOut>
                                        <SignInButton mode="modal">
                                            <button
                                                type="button"
                                                className="rounded-lg px-2.5 py-1.5 text-sm font-semibold text-gray-800 hover:bg-white/80 dark:text-gray-200 dark:hover:bg-white/10 sm:px-3"
                                            >
                                                Log in
                                            </button>
                                        </SignInButton>
                                        <SignUpButton mode="modal">
                                            <button
                                                type="button"
                                                className="rounded-lg bg-amber-600 px-2.5 py-1.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-amber-500 sm:px-3"
                                            >
                                                Sign up
                                            </button>
                                        </SignUpButton>
                                    </SignedOut>
                                </div>
                            </div>
                        </div>
                    </header>
                </div>
                {/* Single 12-col grid: install steps first (compact), then hero; twin tiles span 6+6 */}
                <div className="grid w-full min-w-0 grid-cols-1 gap-3 md:grid-cols-12 md:gap-4">
                <section id="install" className="scroll-mt-8 col-span-12 min-w-0">
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

                <section className="relative col-span-12 min-w-0">
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
                        {/* Specular + rim light (does not participate in grid) */}
                        <div
                            className="pointer-events-none absolute inset-0 overflow-hidden rounded-[inherit]"
                            aria-hidden
                        >
                            <div className="absolute -left-1/4 -top-1/2 h-[90%] w-[70%] rounded-full bg-gradient-to-br from-white/85 via-white/35 to-transparent opacity-65 blur-2xl dark:from-indigo-300/14 dark:via-violet-400/10 dark:to-transparent dark:opacity-90" />
                            <div className="absolute -bottom-1/4 -right-1/4 h-[70%] w-[65%] rounded-full bg-gradient-to-tl from-amber-200/45 via-fuchsia-200/22 to-transparent opacity-55 blur-2xl dark:from-amber-400/14 dark:via-fuchsia-500/10 dark:to-transparent dark:opacity-85" />
                            <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/90 to-transparent dark:via-white/25" />
                        </div>
                        <div className="relative z-10 min-w-0 lg:max-w-[27rem] xl:max-w-[32rem]">
                            <h1 className="font-display text-3xl font-semibold leading-[1.12] tracking-tight text-gray-900 dark:text-white sm:text-4xl md:text-5xl lg:text-[1.75rem] lg:leading-snug xl:text-3xl 2xl:text-4xl">
                                Master the Bar
                                <span className="mt-1.5 block bg-gradient-to-r from-indigo-700 via-violet-700 to-amber-700 bg-clip-text text-transparent dark:from-indigo-200 dark:via-violet-200 dark:to-amber-200 sm:mt-2 lg:mt-1.5">
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
                                    className="inline-flex items-center justify-center gap-2 rounded-xl bg-amber-600 px-6 py-3.5 text-base font-bold text-white shadow-lg shadow-amber-900/30 ring-1 ring-amber-400/50 transition-all hover:bg-amber-500 hover:shadow-[0_0_32px_-4px_rgba(245,158,11,0.55)] active:scale-[0.99] sm:px-8 sm:text-lg lg:px-5 lg:py-2.5 lg:text-sm xl:px-6 xl:py-3 xl:text-base"
                                >
                                    Start reviewing — it&apos;s free
                                    <ArrowRight className="h-5 w-5 shrink-0 lg:h-4 lg:w-4 xl:h-5 xl:w-5" strokeWidth={2.25} />
                                </button>
                                <SignedOut>
                                    <span className="text-sm text-gray-500 dark:text-gray-400 lg:text-xs xl:text-sm">
                                        No credit card. Sign in when you&apos;re ready.
                                    </span>
                                </SignedOut>
                            </div>
                        </div>

                        {/* Compact PWA install walkthrough — no extra glass shell; sits in hero grid cell */}
                        <div className="relative z-10 mt-4 min-w-0 overflow-x-hidden lg:mt-0">
                            <LandingPwaInstallAnimation compact />
                        </div>
                    </div>
                </section>

                    <div className={`${LG} col-span-12 min-w-0 p-6 sm:p-8 md:col-span-6`}>
                        <h2 className="font-display text-xl font-semibold tracking-tight text-gray-900 dark:text-white sm:text-2xl">
                            When prep feels heavier than the syllabus
                        </h2>
                        <p className="mt-4 text-sm leading-relaxed text-gray-600 dark:text-gray-400 sm:text-base">
                            Outlines sprawl across drives, portals lag, and the bar is still a single sitting. You need a
                            way to rehearse doctrines, scan digests for orientation, and drill questions without living
                            inside a PDF reader.
                        </p>
                    </div>
                    <div className={`${LG} col-span-12 min-w-0 p-6 sm:p-8 md:col-span-6`}>
                        <h2 className="font-display text-xl font-semibold tracking-tight text-gray-900 dark:text-white sm:text-2xl">
                            One workspace, built for the Philippine setting
                        </h2>
                        <p className="mt-4 text-sm leading-relaxed text-gray-600 dark:text-gray-400 sm:text-base">
                            LexMatePH keeps codals, SC materials, bar items, flashcards, and audio in reach so you can
                            move between modes of study—reading, listening, and recall—without juggling five different
                            tools.
                        </p>
                    </div>
                </div>

                {/* Pillars — icon colors echo About.jsx feature chips */}
                <section>
                    <h2 className="font-display text-center text-xl font-semibold tracking-tight text-gray-900 dark:text-white sm:text-2xl md:text-3xl">
                        Why candidates open LexMatePH
                    </h2>
                    <p className="mx-auto mt-2 max-w-2xl text-center text-sm text-gray-600 dark:text-gray-400">
                        Same spirit as the rest of the app: structured review, literal attention to sources, LexMatePH is
                        your all-in-one legal companion.
                    </p>
                    <div className="mt-4 grid gap-3 md:grid-cols-3 md:gap-4">
                        {[
                            {
                                icon: Zap,
                                chip: 'bg-amber-100 text-amber-800 dark:bg-amber-900/35 dark:text-amber-300',
                                title: 'Open in seconds',
                                body: 'No app-store queue. Add LexMatePH to your home screen from the browser and jump straight into review.',
                            },
                            {
                                icon: Gavel,
                                chip: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400',
                                title: 'Engineered digests',
                                body: 'Browse Supreme Court decisions and digests grounded in the text of each decision—meant for orientation; always verify with official sources.',
                            },
                            {
                                icon: Library,
                                chip: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
                                title: 'Codals & bar questions',
                                body: 'Major codals and past Philippine Bar Examination questions with suggested answers, side by side with LexCode and Lexify where your plan allows.',
                            },
                        ].map(({ icon: Icon, chip, title, body }) => (
                            <div key={title} className={`${LG} p-6 sm:p-8`}>
                                <div className={`mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl ${chip}`}>
                                    <Icon className="h-6 w-6" strokeWidth={2} />
                                </div>
                                <h3 className="font-display text-lg font-semibold text-gray-900 dark:text-white">{title}</h3>
                                <p className="mt-3 text-sm leading-relaxed text-gray-600 dark:text-gray-400">{body}</p>
                            </div>
                        ))}
                    </div>
                    <div className="mt-3 grid gap-3 sm:grid-cols-2 sm:gap-4">
                        <div className={`${LG} flex gap-4 p-5 sm:p-6`}>
                            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">
                                <Headphones className="h-5 w-5" strokeWidth={2} />
                            </div>
                            <div>
                                <h3 className="font-display text-base font-semibold text-gray-900 dark:text-white">LexPlay</h3>
                                <p className="mt-2 text-sm leading-relaxed text-gray-600 dark:text-gray-400">
                                    Listen to LexMatePH audio alongside reading—codals, digests, and more when your plan
                                    includes it.
                                </p>
                            </div>
                        </div>
                        <div className={`${LG} flex gap-4 p-5 sm:p-6`}>
                            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400">
                                <BookOpen className="h-5 w-5" strokeWidth={2} />
                            </div>
                            <div>
                                <h3 className="font-display text-base font-semibold text-gray-900 dark:text-white">Offline-friendly</h3>
                                <p className="mt-2 text-sm leading-relaxed text-gray-600 dark:text-gray-400">
                                    As a PWA, core assets can stay cached for smoother sessions on shaky campus Wi‑Fi or
                                    long commutes.
                                </p>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Reliability — no cross-device sync claims */}
                <section>
                    <div className={`${LG} flex flex-col gap-4 p-6 sm:flex-row sm:items-center sm:gap-6 sm:p-8`}>
                        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-sky-100 text-sky-800 dark:bg-sky-900/35 dark:text-sky-300">
                            <Shield className="h-7 w-7" strokeWidth={2} />
                        </div>
                        <div className="min-w-0 flex-1">
                            <h2 className="font-display text-lg font-semibold text-gray-900 dark:text-white sm:text-xl">
                                Serious infrastructure for serious study
                            </h2>
                            <p className="mt-2 text-sm leading-relaxed text-gray-600 dark:text-gray-400 sm:text-base">
                                LexMatePH is served from a modern Azure stack—API, database, and storage designed for
                                reliability while you work through dense material. Content is for education and research,
                                not legal advice; always confirm critical points against primary sources and the latest
                                jurisprudence.
                            </p>
                        </div>
                    </div>
                </section>

                {/* Closing — glass + CTA */}
                <section>
                    <div className={`${LG} p-6 text-center sm:p-8`}>
                        <p className="font-display text-lg font-medium italic leading-snug text-gray-800 dark:text-gray-200 sm:text-xl md:text-2xl">
                            Active recall, careful reading, and respect for the text of the law—tools for the pace of
                            Philippine legal study.
                        </p>
                        <p className="mx-auto mt-4 max-w-lg text-xs leading-relaxed text-gray-500 dark:text-gray-500 sm:text-sm">
                            Digests and summaries may be AI-assisted; they are for quick orientation only. LexMatePH
                            does not replace professional judgment or counsel.
                        </p>
                        <button
                            type="button"
                            onClick={onEnterApp}
                            className="mt-8 inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-8 py-3.5 text-base font-bold text-white shadow-lg shadow-indigo-900/25 ring-1 ring-white/25 transition-all hover:opacity-95 hover:shadow-[0_0_36px_-4px_rgba(99,102,241,0.55)] dark:from-indigo-500 dark:to-violet-500 dark:shadow-indigo-950/40 dark:ring-white/15"
                        >
                            Enter the workspace
                            <ArrowRight className="h-5 w-5" />
                        </button>
                    </div>
                </section>
            </div>
        </div>
    );
};

export default LandingPage;
