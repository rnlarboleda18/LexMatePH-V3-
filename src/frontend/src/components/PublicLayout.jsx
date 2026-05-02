import React from 'react';
import { createPortal } from 'react-dom';
import { Sun, Moon, Scale } from 'lucide-react';
import { SignedIn, SignedOut, SignInButton, SignUpButton, UserButton } from '@clerk/clerk-react';
import { APP_HEADER_SURFACE } from '../utils/filterChromeClasses';

/**
 * Public document shell: top bar only, no app sidebar. Used for /legal and /about
 * (DPA-friendly: terms readable without the full product chrome).
 */
const PublicLayout = ({ children, isDarkMode, toggleTheme, onGoToApp, documentTitle = 'LexMatePH' }) => {
  return (
    <div
      className={`min-h-screen transition-colors duration-300 ${isDarkMode ? 'dark bg-zinc-950 text-zinc-200' : 'bg-neutral-100 text-[color:var(--lex-ink)] antialiased'}`}
    >
      <div className="fixed inset-0 z-0 bg-neutral-100 dark:bg-zinc-950" aria-hidden />
      <div className="relative z-10 flex min-h-screen flex-col">
        {typeof document !== 'undefined' &&
          createPortal(
            <div className={isDarkMode ? 'dark' : ''} data-lex-public-chrome>
              <header
                className={`fixed left-0 right-0 top-0 z-50 flex flex-wrap items-center gap-x-2 gap-y-1.5 px-3 pb-[max(0px,calc(0.375rem-2mm))] sm:flex-nowrap sm:gap-y-0 md:gap-x-3 md:px-4 md:pb-[calc(0.5rem-2mm)] lg:gap-x-4 lg:px-5
                    min-h-[calc(var(--app-header-top-gap)+env(safe-area-inset-top,0px)+var(--app-header-height)+var(--app-header-bottom-pad))]
                    pt-[calc(var(--app-header-top-gap)+env(safe-area-inset-top,0px))]
                    ${APP_HEADER_SURFACE}`}
              >
                <div className="relative z-10 flex min-h-0 min-w-0 shrink-0 items-center gap-2 md:gap-2.5">
                  <button
                    type="button"
                    onClick={onGoToApp}
                    className="group flex min-w-0 items-center gap-2.5 text-left"
                  >
                    <div
                      className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-purple-600 to-violet-600 text-white shadow-md shadow-purple-600/30"
                      aria-hidden
                    >
                      <Scale className="h-5 w-5" strokeWidth={2} />
                    </div>
                    <div className="min-w-0">
                      <span className="font-display block truncate text-lg font-semibold tracking-tight text-black dark:text-zinc-50 sm:text-xl">
                        {documentTitle}
                      </span>
                      <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-gray-500 dark:text-gray-400 sm:block sm:text-[11px]">
                        <span className="text-violet-600 dark:text-violet-400">Back to app</span>
                        <span className="ml-1 text-gray-500 dark:text-gray-400">· Public page</span>
                      </span>
                    </div>
                  </button>
                </div>

                <div className="relative z-10 ml-auto flex shrink-0 items-center justify-end gap-1 md:gap-1.5">
                  <button
                    onClick={toggleTheme}
                    type="button"
                    title={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
                    className={`flex items-center gap-1.5 rounded-md px-2 py-1 text-sm font-medium transition-all duration-200 md:gap-2 md:px-2.5 md:py-1.5 md:text-base
                    ${isDarkMode
                    ? 'border border-transparent text-zinc-400 hover:border-zinc-700 hover:bg-zinc-800/80 hover:text-zinc-100'
                    : 'border-2 border-transparent text-neutral-800 hover:border-lex-strong hover:bg-neutral-200/80 hover:text-neutral-950'}`}
                  >
                    {isDarkMode ? (
                      <Sun size={17} className="shrink-0 text-amber-300 md:h-[18px] md:w-[18px]" />
                    ) : (
                      <Moon size={17} className="shrink-0 text-violet-700 md:h-[18px] md:w-[18px]" />
                    )}
                    <span className="hidden sm:inline">{isDarkMode ? 'Light' : 'Dark'}</span>
                  </button>

                  <div className={`hidden sm:block h-4 w-px shrink-0 rounded-full md:h-5 ${isDarkMode ? 'bg-zinc-700' : 'bg-violet-200/80'}`} />

                  <div className="flex items-center gap-1.5 sm:gap-1.5">
                    <SignedIn>
                      <UserButton
                        appearance={{
                          elements: { userButtonAvatarBox: 'h-9 w-9' },
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

        <div className="flex flex-1 flex-col pt-[var(--app-header-offset)]">
          {/* Match FeaturePageShell; extra pt-* clears the fixed header visually (breathing room) */}
          <div className="mx-auto w-full max-w-7xl flex-1 px-3 pb-16 pt-5 sm:px-5 sm:pt-7 lg:px-6 lg:pt-8">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PublicLayout;
