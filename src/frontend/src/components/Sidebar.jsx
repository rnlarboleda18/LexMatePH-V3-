import React from 'react';
import { SquareStack, Info, Newspaper, Gavel, Library, Headphones, LogIn, UserPlus, Brain, Zap, Crown, Star, Shield, Book } from 'lucide-react';
import { SignedIn, SignedOut, SignInButton, SignUpButton, UserButton } from '@clerk/clerk-react';
import { useSubscription } from '../context/SubscriptionContext';

const TIER_ICON = { free: Shield, amicus: Zap, juris: Star, barrister: Crown };
const TIER_COLOR = {
    free: 'text-gray-500 dark:text-gray-400',
    amicus: 'text-blue-600 dark:text-blue-400',
    juris: 'text-purple-600 dark:text-purple-400',
    barrister: 'text-amber-600 dark:text-amber-400',
    admin: 'text-rose-600 dark:text-rose-400',
};
const TIER_BG = {
    free: 'bg-gray-100 dark:bg-gray-800 border-2 border-gray-300 dark:border-gray-700',
    amicus: 'bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-300 dark:border-blue-800',
    juris: 'bg-purple-50 dark:bg-purple-900/20 border-2 border-purple-300 dark:border-purple-800',
    barrister: 'bg-amber-50 dark:bg-amber-900/20 border-2 border-amber-300 dark:border-amber-800',
    admin: 'bg-rose-50 dark:bg-rose-900/20 border-2 border-rose-300 dark:border-rose-800',
};

