import React, { useState, useEffect, useLayoutEffect, useRef, useCallback, lazy, Suspense } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { useUser } from '@clerk/clerk-react';
import { RefreshCcw, AlertTriangle, ClipboardList, Brain, SquareStack, Library } from 'lucide-react';
import Layout from './components/Layout';
import Sidebar from './components/Sidebar';
import ControlBar from './components/ControlBar';
import QuestionCard from './components/QuestionCard';
import SupremeDecisions from './components/SupremeDecisions';
import PageLoadingFallback from './components/PageLoadingFallback';
import ErrorBoundary from './components/ErrorBoundary';
import LandingPage from './components/LandingPage';
import FeaturePageShell from './components/FeaturePageShell';
import { LexPlayer, useLexPlay } from './features/lexplay';
import { useSubscription } from './context/SubscriptionContext';
import { normalizeBarSubject } from './utils/subjectNormalize';
import { useBarQuestions } from './hooks/useBarQuestions';
import { useFlashcardConcepts } from './hooks/useFlashcardConcepts';
import { useGlobalCaseModal } from './hooks/useGlobalCaseModal';

const About = lazy(() => import('./components/About'));
const Updates = lazy(() => import('./components/Updates'));
const LexCodeViewer = lazy(() => import('./components/LexCodeViewer'));
const LexifyApp = lazy(() => import('./features/lexify/LexifyApp'));
const FlashcardSetup = lazy(() => import('./components/FlashcardSetup'));
const Flashcard = lazy(() => import('./components/Flashcard'));
const CaseDecisionModal = lazy(() => import('./components/CaseDecisionModal'));
const QuestionDetailModal = lazy(() => import('./components/QuestionDetailModal'));
const SubscriptionModal = lazy(() => import('./components/SubscriptionModal'));
const UpgradeWall = lazy(() => import('./components/UpgradeWall'));

/** Codal picker options (sidebar submenu removed; filter lives on LexCode page). */
const CODAL_FILTER_OPTIONS = [
  { id: 'rpc', label: 'Revised Penal Code' },
  { id: 'civ', label: 'Civil Code of the Philippines' },
  { id: 'rcc', label: 'Revised Corporation Code' },
  { id: 'fc', label: 'Family Code' },
  { id: 'roc', label: 'Rules of Court' },
  { id: 'const', label: 'Philippine Constitution' },
  { id: 'labor', label: 'Labor Code' },
  { id: 'admin', label: 'Administrative Code', disabled: true },
  { id: 'special', label: 'Special Laws', disabled: true },
];

/** Canonical URL path for each app mode — defined outside the component so it
 *  is never recreated and never causes extra renders via closure references. */
const MODE_TO_PATH = {
  landing: '/',
  supreme_decisions: '/decisions',
  codex: '/lexcode',
  flashcard: '/flashcards',
  quiz: '/lexify',
  about: '/about',
  updates: '/updates',
  browse_bar: '/bar-questions',
  lexplay: '/lexplay',
};

const PATH_TO_MODE = Object.fromEntries(
  Object.entries(MODE_TO_PATH).map(([m, p]) => [p, m])
);

