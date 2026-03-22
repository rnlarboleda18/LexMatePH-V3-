import React, { useState, useRef } from 'react';
import { getSubjectColor } from '../utils/colors';
import { ChevronDown, ChevronRight, BookOpen, Info, History, Scale, Swords, Newspaper, Gavel, Globe, Library, Briefcase, Calculator, Building2, Book, Heart, Users, Headphones, LogIn, UserPlus, Brain } from 'lucide-react';
import { SignedIn, SignedOut, SignInButton, SignUpButton, UserButton } from '@clerk/clerk-react';

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

const Sidebar = ({ onToggleQuiz, onToggleAbout, onToggleUpdates, onToggleSupremeDecisions, onSelectCodal, selectedCodalCode, mode, onToggleLexPlay, onToggleFlashcard }) => {
    const [openSection, setOpenSection] = useState(() => {
        if (mode === 'codex') return 'codex';
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
        <nav className="space-y-1 pb-20"> {/* Added padding bottom for scroll */}

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
                        CodexPhil
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
                                <item.icon size={16} className={`${item.color} ${mode === 'codex' && selectedCodalCode === item.id && !item.disabled ? 'opacity-100 scale-110' : 'opacity-90'} ${item.disabled ? '' : 'group-hover/item:opacity-100 group-hover/item:scale-110 transition-all'}`} />
                                {item.title} {item.disabled && <span className="text-xs ml-auto border rounded px-1 py-0.5 text-gray-500 dark:border-gray-600 not-italic no-underline">Soon</span>}
                            </button>
                        ))}
                    </div>
                )}
            </div>





            {/* Bar Questions Collapsible Section */}



        </nav >
    );
};

export default Sidebar;
