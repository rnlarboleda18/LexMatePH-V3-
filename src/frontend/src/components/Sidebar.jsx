import React from 'react';
import { SquareStack, Info, Newspaper, Gavel, Library, Headphones, LogIn, UserPlus, Brain, Zap, Crown, Star, Shield, Book } from 'lucide-react';
import { SignedIn, SignedOut, SignInButton, SignUpButton, UserButton } from '@clerk/clerk-react';
import { useSubscription } from '../context/SubscriptionContext';
import { SIDEBAR_NAV_ACTIVE, SIDEBAR_NAV_IDLE, SIDEBAR_MOBILE_AUTH_CARD } from '../utils/filterChromeClasses';

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

const Sidebar = ({ onToggleQuiz, onToggleAbout, onToggleUpdates, onToggleSupremeDecisions, onToggleLexCode, mode, onToggleLexPlay, onToggleFlashcard, onSelectSubject }) => {
    const { tier, tierLabel, openUpgradeModal, isAdmin, loading, hideSubscriptionModalForFoundingPromo } = useSubscription();
    const TierIcon = isAdmin ? Crown : (TIER_ICON[tier] || Shield);

    return (
        <nav className="space-y-1 px-1.5 sm:px-2 pb-[calc(var(--app-header-height)+var(--player-height,0px))]">

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
                    <div className={`mb-3 mt-0 flex items-center gap-3 rounded-xl border p-3 shadow-sm backdrop-blur-md ring-1 ring-inset ring-white/35 dark:ring-white/[0.06] ${isAdmin ? TIER_BG.admin : TIER_BG[tier]}`}>
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${isAdmin ? TIER_COLOR.admin : TIER_COLOR[tier]} bg-white/60 dark:bg-black/20`}>
                            <TierIcon size={16} />
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className={`text-xs font-extrabold ${isAdmin ? TIER_COLOR.admin : TIER_COLOR[tier]} uppercase tracking-wide`}>
                                {isAdmin ? 'Administrator' : `${tierLabel} Plan`}
                            </p>
                            {isAdmin && (
                                <p className="text-[10px] text-rose-600 dark:text-rose-400 font-bold italic">Unlimited Access</p>
                            )}
                            {!isAdmin && tier === 'free' && (
                                <p className="text-[10px] text-gray-400 dark:text-gray-500">Limited access</p>
                            )}
                            {!isAdmin && tier === 'barrister' && (
                                <p className="text-[10px] text-amber-600 dark:text-amber-400">Full access</p>
                            )}
                        </div>
                        {!isAdmin && tier !== 'barrister' && !hideSubscriptionModalForFoundingPromo && (
                            <button
                                onClick={() => openUpgradeModal()}
                                className="shrink-0 px-2 py-1 rounded-lg text-[10px] font-bold text-white bg-gradient-to-r from-violet-600 to-purple-700 shadow-sm hover:opacity-90 transition-opacity"
                            >
                                Upgrade
                            </button>
                        )}
                    </div>
                )}
            </SignedIn>

            <button
                onClick={() => {
                    onToggleAbout();
                }}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2.5 text-left text-[15px] font-medium transition-colors md:py-3 md:text-base
                ${mode === 'about'
                        ? SIDEBAR_NAV_ACTIVE
                        : SIDEBAR_NAV_IDLE
                    }`}
            >
                <Info size={20} className={`${mode === 'about' ? 'text-sky-700 dark:text-sky-400' : 'text-sky-600 dark:text-sky-400'} group-hover:scale-110 transition-all duration-200`} />
                About
            </button>

            {/* Updates Button */}
            <button
                onClick={() => {
                    onToggleUpdates();
                }}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2.5 text-left text-[15px] font-medium transition-colors md:py-3 md:text-base
                ${mode === 'updates'
                        ? SIDEBAR_NAV_ACTIVE
                        : SIDEBAR_NAV_IDLE
                    }`}
            >
                <Newspaper size={20} className={`transition-all duration-200 group-hover:scale-110 ${mode === 'updates' ? 'text-emerald-700 dark:text-emerald-400' : 'text-emerald-600 dark:text-emerald-400'}`} />
                Updates
            </button>

            {/* Lexify Button */}
            <button
                onClick={() => {
                    onToggleQuiz();
                }}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2.5 text-left text-[15px] font-medium transition-colors md:py-3 md:text-base
                ${mode === 'quiz'
                        ? SIDEBAR_NAV_ACTIVE
                        : SIDEBAR_NAV_IDLE
                    }`}
            >
                <Brain size={20} className={`${mode === 'quiz' ? 'text-rose-700 dark:text-rose-400' : 'text-rose-600 dark:text-rose-400'} group-hover:scale-110 transition-all duration-200`} />
                Lexify
            </button>

            {/* Flashcards Button */}
            <button
                onClick={() => {
                    if (onToggleFlashcard) onToggleFlashcard();
                }}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2.5 text-left text-[15px] font-medium transition-colors md:py-3 md:text-base
                ${mode === 'flashcard'
                        ? SIDEBAR_NAV_ACTIVE
                        : SIDEBAR_NAV_IDLE
                    }`}
            >
                <SquareStack size={20} className={`${mode === 'flashcard' ? 'text-indigo-700 dark:text-indigo-400' : 'text-indigo-600 dark:text-indigo-400'} group-hover:scale-110 transition-all duration-200`} />
                Flashcards
            </button>

            {/* LexPlay Button */}
            <button
                onClick={() => {
                    if (onToggleLexPlay) onToggleLexPlay();
                }}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2.5 text-left text-[15px] font-medium transition-colors md:py-3 md:text-base ${SIDEBAR_NAV_IDLE}`}
            >
                <Headphones size={20} className="text-violet-600 dark:text-zinc-400 group-hover:scale-110 transition-all duration-200" />
                LexPlay
            </button>


            {/* SC Decisions Button */}
            <button
                onClick={() => {
                    onToggleSupremeDecisions();
                }}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2.5 text-left text-[15px] font-medium transition-colors md:py-3 md:text-base
                ${mode === 'supreme_decisions'
                        ? SIDEBAR_NAV_ACTIVE
                        : SIDEBAR_NAV_IDLE
                    }`}
            >
                <Gavel size={20} className={`transition-all duration-200 group-hover:scale-110 ${mode === 'supreme_decisions' ? 'text-rose-700 dark:text-rose-400' : 'text-rose-600 dark:text-rose-400'}`} />
                Case Digest
            </button>

            {/* LexCode — codal picker lives on the page */}
            <button
                onClick={() => {
                    if (onToggleLexCode) onToggleLexCode();
                }}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2.5 text-left text-[15px] font-medium transition-colors md:py-3 md:text-base
                ${mode === 'codex'
                        ? SIDEBAR_NAV_ACTIVE
                        : SIDEBAR_NAV_IDLE
                    }`}
            >
                <Library size={20} className={`${mode === 'codex' ? 'text-amber-700 dark:text-amber-400' : 'text-amber-600 dark:text-amber-500'} group-hover:scale-110 transition-all duration-200`} />
                LexCode
            </button>




            {/* Bar Questions — subject filter lives on the page */}
            <button
                onClick={() => {
                    if (onSelectSubject) onSelectSubject('All Subjects');
                }}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2.5 text-left text-[15px] font-medium transition-colors md:py-3 md:text-base
                ${mode === 'browse_bar'
                        ? SIDEBAR_NAV_ACTIVE
                        : SIDEBAR_NAV_IDLE
                    }`}
            >
                <Book size={20} className={`${mode === 'browse_bar' ? 'text-amber-700 dark:text-amber-400' : 'text-amber-600 dark:text-amber-500'} group-hover:scale-110 transition-all duration-200`} />
                Bar Questions
            </button>



        </nav >
    );
};

export default Sidebar;
