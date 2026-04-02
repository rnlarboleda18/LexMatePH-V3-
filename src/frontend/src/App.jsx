import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import Layout from './components/Layout';
import Sidebar from './components/Sidebar';
import ControlBar from './components/ControlBar';
import QuestionCard from './components/QuestionCard';
import Flashcard from './components/Flashcard';
import FlashcardSetup from './components/FlashcardSetup';
import LexifyApp from './features/lexify/LexifyApp';
import QuestionDetailModal from './components/QuestionDetailModal';

import About from './components/About';
import Updates from './components/Updates';
import SupremeDecisions from './components/SupremeDecisions';
import LexCodeViewer from './components/LexCodeViewer';
import CaseDecisionModal from './components/CaseDecisionModal';
import SubscriptionModal from './components/SubscriptionModal';
import UpgradeWall from './components/UpgradeWall';
import { LexPlayer, useLexPlay } from './features/lexplay';
import { useUser, SignedIn, SignedOut } from '@clerk/clerk-react';
import { RefreshCcw, AlertTriangle, ClipboardList, Brain } from 'lucide-react';
import { normalizeBarSubject } from './utils/subjectNormalize';
import { apiUrl } from './utils/apiUrl';
import { useSubscription } from './context/SubscriptionContext';
import ErrorBoundary from './components/ErrorBoundary';


