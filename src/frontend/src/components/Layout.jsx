import React, { useState, useEffect } from 'react';
import { Sun, Moon, Menu, X, Scale } from 'lucide-react';
import { SignedIn, SignedOut, SignInButton, SignUpButton, UserButton } from '@clerk/clerk-react';

const Layout = ({
    children,
    sidebarContent,
    isDarkMode,
    toggleTheme,
    mode,
    onToggleMode,
    onToggleQuiz,
    user,
    /** True = hide global header + sidebar (browser fullscreen OR Lexify exam simulation). */
    hideAppChrome = false,
    mainFullWidth = false,
    lexPlayFullscreen = false,
    /** True = blur the background while flashcard study session is active. */
    flashcardStudying = false,
}) => {
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);


    // Close sidebar on mobile when window resizes to desktop
    useEffect(() => {
        const handleResize = () => {
            if (window.innerWidth >= 1280) {
                setIsSidebarOpen(false);
            }
        };
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    // Close sidebar on mobile when mode changes
    useEffect(() => {
        setIsSidebarOpen(false);
    }, [mode]);

    return (
        <div className={`min-h-screen transition-colors duration-300 relative ${isDarkMode ? 'dark bg-[#0a0f1c] text-slate-200' : 'bg-slate-100 text-slate-950 antialiased'}`}>
            {/* Global Glassmorphism Background Orbs — GPU-composited, no external fetch */}
            <div
                className="fixed inset-0 pointer-events-none z-0 overflow-hidden"
                style={{ contain: 'strict', filter: flashcardStudying ? 'blur(8px)' : 'none', transition: 'filter 0.3s ease' }}
            >
                <div className={`absolute -top-[20%] -left-[10%] w-[50%] h-[50%] rounded-full filter blur-[80px] opacity-30 animate-float ${isDarkMode ? 'bg-indigo-900' : 'bg-indigo-200'}`} style={{willChange:'transform'}}></div>
                <div className={`absolute top-[20%] -right-[10%] w-[50%] h-[50%] rounded-full filter blur-[80px] opacity-30 animate-float ${isDarkMode ? 'bg-purple-900' : 'bg-purple-200'}`} style={{animationDelay: '1s', willChange:'transform'}}></div>
                <div className={`absolute -bottom-[20%] left-[20%] w-[50%] h-[50%] rounded-full filter blur-[80px] opacity-20 animate-float ${isDarkMode ? 'bg-blue-900' : 'bg-blue-200'}`} style={{animationDelay: '2s', willChange:'transform'}}></div>
            </div>

            {/* Flashcard blur overlay — removed; blur applied directly via filter on each element below */}

            <div className="relative z-10 flex flex-col min-h-screen">

            {/* Header */}
            {!hideAppChrome && (
                <header
                    className={`fixed top-0 left-0 right-0 z-50 flex flex-wrap items-center gap-x-2 gap-y-1.5 px-3 pt-[env(safe-area-inset-top,0px)] pb-1.5 sm:flex-nowrap sm:gap-y-0 md:gap-x-3 md:px-4 md:pb-2 lg:gap-x-4 lg:px-5
                    min-h-[calc(var(--app-header-height)+env(safe-area-inset-top,0px))]
                    ${isDarkMode
                        ? 'bg-slate-900/60 md:bg-slate-900/40 md:backdrop-blur-xl border-b border-white/10 shadow-[0_4px_30_px_rgba(0,0,0,0.3)]'
                        : 'border-b-2 border-slate-300/90 bg-white/95 md:bg-white/90 md:backdrop-blur-xl shadow-[0_4px_24px_-4px_rgba(15,23,42,0.08)]'
                    }`}
                    style={{ willChange: 'transform', filter: flashcardStudying ? 'blur(4px)' : 'none', transition: 'filter 0.3s ease' }}
                >

                    {/* Brand + menu */}
                    <div className="relative z-10 flex min-w-0 min-h-0 shrink-0 items-center gap-2 md:gap-2.5">
                        <button
                            type="button"
                            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                            className={`xl:hidden flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border transition-colors ${
                                isDarkMode
                                    ? 'border-white/10 bg-white/[0.06] text-gray-300 hover:bg-amber-900/20 hover:text-amber-400'
                                    : 'border-2 border-slate-400/70 bg-white text-gray-700 shadow-sm hover:bg-amber-50 hover:text-amber-800'
                            }`}
                            aria-label="Toggle Sidebar"
                        >
                            {isSidebarOpen ? (
                                <X className="h-[1.1rem] w-[1.1rem]" strokeWidth={2} />
                            ) : (
                                <Menu className="h-[1.1rem] w-[1.1rem]" strokeWidth={2} />
                            )}
                        </button>

                        <div className="flex min-w-0 items-center gap-2 md:gap-2.5">
                            <div
                                className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border ${
                                    isDarkMode
                                        ? 'border-white/10 bg-white/[0.06] text-indigo-300'
                                        : 'border-2 border-slate-400/70 bg-white text-indigo-700 shadow-sm'
                                }`}
                                aria-hidden
                            >
                                <Scale className="h-[1.1rem] w-[1.1rem]" strokeWidth={2} />
                            </div>
                            <div className="flex min-w-0 flex-col justify-center leading-tight">
                                <span
                                    className={`select-none truncate font-semibold tracking-tight text-base sm:text-lg md:text-[1.125rem] ${
                                        isDarkMode
                                            ? 'text-stone-50 drop-shadow-[0_1px_0_rgba(0,0,0,0.35)]'
                                            : 'text-slate-950'
                                    }`}
                                >
                                    LexMatePH
                                </span>
                                <span
                                    className={`mt-0.5 hidden text-[10px] font-medium leading-tight tracking-tight sm:block sm:text-[11px] md:text-xs ${
                                        isDarkMode ? 'text-slate-400' : 'text-slate-600'
                                    }`}
                                >
                                    Your Law Companion
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Center links — flex-1 keeps spacing between brand and actions; wraps only on very narrow sm */}
                    <nav
                        className="order-last hidden w-full min-w-0 justify-center border-t border-slate-200/70 px-1 pt-1.5 dark:border-white/10 sm:order-none sm:flex sm:w-auto sm:flex-1 sm:basis-0 sm:border-t-0 sm:px-1 sm:pt-0 md:px-2"
                        aria-label="LexMatePH feature areas"
                    >
                        <p
                            className={`flex flex-wrap items-center justify-center gap-x-1.5 gap-y-0.5 text-center text-[10px] font-semibold leading-snug tracking-tight sm:text-[11px] md:text-xs lg:text-sm xl:text-[0.9375rem] ${
                                isDarkMode ? 'text-slate-300' : 'text-slate-700'
                            }`}
                        >
                            <span className="whitespace-nowrap">Bar Questions</span>
                            <span className="text-slate-600 dark:text-slate-500" aria-hidden>
                                ·
                            </span>
                            <span className="whitespace-nowrap">SC Decisions</span>
                            <span className="text-slate-600 dark:text-slate-500" aria-hidden>
                                ·
                            </span>
                            <span className="whitespace-nowrap">Case Digests</span>
                            <span className="text-slate-600 dark:text-slate-500" aria-hidden>
                                ·
                            </span>
                            <span className="whitespace-nowrap">Codals</span>
                        </p>
                    </nav>

                    <div className="relative z-10 flex shrink-0 items-center justify-end gap-1 md:gap-1.5">
                        <button
                            onClick={toggleTheme}
                            type="button"
                            title={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
                            className={`flex items-center gap-1.5 rounded-md px-2 py-1 text-sm font-medium transition-all duration-200 md:gap-2 md:px-2.5 md:py-1.5 md:text-base
                                ${isDarkMode
                                    ? 'border border-transparent text-gray-400 hover:border-amber-800/40 hover:bg-amber-900/20 hover:text-amber-400'
                                    : 'border-2 border-transparent text-gray-700 hover:border-amber-300/90 hover:bg-amber-50 hover:text-amber-900'
                                }`}
                        >
                            {isDarkMode ? (
                                <Sun size={17} className="shrink-0 text-amber-400 md:h-[18px] md:w-[18px]" />
                            ) : (
                                <Moon size={17} className="shrink-0 text-violet-500 md:h-[18px] md:w-[18px]" />
                            )}
                            <span className="hidden sm:inline">{isDarkMode ? 'Light' : 'Dark'}</span>
                        </button>

                        <div className={`hidden sm:block h-4 w-px shrink-0 rounded-full md:h-5 ${isDarkMode ? 'bg-gray-700' : 'bg-slate-400/80'}`} />

                        <div className="hidden items-center gap-1.5 md:flex">
                            <SignedIn>
                                <UserButton
                                    appearance={{
                                        elements: {
                                            userButtonAvatarBox: 'h-9 w-9',
                                        },
                                    }}
                                />
                            </SignedIn>
                            <SignedOut>
                                <div className="flex items-center gap-1">
                                    <SignInButton mode="modal">
                                        <button
                                            type="button"
                                            className={`rounded-md px-2.5 py-1.5 text-sm font-semibold transition-all duration-200 md:px-3 md:text-[0.9375rem] ${isDarkMode ? 'text-amber-400 hover:bg-amber-900/20' : 'text-amber-700 hover:bg-amber-50'}`}
                                        >
                                            Log In
                                        </button>
                                    </SignInButton>
                                    <SignUpButton mode="modal">
                                        <button
                                            type="button"
                                            className="rounded-md bg-amber-600 px-2.5 py-1.5 text-sm font-semibold text-white shadow-sm transition-all duration-200 hover:bg-amber-700 md:px-3 md:text-[0.9375rem]"
                                        >
                                            Sign Up
                                        </button>
                                    </SignUpButton>
                                </div>
                            </SignedOut>
                        </div>
                    </div>
                </header>
            )}

            {/* Sidebar (Navigation Drawer) */}
            {!hideAppChrome && (
                <aside
                    className={`fixed left-0 bottom-0 w-52 z-40 transform transition-transform duration-300 ease-in-out shadow-xl overflow-y-auto top-[calc(var(--app-header-height)+env(safe-area-inset-top,0px))]
            ${isDarkMode ? 'bg-slate-900 xl:bg-slate-900/40 xl:backdrop-blur-xl border-r border-white/10 shadow-[6px_0_24px_-4px_rgba(0,0,0,0.3)]' : 'border-r-2 border-slate-300/90 bg-white xl:bg-white/85 xl:backdrop-blur-xl shadow-[6px_0_24px_-4px_rgba(15,23,42,0.08)]'}
            ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'} 
            xl:translate-x-0 xl:block`}
                    style={{ willChange: 'transform', filter: flashcardStudying ? 'blur(4px)' : 'none', transition: 'filter 0.3s ease' }}
                >
                    <div className="h-full flex flex-col pt-4 md:pt-8">
                        {sidebarContent}
                    </div>
                </aside>
            )}

            {/* Main Content Area — z-10 so mobile sidebar scrim can sit above and capture taps */}
            <main
                className={`relative z-10 ${hideAppChrome ? 'pt-0' : lexPlayFullscreen ? 'pt-0 lg:pt-[calc(var(--app-header-height)+env(safe-area-inset-top,0px))]' : 'pt-[calc(var(--app-header-height)+env(safe-area-inset-top,0px))]'} min-h-screen
        ${hideAppChrome ? 'w-full !ml-0 max-w-full px-0' : `xl:ml-52 ${['supreme_decisions', 'codex', 'browse_bar', 'flashcard', 'about', 'updates', 'quiz', 'landing'].includes(mode) ? 'px-0' : 'px-4 lg:px-8'} pb-[var(--player-height,0px)]`}`}
                style={{touchAction:'pan-y', WebkitOverflowScrolling:'touch'}}
            >
                <div
                    className={`${
                        hideAppChrome
                            ? 'max-w-full'
                            : ['codex', 'about', 'updates', 'quiz', 'landing'].includes(mode)
                              ? 'max-w-full ml-0'
                              : mainFullWidth
                                ? 'mx-auto w-full max-w-none'
                                : 'mx-auto max-w-7xl'
                    }`}
                >
                    {children}
                </div>
            </main>

            {/* Mobile sidebar scrim: must be after <main> in DOM so it stacks above page content (z-35 < aside z-40 < header z-50) */}
            {isSidebarOpen && !hideAppChrome && (
                <div
                    className="fixed inset-0 z-[35] bg-black/50 xl:hidden"
                    aria-hidden
                    onClick={() => setIsSidebarOpen(false)}
                />
            )}
            </div>
        </div>
    );
};

export default Layout;
