import React, { useState, useRef } from 'react';
import { getSubjectColor } from '../utils/colors';
import { ChevronDown, ChevronRight, BookOpen, Info, History, Scale, Swords, Newspaper, Gavel, Globe, Library, Briefcase, Calculator, Building2, Book, Heart, Users, Headphones, LogIn, UserPlus, Brain, Zap, Crown, Star, Shield } from 'lucide-react';
import { SignedIn, SignedOut, SignInButton, SignUpButton, UserButton } from '@clerk/clerk-react';
import { useSubscription } from '../context/SubscriptionContext';

const subjects = [
    "Civil Law",
    "Commercial Law",
    "Criminal Law",
    "Labor Law",
    "Legal Ethics",
    "Political Law",
    "Remedial Law",
    "Taxation Law"
];

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

const Sidebar = ({ onToggleQuiz, onToggleAbout, onToggleUpdates, onToggleSupremeDecisions, onSelectCodal, selectedCodalCode, mode, onToggleLexPlay, onToggleFlashcard, onSelectSubject, currentSubject }) => {
    const { tier, tierLabel, openUpgradeModal, isAdmin } = useSubscription();
    const TierIcon = isAdmin ? Crown : (TIER_ICON[tier] || Shield);

    const [openSection, setOpenSection] = useState(() => {
        if (mode === 'codex' || mode === 'browse_bar') return mode === 'codex' ? 'codex' : 'bar';
        return null;
    });
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
        <nav className="space-y-1 pb-[calc(5rem_+_var(--player-height,0px))]"> {/* Dynamic padding for LexPlayer */}

            {/* Mobile Only Actions */}
            <div className="lg:hidden px-4 mb-6 space-y-4">
                {/* Auth Section for Mobile */}
                <div className="bg-gray-50 dark:bg-gray-800/40 p-4 rounded-2xl border border-gray-100 dark:border-gray-700/50">
                    <SignedIn>
                        <div className="flex items-center gap-4">
                            <UserButton 
                                appearance={{
                                    elements: {
                                        userButtonAvatarBox: "w-12 h-12"
                                    }
                                }}
                            />
                            <div className="flex flex-col">
                                <span className="text-sm font-bold text-gray-900 dark:text-white">Account Settings</span>
                                <span className="text-xs text-gray-500 dark:text-gray-400">Manage your profile</span>
                            </div>
                        </div>
                    </SignedIn>
                    <SignedOut>
                        <div className="grid grid-cols-2 gap-3">
                            <SignInButton mode="modal">
                                <button className="flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-bold bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-200 shadow-sm active:scale-95 transition-all">
                                    <LogIn size={18} />
                                    <span>Log In</span>
                                </button>
                            </SignInButton>
                            <SignUpButton mode="modal">
                                <button className="flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-bold bg-amber-600 text-white shadow-md shadow-amber-900/20 active:scale-95 transition-all">
                                    <UserPlus size={18} />
                                    <span>Sign Up</span>
                                </button>
                            </SignUpButton>
                        </div>
                    </SignedOut>
                </div>

                <div className="h-px bg-gray-200 dark:bg-gray-700 my-4"></div>
            </div>




            <button
                onClick={() => {
                    onToggleAbout();
                    setOpenSection(null);
                }}
                className={`w-full text-left px-6 py-4 text-lg font-medium transition-colors border-l-[6px] flex items-center gap-3 group
                ${mode === 'about'
                        ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-600 text-amber-800 dark:text-amber-400'
                        : 'border-transparent hover:bg-gray-50 dark:hover:bg-gray-800/50 text-gray-900 dark:text-white'
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
                className={`w-full text-left px-6 py-4 text-lg font-medium transition-colors border-l-[6px] flex items-center gap-3 group
                ${mode === 'updates'
                        ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-600 text-amber-800 dark:text-amber-400'
                        : 'border-transparent hover:bg-gray-50 dark:hover:bg-gray-800/50 text-gray-900 dark:text-white'
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
                className={`w-full text-left px-6 py-4 text-lg font-medium transition-colors border-l-[6px] flex items-center gap-3 group
                ${mode === 'quiz'
                        ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-600 text-amber-800 dark:text-amber-400'
                        : 'border-transparent hover:bg-gray-50 dark:hover:bg-gray-800/50 text-gray-900 dark:text-white'
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
                className={`w-full text-left px-6 py-4 text-lg font-medium transition-colors border-l-[6px] flex items-center gap-3 group
                ${mode === 'flashcard'
                        ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-600 text-amber-800 dark:text-amber-400'
                        : 'border-transparent hover:bg-gray-50 dark:hover:bg-gray-800/50 text-gray-900 dark:text-white'
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
                className={`w-full text-left px-6 py-4 text-lg font-medium transition-colors border-l-[6px] flex items-center gap-3 group border-transparent hover:bg-gray-50 dark:hover:bg-gray-800/50 text-gray-900 dark:text-white`}
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
                className={`w-full text-left px-6 py-4 text-lg font-medium transition-colors border-l-[6px] flex items-center gap-3 group
                ${mode === 'supreme_decisions'
                        ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-600 text-amber-800 dark:text-amber-400'
                        : 'border-transparent hover:bg-gray-50 dark:hover:bg-gray-800/50 text-gray-900 dark:text-white'
                    }`}
            >
                <Gavel size={20} className={`transition-all duration-200 group-hover:scale-110 ${mode === 'supreme_decisions' ? 'text-rose-700 dark:text-rose-400' : 'text-rose-600 dark:text-rose-400'}`} />
                SC Decisions
            </button>

            {/* Codex Philippine Section */}
            <div>
                <button
                    onClick={() => toggleSection('codex')}
                    className={`w-full text-left px-6 py-4 text-lg font-medium transition-colors border-l-[6px] flex items-center justify-between group
                    ${mode === 'codex'
                            ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-600 text-amber-800 dark:text-amber-400'
                            : 'border-transparent hover:bg-gray-50 dark:hover:bg-gray-800/50 text-gray-900 dark:text-white'
                        }`}
                >
                    <span className="flex items-center gap-3">
                        <Library size={20} className={`${mode === 'codex' ? 'text-amber-700 dark:text-amber-400' : 'text-amber-600 dark:text-amber-500'} group-hover:scale-110 transition-all duration-200`} />
                        LexCode
                    </span>
                    {openSection === 'codex' ? <ChevronDown size={18} className="text-gray-400" /> : <ChevronRight size={18} className="text-gray-400" />}
                </button>

                {openSection === 'codex' && (
                    <div className="animate-in slide-in-from-top-2 duration-200">
                        {codexSubjects.map((item) => (
                            <button
                                key={item.id}
                                disabled={item.disabled}
                                onClick={() => !item.disabled && onSelectCodal && onSelectCodal(item.id)}
                                className={`w-full text-left pl-14 pr-6 py-3 text-base font-medium transition-colors border-l-[6px] flex items-center gap-3 group/item
                                 ${mode === 'codex' && selectedCodalCode === item.id && !item.disabled
                                        ? 'bg-amber-100/50 dark:bg-amber-900/30 border-amber-500 text-amber-900 dark:text-amber-300'
                                        : item.disabled
                                            ? 'border-transparent text-gray-500 dark:text-gray-600 cursor-not-allowed opacity-50'
                                            : 'border-transparent hover:bg-amber-50 dark:hover:bg-amber-900/10 text-gray-600 dark:text-gray-300 hover:text-amber-800 dark:hover:text-amber-400'
                                    }`}
                            >
                                {item.title} {item.disabled && <span className="text-xs ml-auto border rounded px-1 py-0.5 text-gray-500 dark:border-gray-600 not-italic no-underline">Soon</span>}
                            </button>
                        ))}
                    </div>
                )}
            </div>





            {/* Bar Questions Collapsible Section */}
            <div>
                <button
                    onClick={() => toggleSection('bar')}
                    className={`w-full text-left px-6 py-4 text-lg font-medium transition-colors border-l-[6px] flex items-center justify-between group
                    ${mode === 'browse_bar' && openSection === 'bar'
                            ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-600 text-amber-800 dark:text-amber-400'
                            : 'border-transparent hover:bg-gray-50 dark:hover:bg-gray-800/50 text-gray-900 dark:text-white'
                        }`}
                >
                    <span className="flex items-center gap-3">
                        <Book size={20} className={`${openSection === 'bar' ? 'text-amber-700 dark:text-amber-400' : 'text-amber-600 dark:text-amber-500'} group-hover:scale-110 transition-all duration-200`} />
                        Bar Questions
                    </span>
                    {openSection === 'bar' ? <ChevronDown size={18} className="text-gray-400" /> : <ChevronRight size={18} className="text-gray-400" />}
                </button>

                {openSection === 'bar' && (
                    <div className="animate-in slide-in-from-top-2 duration-200">
                        <button
                            onClick={() => onSelectSubject && onSelectSubject('All Subjects')}
                            className={`w-full text-left pl-14 pr-6 py-3 text-base font-medium transition-colors border-l-[6px] group/item
                                ${mode === 'browse_bar' && (currentSubject === null || currentSubject === 'All Subjects')
                                    ? 'bg-amber-100/50 dark:bg-amber-900/30 border-amber-500 text-amber-900 dark:text-amber-300'
                                    : 'border-transparent hover:bg-amber-50 dark:hover:bg-amber-900/10 text-gray-600 dark:text-gray-300 hover:text-amber-800 dark:hover:text-amber-400'
                                }`}
                        >
                            <span className="w-2 h-2 rounded-full mr-2 bg-gray-400 dark:bg-gray-500 opacity-70 group-hover/item:opacity-100 transition-all" />
                            All Subjects
                        </button>
                        {subjects.map((subject) => (
                            <button
                                key={subject}
                                onClick={() => onSelectSubject && onSelectSubject(subject)}
                                className={`w-full text-left pl-14 pr-6 py-3 text-base font-medium transition-colors border-l-[6px] group/item
                                    ${mode === 'browse_bar' && currentSubject === subject
                                        ? 'bg-amber-100/50 dark:bg-amber-900/30 border-amber-500 text-amber-900 dark:text-amber-300'
                                        : 'border-transparent hover:bg-amber-50 dark:hover:bg-amber-900/10 text-gray-600 dark:text-gray-300 hover:text-amber-800 dark:hover:text-amber-400'
                                    }`}
                            >
                                <span className={`w-2 h-2 rounded-full mr-2 ${getSubjectColor(subject)} opacity-70 group-hover/item:opacity-100 transition-all`} />
                                {subject}
                            </button>
                        ))}
                    </div>
                )}
            </div>



            {/* Subscription Tier Badge */}
            <SignedIn>
                <div className={`mx-4 mt-6 mb-2 p-3 rounded-2xl border ${isAdmin ? TIER_BG.admin : TIER_BG[tier]} flex items-center gap-3`}>
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

        </nav >
    );
};

export default Sidebar;
