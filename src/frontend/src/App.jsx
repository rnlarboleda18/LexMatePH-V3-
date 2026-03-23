import React, { useState, useEffect, useMemo } from 'react';
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
import { LexPlayer, useLexPlay } from './features/lexplay';
import { useUser, SignedIn, SignedOut } from '@clerk/clerk-react';
import { ChevronRight } from 'lucide-react';
import { getSubjectColor } from './utils/colors';

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
        const response = await fetch('/api/questions?limit=5000');
        if (!response.ok) throw new Error('Failed to fetch questions');
        const data = await response.json();

        // --- Greedy Grouping Logic ---
        const groupedData = [];
        let currentParent = null;

        // Sort by ID to keep logical flow (consecutive rows usually belong together)
        const sortedRaw = [...data].sort((a, b) => a.id - b.id);

        for (const q of sortedRaw) {
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

    // Preserve the randomized order from the fetch shuffle

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
            setIsPlayerVisible(true);
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
                  {effectiveMode === 'flashcard' && flashcardState === 'setup' && (
                    <FlashcardSetup onStart={handleStartFlashcard} />
                  )}
                  {effectiveMode === 'flashcard' && flashcardState === 'active' && (
                    <Flashcard
                      question={flashcardQuestions[flashcardIndex]}
                      total={flashcardQuestions.length}
                      currentIndex={flashcardIndex}
                      onNext={handleNextFlashcard}
                      onClose={() => setMode('supreme_decisions')}
                    />
                  )}
                  {effectiveMode === 'quiz' && (
                    <LexifyApp
                      questions={questions}
                      onClose={() => setMode('supreme_decisions')}
                    />
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

                      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                        {questions
                          .filter(q => !currentSubject || q.subject === currentSubject)
                          .map((q) => (
                            <QuestionCard
                              key={q.id}
                              question={q}
                              onClick={() => setSelectedQuestion(q)}
                              subjectColor={getSubjectColor(q.subject)}
                            />
                          ))}
                      </div>
                    </div>
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
    </Layout>
  );
}

export default App;