function App() {
  const { isDrawerOpen, setIsDrawerOpen } = useLexPlay();
  const { showUpgradeModal, closeUpgradeModal, tier, canAccess } = useSubscription();
  
  // --- State ---
  const [questions, setQuestions] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedQuestion, setSelectedQuestion] = useState(null);
  const { user } = useUser();


  // Filters
  const [currentSubject, setCurrentSubject] = useState(null);
  const [selectedCodalCode, setSelectedCodalCode] = useState(null);
  const [selectedYear, setSelectedYear] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  // UI State
  const [mode, setMode] = useState('supreme_decisions'); // Default to 'supreme_decisions'
  const [flashcardState, setFlashcardState] = useState('setup'); // 'setup' | 'active'
  const [flashcardQuestions, setFlashcardQuestions] = useState([]);
  const [flashcardIndex, setFlashcardIndex] = useState(0);
  const [flashcardConceptPool, setFlashcardConceptPool] = useState([]);
  const [flashcardConceptsLoading, setFlashcardConceptsLoading] = useState(false);
  const [flashcardConceptsError, setFlashcardConceptsError] = useState(null);
  const [flashcardDeckError, setFlashcardDeckError] = useState(null);
  /** 'concepts' = SC digest key legal concepts; 'bar' = bar exam questions fallback */
  const [isDarkMode, setIsDarkMode] = useState(true); // Default to Dark Mode
  // Global case modal state (shared between SC Decisions and Codex)
  const [globalSelectedCase, setGlobalSelectedCase] = useState(null);
  /** Only block ghost-tap reopen of the *same* case right after close (not all case opens — that broke sync + other picks). */
  const lastClosedCaseIdRef = useRef(null);
  const suppressSameCaseReopenUntilRef = useRef(0);

  const selectGlobalCase = useCallback((next) => {
    if (
      next != null &&
      lastClosedCaseIdRef.current != null &&
      next.id === lastClosedCaseIdRef.current &&
      Date.now() < suppressSameCaseReopenUntilRef.current
    ) {
      return;
    }
    setGlobalSelectedCase(next);
  }, []);

  const closeGlobalCaseModal = useCallback(() => {
    const id = globalSelectedCase?.id;
    if (id != null) {
      lastClosedCaseIdRef.current = id;
    }
    suppressSameCaseReopenUntilRef.current = Date.now() + 750;
    setGlobalSelectedCase(null);
  }, [globalSelectedCase]);
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


  // Intercept playNow signals to force full-screen LexPlay
  useEffect(() => {
    if (isDrawerOpen && mode !== 'lexplay') {
      setPreviousMode(mode);
      setMode('lexplay');
      setIsDrawerOpen(false); // Consume the signal
    }
  }, [isDrawerOpen, mode, setIsDrawerOpen]);

  // No manual session check needed with Clerk

  // 1. Fetch Questions
  useEffect(() => {
    const fetchQuestions = async () => {
      try {
        setLoading(true);
        const response = await fetch('/api/questions?limit=5000');
        if (!response.ok) throw new Error('Failed to fetch questions');
        const data = await response.json();

        // --- Subject Normalizer ---
        // Maps verbose/variant DB subject strings → the 8 canonical Sidebar keys.
        const normalizeSubject = (raw) => {
          const s = (raw || '').toLowerCase();
          if (s.includes('civil')) return 'Civil Law';
          if (s.includes('commercial') || s.includes('mercantile')) return 'Commercial Law';
          if (s.includes('criminal') || s.includes('penal')) return 'Criminal Law';
          if (s.includes('labor') || s.includes('social legislat')) return 'Labor Law';
          if (s.includes('ethics') || s.includes('judicial ethics')) return 'Legal Ethics';
          if (s.includes('political') || s.includes('constitutional')) return 'Political Law';
          if (s.includes('remedial') || s.includes('procedure')) return 'Remedial Law';
          if (s.includes('taxation') || s.includes('tax')) return 'Taxation Law';
          return raw; // keep as-is if no match
        };

        // --- Greedy Grouping Logic ---
        const groupedData = [];
        let currentParent = null;

        // API returns data ordered by year DESC, subject, id ASC — no re-sort needed
        for (const q of data) {
          q.subject = normalizeSubject(q.subject);
          const qText = q.text.trim();
          const aText = (q.answer || "").trim();
          
          // Expanded Regex to identify sub-parts reliably
          // 1. (a), a., 1a., (1a), a)
          // 2. Q1a., A1a., Q1b, A1b
          // 3. (i), (ii), i., ii. (Roman numerals)
          const subPartRegex = /^([\(]?([a-z]|[0-9]+[a-z]|[ivx]+)[\.\)]|[QA]\d+[a-z][:.]?)/i;
          
          // Check BOTH question text and answer text for these markers
          const isSub = subPartRegex.test(qText) || subPartRegex.test(aText);

          const canGroup = currentParent && 
                           currentParent.year === q.year && 
                           currentParent.subject === q.subject;

          if (isSub && canGroup) {
            if (!currentParent.subQuestions) currentParent.subQuestions = [];
            currentParent.subQuestions.push(q);
          } else {
            // New parent/stem question
            currentParent = { ...q, subQuestions: [] };
            groupedData.push(currentParent);
          }
        }

        // Shuffle within groups if needed? No, just shuffle the groupedData.
        // Actually, more important: shuffle the final list within subjects.
        const subjects = {};
        groupedData.forEach(q => {
          if (!subjects[q.subject]) subjects[q.subject] = [];
          subjects[q.subject].push(q);
        });

        // Ensure complete randomness within each subject
        Object.keys(subjects).forEach(key => {
          for (let i = subjects[key].length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [subjects[key][i], subjects[key][j]] = [subjects[key][j], subjects[key][i]];
          }
        });

        // Finally interleave to balance subjects
        const balancedQuestions = [];
        const subjectKeys = Object.keys(subjects);
        let maxCount = 0;
        subjectKeys.forEach(key => maxCount = Math.max(maxCount, subjects[key].length));

        for (let i = 0; i < maxCount; i++) {
          subjectKeys.forEach(key => {
            if (subjects[key][i]) balancedQuestions.push(subjects[key][i]);
          });
        }

        setQuestions(balancedQuestions);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchQuestions();
  }, []);

  const [flashcardFetchNonce, setFlashcardFetchNonce] = useState(0);

  // Load SC digest concepts when Flashcards is opened. Retry adds ?nocache=1 to bypass Redis.
  useEffect(() => {
    if (mode !== 'flashcard') {
      setFlashcardConceptsLoading(false);
      return;
    }

    const ac = new AbortController();
    // Match api/host.json functionTimeout (00:05:00). Heavy path = merge digests when flashcard_concepts is empty.
    const FLASHCARD_FETCH_MS = 300000;
    const tid = setTimeout(() => ac.abort(), FLASHCARD_FETCH_MS);
    let cancelled = false;

    const load = async () => {
      setFlashcardConceptsLoading(true);
      setFlashcardConceptsError(null);
      try {
        const q = flashcardFetchNonce > 0 ? '?nocache=1' : '';
        const res = await fetch(apiUrl(`/api/sc_decisions/flashcard_concepts${q}`), { signal: ac.signal });
        const raw = await res.text();
        if (cancelled) return;
        if (!res.ok) {
          let msg = 'Failed to load key legal concepts';
          try {
            const j = JSON.parse(raw);
            if (j.error) msg = String(j.error);
          } catch (_) {
            if (raw) msg = raw.slice(0, 200);
          }
          throw new Error(msg);
        }
        const data = JSON.parse(raw);
        if (cancelled) return;
        setFlashcardConceptPool(Array.isArray(data.concepts) ? data.concepts : []);
      } catch (e) {
        if (cancelled) return;
        if (e.name === 'AbortError') {
          setFlashcardConceptsError(
            'Request timed out (5 min). The API merges digests from the database when the flashcard_concepts table is empty or the cache is cold—that can take several minutes. Fix: run scripts/populate_flashcard_concepts_from_digest.py on your cloud DB so the API reads the prebuilt table (fast). Also ensure the API and DB are reachable; retry once Redis has cached the response.'
          );
        } else {
          let msg = e.message || 'Load failed';
          if (msg === 'Failed to fetch' || /network/i.test(msg)) {
            msg =
              'Could not reach the API. For local dev, start the backend on port 7071 so Vite can proxy /api (see vite.config.js).';
          }
          setFlashcardConceptsError(msg);
        }
        setFlashcardConceptPool([]);
      } finally {
        clearTimeout(tid);
        setFlashcardConceptsLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
      ac.abort();
    };
  }, [mode, flashcardFetchNonce]);

  const refetchFlashcardConcepts = useCallback(() => {
    setFlashcardFetchNonce((n) => n + 1);
  }, []);

  const flashcardSubjectCounts = useMemo(() => {
    const subjects = [
      'Civil Law',
      'Commercial Law',
      'Criminal Law',
      'Labor Law',
      'Legal Ethics',
      'Political Law',
      'Remedial Law',
      'Taxation Law',
    ];
    const counts = { all: flashcardConceptPool.length };
    subjects.forEach((s) => {
      counts[s] = flashcardConceptPool.filter((c) =>
        (c.sources || []).some((src) => normalizeBarSubject(src.subject) === s)
      ).length;
    });
    return counts;
  }, [flashcardConceptPool]);

  const handleRetryFetch = () => {
    setError(null);
    setLoading(true);
    const doFetch = async () => {
      try {
        const response = await fetch('/api/questions?limit=5000');
        if (!response.ok) throw new Error('Failed to fetch questions');
        const data = await response.json();

        const normalizeSubject = (raw) => {
          const s = (raw || '').toLowerCase();
          if (s.includes('civil')) return 'Civil Law';
          if (s.includes('commercial') || s.includes('mercantile')) return 'Commercial Law';
          if (s.includes('criminal') || s.includes('penal')) return 'Criminal Law';
          if (s.includes('labor') || s.includes('social legislat')) return 'Labor Law';
          if (s.includes('ethics') || s.includes('judicial ethics')) return 'Legal Ethics';
          if (s.includes('political') || s.includes('constitutional')) return 'Political Law';
          if (s.includes('remedial') || s.includes('procedure')) return 'Remedial Law';
          if (s.includes('taxation') || s.includes('tax')) return 'Taxation Law';
          return raw;
        };

        const groupedData = [];
        let currentParent = null;
        const subPartRegex = /^([\(]?([a-z]|[0-9]+[a-z]|[ivx]+)[\.\)]|[QA]\d+[a-z][:.]?)/i;
        for (const q of data) {
          q.subject = normalizeSubject(q.subject);
          const qText = q.text.trim();
          const aText = (q.answer || '').trim();
          const isSub = subPartRegex.test(qText) || subPartRegex.test(aText);
          const canGroup = currentParent && currentParent.year === q.year && currentParent.subject === q.subject;
          if (isSub && canGroup) {
            if (!currentParent.subQuestions) currentParent.subQuestions = [];
            currentParent.subQuestions.push(q);
          } else {
            currentParent = { ...q, subQuestions: [] };
            groupedData.push(currentParent);
          }
        }

        const subjects = {};
        groupedData.forEach(q => { if (!subjects[q.subject]) subjects[q.subject] = []; subjects[q.subject].push(q); });
        Object.keys(subjects).forEach(key => {
          for (let i = subjects[key].length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [subjects[key][i], subjects[key][j]] = [subjects[key][j], subjects[key][i]];
          }
        });
        const balancedQuestions = [];
        const subjectKeys = Object.keys(subjects);
        let maxCount = 0;
        subjectKeys.forEach(key => maxCount = Math.max(maxCount, subjects[key].length));
        for (let i = 0; i < maxCount; i++) {
          subjectKeys.forEach(key => { if (subjects[key][i]) balancedQuestions.push(subjects[key][i]); });
        }
        setQuestions(balancedQuestions);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    doFetch();
  };



  // 2. Theme Management
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
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
      selected = flashcardConceptPool.filter((c) =>
        (c.sources || []).some((src) => normalizeBarSubject(src.subject) === subject)
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
      setMode('supreme_decisions');
    }
  };

  const handleToggleFlashcard = () => {
    setMode('flashcard');
    setFlashcardState('setup');
    setFlashcardDeckError(null);
  };

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
      isFullscreen={isFullscreen}
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
          onSelectCodal={(codeId) => {
            setSelectedCodalCode(codeId);
            setMode('codex');
          }}
          selectedCodalCode={selectedCodalCode}
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
              {loading && effectiveMode !== 'flashcard' ? (
                <div className="flex justify-center items-center h-64">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
                </div>
              ) : error && effectiveMode !== 'flashcard' ? (
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
                  {effectiveMode === 'about' && <About />}
                  {effectiveMode === 'updates' && <Updates />}
                  {effectiveMode === 'supreme_decisions' && (
                    <SupremeDecisions
                      externalSelectedCase={globalSelectedCase}
                      onCaseSelect={selectGlobalCase}
                    />
                  )}
                  {effectiveMode === 'codex' && selectedCodalCode && (
                    <LexCodeViewer
                      shortName={selectedCodalCode.toUpperCase()}
                      onCaseSelect={selectGlobalCase}
                      isFullscreen={isFullscreen}
                      onToggleFullscreen={handleToggleFullscreen}
                      subscriptionTier={tier}
                    />
                  )}
                  {effectiveMode === 'flashcard' && flashcardState === 'setup' && (
                    <div className="min-h-screen bg-transparent text-gray-900 dark:text-gray-100 font-sans">
                      <header
                        className="sticky z-20 overflow-hidden border-b border-white/30 bg-white/25 shadow-[0_8px_30px_rgb(0,0,0,0.06)] backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/35 dark:shadow-[0_8px_30px_rgb(0,0,0,0.25)] md:rounded-b-2xl md:shadow-[0_12px_40px_rgb(0,0,0,0.08)] md:backdrop-blur-2xl dark:md:shadow-[0_12px_40px_rgb(0,0,0,0.22)] lg:shadow-[0_16px_48px_rgb(0,0,0,0.09)] dark:lg:shadow-[0_16px_48px_rgb(0,0,0,0.28)] top-[calc(3.5rem+env(safe-area-inset-top,0px))] md:top-[calc(5rem+env(safe-area-inset-top,0px))]"
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
                        <div className="relative mx-auto flex max-w-7xl items-center gap-3 px-3 py-3.5 sm:gap-4 sm:px-5 sm:py-4 md:gap-5 md:py-5 lg:gap-6 lg:px-6 lg:py-6">
                          <div
                            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-indigo-200/90 bg-gradient-to-br from-indigo-50/95 to-blue-50/90 text-indigo-600 shadow-[0_4px_14px_rgba(79,70,229,0.12)] dark:border-indigo-800/70 dark:from-slate-800/90 dark:to-indigo-950/50 dark:text-indigo-300 dark:shadow-[0_4px_20px_rgba(0,0,0,0.35)] sm:h-12 sm:w-12 md:h-14 md:w-14 md:rounded-2xl md:shadow-[0_8px_24px_rgba(79,70,229,0.15)] lg:h-[3.75rem] lg:w-[3.75rem]"
                            aria-hidden
                          >
                            <Brain className="h-6 w-6 sm:h-7 sm:w-7 md:h-8 md:w-8 lg:h-9 lg:w-9" strokeWidth={2} />
                          </div>
                          <div className="min-w-0 flex-1 border-l-[3px] border-l-indigo-500 pl-3 dark:border-l-indigo-400 sm:pl-4 md:border-l-4 md:pl-5 lg:pl-6">
                            <h1 className="truncate text-lg font-bold tracking-tight sm:text-2xl md:text-3xl md:tracking-tight lg:text-[2rem] xl:text-[2.125rem] bg-gradient-to-r from-indigo-700 via-blue-700 to-indigo-600 bg-clip-text text-transparent dark:from-indigo-200 dark:via-blue-200 dark:to-indigo-100">
                              Flashcards
                            </h1>
                            <p className="mt-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400 sm:text-[11px] md:mt-1.5 md:text-xs md:tracking-[0.22em] lg:text-sm lg:tracking-[0.18em]">
                              Concept and Bar exam study deck
                            </p>
                          </div>
                        </div>
                      </header>
                      <main className="max-w-7xl mx-auto px-3 py-4 sm:px-5 sm:py-5 lg:px-6">
                        <FlashcardSetup
                          embedded
                          onStart={handleStartFlashcard}
                          conceptsLoading={flashcardConceptsLoading}
                          conceptsError={flashcardConceptsError}
                          deckError={flashcardDeckError}
                          subjectCounts={flashcardSubjectCounts}
                          onRetryConcepts={refetchFlashcardConcepts}
                        />
                      </main>
                    </div>
                  )}
                  {effectiveMode === 'flashcard' && flashcardState === 'active' && (
                    <div
                      className="flex h-[calc(100dvh-var(--player-height,0px)-env(safe-area-inset-top,0px)-3.5rem)] min-h-[280px] w-full flex-col items-center justify-center px-3 pb-3 pt-2 text-gray-900 dark:text-gray-100 sm:px-5 md:h-[calc(100dvh-var(--player-height,0px)-env(safe-area-inset-top,0px)-5rem)] md:px-6 md:pb-4 md:pt-3"
                    >
                      <div className="flex h-full min-h-0 w-full max-w-2xl flex-col md:max-h-[min(90vh,calc(100dvh-var(--player-height,0px)-min(5vh,3rem)))]">
                        <Flashcard
                          variant="concepts"
                          card={flashcardQuestions[flashcardIndex]}
                          total={flashcardQuestions.length}
                          currentIndex={flashcardIndex}
                          onNext={handleNextFlashcard}
                          onClose={() => setMode('supreme_decisions')}
                        />
                      </div>
                    </div>
                  )}
                  {effectiveMode === 'quiz' && (
                    canAccess('lexify') ? (
                      <LexifyApp
                        questions={questions}
                        onClose={() => setMode('supreme_decisions')}
                      />
                    ) : (
                      <div className="flex items-center justify-center min-h-[60vh]">
                        <div className="max-w-md w-full">
                          <UpgradeWall feature="lexify" variant="inline" />
                        </div>
                      </div>
                    )
                  )}
                  {effectiveMode === 'browse_bar' && (
                    <div className="min-h-screen bg-transparent text-gray-900 dark:text-gray-100 font-sans">
                      <header
                        className="sticky z-20 overflow-hidden border-b border-white/30 bg-white/25 shadow-[0_8px_30px_rgb(0,0,0,0.06)] backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/35 dark:shadow-[0_8px_30px_rgb(0,0,0,0.25)] md:rounded-b-2xl md:shadow-[0_12px_40px_rgb(0,0,0,0.08)] md:backdrop-blur-2xl dark:md:shadow-[0_12px_40px_rgb(0,0,0,0.22)] lg:shadow-[0_16px_48px_rgb(0,0,0,0.09)] dark:lg:shadow-[0_16px_48px_rgb(0,0,0,0.28)] top-[calc(3.5rem+env(safe-area-inset-top,0px))] md:top-[calc(5rem+env(safe-area-inset-top,0px))]"
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
                        <div className="relative mx-auto flex max-w-7xl items-center gap-3 px-3 py-3.5 sm:gap-4 sm:px-5 sm:py-4 md:gap-5 md:py-5 lg:gap-6 lg:px-6 lg:py-6">
                          <div
                            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-indigo-200/90 bg-gradient-to-br from-indigo-50/95 to-blue-50/90 text-indigo-600 shadow-[0_4px_14px_rgba(79,70,229,0.12)] dark:border-indigo-800/70 dark:from-slate-800/90 dark:to-indigo-950/50 dark:text-indigo-300 dark:shadow-[0_4px_20px_rgba(0,0,0,0.35)] sm:h-12 sm:w-12 md:h-14 md:w-14 md:rounded-2xl md:shadow-[0_8px_24px_rgba(79,70,229,0.15)] lg:h-[3.75rem] lg:w-[3.75rem]"
                            aria-hidden
                          >
                            <ClipboardList className="h-6 w-6 sm:h-7 sm:w-7 md:h-8 md:w-8 lg:h-9 lg:w-9" strokeWidth={2} />
                          </div>
                          <div className="min-w-0 flex-1 border-l-[3px] border-l-indigo-500 pl-3 dark:border-l-indigo-400 sm:pl-4 md:border-l-4 md:pl-5 lg:pl-6">
                            <h1 className="truncate text-lg font-bold tracking-tight sm:text-2xl md:text-3xl md:tracking-tight lg:text-[2rem] xl:text-[2.125rem] bg-gradient-to-r from-indigo-700 via-blue-700 to-indigo-600 bg-clip-text text-transparent dark:from-indigo-200 dark:via-blue-200 dark:to-indigo-100">
                              Bar Questions
                            </h1>
                            <p className="mt-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400 sm:text-[11px] md:mt-1.5 md:text-xs md:tracking-[0.22em] lg:text-sm lg:tracking-[0.18em]">
                              Actual Bar questions & suggested answers
                            </p>
                          </div>
                        </div>
                      </header>
                      <main className="max-w-7xl mx-auto px-3 py-4 sm:px-5 sm:py-5 lg:px-6">
                      <div className="glass mb-4 rounded-lg border border-white/40 bg-white/45 p-4 shadow-sm dark:border-white/10 dark:bg-slate-900/35">
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between sm:gap-4">
                          <div className="min-w-0 flex-1">
                            <label htmlFor="bar-subject-filter" className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">
                              Bar subject
                            </label>
                            <select
                              id="bar-subject-filter"
                              value={currentSubject ?? ''}
                              onChange={(e) => {
                                const v = e.target.value;
                                setCurrentSubject(v === '' ? null : v);
                                setBarCurrentPage(1);
                              }}
                              className="block w-full max-w-md pl-3 pr-8 py-2.5 text-sm border border-stone-400 dark:border-gray-600 shadow-sm focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-amber-500 rounded-lg dark:bg-gray-900 dark:text-white"
                            >
                              <option value="">All subjects</option>
                              {BAR_SUBJECT_OPTIONS.map((s) => (
                                <option key={s} value={s}>
                                  {s}
                                </option>
                              ))}
                            </select>
                          </div>
                          <div className="inline-flex shrink-0 items-center rounded-full border border-indigo-200/60 bg-indigo-50/80 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-indigo-700 dark:border-indigo-800/40 dark:bg-indigo-900/30 dark:text-indigo-300">
                            {questions.filter((q) => !currentSubject || normalizeBarSubject(q.subject) === currentSubject).length}{' '}
                            questions
                          </div>
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
                                className="px-4 py-2 glass bg-white/50 dark:bg-slate-700/40 border border-white/30 dark:border-white/10 rounded-lg shadow-sm text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-white/70 dark:hover:bg-slate-600/60 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
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
                                className="px-4 py-2 glass bg-white/50 dark:bg-slate-700/40 border border-white/30 dark:border-white/10 rounded-lg shadow-sm text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-white/70 dark:hover:bg-slate-600/60 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
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
                  onMinimize={() => setMode(previousMode || 'supreme_decisions')}
                />
              </ErrorBoundary>
            )}
          </>
        );
      })()}


      {/* Doctrinal Detail Modal */}

      {/* Global Case Decision Modal */}
      {globalSelectedCase && (
        <CaseDecisionModal
          decision={globalSelectedCase}
          onClose={closeGlobalCaseModal}
          onCaseSelect={selectGlobalCase}
        />
      )}

      {/* Global Minimized LexPlayer — always visible docked to bottom when not in full LexPlay */}
      {mode !== 'lexplay' && (
        <ErrorBoundary>
          <LexPlayer
            isMinimized={true}
            onExpand={() => {
              setPreviousMode(mode);
              setMode('lexplay');
            }}
          />
        </ErrorBoundary>
      )}

      {/* Question Detail Modal */}
      {selectedQuestion && (() => {
        const currentList = questions.filter((q) => !currentSubject || normalizeBarSubject(q.subject) === currentSubject);
        const idx = currentList.findIndex(q => q.id === selectedQuestion.id);
        return (
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
        );
      })()}
      {/* Global Subscription Upgrade Modal */}
      {showUpgradeModal && (
        <SubscriptionModal onClose={closeUpgradeModal} />
      )}

    </Layout>
  );
}

export default App;
