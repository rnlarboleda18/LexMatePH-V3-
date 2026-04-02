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
import CodexViewer from './components/CodexViewer';
import CaseDecisionModal from './components/CaseDecisionModal';
import SubscriptionModal from './components/SubscriptionModal';
import UpgradeWall from './components/UpgradeWall';
import { LexPlayer, useLexPlay } from './features/lexplay';
import { useUser, SignedIn, SignedOut } from '@clerk/clerk-react';
import { ChevronRight, RefreshCcw, AlertTriangle } from 'lucide-react';
import { getSubjectColor } from './utils/colors';
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
  const [flashcardVariant, setFlashcardVariant] = useState('concepts');
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
    const tid = setTimeout(() => ac.abort(), 120000);
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
            'Request timed out after 2 minutes. The concepts query is heavy: ensure the API is running (local: port 7071), the database is reachable, and try Bar exam questions below. A second open may be faster if Redis cached the result.'
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

  const barFlashcardSubjectCounts = useMemo(() => {
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
    const counts = { all: questions.length };
    subjects.forEach((s) => {
      counts[s] = questions.filter((q) => normalizeBarSubject(q.subject) === s).length;
    });
    return counts;
  }, [questions]);

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
    setFlashcardVariant('concepts');

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
          ? `No key legal concepts found for ${subject} yet. Try another subject, All subjects, or use bar questions below.`
          : 'No key legal concepts are available yet. Use bar exam questions below, or run your digest pipeline to fill legal_concepts.'
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

  const handleStartBarFlashcards = (subject) => {
    if (subject === 'CANCEL') {
      setMode('supreme_decisions');
      return;
    }
    setFlashcardDeckError(null);
    setFlashcardVariant('bar');

    let selected = [];
    if (subject) {
      selected = questions.filter((q) => normalizeBarSubject(q.subject) === subject);
    } else {
      selected = [...questions];
    }

    if (selected.length === 0) {
      setFlashcardDeckError(
        subject ? `No bar questions for ${subject} in the loaded set.` : 'No bar questions loaded.'
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
    setFlashcardVariant('concepts');
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
          currentSubject={currentSubject}
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
                    <CodexViewer
                      shortName={selectedCodalCode.toUpperCase()}
                      onCaseSelect={selectGlobalCase}
                      isFullscreen={isFullscreen}
                      onToggleFullscreen={handleToggleFullscreen}
                      subscriptionTier={tier}
                    />
                  )}
                  {effectiveMode === 'flashcard' && flashcardState === 'setup' && (
                    <FlashcardSetup
                      onStart={handleStartFlashcard}
                      onStartBar={handleStartBarFlashcards}
                      conceptsLoading={flashcardConceptsLoading}
                      conceptsError={flashcardConceptsError}
                      deckError={flashcardDeckError}
                      subjectCounts={flashcardSubjectCounts}
                      barSubjectCounts={barFlashcardSubjectCounts}
                      barAvailable={!loading && !error && questions.length > 0}
                      onRetryConcepts={refetchFlashcardConcepts}
                    />
                  )}
                  {effectiveMode === 'flashcard' && flashcardState === 'active' && (
                    <Flashcard
                      variant={flashcardVariant}
                      card={flashcardQuestions[flashcardIndex]}
                      total={flashcardQuestions.length}
                      currentIndex={flashcardIndex}
                      onNext={handleNextFlashcard}
                      onClose={() => setMode('supreme_decisions')}
                    />
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
                    <div className="p-6">
                      <div className="flex items-center justify-between mb-8">
                        <div>
                          <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 mb-2">
                        <button 
                          onClick={() => setCurrentSubject(null)}
                          className="hover:text-amber-600 dark:hover:text-amber-500 transition-colors"
                        >
                          Bar Questions
                        </button>
                        <ChevronRight size={14} />
                        <span className="text-amber-600 dark:text-amber-500 font-medium">{currentSubject || 'All Subjects'}</span>
                      </div>
                          <p className="text-gray-600 dark:text-gray-400">
    Browse individual bar exam questions and answers.
                          </p>
                        </div>
                        <div className="bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 px-4 py-2 rounded-full text-sm font-bold border border-amber-200 dark:border-amber-800">
                          {questions.filter(q => !currentSubject || q.subject === currentSubject).length} Questions
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-6">
                        {(() => {
                          const filtered = questions.filter(q => !currentSubject || q.subject === currentSubject);
                          const paginated = filtered.slice((barCurrentPage - 1) * BAR_ITEMS_PER_PAGE, barCurrentPage * BAR_ITEMS_PER_PAGE);
                          return paginated.map((q) => (
                            <QuestionCard
                              key={q.id}
                              question={q}
                              onClick={() => setSelectedQuestion(q)}
                              subjectColor={getSubjectColor(q.subject)}
                            />
                          ));
                        })()}
                      </div>

                      {/* Pagination UI copied from SC Decisions */}
                      {(() => {
                        const filtered = questions.filter(q => !currentSubject || q.subject === currentSubject);
                        const totalCount = filtered.length;
                        if (totalCount <= BAR_ITEMS_PER_PAGE) return null;
                        
                        return (
                          <div className="flex flex-col items-center gap-2 mt-12 pb-8">
                            <div className="flex justify-center items-center gap-4">
                              <button
                                onClick={() => {
                                  setBarCurrentPage(prev => Math.max(1, prev - 1));
                                  window.scrollTo({ top: 0, behavior: 'smooth' });
                                }}
                                disabled={barCurrentPage === 1}
                                className="px-5 py-2.5 glass bg-white/40 dark:bg-slate-700/40 backdrop-blur-sm border border-white/20 dark:border-white/5 rounded-lg shadow-sm text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-white/60 dark:hover:bg-slate-600/60 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
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
                                className="px-5 py-2.5 glass bg-white/40 dark:bg-slate-700/40 backdrop-blur-sm border border-white/20 dark:border-white/5 rounded-lg shadow-sm text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-white/60 dark:hover:bg-slate-600/60 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                              >
                                Next
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                              </button>
                            </div>
                          </div>
                        );
                      })()}
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
        const currentList = questions.filter(q => !currentSubject || q.subject === currentSubject);
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
