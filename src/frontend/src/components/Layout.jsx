import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Sun, Moon, Menu, X, Scale } from 'lucide-react';
import { SignedIn, SignedOut, SignInButton, SignUpButton, UserButton } from '@clerk/clerk-react';
import { APP_HEADER_SURFACE, SIDEBAR_ASIDE_SURFACE } from '../utils/filterChromeClasses';

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
        <div className={`min-h-screen transition-colors duration-300 relative ${isDarkMode ? 'dark bg-zinc-950 text-zinc-200' : 'bg-neutral-100 text-neutral-950 antialiased'}`}>
            {/* Flat page background — no animated glass orbs */}
            <div
                className="fixed inset-0 z-0 bg-neutral-100 dark:bg-zinc-950"
                style={{ filter: flashcardStudying ? 'blur(6px)' : 'none', transition: 'filter 0.3s ease' }}
                aria-hidden
            />

            {/* Flashcard blur overlay — removed; blur applied directly via filter on each element below */}

            <div className="relative z-10 flex flex-col min-h-screen">

            {/* Header — portaled to document.body so position:fixed stays tied to the viewport on mobile
                (avoids iOS jank when any ancestor uses filter/transform/contain). */}
            {!hideAppChrome &&
                typeof document !== 'undefined' &&
                createPortal(
                    <div className={isDarkMode ? 'dark' : ''} data-lex-app-chrome>
                        <header
                            className={`fixed top-0 left-0 right-0 z-50 flex flex-wrap items-center gap-x-2 gap-y-1.5 px-3 pt-[env(safe-area-inset-top,0px)] pb-1.5 sm:flex-nowrap sm:gap-y-0 md:gap-x-3 md:px-4 md:pb-2 lg:gap-x-4 lg:px-5
                    min-h-[calc(var(--app-header-height)+env(safe-area-inset-top,0px))]
                    ${APP_HEADER_SURFACE}`}
                            style={{
                                filter: flashcardStudying ? 'blur(4px)' : 'none',
                                transition: 'filter 0.3s ease',
                            }}
                        >

                    {/* Brand + menu */}
                    <div className="relative z-10 flex min-w-0 min-h-0 shrink-0 items-center gap-2 md:gap-2.5">
                        <button
                            type="button"
                            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                            className={`xl:hidden flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border transition-colors backdrop-blur-md ${
                                isDarkMode
                                    ? 'border-zinc-600 bg-zinc-900/80 text-zinc-200 shadow-sm ring-1 ring-inset ring-white/[0.06] hover:bg-zinc-800 hover:text-white'
                                    : 'border-lex-strong bg-white text-black shadow-sm ring-1 ring-inset ring-neutral-200/80 hover:bg-neutral-50'
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
                                className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border backdrop-blur-md ${
                                    isDarkMode
                                        ? 'border-zinc-600 bg-zinc-900/80 text-zinc-200 shadow-sm ring-1 ring-inset ring-white/[0.06]'
                                        : 'border-lex-strong bg-white text-black shadow-sm ring-1 ring-inset ring-neutral-200/80'
                                }`}
                                aria-hidden
                            >
                                <Scale className="h-[1.1rem] w-[1.1rem]" strokeWidth={2} />
                            </div>
                            <div className="flex min-w-0 flex-col justify-center leading-tight">
                                <span
                                    className={`select-none truncate font-semibold tracking-tight text-base sm:text-lg md:text-[1.125rem] ${
                                        isDarkMode
                                            ? 'text-zinc-50 drop-shadow-[0_1px_0_rgba(0,0,0,0.35)]'
                                            : 'text-black'
                                    }`}
                                >
                                    LexMatePH
                                </span>
                                <span
                                    className={`mt-0.5 hidden text-[10px] font-semibold leading-tight tracking-tight sm:block sm:text-[11px] md:text-xs ${
                                        isDarkMode ? 'text-zinc-400' : 'text-black'
                                    }`}
                                >
                                    Your Law Companion
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Center links — flex-1 keeps spacing between brand and actions; wraps only on very narrow sm */}
                    <nav
                        className="order-last hidden w-full min-w-0 justify-center border-t border-lex px-1 pt-1.5 sm:order-none sm:flex sm:w-auto sm:flex-1 sm:basis-0 sm:border-t-0 sm:px-1 sm:pt-0 md:px-2"
                        aria-label="LexMatePH feature areas"
                    >
                        <p
                            className={`flex flex-wrap items-center justify-center gap-x-1.5 gap-y-0.5 text-center text-[10px] font-semibold leading-snug tracking-tight sm:text-[11px] md:text-xs lg:text-sm xl:text-[0.9375rem] ${
                                isDarkMode ? 'text-zinc-300' : 'text-black'
                            }`}
                        >
                            <span className="whitespace-nowrap">Bar Questions</span>
                            <span className="text-neutral-400 dark:text-zinc-600" aria-hidden>
                                ·
                            </span>
                            <span className="whitespace-nowrap">SC Decisions</span>
                            <span className="text-neutral-400 dark:text-zinc-600" aria-hidden>
                                ·
                            </span>
                            <span className="whitespace-nowrap">Case Digests</span>
                            <span className="text-neutral-400 dark:text-zinc-600" aria-hidden>
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
                                    ? 'border border-transparent text-zinc-400 hover:border-zinc-700 hover:bg-zinc-800/80 hover:text-zinc-100'
                                    : 'border-2 border-transparent text-neutral-800 hover:border-lex-strong hover:bg-neutral-200/80 hover:text-neutral-950'
                                }`}
                        >
                            {isDarkMode ? (
                                <Sun size={17} className="shrink-0 text-amber-300 md:h-[18px] md:w-[18px]" />
                            ) : (
                                <Moon size={17} className="shrink-0 text-violet-700 md:h-[18px] md:w-[18px]" />
                            )}
                            <span className="hidden sm:inline">{isDarkMode ? 'Light' : 'Dark'}</span>
                        </button>

                        <div className={`hidden sm:block h-4 w-px shrink-0 rounded-full md:h-5 ${isDarkMode ? 'bg-zinc-700' : 'bg-violet-200/80'}`} />

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
                                            className={`rounded-md px-2.5 py-1.5 text-sm font-semibold transition-all duration-200 md:px-3 md:text-[0.9375rem] ${isDarkMode ? 'text-zinc-300 hover:bg-zinc-800' : 'text-black hover:bg-neutral-100'}`}
                                        >
                                            Log In
                                        </button>
                                    </SignInButton>
                                    <SignUpButton mode="modal">
                                        <button
                                            type="button"
                                            className="rounded-md bg-gradient-to-r from-violet-800 to-purple-900 px-2.5 py-1.5 text-sm font-semibold text-white shadow-md shadow-violet-900/25 transition-all duration-200 hover:opacity-95 md:px-3 md:text-[0.9375rem]"
                                        >
                                            Sign Up
                                        </button>
                                    </SignUpButton>
                                </div>
                            </SignedOut>
                        </div>
                    </div>
                        </header>
                    </div>,
                    document.body
                )}

            {/* Sidebar + mobile scrim — portaled to document.body (same rationale as header) so fixed
                z-40 stacks above LexCode TOC FAB and other body-level portals that only use z-[30]–z-[42]. */}
            {!hideAppChrome &&
                typeof document !== 'undefined' &&
                createPortal(
                    <div className={isDarkMode ? 'dark' : ''} data-lex-app-navigation>
                        {isSidebarOpen && (
                            <div
                                className="fixed inset-0 z-[39] bg-black/50 xl:hidden"
                                aria-hidden
                                onClick={() => setIsSidebarOpen(false)}
                            />
                        )}
                        <aside
                            className={`fixed bottom-0 left-0 top-[calc(var(--app-header-height)+env(safe-area-inset-top,0px))] z-40 w-52 transform overflow-y-auto transition-transform duration-300 ease-in-out xl:block xl:translate-x-0 ${SIDEBAR_ASIDE_SURFACE} ${
                                isSidebarOpen ? 'translate-x-0' : '-translate-x-full'
                            }`}
                            style={{
                                willChange: 'transform',
                                filter: flashcardStudying ? 'blur(4px)' : 'none',
                                transition: 'filter 0.3s ease',
                            }}
                        >
                            <div className="flex h-full flex-col pt-4 md:pt-8">{sidebarContent}</div>
                        </aside>
                    </div>,
                    document.body
                )}

            {/* Main Content Area — z-10 so in-flow stacking stays predictable */}
            <main
                className={`relative z-10 ${hideAppChrome ? 'pt-0' : lexPlayFullscreen ? 'pt-0 lg:pt-[calc(var(--app-header-height)+env(safe-area-inset-top,0px))]' : 'pt-[calc(var(--app-header-height)+env(safe-area-inset-top,0px))]'} min-h-screen
        ${hideAppChrome ? 'w-full !ml-0 max-w-full px-0' : `xl:ml-52 ${['supreme_decisions', 'codex', 'browse_bar', 'flashcard', 'about', 'updates', 'quiz', 'landing'].includes(mode) ? 'px-0' : 'px-4 lg:px-8'} pb-[var(--player-height,0px)]`}`}
                style={{touchAction:'pan-y', WebkitOverflowScrolling:'touch'}}
            >
                <div
                    className={`${
                        hideAppChrome
                            ? 'max-w-full'
                            : ['codex', 'about', 'updates', 'quiz', 'landing', 'supreme_decisions', 'browse_bar', 'flashcard'].includes(mode)
                              ? 'max-w-full ml-0'
                              : mainFullWidth
                                ? 'mx-auto w-full max-w-none'
                                : 'mx-auto max-w-7xl'
                    }`}
                >
                    {children}
                </div>
            </main>

            </div>
        </div>
    );
};

export default Layout;
