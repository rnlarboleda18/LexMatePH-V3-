import React, { useState, useRef } from 'react';
import { ChevronDown, ChevronRight, BookOpen, Info, History, Scale, Swords, Newspaper, Gavel, Globe, Library, Briefcase, Calculator, Building2, Book, Heart, Users, Headphones, LogIn, UserPlus, Brain, Zap, Crown, Star, Shield } from 'lucide-react';
import { SignedIn, SignedOut, SignInButton, SignUpButton, UserButton } from '@clerk/clerk-react';
import { useSubscription } from '../context/SubscriptionContext';

const codexSubjects = [
    { title: "Revised Penal Code", id: "rpc", icon: Swords, color: "text-rose-500" },
    { title: "Civil Code of the Philippines", id: "civ", icon: Users, color: "text-blue-500" },
    { title: "Family Code", id: "fc", icon: Heart, color: "text-pink-500" },
    { title: "Rules of Court", id: "roc", icon: Scale, color: "text-red-500" },
    { title: "Philippine Constitution", id: "const", icon: Globe, color: "text-sky-500" },
    { title: "Labor Code", id: "labor", icon: Briefcase, color: "text-amber-600" },
    { title: "Administrative Code", id: "admin", icon: Building2, color: "text-emerald-500", disabled: true },
    { title: "Special Laws", id: "special", icon: Book, color: "text-violet-500", disabled: true }
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
    free: 'bg-gray-100 dark:bg-gray-800 border-gray-200 dark:border-gray-700',
    amicus: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
    juris: 'bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800',
    barrister: 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800',
    admin: 'bg-rose-50 dark:bg-rose-900/20 border-rose-200 dark:border-rose-800',
};