function App() {
  const { isDrawerOpen, setIsDrawerOpen } = useLexPlay();
  const { showUpgradeModal, closeUpgradeModal, tier, canAccess } = useSubscription();
  const { user } = useUser();

  // --- Hooks ---
  const { questions, loading, error, retry: handleRetryFetch } = useBarQuestions();
  const {
    conceptPool: flashcardConceptPool,
    busy: flashcardConceptsBusy,
    conceptsError: flashcardConceptsError,
    refetch: refetchFlashcardConcepts,
    getPrimarySubject: getCardPrimarySubject,
    subjectCounts: flashcardSubjectCounts,
  } = useFlashcardConcepts();
  const { selectedCase: globalSelectedCase, selectCase: selectGlobalCase, closeModal: closeGlobalCaseModal } = useGlobalCaseModal();

  // --- URL ↔ mode mapping ---
  const navigate = useNavigate();

  // --- State ---
  const [selectedQuestion, setSelectedQuestion] = useState(null);


  // Filters
  const [currentSubject, setCurrentSubject] = useState(null);
  const [selectedCodalCode, setSelectedCodalCode] = useState('rpc');
  const [selectedYear, setSelectedYear] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  // UI State
  /** Marketing landing on every full load; user taps through to the app each time.
   *  Initial mode is derived from the URL so deep-links and refreshes land correctly.
   *  We read window.location.pathname directly (not useLocation) to avoid subscribing
   *  App to the React Router context, which would cause an extra re-render on every
   *  navigate() call and make child components (e.g. SupremeDecisions) re-render needlessly. */
  const [mode, setMode] = useState(() => PATH_TO_MODE[window.location.pathname] ?? 'landing');
  const [flashcardState, setFlashcardState] = useState('setup'); // 'setup' | 'active'
  const [flashcardQuestions, setFlashcardQuestions] = useState([]);
  const [flashcardIndex, setFlashcardIndex] = useState(0);
  const [flashcardDeckError, setFlashcardDeckError] = useState(null);
  const [isDarkMode, setIsDarkMode] = useState(false); // Default to Light Mode
  /** Hide minimized LexPlayer during Lexify exam simulation (not dashboard / results). */
  const [lexifyExamSimulationActive, setLexifyExamSimulationActive] = useState(false);
  /** User dismissed the docked mini LexPlayer (X); show again after opening full LexPlay. */
  const [lexPlayMiniDismissed, setLexPlayMiniDismissed] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [previousMode, setPreviousMode] = useState(null);
  const [barCurrentPage, setBarCurrentPage] = useState(1);
  const BAR_ITEMS_PER_PAGE = 20; // 2 columns * 10 rows

  const BAR_SUBJECT_OPTIONS = [
    'Civil Law',
    'Commercial Law',
    'Criminal Law',
    'Labor Law',
    'Legal Ethics',
    'Political Law',
    'Remedial Law',
    'Taxation Law',
  ];


  // Sync mode → URL.
  // We read window.location.pathname instead of location from useLocation so that
  // the navigate() call below does NOT trigger a React Router context update that
  // would re-render App (and all its heavy children) a second time.
  useEffect(() => {
    const path = MODE_TO_PATH[mode] ?? '/';
    if (window.location.pathname !== path) navigate(path, { replace: true });
  // navigate is stable (React Router guarantee); MODE_TO_PATH is a module constant.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  // Sync URL → mode for browser back/forward navigation.
  // popstate fires on history.back() / history.forward() but NOT on replaceState,
  // so this handler only activates for genuine browser navigation gestures.
  useEffect(() => {
    const handlePopState = () => {
      const m = PATH_TO_MODE[window.location.pathname];
      if (m) setMode(m);
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  // Empty deps: listener is registered once; setMode is stable.
  }, []);

  // Intercept playNow signals to force full-screen LexPlay
  useEffect(() => {
    if (isDrawerOpen && mode !== 'lexplay') {
      // Never return to marketing landing when exiting LexPlay fullscreen
      setPreviousMode(mode === 'landing' ? 'supreme_decisions' : mode);
      setMode('lexplay');
      setIsDrawerOpen(false); // Consume the signal
    }
  }, [isDrawerOpen, mode, setIsDrawerOpen]);

  const handleEnterFromLanding = useCallback(() => {
    setMode('supreme_decisions');
  }, []);

  useEffect(() => {
    if (mode === 'lexplay') setLexPlayMiniDismissed(false);
  }, [mode]);

  // No manual session check needed with Clerk


  // Spinner only when user is on Flashcards and we still have nothing to show.
  const flashcardConceptsLoading =
    mode === 'flashcard' &&
    flashcardConceptsBusy &&
    flashcardConceptPool.length === 0 &&
    !flashcardConceptsError;



  // 2. Theme Management — layout effect so `html.dark` matches state before paint (portaled UI e.g. LexPlayer uses Tailwind `dark:`)
  useLayoutEffect(() => {
    document.documentElement.classList.toggle('dark', isDarkMode);
  }, [isDarkMode]);

  // Reset bar pagination when filters change
  useEffect(() => {
    setBarCurrentPage(1);
  }, [currentSubject, searchTerm]);

  const toggleTheme = () => setIsDarkMode(!isDarkMode);

  // --- Derived State (Filtering) ---



  // --- Pagination ---




  const handleToggleAbout = () => {
    setMode('about');
  };

  const handleSelectSubject = (subject) => {
    setCurrentSubject(subject === 'All Subjects' ? null : subject);
    setSearchTerm(''); // Clear search when picking a subject
    setMode('browse_bar');
  };

  const handleStartFlashcard = (subject) => {
    if (subject === 'CANCEL') {
      setMode('supreme_decisions');
      return;
    }

    setFlashcardDeckError(null);

    let selected = [];
    if (subject) {
      selected = flashcardConceptPool.filter(
        (c) => getCardPrimarySubject(c) === subject
      );
    } else {
      selected = [...flashcardConceptPool];
    }

    if (selected.length === 0) {
      setFlashcardDeckError(
        subject
          ? `No key legal concepts found for ${subject} yet. Try another subject or All subjects.`
          : 'No key legal concepts are available yet. Run your digest pipeline to fill legal_concepts.'
      );
      return;
    }

    for (let i = selected.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [selected[i], selected[j]] = [selected[j], selected[i]];
    }

    setFlashcardQuestions(selected);
    setFlashcardIndex(0);
    setFlashcardState('active');
  };

  const handleToggleQuiz = () => {
    setMode('quiz');
    setFlashcardIndex(0);
  };

  const handleNextFlashcard = () => {
    if (flashcardIndex < flashcardQuestions.length - 1) {
      setFlashcardIndex(prev => prev + 1);
    } else {
      setFlashcardState('setup');
    }
  };

  const handleToggleFlashcard = () => {
    setMode('flashcard');
    setFlashcardState('setup');
    setFlashcardDeckError(null);
  };

  const handleToggleLexCode = useCallback(() => {
    setMode('codex');
  }, []);

  // Handle Native Fullscreen
  useEffect(() => {
    const handleFullscreenChange = () => {
      if (!document.fullscreenElement) {
        setIsFullscreen(false);
      }
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    // Webkit specific
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);

    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
    };
  }, []);

  const handleToggleFullscreen = () => {
    if (!isFullscreen) {
      // Enter Fullscreen
      const elem = document.documentElement;
      if (elem.requestFullscreen) {
        elem.requestFullscreen().catch(err => {
          console.error(`Error attempting to enable fullscreen: ${err.message}`);
        });
      }
      setIsFullscreen(true);
    } else {
      // Exit Fullscreen
      if (document.exitFullscreen && document.fullscreenElement) {
        document.exitFullscreen().catch(err => {
          console.error(`Error attempting to exit fullscreen: ${err.message}`);
        });
      }
      setIsFullscreen(false);
    }
  };

  // --- Render ---
  return (
    <Layout
      isDarkMode={isDarkMode}
      toggleTheme={toggleTheme}
      mode={mode}
      mainFullWidth={mode === 'flashcard' && flashcardState === 'active'}
      flashcardStudying={mode === 'flashcard' && flashcardState === 'active'}
      hideAppChrome={isFullscreen || lexifyExamSimulationActive || mode === 'landing'}
      lexPlayFullscreen={mode === 'lexplay'}
      onToggleQuiz={handleToggleQuiz}
      onToggleMode={(newMode) => {
        setMode(newMode);
        if (newMode === 'supreme_decisions' || newMode === 'browse_bar') {
          setCurrentSubject(null);
        }
      }}
      user={user}
      sidebarContent={
        <Sidebar
          onToggleQuiz={handleToggleQuiz}
          onSelectSubject={handleSelectSubject}
          onToggleAbout={handleToggleAbout}
          onToggleUpdates={() => setMode('updates')}
          onToggleSupremeDecisions={() => setMode('supreme_decisions')}
          onToggleFlashcard={handleToggleFlashcard}
          onToggleLexPlay={() => {
            setPreviousMode(mode);
            setMode('lexplay');
          }}
          onToggleLexCode={handleToggleLexCode}
          mode={mode}
          isFullscreen={isFullscreen}
        />
      }
    >

      {/* Spacer for Fixed Header */}


      {/* Determine what to show in the background if LexPlayer is full screen */}
      {(() => {
        const isLexPlayerFull = mode === 'lexplay';
        const effectiveMode = isLexPlayerFull ? (previousMode || 'supreme_decisions') : mode;

        return (
          <>
            {/* Control Bar Visibility */}
            {false && (
              <ControlBar
                searchTerm={searchTerm}
                onSearchChange={setSearchTerm}
                selectedYear={selectedYear}
                onYearChange={setSelectedYear}
              />
            )}

            {/* Content Area - Always mounted so scroll position is preserved */}
            <div aria-hidden={isLexPlayerFull ? "true" : undefined} className={isLexPlayerFull ? "pointer-events-none" : ""}>
              {loading && effectiveMode !== 'flashcard' && effectiveMode !== 'landing' ? (
                <div className="flex justify-center items-center h-64">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
                </div>
              ) : error && effectiveMode !== 'flashcard' && effectiveMode !== 'landing' ? (
                <div className="flex flex-col items-center justify-center min-h-[50vh] p-8 text-center space-y-6">
                  <div className="w-20 h-20 bg-rose-500/20 rounded-full flex items-center justify-center text-rose-500 shadow-[0_0_30px_rgba(244,63,94,0.3)]">
                    <AlertTriangle size={40} />
                  </div>
                  <div>
                    <h2 className="text-2xl font-black text-gray-900 dark:text-white mb-2 tracking-tight">Data Load Failed</h2>
                    <p className="text-sm text-gray-500 dark:text-gray-400 font-medium max-w-xs mx-auto">
                      {error}
                    </p>
                  </div>
                  <button
                    onClick={() => window.location.reload()}
                    className="px-8 py-3 bg-amber-600 text-white rounded-2xl font-black text-xs uppercase tracking-widest hover:bg-amber-700 transition-all flex items-center gap-2 shadow-lg shadow-amber-900/20"
                  >
                    <RefreshCcw size={16} />
                    Retry Connection
                  </button>
                </div>
              ) : (
                <ErrorBoundary message="Content area encountered an error.">
                  <>
                  {/* Mount default SC Decisions screen while on landing so list + prefetch run in background */}
                  {(mode === 'landing' || effectiveMode === 'supreme_decisions') && (
                    <div
                      className={
                        mode === 'landing'
                          ? 'pointer-events-none fixed left-0 top-0 z-0 min-h-[85vh] w-full max-w-[100rem] -translate-x-full opacity-0'
                          : ''
                      }
                      aria-hidden={mode === 'landing' ? 'true' : undefined}
                    >
                      <SupremeDecisions
                        externalSelectedCase={globalSelectedCase}
                        onCaseSelect={selectGlobalCase}
                      />
                    </div>
                  )}
                  {effectiveMode === 'landing' && (
                    <div className="relative z-10">
                      <LandingPage
                        isDarkMode={isDarkMode}
                        toggleTheme={toggleTheme}
                        onEnterApp={handleEnterFromLanding}
                      />
                    </div>
                  )}
                  {effectiveMode === 'about' && (
                    <Suspense fallback={<PageLoadingFallback label="Loading About…" />}>
                      <About />
                    </Suspense>
                  )}
                  {effectiveMode === 'updates' && (
                    <Suspense fallback={<PageLoadingFallback label="Loading Updates…" />}>
                      <Updates isDarkMode={isDarkMode} />
                    </Suspense>
                  )}
                  {effectiveMode === 'codex' && (
                    <div className="flex flex-col bg-transparent text-gray-900 dark:text-gray-100 font-sans">
                      <header
                        className="sticky z-20 shrink-0 overflow-hidden border-b-2 border-slate-300/85 bg-white/88 shadow-[0_8px_30px_rgb(0,0,0,0.06)] backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/35 dark:shadow-[0_8px_30px_rgb(0,0,0,0.25)] md:rounded-b-2xl md:shadow-[0_12px_40px_rgb(0,0,0,0.08)] md:backdrop-blur-2xl dark:md:shadow-[0_12px_40px_rgb(0,0,0,0.22)] lg:shadow-[0_16px_48px_rgb(0,0,0,0.09)] dark:lg:shadow-[0_16px_48px_rgb(0,0,0,0.28)] top-[calc(2.75rem+env(safe-area-inset-top,0px))] md:top-[calc(5rem+env(safe-area-inset-top,0px))]"
                        style={{ willChange: 'transform' }}
                      >
                        <div
                          className="pointer-events-none absolute -left-[10%] -top-[60%] h-[280px] w-[280px] rounded-full bg-indigo-500/20 blur-[100px] dark:bg-blue-500/15 md:h-[360px] md:w-[360px] md:blur-[120px] lg:left-0 lg:h-[420px] lg:w-[420px]"
                          aria-hidden
                        />
                        <div
                          className="pointer-events-none absolute -bottom-[80%] -right-[15%] h-[260px] w-[260px] rounded-full bg-purple-500/18 blur-[100px] dark:bg-purple-500/12 md:h-[340px] md:w-[340px] md:blur-[120px] lg:right-0 lg:bottom-[-40%] lg:h-[400px] lg:w-[400px]"
                          aria-hidden
                        />
                        <div className="relative mx-auto flex max-w-7xl items-center gap-2 px-3 py-2 sm:gap-3 sm:px-4 sm:py-2.5 md:gap-4 md:py-3 lg:gap-4 lg:px-5 lg:py-3">
                          <div
                            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-indigo-200/90 bg-gradient-to-br from-indigo-50/95 to-blue-50/90 text-indigo-600 shadow-[0_4px_14px_rgba(79,70,229,0.12)] dark:border-indigo-800/70 dark:from-slate-800/90 dark:to-indigo-950/50 dark:text-indigo-300 dark:shadow-[0_4px_20px_rgba(0,0,0,0.35)] sm:h-10 sm:w-10 md:h-11 md:w-11 md:rounded-xl md:shadow-[0_8px_24px_rgba(79,70,229,0.15)] lg:h-11 lg:w-11"
                            aria-hidden
                          >
                            <Library className="h-5 w-5 sm:h-5 sm:w-5 md:h-6 md:w-6 lg:h-6 lg:w-6" strokeWidth={2} />
                          </div>
                          <div className="min-w-0 flex-1 border-l-[3px] border-l-indigo-500 pl-2 dark:border-l-indigo-400 sm:pl-3 md:pl-4 lg:pl-4">
                            <h1 className="truncate text-base font-bold tracking-tight sm:text-lg md:text-xl md:tracking-tight lg:text-[1.375rem] xl:text-[1.5rem] bg-gradient-to-r from-indigo-700 via-blue-700 to-indigo-600 bg-clip-text text-transparent dark:from-indigo-200 dark:via-blue-200 dark:to-indigo-100">
                              LexCode
                            </h1>
                            <p className="mt-0.5 text-[9px] font-semibold uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400 sm:text-[10px] md:mt-1 md:text-[11px] md:tracking-[0.2em] lg:text-xs lg:tracking-[0.16em]">
                              Philippine codals & statutes
                            </p>
                          </div>
                        </div>
                      </header>
                      <div className="mx-auto w-full max-w-7xl px-3 py-4 sm:px-5 sm:py-5 lg:px-6">
                        <Suspense fallback={<PageLoadingFallback label="Loading LexCode…" />}>
                          <LexCodeViewer
                            shortName={selectedCodalCode.toUpperCase()}
                            codalOptions={CODAL_FILTER_OPTIONS}
                            selectedCodal={selectedCodalCode}
                            onCodalChange={(id) => {
                              setSelectedCodalCode(id);
                              window.scrollTo({ top: 0, behavior: 'smooth' });
                            }}
                            onCaseSelect={selectGlobalCase}
                            isFullscreen={isFullscreen}
                            onToggleFullscreen={handleToggleFullscreen}
                            subscriptionTier={tier}
                          />
                        </Suspense>
                      </div>
                    </div>
                  )}
                  {effectiveMode === 'flashcard' && flashcardState === 'setup' && (
                    <div className="min-h-screen bg-transparent text-gray-900 dark:text-gray-100 font-sans">
                      <header
                        className="sticky z-20 overflow-hidden border-b-2 border-slate-300/85 bg-white/88 shadow-[0_8px_30px_rgb(0,0,0,0.06)] backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/35 dark:shadow-[0_8px_30px_rgb(0,0,0,0.25)] md:rounded-b-2xl md:shadow-[0_12px_40px_rgb(0,0,0,0.08)] md:backdrop-blur-2xl dark:md:shadow-[0_12px_40px_rgb(0,0,0,0.22)] lg:shadow-[0_16px_48px_rgb(0,0,0,0.09)] dark:lg:shadow-[0_16px_48px_rgb(0,0,0,0.28)] top-[calc(2.75rem+env(safe-area-inset-top,0px))] md:top-[calc(5rem+env(safe-area-inset-top,0px))]"
                        style={{ willChange: 'transform' }}
                      >
                        <div
                          className="pointer-events-none absolute -left-[10%] -top-[60%] h-[280px] w-[280px] rounded-full bg-indigo-500/20 blur-[100px] dark:bg-blue-500/15 md:h-[360px] md:w-[360px] md:blur-[120px] lg:left-0 lg:h-[420px] lg:w-[420px]"
                          aria-hidden
                        />
                        <div
                          className="pointer-events-none absolute -bottom-[80%] -right-[15%] h-[260px] w-[260px] rounded-full bg-purple-500/18 blur-[100px] dark:bg-purple-500/12 md:h-[340px] md:w-[340px] md:blur-[120px] lg:right-0 lg:bottom-[-40%] lg:h-[400px] lg:w-[400px]"
                          aria-hidden
                        />
                        <div className="relative mx-auto flex max-w-7xl items-center gap-2 px-3 py-2 sm:gap-3 sm:px-4 sm:py-2.5 md:gap-4 md:py-3 lg:gap-4 lg:px-5 lg:py-3">
                          <div
                            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-indigo-200/90 bg-gradient-to-br from-indigo-50/95 to-blue-50/90 text-indigo-600 shadow-[0_4px_14px_rgba(79,70,229,0.12)] dark:border-indigo-800/70 dark:from-slate-800/90 dark:to-indigo-950/50 dark:text-indigo-300 dark:shadow-[0_4px_20px_rgba(0,0,0,0.35)] sm:h-10 sm:w-10 md:h-11 md:w-11 md:rounded-xl md:shadow-[0_8px_24px_rgba(79,70,229,0.15)] lg:h-11 lg:w-11"
                            aria-hidden
                          >
                            <SquareStack className="h-5 w-5 sm:h-5 sm:w-5 md:h-6 md:w-6 lg:h-6 lg:w-6" strokeWidth={2} />
                          </div>
                          <div className="min-w-0 flex-1 border-l-[3px] border-l-indigo-500 pl-2 dark:border-l-indigo-400 sm:pl-3 md:pl-4 lg:pl-4">
                            <h1 className="truncate text-base font-bold tracking-tight sm:text-lg md:text-xl md:tracking-tight lg:text-[1.375rem] xl:text-[1.5rem] bg-gradient-to-r from-indigo-700 via-blue-700 to-indigo-600 bg-clip-text text-transparent dark:from-indigo-200 dark:via-blue-200 dark:to-indigo-100">
                              Flashcards
                            </h1>
                            <p className="mt-0.5 text-[9px] font-semibold uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400 sm:text-[10px] md:mt-1 md:text-[11px] md:tracking-[0.2em] lg:text-xs lg:tracking-[0.16em]">
                              Bar syllabus–aligned key concepts from SC digests
                            </p>
                          </div>
                        </div>
                      </header>
                      <main className="max-w-7xl mx-auto px-3 py-4 sm:px-5 sm:py-5 lg:px-6">
                        <Suspense fallback={<PageLoadingFallback label="Loading Flashcards…" />}>
                          <FlashcardSetup
                            embedded
                            onStart={handleStartFlashcard}
                            conceptsLoading={flashcardConceptsLoading}
                            conceptsError={flashcardConceptsError}
                            deckError={flashcardDeckError}
                            subjectCounts={flashcardSubjectCounts}
                            onRetryConcepts={refetchFlashcardConcepts}
                          />
                        </Suspense>
                      </main>
                    </div>
                  )}
                  {effectiveMode === 'flashcard' && flashcardState === 'active' && createPortal(
                    <div
                      className="fixed inset-0 z-[540] lex-modal-overlay justify-center bg-transparent animate-in fade-in duration-200 md:!items-stretch"
                      onClick={() => setFlashcardState('setup')}
                      role="presentation"
                    >
                      <div
                        className="lex-modal-card relative flex max-w-5xl flex-col overflow-visible border-0 bg-transparent shadow-none animate-in zoom-in-95 duration-300 md:!h-full md:max-h-full md:min-h-0 md:w-full md:max-w-6xl lg:max-w-7xl"
                        role="dialog"
                        aria-modal="true"
                        aria-label="Flashcard"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div className="flex min-h-0 w-full flex-1 flex-col overflow-y-auto p-2 max-md:min-h-0 md:h-full md:max-h-full md:items-center md:justify-center md:overflow-visible md:p-6 lg:p-8">
                          <Suspense fallback={<PageLoadingFallback label="Loading card…" />}>
                            <Flashcard
                              variant="concepts"
                              card={flashcardQuestions[flashcardIndex]}
                              total={flashcardQuestions.length}
                              currentIndex={flashcardIndex}
                              onNext={handleNextFlashcard}
                              onClose={() => setFlashcardState('setup')}
                            />
                          </Suspense>
                        </div>
                      </div>
                    </div>,
                    document.body
                  )}
                  {effectiveMode === 'quiz' && (
                    canAccess('lexify') ? (
                      <Suspense fallback={<PageLoadingFallback label="Loading Lexify…" />}>
                        <LexifyApp
                          questions={questions}
                          onClose={() => setMode('supreme_decisions')}
                          onExamSimulationChange={setLexifyExamSimulationActive}
                        />
                      </Suspense>
                    ) : (
                      <FeaturePageShell
                        icon={Brain}
                        title="Lexify"
                        subtitle="2026 Philippine Bar mock exams · upgrade to unlock"
                      >
                        <div className="flex min-h-[40vh] items-center justify-center">
                          <div className="w-full max-w-md">
                            <Suspense fallback={<PageLoadingFallback />}>
                              <UpgradeWall feature="lexify" variant="inline" />
                            </Suspense>
                          </div>
                        </div>
                      </FeaturePageShell>
                    )
                  )}
                  {effectiveMode === 'browse_bar' && (
                    <div className="min-h-screen bg-transparent text-gray-900 dark:text-gray-100 font-sans">
                      <header
                        className="sticky z-20 overflow-hidden border-b-2 border-slate-300/85 bg-white/88 shadow-[0_8px_30px_rgb(0,0,0,0.06)] backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/35 dark:shadow-[0_8px_30px_rgb(0,0,0,0.25)] md:rounded-b-2xl md:shadow-[0_12px_40px_rgb(0,0,0,0.08)] md:backdrop-blur-2xl dark:md:shadow-[0_12px_40px_rgb(0,0,0,0.22)] lg:shadow-[0_16px_48px_rgb(0,0,0,0.09)] dark:lg:shadow-[0_16px_48px_rgb(0,0,0,0.28)] top-[calc(2.75rem+env(safe-area-inset-top,0px))] md:top-[calc(5rem+env(safe-area-inset-top,0px))]"
                        style={{ willChange: 'transform' }}
                      >
                        <div
                          className="pointer-events-none absolute -left-[10%] -top-[60%] h-[280px] w-[280px] rounded-full bg-indigo-500/20 blur-[100px] dark:bg-blue-500/15 md:h-[360px] md:w-[360px] md:blur-[120px] lg:left-0 lg:h-[420px] lg:w-[420px]"
                          aria-hidden
                        />
                        <div
                          className="pointer-events-none absolute -bottom-[80%] -right-[15%] h-[260px] w-[260px] rounded-full bg-purple-500/18 blur-[100px] dark:bg-purple-500/12 md:h-[340px] md:w-[340px] md:blur-[120px] lg:right-0 lg:bottom-[-40%] lg:h-[400px] lg:w-[400px]"
                          aria-hidden
                        />
                        <div className="relative mx-auto flex max-w-7xl items-center gap-2 px-3 py-2 sm:gap-3 sm:px-4 sm:py-2.5 md:gap-4 md:py-3 lg:gap-4 lg:px-5 lg:py-3">
                          <div
                            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-indigo-200/90 bg-gradient-to-br from-indigo-50/95 to-blue-50/90 text-indigo-600 shadow-[0_4px_14px_rgba(79,70,229,0.12)] dark:border-indigo-800/70 dark:from-slate-800/90 dark:to-indigo-950/50 dark:text-indigo-300 dark:shadow-[0_4px_20px_rgba(0,0,0,0.35)] sm:h-10 sm:w-10 md:h-11 md:w-11 md:rounded-xl md:shadow-[0_8px_24px_rgba(79,70,229,0.15)] lg:h-11 lg:w-11"
                            aria-hidden
                          >
                            <ClipboardList className="h-5 w-5 sm:h-5 sm:w-5 md:h-6 md:w-6 lg:h-6 lg:w-6" strokeWidth={2} />
                          </div>
                          <div className="min-w-0 flex-1 border-l-[3px] border-l-indigo-500 pl-2 dark:border-l-indigo-400 sm:pl-3 md:pl-4 lg:pl-4">
                            <h1 className="truncate text-base font-bold tracking-tight sm:text-lg md:text-xl md:tracking-tight lg:text-[1.375rem] xl:text-[1.5rem] bg-gradient-to-r from-indigo-700 via-blue-700 to-indigo-600 bg-clip-text text-transparent dark:from-indigo-200 dark:via-blue-200 dark:to-indigo-100">
                              Bar Questions
                            </h1>
                            <p className="mt-0.5 text-[9px] font-semibold uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400 sm:text-[10px] md:mt-1 md:text-[11px] md:tracking-[0.2em] lg:text-xs lg:tracking-[0.16em]">
                              Actual Bar questions & suggested answers
                            </p>
                          </div>
                        </div>
                      </header>
                      <main className="max-w-7xl mx-auto px-3 py-4 sm:px-5 sm:py-5 lg:px-6">
                      <div className="glass mb-4 rounded-lg border-2 border-slate-300/85 bg-white/90 p-4 shadow-md dark:border-white/10 dark:bg-slate-900/35">
                        <div className="min-w-0 w-full">
                          <label htmlFor="bar-subject-filter" className="mb-1.5 block text-xs font-medium text-gray-500 dark:text-gray-400">
                            Bar subject
                            <span className="ml-2 font-normal tabular-nums text-gray-400 dark:text-gray-500">
                              (
                              {questions.filter((q) => !currentSubject || normalizeBarSubject(q.subject) === currentSubject).length}{' '}
                              questions)
                            </span>
                          </label>
                          <select
                            id="bar-subject-filter"
                            value={currentSubject ?? ''}
                            onChange={(e) => {
                              const v = e.target.value;
                              setCurrentSubject(v === '' ? null : v);
                              setBarCurrentPage(1);
                            }}
                            className="block w-full pl-3 pr-8 py-2.5 text-sm border border-stone-400 dark:border-gray-600 shadow-sm focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-amber-500 rounded-lg dark:bg-gray-900 dark:text-white"
                          >
                            <option value="">All subjects</option>
                            {BAR_SUBJECT_OPTIONS.map((s) => (
                              <option key={s} value={s}>
                                {s}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                        {(() => {
                          const filtered = questions.filter((q) => !currentSubject || normalizeBarSubject(q.subject) === currentSubject);
                          const paginated = filtered.slice((barCurrentPage - 1) * BAR_ITEMS_PER_PAGE, barCurrentPage * BAR_ITEMS_PER_PAGE);
                          return paginated.map((q) => (
                            <QuestionCard
                              key={q.id}
                              question={q}
                              onClick={() => setSelectedQuestion(q)}
                            />
                          ));
                        })()}
                      </div>

                      {/* Pagination UI */}
                      {(() => {
                        const filtered = questions.filter((q) => !currentSubject || normalizeBarSubject(q.subject) === currentSubject);
                        const totalCount = filtered.length;
                        if (totalCount <= BAR_ITEMS_PER_PAGE) return null;
                        
                        return (
                          <div className="mt-8 flex flex-col items-center gap-2 pb-6">
                            <div className="flex justify-center items-center gap-4">
                              <button
                                onClick={() => {
                                  setBarCurrentPage(prev => Math.max(1, prev - 1));
                                  window.scrollTo({ top: 0, behavior: 'smooth' });
                                }}
                                disabled={barCurrentPage === 1}
                                className="px-4 py-2 glass rounded-lg border-2 border-slate-300/80 bg-white/85 text-sm font-medium text-gray-800 shadow-sm transition-colors hover:bg-white dark:border-white/10 dark:bg-slate-700/40 dark:text-gray-200 dark:hover:bg-slate-600/60 flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-50"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
                                Previous
                              </button>
                              <span className="text-sm text-gray-600 dark:text-gray-400 font-medium">
                                Page {barCurrentPage} of {Math.ceil(totalCount / BAR_ITEMS_PER_PAGE) || 1}
                              </span>
                              <button
                                onClick={() => {
                                  setBarCurrentPage(prev => prev + 1);
                                  window.scrollTo({ top: 0, behavior: 'smooth' });
                                }}
                                disabled={barCurrentPage * BAR_ITEMS_PER_PAGE >= totalCount}
                                className="px-4 py-2 glass rounded-lg border-2 border-slate-300/80 bg-white/85 text-sm font-medium text-gray-800 shadow-sm transition-colors hover:bg-white dark:border-white/10 dark:bg-slate-700/40 dark:text-gray-200 dark:hover:bg-slate-600/60 flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-50"
                              >
                                Next
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                              </button>
                            </div>
                          </div>
                        );
                      })()}
                      </main>
                    </div>
                  )}
                  </>
                </ErrorBoundary>
              )}
            </div>

            {/* Full Player Overlay */}
            {isLexPlayerFull && (
              <ErrorBoundary message="LexPlayer encountered an error. Try resetting your queue.">
                <LexPlayer
                  isMinimized={false}
                  isDarkMode={isDarkMode}
                  onMinimize={() => setMode(previousMode || 'supreme_decisions')}
                  onCloseFull={() => {
                    setMode(previousMode || 'supreme_decisions');
                    setLexPlayMiniDismissed(true);
                  }}
                />
              </ErrorBoundary>
            )}
          </>
        );
      })()}


      {/* Doctrinal Detail Modal */}

      {/* Global Case Decision Modal */}
      {globalSelectedCase && (
        <Suspense fallback={null}>
          <CaseDecisionModal
            key={globalSelectedCase.id}
            decision={globalSelectedCase}
            onClose={closeGlobalCaseModal}
            onCaseSelect={selectGlobalCase}
          />
        </Suspense>
      )}

      {/* Global Minimized LexPlayer — docked to bottom when not in full LexPlay; hidden during Lexify exam simulation */}
      {mode !== 'lexplay' && !lexifyExamSimulationActive && !lexPlayMiniDismissed && (
        <ErrorBoundary>
          <LexPlayer
            isMinimized={true}
            isDarkMode={isDarkMode}
            onExpand={() => {
              setPreviousMode(mode);
              setMode('lexplay');
            }}
            onCloseMini={() => setLexPlayMiniDismissed(true)}
          />
        </ErrorBoundary>
      )}

      {/* Question Detail Modal */}
      {selectedQuestion && (() => {
        const currentList = questions.filter((q) => !currentSubject || normalizeBarSubject(q.subject) === currentSubject);
        const idx = currentList.findIndex(q => q.id === selectedQuestion.id);
        return (
          <Suspense fallback={null}>
            <QuestionDetailModal
              question={selectedQuestion}
              onClose={() => setSelectedQuestion(null)}
              hasNext={idx < currentList.length - 1}
              hasPrev={idx > 0}
              onNext={() => {
                if (idx < currentList.length - 1) {
                  setSelectedQuestion(currentList[idx + 1]);
                }
              }}
              onPrev={() => {
                if (idx > 0) {
                  setSelectedQuestion(currentList[idx - 1]);
                }
              }}
            />
          </Suspense>
        );
      })()}
      {/* Global Subscription Upgrade Modal */}
      {showUpgradeModal && (
        <Suspense fallback={null}>
          <SubscriptionModal onClose={closeUpgradeModal} />
        </Suspense>
      )}

    </Layout>
  );
}

export default App;
