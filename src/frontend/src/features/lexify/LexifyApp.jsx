import React, { useState, useEffect, useCallback } from 'react';
import LexifyDashboard from './LexifyDashboard';
import LexifySidebar from './LexifySidebar';
import LexifyWorkspace from './LexifyWorkspace';
import LexifyControls from './LexifyControls';
import LexifyNotes from './LexifyNotes';
import LexifyCalculator from './LexifyCalculator';
import LexifyResults from './LexifyResults';

// ... state definitions intact

const LexifyApp = ({ questions: propQuestions, onClose, onExamSimulationChange }) => {
    const [examState, setExamState] = useState(0);
    const [activeQuestions, setActiveQuestions] = useState(propQuestions || []);
    const [examLabel, setExamLabel] = useState('');
    const [fetchError, setFetchError] = useState('');
    const [currentIndex, setCurrentIndex] = useState(0);
    const [userAnswers, setUserAnswers] = useState({});
    const [flaggedQuestions, setFlaggedQuestions] = useState(new Set());
    const [notesOpen, setNotesOpen] = useState(false);
    const [calculatorOpen, setCalculatorOpen] = useState(false);
    const [spellCheck, setSpellCheck] = useState(false);
    const [alarmTime, setAlarmTime] = useState('00:30:00');
    // ...
    // ... lines omitted for brevity ...

    const [gradingResults, setGradingResults] = useState([]);
    const [gradingError, setGradingError] = useState('');
    const [examStartTime, setExamStartTime] = useState(null);
    const [timeUsed, setTimeUsed] = useState(0);
    const [showDisclaimer, setShowDisclaimer] = useState(false); // Added for custom disclaimer overlay

    // Tell App to hide minimized LexPlayer during simulation (loading, lockdown, exam, submit, grading — not dashboard or results).
    useEffect(() => {
        if (!onExamSimulationChange) return;
        const inSimulation = examState !== 0 && examState !== 6;
        onExamSimulationChange(inSimulation);
        return () => onExamSimulationChange(false);
    }, [examState, onExamSimulationChange]);

    // Security: Alert on tab switch during active exam
    useEffect(() => {
        if (examState !== 2) return;
        const handleVisibilityChange = () => {
            if (document.hidden) {
                alert('⚠ SECURITY NOTICE: Switching tabs or minimizing during the exam is prohibited and may be reported in a real examination.');
            }
        };
        const handleBeforeUnload = (e) => {
            e.preventDefault();
            e.returnValue = '';
        };
        document.addEventListener('visibilitychange', handleVisibilityChange);
        window.addEventListener('beforeunload', handleBeforeUnload);
        return () => {
            document.removeEventListener('visibilitychange', handleVisibilityChange);
            window.removeEventListener('beforeunload', handleBeforeUnload);
        };
    }, [examState]);

    const handleBeginExam = async (examId, alarm, prefillAnswers = false) => {
        setAlarmTime(alarm || '00:30:00');
        setFetchError('');
        setExamState(-1); // Loading state

        try {
            // Fetch weighted questions for this specific exam
            const res = await fetch(`/api/lexify_questions?exam=${examId}`);
            if (!res.ok) throw new Error(`API error ${res.status}`);
            const data = await res.json();
            const qs = data.questions || [];

            if (qs.length === 0) {
                setFetchError('No questions found for this exam. Please run the sub-topic classifier first.');
                setExamState(0);
                return;
            }

            setActiveQuestions(qs);
            setExamLabel(data.exam_label || '');
            setCurrentIndex(0);
            setFlaggedQuestions(new Set());

            if (prefillAnswers) {
                const initialAnswers = {};
                qs.forEach((q, i) => {
                    initialAnswers[i] = q.suggested_answer || q.answer || '';
                });
                setUserAnswers(initialAnswers);
            } else {
                setUserAnswers({});
            }

        } catch (e) {
            setFetchError(`Failed to load questions: ${e.message}`);
            setExamState(0);
            return;
        }

        setExamState(1); // Lockdown

        // Request fullscreen
        const elem = document.documentElement;
        if (elem.requestFullscreen) {
            elem.requestFullscreen().catch(() => {});
        }
        setTimeout(() => {
            setExamState(2);
            setExamStartTime(Date.now());
        }, 2500);
    };

    const handleSubmit = async () => {
        const plainTextOf = (html) => html?.replace(/<[^>]*>?/gm, '').trim() || '';
        const unanswered = activeQuestions.filter((_, i) => !plainTextOf(userAnswers[i])).length;

        if (unanswered > 0) {
            const proceed = window.confirm(`You have ${unanswered} unanswered question(s). Are you sure you want to submit?`);
            if (!proceed) return;
        }

        setShowDisclaimer(true); // Open custom disclaimer modal
    };

    const handleProceedSubmit = () => {
        setShowDisclaimer(false);

        if (examStartTime) {
            setTimeUsed(Math.floor((Date.now() - examStartTime) / 1000));
        }

        if (document.fullscreenElement) {
            document.exitFullscreen().catch(() => {});
        }

        setExamState(3); // Green success screen

        // After showing green screen, start grading
        setTimeout(() => {
            setExamState(5); // Grading...
            runGrading();
        }, 3000);
    };

    const runGrading = async () => {
        setGradingError('');
        try {
            // Grade each question individually and collect results
            const results = await Promise.all(
                activeQuestions.map(async (q, i) => {
                    const answer = userAnswers[i] || '';
                    if (!answer.replace(/<[^>]*>?/gm, '').trim()) {
                        return null; // skipped / no answer
                    }
                    try {
                        const res = await fetch('/api/lexify_grade', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                answer: answer.replace(/<[^>]*>?/gm, ''),
                                suggested_answer: q.answer || q.suggested_answer || '',
                                subject: q.subject || '',
                                question_text: q.text || ''
                            })
                        });
                        if (!res.ok) {
                            const errData = await res.json().catch(() => ({}));
                            setGradingError(errData.error || errData.detail || `Grading failed (Status ${res.status})`);
                            return null;
                        }
                        return await res.json();
                    } catch (e) {
                        return null;
                    }
                })
            );

            // Check if all are null (everything failed)
            if (results.every(r => r === null) && !gradingError) {
                setGradingError('All grading requests failed. Please check your AI API key configurations.');
            }

            setGradingResults(results);
            setExamState(6); // Results

            // Save to Attempt History (localStorage)
            try {
                const stored = localStorage.getItem('lexify_attempts');
                const attempts = stored ? JSON.parse(stored) : { current: 1, history: {} };
                const curr = attempts.current || 1;
                
                if (!attempts.history[curr]) attempts.history[curr] = {};

                const validResults = results.filter(Boolean);
                const totalScore = validResults.reduce((acc, r) => acc + (r?.score || 0), 0);
                const maxPossible = activeQuestions.length * 5;
                const rawScorePct = maxPossible > 0 ? (totalScore / maxPossible) * 100 : 0;
                
                const examIdKey = activeQuestions[0]?.exam_id || "unknown";

                attempts.history[curr][examIdKey] = {
                    score: rawScorePct.toFixed(1),
                    date: new Date().toLocaleDateString(),
                    answered: validResults.length,
                    total: activeQuestions.length
                };

                localStorage.setItem('lexify_attempts', JSON.stringify(attempts));
            } catch (e) {
                console.error("Failed to save attempt to localStorage", e);
            }

        } catch (e) {
            setGradingError('Grading failed. Please try again.');
            setExamState(6);
        }
    };

    const handleExit = useCallback(() => {
        const confirm = window.confirm('Are you sure you want to exit? All unsubmitted progress will be lost.');
        if (confirm) {
            if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
            onClose();
        }
    }, [onClose]);

    const handleReturnToDashboard = () => {
        setExamState(0);
        setCurrentIndex(0);
        setUserAnswers({});
        setFlaggedQuestions(new Set());
        setGradingResults([]);
        setNotesOpen(false);
        setSpellCheck(false);
    };

    // ——— SCREENS ———

    // State -1: Fetching Questions
    if (examState === -1) {
        return (
            <div className="fixed inset-0 z-[100] bg-[#0d1117] text-white flex flex-col items-center justify-center p-8">
                <div className="text-center">
                    <div className="w-16 h-16 border-4 border-white/10 border-t-[#e94560] rounded-full animate-spin mx-auto mb-6" />
                    <h2 className="text-xl font-bold mb-2">Loading Exam Questions...</h2>
                    <p className="text-white/40 text-sm">Fetching weighted question set from the database</p>
                    {fetchError && (
                        <div className="mt-6 bg-red-500/10 border border-red-500/20 rounded-xl px-5 py-3 text-red-400 text-sm max-w-sm">
                            {fetchError}
                            <button onClick={() => setExamState(0)} className="block mt-3 text-xs underline text-red-300">← Back to Dashboard</button>
                        </div>
                    )}
                </div>
            </div>
        );
    }

    // State 0: Dashboard
    if (examState === 0) {
        return <LexifyDashboard onBeginExam={handleBeginExam} onClose={onClose} fetchError={fetchError} />;
    }

    // State 1: Orange Lockdown Screen
    if (examState === 1) {
        return (
            <div className="fixed inset-0 z-[100] bg-[#f97316] text-white flex flex-col items-center justify-center p-8 font-sans">
                <div className="text-center">
                    <div className="w-20 h-20 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-6 animate-pulse">
                        <span className="text-4xl">🔒</span>
                    </div>
                    <h1 className="text-4xl font-extrabold mb-3 tracking-tight">SECURE MODE ENABLED</h1>
                    <p className="text-xl text-white/80 mb-2">Enforcing Lockdown...</p>
                    <p className="text-base text-white/60">Closing background apps and securing testing environment.</p>
                    <div className="mt-8 flex gap-2 justify-center">
                        {[0, 1, 2].map(i => (
                            <span key={i} className="w-3 h-3 rounded-full bg-white/60 animate-bounce" style={{ animationDelay: `${i * 0.2}s` }} />
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    // State 3: Green Upload Success
    if (examState === 3) {
        return (
            <div className="fixed inset-0 z-[100] bg-[#16a34a] text-white flex flex-col items-center justify-center p-8">
                <div className="text-center">
                    <div className="w-24 h-24 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-6">
                        <svg className="w-14 h-14 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                    </div>
                    <h1 className="text-5xl font-extrabold mb-3">UPLOAD COMPLETE</h1>
                    <p className="text-xl text-white/80 mb-2">Your exam has been submitted successfully.</p>
                    <p className="text-base text-white/60">Please show this screen to your proctor before leaving your seat.</p>
                    <div className="mt-8 text-white/40 text-sm">Processing AI grading...</div>
                </div>
            </div>
        );
    }

    // State 4: Exam Hidden
    if (examState === 4) {
        return (
            <div className="fixed inset-0 z-[100] bg-[#0f172a] text-white flex flex-col items-center justify-center p-8">
                <div className="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-6">
                    <span className="text-4xl">👁️‍🗨️</span>
                </div>
                <h1 className="text-4xl font-bold mb-3">EXAM HIDDEN</h1>
                <p className="text-white/50 mb-8">Your exam is paused and hidden from view.</p>
                <button
                    onClick={() => setExamState(2)}
                    className="px-8 py-3 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-xl transition shadow-lg active:scale-95"
                >
                    Resume Exam →
                </button>
            </div>
        );
    }

    // State 5: Grading in Progress
    if (examState === 5) {
        return (
            <div className="fixed inset-0 z-[100] bg-[#0a0a1a] text-white flex flex-col items-center justify-center p-8">
                <div className="text-center">
                    <div className="w-20 h-20 mx-auto mb-6 relative">
                        <div className="w-20 h-20 border-4 border-white/10 rounded-full" />
                        <div className="w-20 h-20 border-4 border-t-[#e94560] rounded-full animate-spin absolute top-0 left-0" />
                    </div>
                    <h1 className="text-3xl font-bold mb-3">AI Grading in Progress</h1>
                    <p className="text-white/50 mb-2">Analyzing your answers using Gemini AI...</p>
                    <p className="text-white/30 text-sm">This may take up to a minute depending on the number of questions.</p>
                    {gradingError && <p className="text-red-400 mt-4 text-sm">{gradingError}</p>}
                </div>
            </div>
        );
    }

    // State 6: Results
    if (examState === 6) {
        return (
            <LexifyResults
                results={gradingResults}
                questions={activeQuestions}
                totalTime={timeUsed}
                onReturnToDashboard={handleReturnToDashboard}
                examLabel={examLabel}
                error={gradingError}
            />
        );
    }

    // State 2: Active Exam
    return (
        <div className="fixed inset-0 z-[100] bg-[#f5f5f5] text-black flex flex-col overflow-hidden" style={{ fontFamily: '"Times New Roman", Times, serif' }}>
            {/* Top Bar */}
            <LexifyControls
                onSubmit={handleSubmit}
                onHide={() => setExamState(4)}
                onExit={handleExit}
                onToggleNotes={() => setNotesOpen(prev => !prev)}
                notesOpen={notesOpen}
                onToggleCalculator={() => setCalculatorOpen(prev => !prev)}
                calculatorOpen={calculatorOpen}
                answeredCount={Object.values(userAnswers).filter(a => a?.replace(/<[^>]*>?/gm, '').trim()).length}
                totalCount={activeQuestions.length}
                spellCheck={spellCheck}
                onToggleSpellCheck={() => setSpellCheck(prev => !prev)}
                alarmTime={alarmTime}
                setAlarmTime={setAlarmTime}
                examLabel={examLabel}
            />

            {/* Main 3-Pane Layout */}
            <div className="flex flex-1 overflow-hidden mt-12">
                {/* Left Sidebar */}
                <LexifySidebar
                    questions={activeQuestions}
                    currentIndex={currentIndex}
                    setCurrentIndex={setCurrentIndex}
                    userAnswers={userAnswers}
                    flaggedQuestions={flaggedQuestions}
                    setFlaggedQuestions={setFlaggedQuestions}
                />

                {/* Main Workspace */}
                <LexifyWorkspace
                    question={activeQuestions[currentIndex]}
                    currentIndex={currentIndex}
                    totalQuestions={activeQuestions.length}
                    userAnswer={userAnswers[currentIndex] || ""}
                    setUserAnswer={(val) => setUserAnswers({ ...userAnswers, [currentIndex]: val })}
                    onPrev={() => setCurrentIndex(prev => Math.max(0, prev - 1))}
                    onNext={() => setCurrentIndex(prev => Math.min(activeQuestions.length - 1, prev + 1))}
                    spellCheck={spellCheck}
                    isFlagged={flaggedQuestions.has(currentIndex)}
                    onToggleFlag={() => {
                        const newFlags = new Set(flaggedQuestions);
                        if (newFlags.has(currentIndex)) newFlags.delete(currentIndex);
                        else newFlags.add(currentIndex);
                        setFlaggedQuestions(newFlags);
                    }}
                />
            </div>

            {/* Floating Overlays */}
            {notesOpen && <LexifyNotes onClose={() => setNotesOpen(false)} />}

            {showDisclaimer && (
                <div className="fixed inset-0 z-[300] bg-black/80 flex items-center justify-center p-4 backdrop-blur-sm">
                    <div className="bg-[#161b22] border border-white/10 rounded-2xl w-full max-w-lg p-6 shadow-2xl font-sans">
                        <div className="text-center mb-5">
                            <div className="w-12 h-12 bg-amber-500/10 rounded-full flex items-center justify-center mx-auto mb-3 text-xl">⚠️</div>
                            <h3 className="text-lg font-bold font-serif text-white">LEGAL DISCLAIMER & AI NOTICE</h3>
                            <p className="text-white/40 text-xs mt-1">Please read and acknowledge before submitting your exam:</p>
                        </div>

                        <div className="space-y-3 text-xs text-white/70 leading-relaxed max-h-80 overflow-y-auto pr-2">
                            <div className="bg-white/5 p-3 rounded-xl border border-white/5">
                                <p className="font-bold text-amber-400 mb-1">1. Artificial Intelligence Evaluation</p>
                                <p>Your answers are graded by **Google Gemini AI** comparing against suggested answer guidelines. It evaluates structural and content precision. Scores do not take into account subjective interpretation differences.</p>
                            </div>
                            <div className="bg-white/5 p-3 rounded-xl border border-white/5">
                                <p className="font-bold text-amber-400 mb-1">2. Simulation Purposes Only</p>
                                <p>This software is built **strictly for self-assessment and mock-simulation purposes**. It is not affiliated with, endorsed by, or representative of the Supreme Court of the Philippines or any official Board of Bar Examiners.</p>
                            </div>
                            <div className="bg-white/5 p-3 rounded-xl border border-white/5">
                                <p className="font-bold text-amber-400 mb-1">3. No Guarantee of Results</p>
                                <p>Scores do not guarantee passing OR failing the actual Bar Exam. High scores don't guarantee success, and **low scores should not discourage you**; AI grading has variance and is designed strictly to augment, not define, your review diagnostics.</p>
                            </div>
                        </div>

                        <div className="flex gap-3 mt-6">
                            <button onClick={() => setShowDisclaimer(false)} className="flex-1 py-2 border border-white/10 rounded-xl text-sm text-white/40 hover:text-white transition">Cancel</button>
                            <button onClick={handleProceedSubmit} className="flex-1 py-2 bg-[#e94560] hover:bg-[#c73652] text-white font-bold rounded-xl text-sm transition">I Understand & Submit</button>
                        </div>
                    </div>
                </div>
            )}
            {calculatorOpen && <LexifyCalculator onClose={() => setCalculatorOpen(false)} />}
        </div>
    );
};

export default LexifyApp;
