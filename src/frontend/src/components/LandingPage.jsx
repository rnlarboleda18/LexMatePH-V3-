import React from 'react';
import { createPortal } from 'react-dom';
import {
    ArrowRight,
    BookOpen,
    Gavel,
    Headphones,
    Library,
    Moon,
    Scale,
    Shield,
    Smartphone,
    Sparkles,
    Sun,
    Zap,
} from 'lucide-react';
import { SignedIn, SignedOut, SignInButton, SignUpButton, UserButton } from '@clerk/clerk-react';

/** Scoped “premium glass” — see index.css `.landing-page .landing-glass*`. */
const LG = 'landing-glass rounded-2xl';
const LG_HERO = 'landing-glass-hero';
const LG_NEST = 'landing-glass-nested';

/**
 * Marketing landing — pronounced glassmorphism (scoped CSS + layered highlights).
 * Copy echoes About: one workspace, engineered digests, verify primary sources.
 */
const LandingPage = ({ isDarkMode, toggleTheme, onEnterApp }) => {
    const landingHeader =
        typeof document !== 'undefined' ? (
            createPortal(
                <div className={isDarkMode ? 'dark' : ''} data-lex-landing-chrome>
                    <header className="landing-page fixed top-0 left-0 right-0 z-50 px-3 pt-[max(0.5rem,env(safe-area-inset-top))] pb-2 sm:px-5">
                        <div
                            className={`${LG} landing-glass-header mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-5`}
                        >
                            <div className="flex min-w-0 items-center gap-2.5">
                                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-indigo-200/90 bg-gradient-to-br from-indigo-50/95 to-blue-50/90 text-indigo-600 shadow-sm dark:border-indigo-800/70 dark:from-slate-800/90 dark:to-indigo-950/50 dark:text-indigo-300 sm:h-10 sm:w-10">
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
                </div>,
                document.body
            )
        ) : null;

    return (
        <div className="landing-page min-h-screen bg-transparent font-sans text-gray-900 dark:text-gray-100">
            {landingHeader}
            <div className="lex-landing-header-spacer shrink-0" aria-hidden />

            <div className="mx-auto max-w-6xl space-y-10 px-3 pb-20 pt-4 sm:space-y-12 sm:px-5 sm:pb-24 sm:pt-6">
                {/* Hero — large glass panel */}
                <section className="relative">
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
                    <div className={`${LG_HERO} relative p-6 sm:p-8 md:p-10 lg:grid lg:grid-cols-[1fr_minmax(0,380px)] lg:items-center lg:gap-10`}>
                        {/* Specular + rim light (does not participate in grid) */}
                        <div
                            className="pointer-events-none absolute inset-0 overflow-hidden rounded-[inherit]"
                            aria-hidden
                        >
                            <div className="absolute -left-1/4 -top-1/2 h-[90%] w-[70%] rounded-full bg-gradient-to-br from-white/85 via-white/35 to-transparent opacity-65 blur-2xl dark:from-indigo-300/14 dark:via-violet-400/10 dark:to-transparent dark:opacity-90" />
                            <div className="absolute -bottom-1/4 -right-1/4 h-[70%] w-[65%] rounded-full bg-gradient-to-tl from-amber-200/45 via-fuchsia-200/22 to-transparent opacity-55 blur-2xl dark:from-amber-400/14 dark:via-fuchsia-500/10 dark:to-transparent dark:opacity-85" />
                            <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/90 to-transparent dark:via-white/25" />
                        </div>
                        <div className="relative z-10 min-w-0">
                            <p className="mb-3 inline-flex items-center gap-2 rounded-full border border-indigo-300/60 bg-indigo-50/70 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.14em] text-indigo-800 shadow-sm shadow-indigo-500/10 backdrop-blur-md dark:border-indigo-400/25 dark:bg-indigo-950/55 dark:text-indigo-100 dark:shadow-indigo-950/40">
                                <Sparkles className="h-3.5 w-3.5" />
                                Philippine Bar &amp; practice
                            </p>
                            <h1 className="font-display text-3xl font-semibold leading-[1.12] tracking-tight text-gray-900 dark:text-white sm:text-4xl md:text-5xl">
                                Master the Bar
                                <span className="mt-1 block bg-gradient-to-r from-indigo-700 via-violet-700 to-amber-700 bg-clip-text text-transparent dark:from-indigo-200 dark:via-violet-200 dark:to-amber-200">
                                    without the burnout.
                                </span>
                            </h1>
                            <p className="mt-5 max-w-xl text-base leading-relaxed text-gray-600 dark:text-gray-400 sm:text-lg">
                                Built for law students, bar candidates, and practitioners: past bar questions, Supreme
                                Court decisions, evidence-grounded digests, major codals, flashcards, and LexPlay
                                listening—together in one fast, installable workspace.
                            </p>
                            <div className="mt-8 flex flex-wrap items-center gap-3">
                                <button
                                    type="button"
                                    onClick={onEnterApp}
                                    className="inline-flex items-center justify-center gap-2 rounded-xl bg-amber-600 px-6 py-3.5 text-base font-bold text-white shadow-lg shadow-amber-900/30 ring-1 ring-amber-400/50 transition-all hover:bg-amber-500 hover:shadow-[0_0_32px_-4px_rgba(245,158,11,0.55)] active:scale-[0.99] sm:px-8 sm:text-lg"
                                >
                                    Start reviewing — it&apos;s free
                                    <ArrowRight className="h-5 w-5 shrink-0" strokeWidth={2.25} />
                                </button>
                                <SignedOut>
                                    <span className="text-sm text-gray-500 dark:text-gray-400">
                                        No credit card. Sign in when you&apos;re ready.
                                    </span>
                                </SignedOut>
                            </div>
                        </div>

                        {/* Device mockup — nested glass layer */}
                        <div className="relative z-10 mt-10 min-w-0 lg:mt-0" aria-hidden>
                            <div className={`${LG_NEST} p-4 sm:p-5`}>
                                <div className="flex items-end justify-center gap-3 sm:gap-4">
                                    <div
                                        className="relative w-[36%] max-w-[140px] rounded-lg border-[3px] border-slate-600/90 bg-slate-800 p-1 shadow-inner sm:max-w-[155px]"
                                        style={{ aspectRatio: '9 / 19' }}
                                    >
                                        <div className="flex h-full flex-col overflow-hidden rounded-lg bg-gradient-to-b from-slate-100 to-slate-200">
                                            <div className="h-1.5 shrink-0 bg-slate-300/90" />
                                            <div className="flex flex-1 flex-col gap-1 p-1.5">
                                                <div className="h-1.5 w-3/4 rounded bg-slate-300" />
                                                <div className="h-1.5 w-full rounded bg-slate-200" />
                                                <div className="mt-1.5 h-6 rounded bg-indigo-200/90" />
                                            </div>
                                        </div>
                                    </div>
                                    <div className="relative w-[58%] max-w-[260px] rounded-lg border-[8px] border-slate-600/90 bg-slate-800 p-1.5 shadow-inner sm:max-w-[300px]">
                                        <div className="overflow-hidden rounded-md bg-gradient-to-br from-slate-50 via-white to-slate-200">
                                            <div className="flex h-5 items-center gap-1 border-b border-slate-200/90 bg-slate-100/90 px-1.5">
                                                <span className="h-1.5 w-1.5 rounded-full bg-rose-400" />
                                                <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                                                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                                            </div>
                                            <div className="space-y-1.5 p-2">
                                                <div className="h-1.5 w-1/3 rounded bg-slate-300" />
                                                <div className="h-12 rounded-md bg-indigo-100/95" />
                                                <div className="h-1.5 w-full rounded bg-slate-200" />
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <p className="mt-3 text-center text-[11px] font-medium text-gray-500 dark:text-gray-400">
                                    <Smartphone className="mr-1 inline h-3.5 w-3.5 align-text-bottom text-indigo-500 dark:text-indigo-400" />
                                    Browser or installed PWA — same LexMatePH experience.
                                </p>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Problem / approach — twin glass cards */}
                <section className="grid gap-6 md:grid-cols-2 md:gap-8">
                    <div className={`${LG} p-6 sm:p-8`}>
                        <h2 className="font-display text-xl font-semibold tracking-tight text-gray-900 dark:text-white sm:text-2xl">
                            When prep feels heavier than the syllabus
                        </h2>
                        <p className="mt-4 text-sm leading-relaxed text-gray-600 dark:text-gray-400 sm:text-base">
                            Outlines sprawl across drives, portals lag, and the bar is still a single sitting. You need a
                            way to rehearse doctrines, scan digests for orientation, and drill questions without living
                            inside a PDF reader.
                        </p>
                    </div>
                    <div className={`${LG} p-6 sm:p-8`}>
                        <h2 className="font-display text-xl font-semibold tracking-tight text-gray-900 dark:text-white sm:text-2xl">
                            One workspace, built for the Philippine setting
                        </h2>
                        <p className="mt-4 text-sm leading-relaxed text-gray-600 dark:text-gray-400 sm:text-base">
                            LexMatePH keeps codals, SC materials, bar items, flashcards, and audio in reach so you can
                            move between modes of study—reading, listening, and recall—without juggling five different
                            tools.
                        </p>
                    </div>
                </section>

                {/* Pillars — icon colors echo About.jsx feature chips */}
                <section>
                    <h2 className="font-display text-center text-xl font-semibold tracking-tight text-gray-900 dark:text-white sm:text-2xl md:text-3xl">
                        Why candidates open LexMatePH
                    </h2>
                    <p className="mx-auto mt-2 max-w-2xl text-center text-sm text-gray-600 dark:text-gray-400">
                        Same spirit as the rest of the app: structured review, literal attention to sources, and room
                        to verify against reporters and current law.
                    </p>
                    <div className="mt-10 grid gap-6 md:grid-cols-3">
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
                            <div key={title} className={`${LG} p-6 sm:p-7`}>
                                <div className={`mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl ${chip}`}>
                                    <Icon className="h-6 w-6" strokeWidth={2} />
                                </div>
                                <h3 className="font-display text-lg font-semibold text-gray-900 dark:text-white">{title}</h3>
                                <p className="mt-3 text-sm leading-relaxed text-gray-600 dark:text-gray-400">{body}</p>
                            </div>
                        ))}
                    </div>
                    <div className="mt-6 grid gap-6 sm:grid-cols-2">
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
                    <div className={`${LG} flex flex-col gap-5 p-6 sm:flex-row sm:items-center sm:gap-8 sm:p-8`}>
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

                {/* Install */}
                <section id="install" className="scroll-mt-24">
                    <div className={`${LG_HERO} relative overflow-hidden p-6 sm:p-8`}>
                        <div className="pointer-events-none absolute inset-0" aria-hidden>
                            <div className="absolute -left-16 top-1/2 h-44 w-44 -translate-y-1/2 rounded-full bg-indigo-400/25 blur-3xl dark:bg-indigo-500/18" />
                            <div className="absolute -right-10 bottom-0 h-36 w-36 rounded-full bg-violet-400/20 blur-3xl dark:bg-violet-500/14" />
                            <div className="absolute inset-x-8 top-0 h-px bg-gradient-to-r from-transparent via-white/80 to-transparent dark:via-white/20" />
                        </div>
                        <div className="relative z-10">
                        <h2 className="font-display text-xl font-semibold text-gray-900 dark:text-white sm:text-2xl">
                            Install in three taps
                        </h2>
                        <p className="mt-2 max-w-2xl text-sm text-gray-600 dark:text-gray-400 sm:text-base">
                            LexMatePH is a website you can pin like an app—full-screen icon, no store approval drama.
                        </p>
                        <ol className="mt-8 grid gap-5 md:grid-cols-3">
                            {[
                                {
                                    step: '1',
                                    title: 'Open in Safari or Chrome',
                                    body: 'Use this site on your phone or desktop browser.',
                                },
                                {
                                    step: '2',
                                    title: 'Share or menu',
                                    body: 'iOS: Share. Android: ⋮. Desktop Chrome: install icon in the address bar.',
                                },
                                {
                                    step: '3',
                                    title: 'Add to Home Screen',
                                    body: 'Choose “Add to Home Screen” or “Install app”. Core assets cache for a smoother launch next time.',
                                },
                            ].map(({ step, title, body }) => (
                                <li key={step} className={`${LG} relative overflow-hidden p-5`}>
                                    <span className="absolute right-3 top-3 font-display text-4xl font-bold tabular-nums text-gray-200/80 dark:text-white/[0.07]">
                                        {step}
                                    </span>
                                    <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-sm font-bold text-indigo-900 dark:bg-indigo-900/50 dark:text-indigo-200">
                                        {step}
                                    </span>
                                    <h3 className="mt-3 font-display text-base font-semibold text-gray-900 dark:text-white">{title}</h3>
                                    <p className="mt-2 text-sm leading-relaxed text-gray-600 dark:text-gray-400">{body}</p>
                                </li>
                            ))}
                        </ol>
                        </div>
                    </div>
                </section>

                {/* Closing — glass + CTA */}
                <section>
                    <div className={`${LG} p-8 text-center sm:p-10`}>
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
