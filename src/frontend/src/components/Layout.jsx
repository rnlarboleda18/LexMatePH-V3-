import React, { useState, useEffect } from 'react';
import { Sun, Moon, BookOpen, LayoutGrid, Brain, Menu, X } from 'lucide-react';
import { useLexPlay } from '../features/lexplay/useLexPlay';
import { SignedIn, SignedOut, SignInButton, SignUpButton, UserButton } from '@clerk/clerk-react';

const Layout = ({ children, sidebarContent, isDarkMode, toggleTheme, mode, onToggleMode, onToggleQuiz, user, isFullscreen }) => {
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const { isDrawerOpen } = useLexPlay();


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
            {!isFullscreen && (
                <header className={`fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 md:px-8
                    ${isDarkMode
                        ? 'h-24 bg-slate-900/60 md:bg-slate-900/40 md:backdrop-blur-xl border-b border-white/10 shadow-[0_4px_30px_rgba(0,0,0,0.3)]'
                        : 'h-24 bg-white/80 md:bg-white/40 md:backdrop-blur-xl border-b border-white/40 shadow-[0_4px_30px_rgba(0,0,0,0.05)]'
                    }`} style={{willChange:'transform'}}>

                    {/* LEFT — Brand */}
                    <div className="flex items-center gap-3">
                        {/* Mobile hamburger */}
                        <button
                            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                            className={`xl:hidden p-2 rounded-lg transition-colors ${isDarkMode ? 'text-gray-400 hover:text-amber-400 hover:bg-amber-900/20' : 'text-gray-500 hover:text-amber-700 hover:bg-amber-50'}`}
                            aria-label="Toggle Sidebar"
                        >
                            {isSidebarOpen ? <X size={22} /> : <Menu size={22} />}
                        </button>

                        {/* Brand block */}
                        <div className="flex flex-col items-start justify-center">
                            {/* Brand name */}
                            <div className="text-2xl sm:text-3xl font-black tracking-widest select-none leading-none mb-0.5 pointer-events-none">
                                <span className={isDarkMode ? 'text-stone-100' : 'text-slate-800'}>LexMate</span><span className="text-blue-500">P</span><span className="text-red-500">H</span>
                            </div>
                            {/* Tag line — desktop only */}
                            <div className={`hidden lg:flex items-center gap-4 text-lg font-semibold tracking-wide mt-2 ${isDarkMode ? 'text-amber-600/80' : 'text-amber-700/70'}`}>
                                <span className="cursor-default">Bar Questions</span>
                                <span>·</span>
                                <span className="cursor-default">SC Decisions</span>
                                <span>·</span>
                                <span className="cursor-default">Case Digests</span>
                                <span>·</span>
                                <span className="cursor-default">Codals</span>
                            </div>
                        </div>
                    </div>

                    {/* RIGHT — Actions */}
                    <div className="flex items-center gap-1.5 md:gap-2">

                        {/* Theme Toggle */}
                        <button
                            onClick={toggleTheme}
                            title={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
                            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-lg font-medium transition-all duration-200
                                ${isDarkMode
                                    ? 'text-gray-400 hover:text-amber-400 hover:bg-amber-900/20 border border-transparent hover:border-amber-800/40'
                                    : 'text-gray-500 hover:text-amber-700 hover:bg-amber-50 border border-transparent hover:border-amber-200'
                                }`}
                        >
                            {isDarkMode ? <Sun size={20} className="text-amber-400" /> : <Moon size={20} className="text-violet-500" />}
                            <span className="hidden md:inline">{isDarkMode ? 'Light' : 'Dark'}</span>
                        </button>


                        {/* Divider */}
                        <div className={`hidden sm:block w-px h-6 mx-1 ${isDarkMode ? 'bg-gray-700' : 'bg-stone-200'}`} />

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
            {!isFullscreen && (
                <aside
                    className={`fixed top-28 left-0 bottom-0 w-64 z-40 transform transition-transform duration-300 ease-in-out shadow-xl overflow-y-auto
            ${isDarkMode ? 'bg-slate-900 xl:bg-slate-900/40 xl:backdrop-blur-xl border-r border-white/10 shadow-[6px_0_24px_-4px_rgba(0,0,0,0.3)]' : 'bg-white xl:bg-white/40 xl:backdrop-blur-xl border-r border-white/40 shadow-[6px_0_24px_-4px_rgba(0,0,0,0.1)]'}
            ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'} 
            xl:translate-x-0 xl:block`}
                    style={{willChange:'transform'}}
                >
                    <div className="h-full flex flex-col pt-8">
                        {sidebarContent}
                    </div>
                </aside>
            )}

            {/* Overlay for Mobile Sidebar */}
            {isSidebarOpen && !isFullscreen && (
                <div
                    className="fixed inset-0 z-30 bg-black bg-opacity-50 xl:hidden"
                    onClick={() => setIsSidebarOpen(false)}
                />
            )}

            {/* Main Content Area */}
            <main
                className={`${isFullscreen ? 'pt-0' : 'pt-28'} min-h-screen
        ${isFullscreen ? 'w-full !ml-0 max-w-full px-0' : `xl:ml-64 ${['supreme_decisions', 'codex'].includes(mode) ? 'px-0' : 'px-4 lg:px-8'} pb-[calc(2rem_+_var(--player-height,0px))]`}`}
                style={{touchAction:'pan-y', WebkitOverflowScrolling:'touch'}}
            >
                <div className={`${isFullscreen ? 'max-w-full' : (mode === 'codex' ? 'max-w-full ml-0' : 'mx-auto max-w-7xl')}`}>
                    {children}
                </div>
            </main>
            </div>
        </div>
    );
};

export default Layout;
