import React, { useState, useEffect, useMemo } from 'react';
import Layout from './components/Layout';
import Sidebar from './components/Sidebar';
import ControlBar from './components/ControlBar';
import QuestionCard from './components/QuestionCard';
import Flashcard from './components/Flashcard';
import FlashcardSetup from './components/FlashcardSetup';
import MockTest from './components/MockTest';
import QuestionDetailModal from './components/QuestionDetailModal';

import About from './components/About';
import Updates from './components/Updates';
import SupremeDecisions from './components/SupremeDecisions';
import CodexViewer from './components/CodexViewer';
import CaseDecisionModal from './components/CaseDecisionModal';
import { LexPlayer, useLexPlay } from './features/lexplay';
import { useUser, SignedIn, SignedOut } from '@clerk/clerk-react';

function App() {
  const { isDrawerOpen, setIsDrawerOpen } = useLexPlay();
  
  // --- State ---
  const [questions, setQuestions] = useState([]);
  console.log('App render. Mode: (initializing)', 'Fullscreen: (initializing)');
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
  const [isDarkMode, setIsDarkMode] = useState(true); // Default to Dark Mode
  // Global case modal state (shared between SC Decisions and Codex)
  const [globalSelectedCase, setGlobalSelectedCase] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isPlayerVisible, setIsPlayerVisible] = useState(true);
  const [previousMode, setPreviousMode] = useState(null);
  console.log('App render. Mode:', mode, 'Fullscreen:', isFullscreen);

  // Intercept playNow signals to force player open
  useEffect(() => {
    if (isDrawerOpen && mode !== 'lexplay') {
      setIsPlayerVisible(true); // Guarantee the minimized player exists if they minimize it later
      setPreviousMode(mode);
      setMode('lexplay');
      setIsDrawerOpen(false); // Consume the signal
    }
  }, [isDrawerOpen, mode, setIsDrawerOpen, setIsPlayerVisible]);

  // No manual session check needed with Clerk

  // 1. Fetch Questions
  useEffect(() => {
    const fetchQuestions = async () => {
      try {
        setLoading(true);
        const response = await fetch('/api/questions?limit=100');
        if (!response.ok) throw new Error('Failed to fetch questions');
        const data = await response.json();

        // Balanced Shuffle: Group by subject, then interleave
        const subjects = {};
        data.forEach(q => {
          if (!subjects[q.subject]) subjects[q.subject] = [];
          subjects[q.subject].push(q);
        });

        // Sort each subject's questions by year (descending)
        Object.keys(subjects).forEach(key => {
          subjects[key].sort((a, b) => (b.year || 0) - (a.year || 0));
        });

        const balancedQuestions = [];
        const subjectKeys = Object.keys(subjects);
        let maxCount = 0;
        subjectKeys.forEach(key => maxCount = Math.max(maxCount, subjects[key].length));

        for (let i = 0; i < maxCount; i++) {
          subjectKeys.forEach(key => {
            if (subjects[key][i]) {
              balancedQuestions.push(subjects[key][i]);
            }
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



  // 2. Theme Management
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  const toggleTheme = () => setIsDarkMode(!isDarkMode);

  // --- Derived State (Filtering) ---
  const filteredQuestions = useMemo(() => {
    return questions.filter(q => {
      // If searching, ignore subject filter. Otherwise, respect it.
      const matchesSubject = searchTerm
        ? true
        : (currentSubject ? q.subject === currentSubject : true);

      const matchesYear = selectedYear ? q.year === parseInt(selectedYear) : true;

      const lowerSearch = searchTerm ? searchTerm.toLowerCase() : '';
      const matchesSearch = searchTerm
        ? q.text.toLowerCase().includes(lowerSearch) ||
        (q.answer && q.answer.toLowerCase().includes(lowerSearch))
        : true;

      return matchesSubject && matchesYear && matchesSearch;
    });
  }, [questions, currentSubject, selectedYear, searchTerm]);



  // --- Pagination ---
  // --- Pagination ---
  const [currentPage, setCurrentPage] = useState(1);

  const itemsPerPage = 8;

  const handlePageChange = (newPage) => {
    setCurrentPage(newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Reset page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [currentSubject, selectedYear, searchTerm]);

  const totalPages = Math.ceil(filteredQuestions.length / itemsPerPage);
  const paginatedQuestions = filteredQuestions.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );



  const handleToggleMode = () => {
    if (mode === 'browse') {
      setMode('flashcard');
      setFlashcardState('setup');
    } else {
      setMode('browse');
    }
  };

  const handleToggleAbout = () => {
    setMode('about');
  };

  const handleStartFlashcard = (subject) => {
    if (subject === 'CANCEL') {
      setMode('browse');
      return;
    }

    let selected = [];
    if (subject) {
      // Filter by subject, but still respect global year/search if desired? 
      // User request implies "random subjects or any subject", likely ignoring current browse filters.
      // Let's filter from the FULL `questions` list to be safe and independent.
      selected = questions.filter(q => q.subject === subject);
    } else {
      // Random / All
      selected = [...questions];
    }

    // Sort by year (descending)
    selected.sort((a, b) => (b.year || 0) - (a.year || 0));

    setFlashcardQuestions(selected);
    setFlashcardIndex(0);
    setFlashcardState('active');
  };

  const handleToggleQuiz = () => {
    setMode('quiz');
    setFlashcardIndex(0);
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
      onToggleMode={handleToggleMode}
      onToggleQuiz={handleToggleQuiz}
      user={user}
      sidebarContent={
        <Sidebar
          currentSubject={currentSubject}
          onSelectSubject={(subject, type = 'questions') => {
            setCurrentSubject(subject);
            setMode('browse');
          }}
          onToggleQuiz={handleToggleQuiz}
          onToggleMode={handleToggleMode}
          onToggleAbout={handleToggleAbout}
          onToggleHistory={() => setMode('history')}
          onToggleUpdates={() => setMode('updates')}
          onToggleSupremeDecisions={() => setMode('supreme_decisions')}
          onToggleLexPlay={() => {
            setPreviousMode(mode);
            setMode('lexplay');
            setIsPlayerVisible(true);
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
            {effectiveMode !== 'quiz' && effectiveMode !== 'about' && !isLexPlayerFull && effectiveMode !== 'login' && effectiveMode !== 'register' && effectiveMode !== 'updates' && effectiveMode !== 'supreme_decisions' && effectiveMode !== 'codex' && (
              <ControlBar
                searchTerm={searchTerm}
                onSearchChange={setSearchTerm}
                selectedYear={selectedYear}
                onYearChange={setSelectedYear}
              />
            )}

            {/* Content Area - Keep mounted but hide when LexPlayer is full */}
            <div className={isLexPlayerFull ? 'hidden' : ''}>
              {loading ? (
                <div className="flex justify-center items-center h-64">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
                </div>
              ) : error ? (
                <div className="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 p-4 rounded-lg text-center">
                  Error: {error}
                </div>
              ) : (
                <>
                  {effectiveMode === 'about' && <About />}
                  {effectiveMode === 'updates' && <Updates />}
                  {effectiveMode === 'supreme_decisions' && (
                    <SupremeDecisions
                      externalSelectedCase={globalSelectedCase}
                      onCaseSelect={setGlobalSelectedCase}
                    />
                  )}
                  {effectiveMode === 'codex' && selectedCodalCode && (
                    <CodexViewer
                      shortName={selectedCodalCode.toUpperCase()}
                      onCaseSelect={setGlobalSelectedCase}
                      isFullscreen={isFullscreen}
                      onToggleFullscreen={handleToggleFullscreen}
                    />
                  )}
                  {effectiveMode === 'browse' && filteredQuestions.length === 0 ? (
                    <div className="text-center py-20 text-gray-500 dark:text-gray-400">
                      <p className="text-xl font-medium">No questions found.</p>
                      <p className="mt-2">Try adjusting your filters.</p>
                    </div>
                  ) : effectiveMode === 'browse' && (
                    <>
                      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
                        {paginatedQuestions.map(q => (
                          <QuestionCard
                            key={q.id}
                            question={q}
                            searchQuery={searchTerm}
                            onClick={() => setSelectedQuestion(q)}
                          />
                        ))}
                      </div>
                      {totalPages > 1 && (
                        <div className="flex justify-center items-center gap-4 pb-6">
                          <button
                            onClick={() => handlePageChange(currentPage - 1)}
                            disabled={currentPage === 1}
                            className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 disabled:opacity-50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-sm"
                          >
                            Previous
                          </button>
                          <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
                            Page {currentPage} of {totalPages}
                          </span>
                          <button
                            onClick={() => handlePageChange(currentPage + 1)}
                            disabled={currentPage === totalPages}
                            className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 disabled:opacity-50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-sm"
                          >
                            Next
                          </button>
                        </div>
                      )}
                    </>
                  )}
                  {effectiveMode === 'flashcard' && flashcardState === 'setup' && (
                    <FlashcardSetup onStart={handleStartFlashcard} />
                  )}
                  {effectiveMode === 'flashcard' && flashcardState === 'active' && (
                    <Flashcard
                      question={flashcardQuestions[flashcardIndex]}
                      total={flashcardQuestions.length}
                      currentIndex={flashcardIndex}
                      onNext={handleNextFlashcard}
                      onClose={() => setMode('browse')}
                    />
                  )}
                  {effectiveMode === 'quiz' && (
                    <MockTest
                      questions={questions}
                      onFinish={() => setMode('browse')}
                    />
                  )}
                </>
              )}
            </div>

            {/* Full Player Overlay */}
            {isLexPlayerFull && (
              <LexPlayer
                isMinimized={false}
                onMinimize={() => setMode(previousMode || 'supreme_decisions')}
                onClose={() => {
                  setIsPlayerVisible(false);
                  setMode(previousMode || 'supreme_decisions');
                }}
              />
            )}
          </>
        );
      })()}

      {/* Question Detail Modal */}
      {selectedQuestion && (
        <QuestionDetailModal
          question={selectedQuestion}
          onClose={() => setSelectedQuestion(null)}
          searchQuery={searchTerm}
        />
      )}

      {/* Doctrinal Detail Modal */}

      {/* Global Case Decision Modal */}
      {globalSelectedCase && (
        <CaseDecisionModal
          decision={globalSelectedCase}
          onClose={() => setGlobalSelectedCase(null)}
          onCaseSelect={setGlobalSelectedCase}
        />
      )}

      {/* Global Minimized LexPlayer */}
      {mode !== 'lexplay' && isPlayerVisible && (
        <LexPlayer
          isMinimized={true}
          onExpand={() => {
            setPreviousMode(mode);
            setMode('lexplay');
          }}
          onClose={() => setIsPlayerVisible(false)}
        />
      )}

    </Layout>
  );
}

export default App;
