import React, { useState } from 'react';
import { SquareStack, Info, Newspaper, Gavel, Library, Headphones, LogIn, UserPlus, Brain, Zap, Crown, Star, Shield, Book, Terminal, Scale, MessageSquare, ChevronDown, ChevronRight } from 'lucide-react';
import { SignedIn, SignedOut, SignInButton, SignUpButton, UserButton } from '@clerk/clerk-react';
import { useSubscription } from '../context/SubscriptionContext';
import { SIDEBAR_NAV_ACTIVE, SIDEBAR_NAV_IDLE, SIDEBAR_MOBILE_AUTH_CARD } from '../utils/filterChromeClasses';

const LEXCODE_SUBJECTS = [
    {
        id: 'civil',
        label: 'Civil Law',
        laws: [
            { id: 'civ',  label: 'Civil Code' },
            { id: 'fc',   label: 'Family Code' },
        ],
    },
    {
        id: 'criminal',
        label: 'Criminal Law',
        laws: [
            { id: 'rpc', label: 'Revised Penal Code' },
        ],
    },
    {
        id: 'commercial',
        label: 'Commercial Law',
        laws: [
            { id: 'rcc', label: 'Revised Corporation Code' },
        ],
    },
    {
        id: 'political',
        label: 'Political Law',
        laws: [
            { id: 'const', label: 'Philippine Constitution' },
        ],
    },
    {
        id: 'labor',
        label: 'Labor Law & Social Legislation',
        laws: [
            { id: 'labor', label: 'Labor Code' },
        ],
    },
    {
        id: 'remedial',
        label: 'Remedial Law & Legal Ethics',
        laws: [
            { id: 'roc',          label: 'Rules of Court' },
            { id: 'AM-07-9-12-SC', label: 'Writ of Amparo' },
            { id: 'AM-08-1-16-SC', label: 'Writ of Habeas Data' },
            { id: 'AM-09-6-8-SC',  label: 'Rules for Environmental Cases' },
            { id: 'AM-01-7-01-SC', label: 'Rules on Electronic Evidence' },
            { id: 'CPRA',          label: 'Code of Professional Responsibility & Accountability' },
            { id: 'AM-02-8-13-SC', label: '2004 Rules on Notarial Practice' },
            { id: 'NCJC',          label: 'New Code of Judicial Conduct' },
            { id: 'RA-11642',      label: 'Domestic Administrative Adoption Act' },
        ],
    },
];

const TIER_ICON = { free: Shield, amicus: Zap, juris: Star, barrister: Crown };
const TIER_COLOR = {
    free: 'text-gray-500 dark:text-gray-400',
    amicus: 'text-blue-600 dark:text-blue-400',
    juris: 'text-purple-600 dark:text-purple-400',
    barrister: 'text-amber-600 dark:text-amber-400',
    admin: 'text-rose-600 dark:text-rose-400',
};
const TIER_BG = {
    free: 'bg-gray-100 border-2 border-gray-300 dark:border-zinc-700 dark:bg-zinc-900/70 dark:backdrop-blur-md',
    amicus: 'bg-blue-50 border-2 border-blue-300 dark:border-zinc-700 dark:bg-zinc-900/70 dark:backdrop-blur-md',
    juris: 'bg-purple-50 border-2 border-purple-300 dark:border-zinc-700 dark:bg-zinc-900/70 dark:backdrop-blur-md',
    barrister: 'bg-amber-50 border-2 border-amber-300 dark:border-zinc-700 dark:bg-zinc-900/70 dark:backdrop-blur-md',
    admin: 'bg-rose-50/90 border-2 border-rose-200 dark:border-zinc-600 dark:bg-zinc-900/75 dark:backdrop-blur-md',
};

