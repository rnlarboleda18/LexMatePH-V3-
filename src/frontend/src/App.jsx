import React, { useState, useEffect, useLayoutEffect, useRef, useCallback, useMemo, lazy, Suspense } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { useUser } from '@clerk/clerk-react';
import { RefreshCcw, AlertTriangle, Search } from 'lucide-react';
import Fuse from 'fuse.js';
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
  // Bar-questions search term — seeded from ?q= if we land directly on /bar-questions
  const [searchTerm, setSearchTerm] = useState(() =>
    PATH_TO_MODE[window.location.pathname] === 'browse_bar'
      ? (new URLSearchParams(window.location.search).get('q') ?? '')
      : ''
  );

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
  const [previousMode, setPreviousMode] = useState(null);
  const [barCurrentPage, setBarCurrentPage] = useState(1);
  const BAR_ITEMS_PER_PAGE = 20; // 2 columns * 10 rows

  // Bar search portal
  const [showBarSuggestions, setShowBarSuggestions] = useState(false);
  const [barSearchRect, setBarSearchRect] = useState(null);
  const barSearchInputRef = useRef(null);
  /** Fixed filter row height → main padding (same pattern as SupremeDecisions). */
  const barFilterChromeRef = useRef(null);
  const [barFilterChromeHeight, setBarFilterChromeHeight] = useState(52);
  /** Match Tailwind `xl:` (1280px) — fixed bar-questions chrome only at desktop. */
  const [xlFixedChrome, setXlFixedChrome] = useState(() =>
    typeof window !== 'undefined' && window.matchMedia('(min-width: 1280px)').matches,
  );
  useEffect(() => {
    const mq = window.matchMedia('(min-width: 1280px)');
    const on = () => setXlFixedChrome(mq.matches);
    on();
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, []);
  const barCloseSuggestionsTimerRef = useRef(null);
  const barFuseRef = useRef(null);
  const [barFuseReady, setBarFuseReady] = useState(false);

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

  // Persist bar-questions search term in the URL (?q=) so users can share / refresh.
  // Uses window.history.replaceState directly (no React Router) to avoid triggering
  // a router context update that would cause extra re-renders.
  useEffect(() => {
    if (mode !== 'browse_bar') return;
    const params = new URLSearchParams(window.location.search);
    if (searchTerm) {
      params.set('q', searchTerm);
    } else {
      params.delete('q');
    }
    const qs = params.toString();
    window.history.replaceState(
      null,
      '',
      window.location.pathname + (qs ? `?${qs}` : '')
    );
  }, [searchTerm, mode]);

  // Reset bar page when search term or subject changes
  useEffect(() => {
    setBarCurrentPage(1);
  }, [currentSubject, searchTerm]);

  // Build fuzzy-search index whenever the questions list changes.
  useEffect(() => {
    if (!questions?.length) {
      barFuseRef.current = null;
      setBarFuseReady(false);
      return;
    }
    barFuseRef.current = new Fuse(questions, {
      keys: [
        { name: 'question', weight: 0.5 },
        { name: 'answer',   weight: 0.3 },
        { name: 'subject',  weight: 0.2 },
      ],
      threshold: 0.4,
      distance: 400,
      minMatchCharLength: 2,
      includeScore: false,
    });
    setBarFuseReady(true);
  }, [questions]);

  // Keep bar-search dropdown anchored when page scrolls / resizes.
  useEffect(() => {
    if (!showBarSuggestions) return;
    const update = () => {
      if (barSearchInputRef.current) {
        setBarSearchRect(barSearchInputRef.current.getBoundingClientRect());
      }
    };
    window.addEventListener('scroll', update, true);
    window.addEventListener('resize', update);
    return () => {
      window.removeEventListener('scroll', update, true);
      window.removeEventListener('resize', update);
    };
  }, [showBarSuggestions]);

  /** Bar list stays mounted under LexPlay fullscreen (effectiveMode); keep chrome height in sync. */
  const browseBarFilterChromeActive =
    mode === 'browse_bar' || (mode === 'lexplay' && previousMode === 'browse_bar');

  useLayoutEffect(() => {
    if (!browseBarFilterChromeActive) return undefined;
    const el = barFilterChromeRef.current;
    if (!el || typeof ResizeObserver === 'undefined') {
      return undefined;
    }
    const measure = () => {
      setBarFilterChromeHeight(Math.ceil(el.getBoundingClientRect().height));
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [browseBarFilterChromeActive, searchTerm, currentSubject]);

  // Pre-filter bar questions (both subject and free-text/fuzzy) so the JSX stays clean.
  const filteredBarQuestions = useMemo(() => {
    let pool = questions;
    if (currentSubject) {
      pool = pool.filter(
        (q) => normalizeBarSubject(q.subject) === currentSubject
      );
    }
    if (!searchTerm.trim()) return pool;
    if (barFuseRef.current) {
      const matchedIds = new Set(
        barFuseRef.current.search(searchTerm).map((r) => r.item.id)
      );
      return pool.filter((q) => matchedIds.has(q.id));
    }
    // Fuse index not ready yet — fall back to includes.
    const lq = searchTerm.toLowerCase();
    return pool.filter(
      (q) =>
        (q.question || '').toLowerCase().includes(lq) ||
        (q.answer || '').toLowerCase().includes(lq) ||
        (q.subject || '').toLowerCase().includes(lq)
    );
  }, [questions, currentSubject, searchTerm, barFuseReady]);

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

  // --- Render ---
  return (
    <Layout
      isDarkMode={isDarkMode}
      toggleTheme={toggleTheme}
      mode={mode}
      mainFullWidth={mode === 'flashcard' && flashcardState === 'active'}
      flashcardStudying={mode === 'flashcard' && flashcardState === 'active'}
      hideAppChrome={lexifyExamSimulationActive || mode === 'landing'}
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
                      <Suspense fallback={<PageLoadingFallback label="Loading LexCode…" />}>
                        <LexCodeViewer
                          shortName={selectedCodalCode ? selectedCodalCode.toUpperCase() : ''}
                          codalOptions={CODAL_FILTER_OPTIONS}
                          selectedCodal={selectedCodalCode}
                          onCodalChange={(id) => {
                            setSelectedCodalCode(id);
                            window.scrollTo({ top: 0, behavior: 'smooth' });
                          }}
                          onCaseSelect={selectGlobalCase}
                          subscriptionTier={tier}
                        />
                      </Suspense>
                    </div>
                  )}
                  {effectiveMode === 'flashcard' && flashcardState === 'setup' && (
                    <div className="min-h-screen bg-transparent text-gray-900 dark:text-gray-100 font-sans">
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
                      <FeaturePageShell>
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
                    <div className="min-h-screen w-full min-w-0 bg-transparent text-gray-900 dark:text-gray-100 font-sans">
                      {/* Search + filter — scrolls with page below xl; fixed at xl+ */}
                      <div
                        ref={barFilterChromeRef}
                        className={`z-20 w-full xl:w-auto min-w-0 border-b border-slate-200/80 bg-white/95 shadow-sm backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/95 ${
                          xlFixedChrome
                            ? 'fixed left-0 right-0 top-[calc(var(--app-header-height)+env(safe-area-inset-top,0px))] xl:left-52'
                            : 'relative'
                        }`}
                      >
                        <div className="w-full min-w-0 max-w-7xl px-3 py-2 sm:px-5 lg:px-6">
                          <div className="flex w-full min-w-0 flex-col gap-2 sm:flex-row sm:flex-nowrap sm:items-center sm:gap-2">
                            <div className="flex min-w-0 shrink-0 flex-col sm:w-[min(100%,14rem)] md:w-44">
                              <label htmlFor="bar-subject-filter" className="mb-0.5 block text-[10px] font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400 sm:sr-only">
                                Bar subject ({filteredBarQuestions.length} question{filteredBarQuestions.length !== 1 ? 's' : ''})
                              </label>
                              <select
                                id="bar-subject-filter"
                                aria-label="Filter by Bar subject"
                                value={currentSubject ?? ''}
                                onChange={(e) => {
                                  const v = e.target.value;
                                  setCurrentSubject(v === '' ? null : v);
                                  setBarCurrentPage(1);
                                }}
                                className="box-border block h-9 w-full rounded-md border border-stone-400 bg-gray-50 py-1.5 pl-2 pr-6 text-xs leading-tight text-gray-900 shadow-sm focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500 dark:border-gray-600 dark:bg-gray-900 dark:text-white sm:text-sm"
                              >
                                <option value="">All subjects</option>
                                {BAR_SUBJECT_OPTIONS.map((s) => (
                                  <option key={s} value={s}>{s}</option>
                                ))}
                              </select>
                            </div>
                            <div className="relative min-w-0 w-full flex-1 basis-0 sm:w-auto">
                              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-2">
                                <Search className="h-3.5 w-3.5 text-gray-400" strokeWidth={2} />
                              </div>
                              <input
                                ref={barSearchInputRef}
                                type="search"
                                placeholder="Search questions, answers, subjects…"
                                value={searchTerm}
                                onChange={(e) => {
                                  setSearchTerm(e.target.value);
                                  setBarCurrentPage(1);
                                  setShowBarSuggestions(true);
                                }}
                                onFocus={() => {
                                  clearTimeout(barCloseSuggestionsTimerRef.current);
                                  if (barSearchInputRef.current) {
                                    setBarSearchRect(barSearchInputRef.current.getBoundingClientRect());
                                  }
                                  setShowBarSuggestions(true);
                                }}
                                onBlur={() => {
                                  barCloseSuggestionsTimerRef.current = setTimeout(
                                    () => setShowBarSuggestions(false),
                                    160
                                  );
                                }}
                                onKeyDown={(e) => {
                                  if (e.key === 'Escape') {
                                    setShowBarSuggestions(false);
                                    barSearchInputRef.current?.blur();
                                  } else if (e.key === 'Enter') {
                                    setShowBarSuggestions(false);
                                  }
                                }}
                                className="box-border block h-9 min-w-0 w-full max-w-full rounded-md border border-stone-400 bg-gray-50 py-1.5 pl-7 pr-3 text-xs leading-tight text-gray-900 shadow-sm placeholder-gray-500 transition-colors focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500 dark:border-gray-600 dark:bg-gray-900 dark:text-white dark:placeholder-gray-500 sm:text-sm"
                              />
                            </div>
                          </div>
                        </div>
                      </div>

                      <main
                        className="w-full min-w-0 max-w-7xl px-3 pb-4 pt-3 sm:px-5 sm:pb-5 lg:px-6 xl:pt-0"
                        style={xlFixedChrome ? { paddingTop: `${barFilterChromeHeight + 12}px` } : undefined}
                      >
                      {/* Bar search suggestions — portaled to body so it escapes overflow-hidden */}
                      {showBarSuggestions && barSearchRect && typeof document !== 'undefined' &&
                        createPortal(
                          <div
                            className="fixed z-[200] max-h-72 overflow-y-auto rounded-xl border border-slate-200 bg-white shadow-2xl dark:border-white/10 dark:bg-slate-900"
                            style={{
                              top: barSearchRect.bottom + 4,
                              left: barSearchRect.left,
                              width: barSearchRect.width,
                            }}
                            onMouseDown={(e) => e.preventDefault()}
                          >
                            {/* Fuzzy question matches */}
                            {(() => {
                              if (!searchTerm.trim()) {
                                return (
                                  <p className="px-3 py-3 text-center text-xs text-gray-400 dark:text-gray-500">
                                    Start typing to search questions…
                                  </p>
                                );
                              }
                              const hits = barFuseRef.current
                                ? barFuseRef.current.search(searchTerm).map((r) => r.item).slice(0, 8)
                                : [];
                              if (hits.length === 0) {
                                return (
                                  <p className="px-3 py-3 text-center text-xs text-gray-400 dark:text-gray-500">
                                    No questions match &ldquo;{searchTerm}&rdquo;
                                  </p>
                                );
                              }
                              return (
                                <>
                                  <div className="border-b border-gray-100 px-3 py-1.5 dark:border-white/10">
                                    <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
                                      Top matches — click to open
                                    </span>
                                  </div>
                                  <div className="divide-y divide-gray-100 dark:divide-white/5">
                                    {hits.map((q) => (
                                      <button
                                        key={q.id}
                                        type="button"
                                        onClick={() => {
                                          setShowBarSuggestions(false);
                                          setSelectedQuestion(q);
                                        }}
                                        className="w-full px-3 py-2.5 text-left transition-colors hover:bg-amber-50 dark:hover:bg-amber-900/20"
                                      >
                                        <p className="line-clamp-2 text-sm font-semibold text-gray-800 dark:text-gray-200">
                                          {q.question}
                                        </p>
                                        <p className="mt-0.5 text-[11px] text-gray-400 dark:text-gray-500">
                                          {q.subject} · {q.year}
                                        </p>
                                      </button>
                                    ))}
                                  </div>
                                </>
                              );
                            })()}
                          </div>,
                          document.body
                        )
                      }

                      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                        {filteredBarQuestions
                          .slice(
                            (barCurrentPage - 1) * BAR_ITEMS_PER_PAGE,
                            barCurrentPage * BAR_ITEMS_PER_PAGE
                          )
                          .map((q) => (
                            <QuestionCard
                              key={q.id}
                              question={q}
                              searchQuery={searchTerm}
                              onClick={() => setSelectedQuestion(q)}
                            />
                          ))}
                      </div>

                      {filteredBarQuestions.length === 0 && !loading && (
                        <p className="py-12 text-center text-sm text-gray-400 dark:text-gray-500">
                          No questions match your search.
                        </p>
                      )}

                      {/* Pagination UI */}
                      {(() => {
                        const totalCount = filteredBarQuestions.length;
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
