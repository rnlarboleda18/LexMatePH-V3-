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

    return (
        <div className={`min-h-screen transition-colors duration-300 relative ${isDarkMode ? 'dark bg-[#0a0f1c] text-slate-200' : 'bg-slate-50 text-slate-900'}`}>
            {/* Global Glassmorphism Background Orbs — GPU-composited, no external fetch */}
            <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden" style={{contain:'strict'}}>
                <div className={`absolute -top-[20%] -left-[10%] w-[50%] h-[50%] rounded-full filter blur-[80px] opacity-30 animate-float ${isDarkMode ? 'bg-indigo-900' : 'bg-indigo-200'}`} style={{willChange:'transform'}}></div>
                <div className={`absolute top-[20%] -right-[10%] w-[50%] h-[50%] rounded-full filter blur-[80px] opacity-30 animate-float ${isDarkMode ? 'bg-purple-900' : 'bg-purple-200'}`} style={{animationDelay: '1s', willChange:'transform'}}></div>
                <div className={`absolute -bottom-[20%] left-[20%] w-[50%] h-[50%] rounded-full filter blur-[80px] opacity-20 animate-float ${isDarkMode ? 'bg-blue-900' : 'bg-blue-200'}`} style={{animationDelay: '2s', willChange:'transform'}}></div>
            </div>
            
            <div className="relative z-10 flex flex-col min-h-screen">

            {/* Header */}
            {!hideAppChrome && (
                <header className={`fixed top-0 left-0 right-0 z-50 grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-2 px-3 pt-[env(safe-area-inset-top,0px)] md:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] md:gap-x-4 md:px-8
                    ${isDarkMode
                        ? 'min-h-[calc(3.5rem+env(safe-area-inset-top,0px))] md:min-h-[calc(5rem+env(safe-area-inset-top,0px))] bg-slate-900/60 md:bg-slate-900/40 md:backdrop-blur-xl border-b border-white/10 shadow-[0_4px_30_px_rgba(0,0,0,0.3)]'
                        : 'min-h-[calc(3.5rem+env(safe-area-inset-top,0px))] md:min-h-[calc(5rem+env(safe-area-inset-top,0px))] bg-white/80 md:bg-white/40 md:backdrop-blur-xl border-b border-white/40 shadow-[0_4px_30_px_rgba(0,0,0,0.05)]'
                    }`} style={{willChange:'transform'}}>

                    {/* LEFT — Brand */}
                    <div className="relative z-10 flex min-w-0 items-center gap-2 md:gap-3">
                        {/* Mobile hamburger — box size matches scales mark beside it */}
                        <button
                            type="button"
                            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                            className={`xl:hidden flex shrink-0 h-9 w-9 items-center justify-center rounded-xl border transition-colors sm:h-10 sm:w-10 md:h-12 md:w-12 lg:h-14 lg:w-14 ${
                                isDarkMode
                                    ? 'border-white/10 bg-white/[0.06] text-gray-300 hover:text-amber-400 hover:bg-amber-900/20'
                                    : 'border-slate-200/90 bg-white text-gray-600 shadow-sm hover:text-amber-700 hover:bg-amber-50'
                            }`}
                            aria-label="Toggle Sidebar"
                        >
                            {isSidebarOpen ? (
                                <X className="h-[1.15rem] w-[1.15rem] sm:h-6 sm:w-6 md:h-7 md:w-7 lg:h-8 lg:w-8" strokeWidth={2} />
                            ) : (
                                <Menu className="h-[1.15rem] w-[1.15rem] sm:h-6 sm:w-6 md:h-7 md:w-7 lg:h-8 lg:w-8" strokeWidth={2} />
                            )}
                        </button>

                        {/* Brand — wordmark + scales mark (no vertical bar); LexMatePH casing preserved */}
                        <div className="flex min-w-0 items-center gap-2.5 md:gap-3">
                            <div
                                className={`flex shrink-0 items-center justify-center rounded-xl border h-9 w-9 sm:h-10 sm:w-10 md:h-12 md:w-12 lg:h-14 lg:w-14 ${
                                    isDarkMode
                                        ? 'border-white/10 bg-white/[0.06] text-indigo-300'
                                        : 'border-slate-200/90 bg-white text-indigo-600 shadow-sm'
                                }`}
                                aria-hidden
                            >
                                <Scale
                                    className="h-[1.15rem] w-[1.15rem] sm:h-6 sm:w-6 md:h-7 md:w-7 lg:h-8 lg:w-8"
                                    strokeWidth={2}
                                />
                            </div>
                            <div className="flex min-w-0 flex-col">
                                <span
                                    className={`select-none font-semibold leading-none tracking-tight text-[1.125rem] sm:text-xl md:text-2xl lg:text-[1.75rem] ${
                                        isDarkMode
                                            ? 'text-stone-50 drop-shadow-[0_1px_0_rgba(0,0,0,0.35)]'
                                            : 'text-slate-900'
                                    }`}
                                >
                                    LexMatePH
                                </span>
                                <span
                                    className={`mt-1 hidden text-[11px] font-medium leading-snug tracking-tight md:block md:text-xs lg:text-[13px] ${
                                        isDarkMode ? 'text-slate-400' : 'text-slate-500'
                                    }`}
                                >
                                    Your Law Companion
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* CENTER — Feature strip (same row as logo; grid-centered between brand and actions) */}
                    <nav
                        className="hidden min-w-0 max-w-[min(46vw,32rem)] justify-center justify-self-center px-1 text-center md:flex md:items-center"
                        aria-label="LexMatePH feature areas"
                    >
                        <p
                            className={`flex flex-wrap items-center justify-center gap-x-2 gap-y-1 text-[15px] font-semibold leading-snug tracking-tight md:text-[17px] lg:text-lg xl:text-xl ${
                                isDarkMode ? 'text-slate-300' : 'text-slate-600'
                            }`}
                        >
                            <span className="whitespace-nowrap">Bar Questions</span>
                            <span className="text-slate-500 dark:text-slate-500" aria-hidden>
                                ·
                            </span>
                            <span className="whitespace-nowrap">SC Decisions</span>
                            <span className="text-slate-500 dark:text-slate-500" aria-hidden>
                                ·
                            </span>
                            <span className="whitespace-nowrap">Case Digests</span>
                            <span className="text-slate-500 dark:text-slate-500" aria-hidden>
                                ·
                            </span>
                            <span className="whitespace-nowrap">Codals</span>
                        </p>
                    </nav>

                    {/* RIGHT — Actions */}
                    <div className="relative z-10 col-start-2 flex shrink-0 items-center justify-end gap-1.5 justify-self-end md:col-start-3 md:gap-2">

                        {/* Theme Toggle */}
                        <button
                            onClick={toggleTheme}
                            title={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
                            className={`flex items-center gap-2 px-3 py-1.5 md:px-4 md:py-2 rounded-lg text-base md:text-lg font-medium transition-all duration-200
                                ${isDarkMode
                                    ? 'text-gray-400 hover:text-amber-400 hover:bg-amber-900/20 border border-transparent hover:border-amber-800/40'
                                    : 'text-gray-500 hover:text-amber-700 hover:bg-amber-50 border border-transparent hover:border-amber-200'
                                }`}
                        >
                            {isDarkMode ? <Sun size={18} className="text-amber-400 md:w-[20px] md:h-[20px]" /> : <Moon size={18} className="text-violet-500 md:w-[20px] md:h-[20px]" />}
                            <span className="hidden md:inline">{isDarkMode ? 'Light' : 'Dark'}</span>
                        </button>


                        {/* Divider */}
                        <div className={`hidden sm:block w-px h-5 md:h-6 mx-1 ${isDarkMode ? 'bg-gray-700' : 'bg-stone-200'}`} />

                        {/* Auth - Hidden on mobile, moved to sidebar */}
                        <div className="hidden md:flex items-center gap-2">
                            <SignedIn>
                                <UserButton 
                                    appearance={{
                                        elements: {
                                            userButtonAvatarBox: "w-10 h-10"
                                        }
                                    }}
                                />
                            </SignedIn>
                            <SignedOut>
                                <div className="flex items-center gap-1.5">
                                    <SignInButton mode="modal">
                                        <button className={`px-4 py-2 rounded-lg text-lg font-semibold transition-all duration-200 ${isDarkMode ? 'text-amber-400 hover:bg-amber-900/20' : 'text-amber-700 hover:bg-amber-50'}`}>
                                            Log In
                                        </button>
                                    </SignInButton>
                                    <SignUpButton mode="modal">
                                        <button className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-lg font-semibold transition-all duration-200 shadow-sm">
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
                    className={`fixed left-0 bottom-0 w-52 z-40 transform transition-transform duration-300 ease-in-out shadow-xl overflow-y-auto top-[calc(3.5rem+env(safe-area-inset-top,0px))] md:top-[calc(5rem+env(safe-area-inset-top,0px))]
            ${isDarkMode ? 'bg-slate-900 xl:bg-slate-900/40 xl:backdrop-blur-xl border-r border-white/10 shadow-[6px_0_24px_-4px_rgba(0,0,0,0.3)]' : 'bg-white xl:bg-white/40 xl:backdrop-blur-xl border-r border-white/40 shadow-[6px_0_24px_-4px_rgba(0,0,0,0.1)]'}
            ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'} 
            xl:translate-x-0 xl:block`}
                    style={{willChange:'transform'}}
                >
                    <div className="h-full flex flex-col pt-4 md:pt-8">
                        {sidebarContent}
                    </div>
                </aside>
            )}

            {/* Main Content Area — z-10 so mobile sidebar scrim (rendered after) can sit above and capture taps */}
            <main
                className={`relative z-10 ${hideAppChrome ? 'pt-0' : lexPlayFullscreen ? 'pt-0 lg:pt-[calc(5rem+env(safe-area-inset-top,0px))]' : 'pt-[calc(3.5rem+env(safe-area-inset-top,0px))] md:pt-[calc(5rem+env(safe-area-inset-top,0px))]'} min-h-screen
        ${hideAppChrome ? 'w-full !ml-0 max-w-full px-0' : `xl:ml-52 ${['supreme_decisions', 'codex', 'browse_bar', 'flashcard', 'about', 'updates', 'quiz'].includes(mode) ? 'px-0' : 'px-4 lg:px-8'} pb-[var(--player-height,0px)]`}`}
                style={{touchAction:'pan-y', WebkitOverflowScrolling:'touch'}}
            >
                <div
                    className={`${
                        hideAppChrome
                            ? 'max-w-full'
                            : ['codex', 'about', 'updates', 'quiz'].includes(mode)
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