const Sidebar = ({
  onToggleQuiz,
  onToggleAbout,
  onToggleUpdates,
  onToggleSupremeDecisions,
  onToggleLexCode,
  onToggleLexMate,
  mode,
  onToggleLexPlay,
  onToggleFlashcard,
  onSelectSubject,
  onToggleAdminTools,
  onToggleBar2026,
  onSelectCodal,
  selectedCodalCode,
}) => {
    const { tier, tierLabel, openUpgradeModal, openAccountBillingModal, isAdmin, loading, isFoundingPromo, foundingPromoDaysLeft } = useSubscription();
    const TierIcon = isAdmin ? Crown : (TIER_ICON[tier] || Shield);

    const activeLawId = (selectedCodalCode || '').toLowerCase();
    const activeSubjectId = LEXCODE_SUBJECTS.find(s =>
        s.laws.some(l => l.id.toLowerCase() === activeLawId)
    )?.id ?? null;

    const [lexOpen, setLexOpen] = useState(mode === 'codex');
    useEffect(() => {
        if (mode === 'codex') setLexOpen(true);
    }, [mode]);
    const [openSubjects, setOpenSubjects] = useState(() => {
        if (activeSubjectId) return { [activeSubjectId]: true };
        return {};
    });

    const toggleSubject = (id) =>
        setOpenSubjects(p => ({ ...p, [id]: !p[id] }));

    const handleLexCodeClick = () => {
        setLexOpen(p => !p);
    };

    return (
        <nav className="space-y-0.5 px-1.5 sm:px-2 pb-[calc(var(--app-header-height)+var(--player-height,0px))]">

            {/* Mobile Only Actions */}
            <div className="mb-3 space-y-3 lg:hidden">
                {/* Auth Section for Mobile */}
                <div className={SIDEBAR_MOBILE_AUTH_CARD}>
                    <SignedIn>
                        <div className="flex items-center gap-3">
                            <UserButton 
                                appearance={{
                                    elements: {
                                        userButtonAvatarBox: "w-12 h-12"
                                    }
                                }}
                            />
                            <div className="flex min-w-0 flex-col">
                                <span className="text-sm font-semibold text-black dark:text-zinc-100">Account</span>
                                <span className="text-xs text-neutral-700 dark:text-zinc-400">Profile & settings</span>
                            </div>
                        </div>
                    </SignedIn>
                    <SignedOut>
                        <div className="flex flex-col gap-2">
                            <SignInButton mode="modal">
                                <button
                                    type="button"
                                    className="flex w-full min-h-11 items-center justify-center gap-2 rounded-xl border-2 border-lex-strong bg-white px-3 py-2.5 text-center text-xs font-semibold leading-tight tracking-tight text-black shadow-md transition-all active:scale-[0.98] hover:bg-neutral-50 dark:bg-zinc-900 dark:text-zinc-100 sm:text-[13px]"
                                >
                                    <LogIn className="h-4 w-4 shrink-0" strokeWidth={2.25} aria-hidden />
                                    <span className="min-w-0">Log In</span>
                                </button>
                            </SignInButton>
                            <SignUpButton mode="modal">
                                <button
                                    type="button"
                                    className="flex w-full min-h-11 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-purple-700 px-3 py-2.5 text-center text-xs font-semibold leading-tight tracking-tight text-white shadow-md shadow-violet-900/30 transition-all active:scale-[0.98] hover:opacity-95 sm:text-[13px]"
                                >
                                    <UserPlus className="h-4 w-4 shrink-0" strokeWidth={2.25} aria-hidden />
                                    <span className="min-w-0">Sign Up</span>
                                </button>
                            </SignUpButton>
                        </div>
                    </SignedOut>
                </div>

                <div className="my-2 h-0.5 rounded-full bg-violet-300/70 dark:bg-zinc-700" />
            </div>

            {/* Subscription Tier Badge */}
            <SignedIn>
                {loading ? (
                    <div className="mb-3 mt-0 flex items-center gap-3 rounded-xl border-2 border-violet-200/70 dark:border-purple-500/30 bg-violet-50/80 dark:bg-slate-900/70 p-3 shadow-sm animate-pulse">
                        <div className="w-8 h-8 rounded-lg bg-slate-300 dark:bg-slate-700 shrink-0" />
                        <div className="flex-1 space-y-1.5">
                            <div className="h-2.5 w-20 rounded bg-slate-300 dark:bg-slate-700" />
                            <div className="h-2 w-14 rounded bg-slate-200 dark:bg-slate-600" />
                        </div>
                    </div>
                ) : (
                    <div
                        className={`mb-2 mt-0 flex items-center gap-2 rounded-xl border p-2 shadow-sm backdrop-blur-md ring-1 ring-inset ring-white/35 dark:ring-white/[0.06] ${isAdmin ? TIER_BG.admin : TIER_BG[tier]}`}
                    >
                        <button
                            type="button"
                            onClick={() => openAccountBillingModal()}
                            className="flex min-w-0 flex-1 items-center gap-3 rounded-lg text-left outline-none ring-violet-500/40 transition hover:bg-black/[0.04] focus-visible:ring-2 dark:hover:bg-white/[0.06]"
                            aria-label="Open account and billing"
                        >
                            <div className={`w-8 h-8 shrink-0 rounded-lg flex items-center justify-center ${isAdmin ? TIER_COLOR.admin : TIER_COLOR[tier]} bg-white/60 dark:bg-black/20`}>
                                <TierIcon size={16} />
                            </div>
                            <div className="min-w-0 flex-1">
                                <p className={`text-xs font-extrabold ${isAdmin ? TIER_COLOR.admin : TIER_COLOR[tier]} uppercase tracking-wide`}>
                                    {isAdmin ? 'Administrator' : `${tierLabel} Plan`}
                                </p>
                                {isAdmin && (
                                    <p className="text-[10px] text-rose-600 dark:text-rose-400 font-bold italic">Unlimited Access</p>
                                )}
                                {!isAdmin && isFoundingPromo && (
                                    <p className="text-[10px] text-amber-600 dark:text-amber-400">
                                        {foundingPromoDaysLeft !== null
                                            ? `${foundingPromoDaysLeft} day${foundingPromoDaysLeft !== 1 ? 's' : ''} left · tap for billing`
                                            : 'Full access · tap for billing'}
                                    </p>
                                )}
                                {!isAdmin && !isFoundingPromo && tier === 'free' && (
                                    <p className="text-[10px] text-gray-400 dark:text-gray-500">Limited access · tap for billing</p>
                                )}
                                {!isAdmin && !isFoundingPromo && tier === 'barrister' && (
                                    <p className="text-[10px] text-amber-600 dark:text-amber-400">Full access · tap for billing</p>
                                )}
                                {!isAdmin && !isFoundingPromo && tier !== 'free' && tier !== 'barrister' && (
                                    <p className="text-[10px] text-gray-500 dark:text-gray-400">Tap for account & billing</p>
                                )}
                            </div>
                        </button>
                        {!isAdmin && tier !== 'barrister' && (
                            <button
                                type="button"
                                onClick={() => openUpgradeModal()}
                                className="shrink-0 px-2 py-1 rounded-lg text-[10px] font-bold text-white bg-gradient-to-r from-violet-600 to-purple-700 shadow-sm hover:opacity-90 transition-opacity"
                            >
                                Upgrade
                            </button>
                        )}
                    </div>
                )}
            </SignedIn>

            {/* Admin Tools — only visible to admins */}
            {isAdmin && (
                <>
                    <div className="my-1.5 h-px rounded-full bg-rose-200/80 dark:bg-zinc-700" />
                    <button
                        onClick={() => { if (onToggleAdminTools) onToggleAdminTools(); }}
                        className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2 text-left text-sm font-medium transition-colors
                        ${mode === 'admin_tools'
                            ? SIDEBAR_NAV_ACTIVE
                            : SIDEBAR_NAV_IDLE
                        }`}
                    >
                        <Terminal size={18} className={`${mode === 'admin_tools' ? 'text-rose-700 dark:text-rose-400' : 'text-rose-600 dark:text-rose-400'} group-hover:scale-110 transition-all duration-200`} />
                        Admin Tools
                    </button>
                    <div className="my-1.5 h-px rounded-full bg-violet-300/70 dark:bg-zinc-700" />
                </>
            )}

            <button
                onClick={() => {
                    onToggleAbout();
                }}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2 text-left text-sm font-medium transition-colors
                ${mode === 'about'
                        ? SIDEBAR_NAV_ACTIVE
                        : SIDEBAR_NAV_IDLE
                    }`}
            >
                <Info size={18} className={`${mode === 'about' ? 'text-sky-700 dark:text-sky-400' : 'text-sky-600 dark:text-sky-400'} group-hover:scale-110 transition-all duration-200`} />
                About
            </button>

            {/* Updates Button */}
            <button
                onClick={() => {
                    onToggleUpdates();
                }}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2 text-left text-sm font-medium transition-colors
                ${mode === 'updates'
                        ? SIDEBAR_NAV_ACTIVE
                        : SIDEBAR_NAV_IDLE
                    }`}
            >
                <Newspaper size={18} className={`transition-all duration-200 group-hover:scale-110 ${mode === 'updates' ? 'text-emerald-700 dark:text-emerald-400' : 'text-emerald-600 dark:text-emerald-400'}`} />
                Updates
            </button>

            {/* Lexify Button */}
            <button
                onClick={() => {
                    onToggleQuiz();
                }}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2 text-left text-sm font-medium transition-colors
                ${mode === 'quiz'
                        ? SIDEBAR_NAV_ACTIVE
                        : SIDEBAR_NAV_IDLE
                    }`}
            >
                <Brain size={18} className={`${mode === 'quiz' ? 'text-rose-700 dark:text-rose-400' : 'text-rose-600 dark:text-rose-400'} group-hover:scale-110 transition-all duration-200`} />
                Lexify
            </button>

            {/* Flashcards Button */}
            <button
                onClick={() => {
                    if (onToggleFlashcard) onToggleFlashcard();
                }}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2 text-left text-sm font-medium transition-colors
                ${mode === 'flashcard'
                        ? SIDEBAR_NAV_ACTIVE
                        : SIDEBAR_NAV_IDLE
                    }`}
            >
                <SquareStack size={18} className={`${mode === 'flashcard' ? 'text-indigo-700 dark:text-indigo-400' : 'text-indigo-600 dark:text-indigo-400'} group-hover:scale-110 transition-all duration-200`} />
                Flashcards
            </button>

            {/* LexMate Button — admin only */}
            {isAdmin && (
            <button
                onClick={() => { if (onToggleLexMate) onToggleLexMate(); }}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2 text-left text-sm font-medium transition-colors
                ${mode === 'lexmate'
                        ? SIDEBAR_NAV_ACTIVE
                        : SIDEBAR_NAV_IDLE
                    }`}
            >
                <MessageSquare size={18} className={`${mode === 'lexmate' ? 'text-indigo-700 dark:text-indigo-400' : 'text-indigo-600 dark:text-indigo-400'} group-hover:scale-110 transition-all duration-200`} />
                LexMate AI
            </button>
            )}

            {/* LexPlay Button */}
            <button
                onClick={() => {
                    if (onToggleLexPlay) onToggleLexPlay();
                }}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2 text-left text-sm font-medium transition-colors ${SIDEBAR_NAV_IDLE}`}
            >
                <Headphones size={18} className="text-violet-600 dark:text-zinc-400 group-hover:scale-110 transition-all duration-200" />
                LexPlay
            </button>


            {/* SC Decisions Button */}
            <button
                onClick={() => {
                    onToggleSupremeDecisions();
                }}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2 text-left text-sm font-medium transition-colors
                ${mode === 'supreme_decisions'
                        ? SIDEBAR_NAV_ACTIVE
                        : SIDEBAR_NAV_IDLE
                    }`}
            >
                <Gavel size={18} className={`transition-all duration-200 group-hover:scale-110 ${mode === 'supreme_decisions' ? 'text-rose-700 dark:text-rose-400' : 'text-rose-600 dark:text-rose-400'}`} />
                Case Digest
            </button>

            {/* LexCode — expandable subject tree */}
            <button
                onClick={handleLexCodeClick}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2 text-left text-sm font-medium transition-colors
                ${mode === 'codex' ? SIDEBAR_NAV_ACTIVE : SIDEBAR_NAV_IDLE}`}
            >
                <Library size={18} className={`${mode === 'codex' ? 'text-amber-700 dark:text-amber-400' : 'text-amber-600 dark:text-amber-500'} group-hover:scale-110 transition-all duration-200`} />
                <span className="flex-1">LexCode</span>
                {lexOpen
                    ? <ChevronDown size={14} className="shrink-0 text-neutral-400 dark:text-zinc-500" />
                    : <ChevronRight size={14} className="shrink-0 text-neutral-400 dark:text-zinc-500" />
                }
            </button>

            {/* Subject tree — visible when LexCode is open */}
            {lexOpen && (
                <div className="ml-2 border-l border-amber-200 dark:border-zinc-700 pl-1.5 space-y-0">
                    {LEXCODE_SUBJECTS.map(subject => {
                        const isSubjectOpen = !!openSubjects[subject.id];
                        const hasActive = subject.laws.some(l => l.id.toLowerCase() === activeLawId);
                        return (
                            <div key={subject.id}>
                                {/* Subject header */}
                                <button
                                    onClick={() => toggleSubject(subject.id)}
                                    className={`flex w-full items-center gap-1.5 rounded-lg px-2 py-1.5 text-left text-[12px] font-semibold transition-colors
                                        ${hasActive
                                            ? 'text-amber-700 dark:text-amber-400'
                                            : 'text-neutral-600 hover:text-neutral-900 dark:text-zinc-400 dark:hover:text-zinc-200'
                                        } hover:bg-neutral-100 dark:hover:bg-zinc-800/60`}
                                >
                                    <span className="flex-1 leading-snug">{subject.label}</span>
                                    {(isSubjectOpen || hasActive)
                                        ? <ChevronDown size={11} className="shrink-0 opacity-60" />
                                        : <ChevronRight size={11} className="shrink-0 opacity-40" />
                                    }
                                </button>

                                {/* Law items */}
                                {(isSubjectOpen || hasActive) && (
                                    <div className="ml-2 mt-0.5 space-y-0.5 border-l border-neutral-200 dark:border-zinc-700/60 pl-2 pb-1">
                                        {subject.laws.map(law => {
                                            const isActive = law.id.toLowerCase() === activeLawId && mode === 'codex';
                                            return (
                                                <button
                                                    key={law.id}
                                                    onClick={() => {
                                                        if (onSelectCodal) onSelectCodal(law.id);
                                                    }}
                                                    className={`w-full rounded-md px-2 py-1 text-left text-[11px] leading-snug transition-colors
                                                        ${isActive
                                                            ? 'bg-amber-100 font-semibold text-amber-800 dark:bg-amber-950/40 dark:text-amber-300'
                                                            : 'text-neutral-500 hover:bg-neutral-100 hover:text-neutral-800 dark:text-zinc-500 dark:hover:bg-zinc-800 dark:hover:text-zinc-200'
                                                        }`}
                                                >
                                                    {law.label}
                                                </button>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}




            {/* Bar Questions — subject filter lives on the page */}
            <button
                onClick={() => {
                    if (onSelectSubject) onSelectSubject('All Subjects');
                }}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2 text-left text-sm font-medium transition-colors
                ${mode === 'browse_bar'
                        ? SIDEBAR_NAV_ACTIVE
                        : SIDEBAR_NAV_IDLE
                    }`}
            >
                <Book size={18} className={`${mode === 'browse_bar' ? 'text-amber-700 dark:text-amber-400' : 'text-amber-600 dark:text-amber-500'} group-hover:scale-110 transition-all duration-200`} />
                Bar Questions
            </button>

            {/* BAR 2026 — admin only */}
            {isAdmin && (
                <button
                    onClick={() => {
                        if (onToggleBar2026) onToggleBar2026();
                    }}
                    className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2 text-left text-sm font-medium transition-colors
                    ${mode === 'bar_2026'
                            ? SIDEBAR_NAV_ACTIVE
                            : SIDEBAR_NAV_IDLE
                        }`}
                >
                    <Scale size={18} className={`${mode === 'bar_2026' ? 'text-violet-700 dark:text-violet-400' : 'text-violet-600 dark:text-violet-400'} group-hover:scale-110 transition-all duration-200`} />
                    <span className="flex-1">BAR 2026</span>
                    <span className="shrink-0 rounded-full bg-violet-100 px-1.5 py-0.5 text-[10px] font-bold text-violet-700 dark:bg-violet-900/40 dark:text-violet-300">NEW</span>
                </button>
            )}



        </nav >
    );
};

export default Sidebar;