const Sidebar = ({ onToggleQuiz, onToggleAbout, onToggleUpdates, onToggleSupremeDecisions, onSelectCodal, selectedCodalCode, mode, onToggleLexPlay, onToggleFlashcard, onSelectSubject }) => {
    const { tier, tierLabel, openUpgradeModal, isAdmin } = useSubscription();
    const TierIcon = isAdmin ? Crown : (TIER_ICON[tier] || Shield);

    const [openSection, setOpenSection] = useState(() => (mode === 'codex' ? 'codex' : null));
    const timeoutRef = useRef(null);

    const toggleSection = (section) => {
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        setOpenSection(openSection === section ? null : section);
    };

    const handleMouseEnter = (section) => {
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        timeoutRef.current = setTimeout(() => {
            setOpenSection(section);
        }, 500);
    };

    const handleMouseLeave = () => {
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        setOpenSection(null);
    };

    return (
        <nav className="space-y-1 px-2 sm:px-3 pb-[calc(5rem_+_var(--player-height,0px))]">

            {/* Mobile Only Actions */}
            <div className="lg:hidden mb-5 space-y-4">
                {/* Auth Section for Mobile */}
                <div className="glass rounded-xl border border-white/40 bg-white/35 p-4 shadow-sm backdrop-blur-md dark:border-white/10 dark:bg-slate-900/40">
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
                        <div className="grid grid-cols-2 gap-2.5">
                            <SignInButton mode="modal">
                                <button className="flex items-center justify-center gap-2 rounded-xl border border-white/50 bg-white/70 py-2.5 text-sm font-semibold text-slate-800 shadow-sm backdrop-blur-sm transition-all active:scale-[0.98] dark:border-white/10 dark:bg-slate-800/60 dark:text-slate-100">
                                    <LogIn size={18} />
                                    <span>Log In</span>
                                </button>
                            </SignInButton>
                            <SignUpButton mode="modal">
                                <button className="flex items-center justify-center gap-2 rounded-xl bg-amber-600 py-2.5 text-sm font-semibold text-white shadow-md shadow-amber-900/25 transition-all active:scale-[0.98]">
                                    <UserPlus size={18} />
                                    <span>Sign Up</span>
                                </button>
                            </SignUpButton>
                        </div>
                    </SignedOut>
                </div>

                <div className="my-3 h-px bg-white/30 dark:bg-white/10" />
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
                    setOpenSection(null);
                }}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-3 py-2.5 text-left text-[15px] font-medium transition-colors md:py-3 md:text-base
                ${mode === 'about'
                        ? 'border-indigo-500 bg-indigo-50/95 text-slate-900 shadow-sm dark:border-indigo-400 dark:bg-indigo-950/35 dark:text-white'
                        : 'border-transparent text-slate-800 hover:bg-white/55 dark:text-slate-100 dark:hover:bg-white/[0.06]'
                    }`}
            >
                <Info size={20} className={`${mode === 'about' ? 'text-sky-700 dark:text-sky-400' : 'text-sky-600 dark:text-sky-400'} group-hover:scale-110 transition-all duration-200`} />
                About
            </button>

            {/* Updates Button */}
            <button
                onClick={() => {
                    onToggleUpdates();
                    setOpenSection(null);
                }}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-3 py-2.5 text-left text-[15px] font-medium transition-colors md:py-3 md:text-base
                ${mode === 'updates'
                        ? 'border-indigo-500 bg-indigo-50/95 text-slate-900 shadow-sm dark:border-indigo-400 dark:bg-indigo-950/35 dark:text-white'
                        : 'border-transparent text-slate-800 hover:bg-white/55 dark:text-slate-100 dark:hover:bg-white/[0.06]'
                    }`}
            >
                <Newspaper size={20} className={`transition-all duration-200 group-hover:scale-110 ${mode === 'updates' ? 'text-emerald-700 dark:text-emerald-400' : 'text-emerald-600 dark:text-emerald-400'}`} />
                Updates
            </button>

            {/* Lexify Button */}
            <button
                onClick={() => {
                    onToggleQuiz();
                    setOpenSection(null);
                }}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-3 py-2.5 text-left text-[15px] font-medium transition-colors md:py-3 md:text-base
                ${mode === 'quiz'
                        ? 'border-indigo-500 bg-indigo-50/95 text-slate-900 shadow-sm dark:border-indigo-400 dark:bg-indigo-950/35 dark:text-white'
                        : 'border-transparent text-slate-800 hover:bg-white/55 dark:text-slate-100 dark:hover:bg-white/[0.06]'
                    }`}
            >
                <Brain size={20} className={`${mode === 'quiz' ? 'text-rose-700 dark:text-rose-400' : 'text-rose-600 dark:text-rose-400'} group-hover:scale-110 transition-all duration-200`} />
                Lexify
            </button>

            {/* Flashcards Button */}
            <button
                onClick={() => {
                    if (onToggleFlashcard) onToggleFlashcard();
                    setOpenSection(null);
                }}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-3 py-2.5 text-left text-[15px] font-medium transition-colors md:py-3 md:text-base
                ${mode === 'flashcard'
                        ? 'border-indigo-500 bg-indigo-50/95 text-slate-900 shadow-sm dark:border-indigo-400 dark:bg-indigo-950/35 dark:text-white'
                        : 'border-transparent text-slate-800 hover:bg-white/55 dark:text-slate-100 dark:hover:bg-white/[0.06]'
                    }`}
            >
                <BookOpen size={20} className={`${mode === 'flashcard' ? 'text-indigo-700 dark:text-indigo-400' : 'text-indigo-600 dark:text-indigo-400'} group-hover:scale-110 transition-all duration-200`} />
                Flashcards
            </button>

            {/* LexPlay Button */}
            <button
                onClick={() => {
                    if (onToggleLexPlay) onToggleLexPlay();
                    setOpenSection(null);
                }}
                className="group flex w-full items-center gap-3 rounded-xl border-l-[3px] border-transparent px-3 py-2.5 text-left text-[15px] font-medium text-slate-800 transition-colors hover:bg-white/55 dark:text-slate-100 dark:hover:bg-white/[0.06] md:py-3 md:text-base"
            >
                <Headphones size={20} className="text-purple-600 dark:text-purple-400 group-hover:scale-110 transition-all duration-200" />
                LexPlay
            </button>


            {/* SC Decisions Button */}
            <button
                onClick={() => {
                    onToggleSupremeDecisions();
                    setOpenSection(null);
                }}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-3 py-2.5 text-left text-[15px] font-medium transition-colors md:py-3 md:text-base
                ${mode === 'supreme_decisions'
                        ? 'border-indigo-500 bg-indigo-50/95 text-slate-900 shadow-sm dark:border-indigo-400 dark:bg-indigo-950/35 dark:text-white'
                        : 'border-transparent text-slate-800 hover:bg-white/55 dark:text-slate-100 dark:hover:bg-white/[0.06]'
                    }`}
            >
                <Gavel size={20} className={`transition-all duration-200 group-hover:scale-110 ${mode === 'supreme_decisions' ? 'text-rose-700 dark:text-rose-400' : 'text-rose-600 dark:text-rose-400'}`} />
                SC Decisions
            </button>

            {/* Codex Philippine Section */}
            <div>
                <button
                    onClick={() => toggleSection('codex')}
                    className={`group flex w-full items-center justify-between rounded-xl border-l-[3px] px-3 py-2.5 text-left text-[15px] font-medium transition-colors md:py-3 md:text-base
                    ${mode === 'codex'
                            ? 'border-indigo-500 bg-indigo-50/95 text-slate-900 shadow-sm dark:border-indigo-400 dark:bg-indigo-950/35 dark:text-white'
                            : 'border-transparent text-slate-800 hover:bg-white/55 dark:text-slate-100 dark:hover:bg-white/[0.06]'
                        }`}
                >
                    <span className="flex items-center gap-3">
                        <Library size={20} className={`${mode === 'codex' ? 'text-amber-700 dark:text-amber-400' : 'text-amber-600 dark:text-amber-500'} group-hover:scale-110 transition-all duration-200`} />
                        LexCode
                    </span>
                    {openSection === 'codex' ? <ChevronDown size={18} className="text-slate-400 dark:text-slate-500" /> : <ChevronRight size={18} className="text-slate-400 dark:text-slate-500" />}
                </button>

                {openSection === 'codex' && (
                    <div className="animate-in slide-in-from-top-2 duration-200 overflow-hidden rounded-lg border border-white/20 bg-white/20 dark:border-white/5 dark:bg-slate-900/20">
                        {codexSubjects.map((item) => (
                            <button
                                key={item.id}
                                disabled={item.disabled}
                                onClick={() => !item.disabled && onSelectCodal && onSelectCodal(item.id)}
                                className={`group/item flex w-full items-center gap-3 border-l-[3px] py-2.5 pl-11 pr-3 text-left text-[14px] font-medium transition-colors md:pl-12 md:text-[15px]
                                 ${mode === 'codex' && selectedCodalCode === item.id && !item.disabled
                                        ? 'border-indigo-500 bg-indigo-50/90 text-slate-900 dark:border-indigo-400 dark:bg-indigo-950/40 dark:text-white'
                                        : item.disabled
                                            ? 'cursor-not-allowed border-transparent text-slate-500 opacity-50 dark:text-slate-600'
                                            : 'border-transparent text-slate-600 hover:bg-white/50 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-white/[0.05] dark:hover:text-white'
                                    }`}
                            >
                                {item.title} {item.disabled && <span className="text-xs ml-auto border rounded px-1 py-0.5 text-gray-500 dark:border-gray-600 not-italic no-underline">Soon</span>}
                            </button>
                        ))}
                    </div>
                )}
            </div>





            {/* Bar Questions — subject filter lives on the page */}
            <button
                onClick={() => {
                    if (onSelectSubject) onSelectSubject('All Subjects');
                    setOpenSection(null);
                }}
                className={`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-3 py-2.5 text-left text-[15px] font-medium transition-colors md:py-3 md:text-base
                ${mode === 'browse_bar'
                        ? 'border-indigo-500 bg-indigo-50/95 text-slate-900 shadow-sm dark:border-indigo-400 dark:bg-indigo-950/35 dark:text-white'
                        : 'border-transparent text-slate-800 hover:bg-white/55 dark:text-slate-100 dark:hover:bg-white/[0.06]'
                    }`}
            >
                <Book size={20} className={`${mode === 'browse_bar' ? 'text-amber-700 dark:text-amber-400' : 'text-amber-600 dark:text-amber-500'} group-hover:scale-110 transition-all duration-200`} />
                Bar Questions
            </button>



        </nav >
    );
};

export default Sidebar;