const Sidebar = ({ onToggleQuiz, onToggleAbout, onToggleUpdates, onToggleSupremeDecisions, onToggleLexCode, mode, onToggleLexPlay, onToggleFlashcard, onSelectSubject }) => {
    const { tier, tierLabel, openUpgradeModal, isAdmin } = useSubscription();
    const TierIcon = isAdmin ? Crown : (TIER_ICON[tier] || Shield);

    return (
        <nav className="space-y-1 px-1.5 sm:px-2 pb-[calc(var(--app-header-height)+var(--player-height,0px))]">

            {/* Mobile Only Actions */}
            <div className="lg:hidden mb-5 space-y-4">
                {/* Auth Section for Mobile */}
                <div className="glass rounded-xl border-2 border-slate-300/85 bg-white/92 p-4 shadow-md backdrop-blur-md dark:border-white/10 dark:bg-slate-900/40">
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
                                <span className="text-sm font-semibold text-slate-900 dark:text-white">Account</span>
                                <span className="text-xs text-slate-500 dark:text-slate-400">Profile & settings</span>
                            </div>
                        </div>
                    </SignedIn>
                    <SignedOut>
                        <div className="flex flex-col gap-2">
                            <SignInButton mode="modal">
                                <button
                                    type="button"
                                    className="flex w-full min-h-11 items-center justify-center gap-2 rounded-xl border-2 border-slate-400/70 bg-white px-3 py-2.5 text-center text-xs font-semibold leading-tight tracking-tight text-slate-900 shadow-sm backdrop-blur-sm transition-all active:scale-[0.98] dark:border-white/10 dark:bg-slate-800/60 dark:text-slate-100 sm:text-[13px]"
                                >
                                    <LogIn className="h-4 w-4 shrink-0" strokeWidth={2.25} aria-hidden />
                                    <span className="min-w-0">Log In</span>
                                </button>
                            </SignInButton>
                            <SignUpButton mode="modal">
                                <button
                                    type="button"
                                    className="flex w-full min-h-11 items-center justify-center gap-2 rounded-xl bg-amber-600 px-3 py-2.5 text-center text-xs font-semibold leading-tight tracking-tight text-white shadow-md shadow-amber-900/25 transition-all active:scale-[0.98] sm:text-[13px]"
                                >
                                    <UserPlus className="h-4 w-4 shrink-0" strokeWidth={2.25} aria-hidden />
                                    <span className="min-w-0">Sign Up</span>
                                </button>
                            </SignUpButton>
                        </div>
                    </SignedOut>
                </div>

                <div className="my-3 h-0.5 rounded-full bg-slate-300/80 dark:bg-white/10" />
            </div>




            {/* Subscription Tier Badge */}
            <SignedIn>
                <div className={`mb-3 mt-1 flex items-center gap-3 rounded-xl border p-3 shadow-sm backdrop-blur-sm ${isAdmin ? TIER_BG.admin : TIER_BG[tier]}`}>
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
                    {!isAdmin && tier !== 'barrister' && (
                        <button
                            onClick={() => openUpgradeModal()}
                            className="shrink-0 px-2 py-1 rounded-lg text-[10px] font-bold text-white bg-gradient-to-r from-blue-500 to-indigo-600 shadow-sm hover:opacity-90 transition-opacity"
                        >
                            Upgrade
                        </button>
                    )}
                </div>
            </SignedIn>

            <button
                onClick={() => {
                    onToggleAbout();
                }}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2.5 text-left text-[15px] font-medium transition-colors md:py-3 md:text-base
                ${mode === 'about'
                        ? 'border-indigo-500 bg-indigo-50/95 text-slate-900 shadow-sm dark:border-indigo-400 dark:bg-indigo-950/35 dark:text-white'
                        : 'border border-transparent text-slate-900 hover:border-slate-300/90 hover:bg-slate-100/95 dark:border-transparent dark:text-slate-100 dark:hover:border-transparent dark:hover:bg-white/[0.06]'
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
                        ? 'border-indigo-500 bg-indigo-50/95 text-slate-900 shadow-sm dark:border-indigo-400 dark:bg-indigo-950/35 dark:text-white'
                        : 'border border-transparent text-slate-900 hover:border-slate-300/90 hover:bg-slate-100/95 dark:border-transparent dark:text-slate-100 dark:hover:border-transparent dark:hover:bg-white/[0.06]'
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
                        ? 'border-indigo-500 bg-indigo-50/95 text-slate-900 shadow-sm dark:border-indigo-400 dark:bg-indigo-950/35 dark:text-white'
                        : 'border border-transparent text-slate-900 hover:border-slate-300/90 hover:bg-slate-100/95 dark:border-transparent dark:text-slate-100 dark:hover:border-transparent dark:hover:bg-white/[0.06]'
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
                        ? 'border-indigo-500 bg-indigo-50/95 text-slate-900 shadow-sm dark:border-indigo-400 dark:bg-indigo-950/35 dark:text-white'
                        : 'border border-transparent text-slate-900 hover:border-slate-300/90 hover:bg-slate-100/95 dark:border-transparent dark:text-slate-100 dark:hover:border-transparent dark:hover:bg-white/[0.06]'
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
                className="group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2.5 text-left text-[15px] font-medium transition-colors md:py-3 md:text-base border border-transparent text-slate-900 hover:border-slate-300/90 hover:bg-slate-100/95 dark:border-transparent dark:text-slate-100 dark:hover:border-transparent dark:hover:bg-white/[0.06]"
            >
                <Headphones size={20} className="text-purple-600 dark:text-purple-400 group-hover:scale-110 transition-all duration-200" />
                LexPlay
            </button>


            {/* SC Decisions Button */}
            <button
                onClick={() => {
                    onToggleSupremeDecisions();
                }}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2.5 text-left text-[15px] font-medium transition-colors md:py-3 md:text-base
                ${mode === 'supreme_decisions'
                        ? 'border-indigo-500 bg-indigo-50/95 text-slate-900 shadow-sm dark:border-indigo-400 dark:bg-indigo-950/35 dark:text-white'
                        : 'border border-transparent text-slate-900 hover:border-slate-300/90 hover:bg-slate-100/95 dark:border-transparent dark:text-slate-100 dark:hover:border-transparent dark:hover:bg-white/[0.06]'
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
                        ? 'border-indigo-500 bg-indigo-50/95 text-slate-900 shadow-sm dark:border-indigo-400 dark:bg-indigo-950/35 dark:text-white'
                        : 'border border-transparent text-slate-900 hover:border-slate-300/90 hover:bg-slate-100/95 dark:border-transparent dark:text-slate-100 dark:hover:border-transparent dark:hover:bg-white/[0.06]'
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
                        ? 'border-indigo-500 bg-indigo-50/95 text-slate-900 shadow-sm dark:border-indigo-400 dark:bg-indigo-950/35 dark:text-white'
                        : 'border border-transparent text-slate-900 hover:border-slate-300/90 hover:bg-slate-100/95 dark:border-transparent dark:text-slate-100 dark:hover:border-transparent dark:hover:bg-white/[0.06]'
                    }`}
            >
                <Book size={20} className={`${mode === 'browse_bar' ? 'text-amber-700 dark:text-amber-400' : 'text-amber-600 dark:text-amber-500'} group-hover:scale-110 transition-all duration-200`} />
                Bar Questions
            </button>



        </nav >
    );
};

export default Sidebar;
