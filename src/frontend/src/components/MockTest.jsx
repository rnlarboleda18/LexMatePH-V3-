import React, { useState, useEffect } from 'react';
import { ChevronRight, CheckCircle, XCircle, Clock, AlertTriangle, HelpCircle, Info } from 'lucide-react';
import { getSubjectColor } from '../utils/colors';

const MockTest = ({ questions, onFinish, userInfo }) => {
    const [testState, setTestState] = useState('setup'); // 'setup', 'taking', 'review'
    const [testQuestions, setTestQuestions] = useState([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [userAnswers, setUserAnswers] = useState({});
    const [timeLeft, setTimeLeft] = useState(0); // in seconds
    const [currentSlot, setCurrentSlot] = useState(null);
    const [showGradingInfo, setShowGradingInfo] = useState(false);

    // --- Grading Logic ---
    const [gradingResults, setGradingResults] = useState({});
    const [isGrading, setIsGrading] = useState(false);

    const gradeAnswers = async () => {
        setIsGrading(true);
        const results = {};

        for (const q of testQuestions) {
            const answer = userAnswers[q.id];
            if (!answer) continue;

            try {
                const response = await fetch('/api/grade_essay', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        question: q.text,
                        answer: answer,
                        suggested_answer: q.answer,
                        question_id: q.id,
                        subject: q.subject,
                        user_id: userInfo ? userInfo.userId : 'anonymous'
                    })
                });

                if (response.ok) {
                    const data = await response.json();
                    results[q.id] = data;
                }
            } catch (error) {
                console.error("Grading failed for", q.id, error);
            }
        }
        setGradingResults(results);
        setIsGrading(false);
    };

    // Trigger grading when entering review state
    React.useEffect(() => {
        if (testState === 'review') {
            gradeAnswers();
        }
    }, [testState]);

    // Timer Logic
    useEffect(() => {
        let timer;
        if (testState === 'taking' && timeLeft > 0) {
            timer = setInterval(() => {
                setTimeLeft((prev) => {
                    if (prev <= 1) {
                        clearInterval(timer);
                        setTestState('review');
                        return 0;
                    }
                    return prev - 1;
                });
            }, 1000);
        }
        return () => clearInterval(timer);
    }, [testState, timeLeft]);

    const formatTime = (seconds) => {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    };

    // Helper to get random questions
    const getRandomQuestions = (pool, count) => {
        const shuffled = [...pool].sort(() => 0.5 - Math.random());
        return shuffled.slice(0, count);
    };

    // 2025 Bar Exam Configuration
    const examSlots = [
        {
            id: 'day1_am',
            title: "Political & Public Int'l Law",
            subjects: ["Political Law"], // Assuming "Political Law" covers Public Int'l Law in our data
            weight: "15%",
            questions: 20,
            duration: 4 * 60 * 60 // 4 hours
        },
        {
            id: 'day1_pm',
            title: "Commercial & Taxation Laws",
            subjects: ["Commercial Law", "Taxation Law"],
            weight: "20%",
            questions: 20,
            distribution: { "Commercial Law": 12, "Taxation Law": 8 },
            duration: 4 * 60 * 60
        },
        {
            id: 'day2_am',
            title: "Civil Law",
            subjects: ["Civil Law"],
            weight: "20%",
            questions: 20,
            duration: 4 * 60 * 60
        },
        {
            id: 'day2_pm',
            title: "Labor Law & Social Legislation",
            subjects: ["Labor Law"],
            weight: "10%",
            questions: 20,
            duration: 4 * 60 * 60
        },
        {
            id: 'day3_am',
            title: "Criminal Law",
            subjects: ["Criminal Law"],
            weight: "10%",
            questions: 20,
            duration: 4 * 60 * 60
        },
        {
            id: 'day3_pm',
            title: "Remedial Law & Legal Ethics",
            subjects: ["Remedial Law", "Legal Ethics"],
            weight: "25%",
            questions: 20,
            distribution: { "Remedial Law": 16, "Legal Ethics": 4 },
            duration: 4 * 60 * 60
        }
    ];

    const handleStartExamSlot = (slot) => {
        let selectedQuestions = [];

        if (slot.distribution) {
            // Handle specific distribution (e.g. Comm/Tax)
            Object.entries(slot.distribution).forEach(([subj, count]) => {
                const pool = questions.filter(q => q.subject === subj);
                if (pool.length < count) {
                    console.warn(`Not enough questions for ${subj}. Requested ${count}, found ${pool.length}`);
                    selectedQuestions = [...selectedQuestions, ...pool];
                } else {
                    selectedQuestions = [...selectedQuestions, ...getRandomQuestions(pool, count)];
                }
            });
        } else {
            // Handle standard pool (single or multiple subjects mixed)
            const pool = questions.filter(q => slot.subjects.includes(q.subject));
            if (pool.length < slot.questions) {
                console.warn(`Not enough questions for ${slot.title}. Requested ${slot.questions}, found ${pool.length}`);
                selectedQuestions = [...pool];
            } else {
                selectedQuestions = getRandomQuestions(pool, slot.questions);
            }
        }

        if (selectedQuestions.length === 0) {
            alert(`No questions found for ${slot.title}.`);
            return;
        }

        // Shuffle the final set so subjects are mixed if needed (though usually grouped in real bar)
        // User said: "Questions 1–12 (approx): Commercial Law... Questions 13–20 (approx): Taxation Law"
        // So we should NOT shuffle if it's the Comm/Tax slot.
        if (!slot.distribution) {
            selectedQuestions.sort(() => 0.5 - Math.random());
        }

        setTestQuestions(selectedQuestions);
        setCurrentSlot(slot);
        setTimeLeft(slot.duration);
        setTestState('taking');
        setCurrentIndex(0);
        setUserAnswers({});
    };

    const currentQuestion = testQuestions[currentIndex];
    const total = testQuestions.length;

    // Safety check
    if (testState === 'taking' && !currentQuestion) {
        return (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                <div className="bg-white dark:bg-dark-card p-8 rounded-xl shadow-xl text-center">
                    <h3 className="text-xl font-bold text-red-600 mb-2">Error Loading Question</h3>
                    <p className="text-gray-600 dark:text-gray-400 mb-4">
                        Unable to load the current question. Please try again.
                    </p>
                    <button
                        onClick={onFinish}
                        className="px-6 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                    >
                        Close
                    </button>
                </div>
            </div>
        );
    }

    const handleAnswerChange = (e) => {
        setUserAnswers({
            ...userAnswers,
            [currentQuestion.id]: e.target.value
        });
    };

    const handleNext = () => {
        if (currentIndex < total - 1) {
            setCurrentIndex(currentIndex + 1);
        } else {
            setTestState('review');
        }
    };

    // --- GRADING INFO MODAL ---
    const GradingInfoModal = () => (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white dark:bg-dark-card rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto animate-in zoom-in-95 duration-200">
                <div className="p-6 border-b border-gray-100 dark:border-gray-800 flex justify-between items-center">
                    <h3 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                        <Info className="text-blue-600" />
                        How You Are Graded
                    </h3>
                    <button onClick={() => setShowGradingInfo(false)} className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
                        <XCircle size={24} />
                    </button>
                </div>
                <div className="p-6 space-y-6 text-gray-700 dark:text-gray-300">
                    <section>
                        <h4 className="font-bold text-lg mb-2 text-gray-900 dark:text-white">1. The 0-5 Point Scale</h4>
                        <p className="mb-4 text-sm">
                            Each essay answer is graded individually on a quality scale, mimicking the actual examiner's rubric:
                        </p>
                        <ul className="space-y-2 text-sm">
                            <li className="flex gap-3"><span className="font-bold text-green-600 w-12 shrink-0">5 pts</span> <span>Excellent: Correct conclusion + Correct legal basis + Polished delivery.</span></li>
                            <li className="flex gap-3"><span className="font-bold text-green-500 w-12 shrink-0">4 pts</span> <span>Very Good: Correct conclusion + Correct legal basis + Minor flaws.</span></li>
                            <li className="flex gap-3"><span className="font-bold text-yellow-600 w-12 shrink-0">3 pts</span> <span>Good/Fair: Correct conclusion + Incorrect/Inapplicable basis (or vice versa).</span></li>
                            <li className="flex gap-3"><span className="font-bold text-orange-500 w-12 shrink-0">2 pts</span> <span>Needs Improvement: Incorrect conclusion + Good legal reasoning (credit for effort).</span></li>
                            <li className="flex gap-3"><span className="font-bold text-red-500 w-12 shrink-0">1 pt</span> <span>Poor: Incorrect conclusion + Poor reasoning.</span></li>
                            <li className="flex gap-3"><span className="font-bold text-gray-500 w-12 shrink-0">0 pts</span> <span>No answer or completely unresponsive.</span></li>
                        </ul>
                    </section>

                    <section>
                        <h4 className="font-bold text-lg mb-2 text-gray-900 dark:text-white">2. Subject Grade Calculation</h4>
                        <p className="text-sm mb-2">
                            Your <strong>Raw Score</strong> is the sum of all points earned in the exam slot.
                        </p>
                        <div className="bg-gray-100 dark:bg-gray-800 p-3 rounded-lg text-sm font-mono mb-2">
                            Subject Grade % = (Total Points Earned / Max Possible Points) × 100
                        </div>
                        <p className="text-xs text-gray-500">
                            *Max Possible Points = 20 Questions × 5 Points = 100 Points.
                        </p>
                    </section>

                    <section>
                        <h4 className="font-bold text-lg mb-2 text-gray-900 dark:text-white">3. Bar Weight Contribution</h4>
                        <p className="text-sm mb-2">
                            Your final contribution to the Bar Exam is your Subject Grade multiplied by the subject's weight.
                        </p>
                        <div className="grid grid-cols-2 gap-4 text-xs mt-2">
                            <div>• Political Law: 15%</div>
                            <div>• Commercial & Tax: 20%</div>
                            <div>• Civil Law: 20%</div>
                            <div>• Labor Law: 10%</div>
                            <div>• Criminal Law: 10%</div>
                            <div>• Remedial & Ethics: 25%</div>
                        </div>
                    </section>

                    <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 flex gap-3 items-start">
                        <AlertTriangle className="text-yellow-600 dark:text-yellow-500 shrink-0 mt-0.5" size={20} />
                        <div className="text-sm text-yellow-800 dark:text-yellow-200">
                            <strong>AI Grading Disclaimer:</strong> This grading is performed by an Artificial Intelligence model designed to simulate a strict Bar Examiner, following the official grading system of the Supreme Court of the Philippines per <strong>Bar Bulletin No. 1 (Series of 2024)</strong>. While it follows the official rubric, it may not perfectly capture the nuances of human grading. Use these scores as a guidance tool for your review, not as a definitive prediction of your actual Bar Exam performance.
                        </div>
                    </div>
                </div>
                <div className="p-6 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50 text-center">
                    <button onClick={() => setShowGradingInfo(false)} className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                        Got it
                    </button>
                </div>
            </div>
        </div>
    );

    // --- SETUP VIEW ---
    if (testState === 'setup') {
        return (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
                <div className="bg-white dark:bg-dark-card rounded-2xl shadow-2xl w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col animate-in zoom-in-95 duration-200">

                    {/* Header */}
                    <div className="p-8 border-b border-gray-100 dark:border-gray-800 text-center relative">
                        <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                            2025 Philippine Bar Exam Simulation
                        </h2>
                        <p className="text-gray-500 dark:text-gray-400">
                            Select an exam slot to begin. Each slot is 4 hours with 20 questions.
                        </p>
                        <button
                            onClick={() => setShowGradingInfo(true)}
                            className="absolute top-8 right-8 text-blue-600 hover:text-blue-700 flex items-center gap-1 text-sm font-semibold"
                        >
                            <HelpCircle size={18} />
                            How grading works
                        </button>
                    </div>

                    {/* Content - Grid of Options */}
                    <div className="flex-1 overflow-y-auto p-8">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {examSlots.map(slot => {
                                const mainSubject = slot.subjects[0];
                                const colorClass = getSubjectColor(mainSubject);
                                const borderColor = colorClass.split(' ').find(c => c.startsWith('border-'));
                                const textColor = colorClass.split(' ').find(c => c.startsWith('text-'));

                                return (
                                    <button
                                        key={slot.id}
                                        onClick={() => handleStartExamSlot(slot)}
                                        className={`group p-6 rounded-xl border-2 ${borderColor} bg-white dark:bg-gray-800/50 hover:brightness-105 transition-all text-left flex flex-col gap-3 shadow-sm hover:shadow-md relative overflow-hidden`}
                                    >
                                        <div className={`absolute top-0 right-0 p-2 opacity-10 group-hover:opacity-20 transition-opacity`}>
                                            <Clock size={48} />
                                        </div>

                                        <div className="flex justify-between items-start">
                                            <span className="text-xs font-bold uppercase tracking-wider text-gray-400">
                                                {slot.weight} Weight
                                            </span>
                                            <span className="text-xs font-bold uppercase tracking-wider text-gray-400">
                                                4 Hours
                                            </span>
                                        </div>

                                        <h3 className={`text-lg font-bold ${textColor} leading-tight`}>
                                            {slot.title}
                                        </h3>

                                        <div className="mt-auto pt-2 border-t border-gray-100 dark:border-gray-700/50">
                                            <span className="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-2">
                                                <span className="w-2 h-2 rounded-full bg-gray-400"></span>
                                                {slot.questions} Questions
                                            </span>
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* Footer */}
                    <div className="p-6 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50 flex justify-center">
                        <button
                            onClick={onFinish}
                            className="px-6 py-2 rounded-lg bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium transition-colors shadow-sm"
                        >
                            Cancel
                        </button>
                    </div>
                </div>
                {showGradingInfo && <GradingInfoModal />}
            </div>
        );
    }

    // --- REVIEW VIEW ---

    if (testState === 'review') {
        // Calculate Scores
        const totalQuestions = testQuestions.length;
        let totalRawScore = 0;
        let gradedCount = 0;

        testQuestions.forEach(q => {
            const result = gradingResults[q.id];
            if (result && result.score !== undefined) {
                totalRawScore += result.score;
                gradedCount++;
            }
        });

        // Slot Score (0-100%)
        // Logic: Raw Score (Sum of 0-5s) / Max Possible Score (Questions * 5) * 100
        const maxPossibleScore = totalQuestions * 5;
        const slotScore = maxPossibleScore > 0 ? (totalRawScore / maxPossibleScore) * 100 : 0;

        // Weighted Score
        const weightPercent = currentSlot ? parseFloat(currentSlot.weight) : 0;
        const weightedContribution = (slotScore * weightPercent) / 100;

        return (
            <div className="max-w-4xl mx-auto space-y-8 pb-20 pt-12 px-6">
                <div className="text-center space-y-4">
                    <h2 className="text-3xl font-bold text-gray-900 dark:text-white">Exam Completed</h2>
                    <p className="text-gray-600 dark:text-gray-400">
                        {isGrading ? "AI is grading your answers..." : "Review your AI-graded results below."}
                    </p>

                    {!isGrading && currentSlot && (
                        <div className="bg-blue-50 dark:bg-blue-900/20 p-6 rounded-2xl inline-block mx-auto border border-blue-100 dark:border-blue-800">
                            <div className="grid grid-cols-2 gap-8 text-left">
                                <div>
                                    <p className="text-sm font-bold text-gray-500 uppercase tracking-wider">Subject Grade</p>
                                    <p className="text-4xl font-bold text-blue-600 dark:text-blue-400">
                                        {slotScore.toFixed(2)}%
                                    </p>
                                    <p className="text-xs text-gray-400 mt-1">
                                        (Raw Score: {totalRawScore}/{maxPossibleScore})
                                    </p>
                                </div>
                                <div>
                                    <p className="text-sm font-bold text-gray-500 uppercase tracking-wider">Bar Weight Contribution</p>
                                    <p className="text-4xl font-bold text-green-600 dark:text-green-400">
                                        {weightedContribution.toFixed(2)}%
                                    </p>
                                    <p className="text-xs text-gray-400 mt-1">
                                        (Out of {currentSlot.weight} Total)
                                    </p>
                                </div>
                            </div>
                            <div className="mt-4 text-center">
                                <button
                                    onClick={() => setShowGradingInfo(true)}
                                    className="text-blue-600 hover:text-blue-700 text-sm font-semibold flex items-center justify-center gap-1 mx-auto"
                                >
                                    <HelpCircle size={14} />
                                    Explain this score
                                </button>
                            </div>
                        </div>
                    )}

                    {!isGrading && (
                        <div className="mt-6">
                            <button
                                onClick={onFinish}
                                className="px-8 py-3 rounded-full bg-blue-600 text-white font-semibold hover:bg-blue-700 transition-colors"
                            >
                                Return to Browse
                            </button>
                        </div>
                    )}
                </div>

                {isGrading && (
                    <div className="flex justify-center py-12">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                    </div>
                )}

                {!isGrading && (
                    <div className="space-y-8">
                        {testQuestions.map((q, index) => {
                            const colorClass = getSubjectColor(q.subject);
                            const textColor = colorClass.split(' ').find(c => c.startsWith('text-'));
                            const result = gradingResults[q.id];
                            const score = result?.score || 0;
                            // Pass is 3/5 (60%) or 4/5 (80%)? 75% is pass, so 3.75. 
                            // Let's say 4 is pass for visual green, 3 is fair.
                            const isPass = score >= 4;

                            return (
                                <div key={q.id} className="bg-white dark:bg-dark-card rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
                                    <div className="p-6 border-b border-gray-100 dark:border-gray-800">
                                        <div className="flex justify-between items-center mb-4">
                                            <span className={`text-sm font-bold uppercase tracking-wider ${textColor}`}>{q.subject}</span>
                                            <div className="flex items-center gap-3">
                                                <span className="text-sm text-gray-500">Question {index + 1}</span>
                                                {result && (
                                                    <span className={`px-3 py-1 rounded-full text-sm font-bold ${score >= 4 ? 'bg-green-100 text-green-700' : score >= 3 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}`}>
                                                        {score}/5 PTS
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                        <p className="text-gray-800 dark:text-gray-200">{q.text}</p>
                                    </div>

                                    {/* AI Feedback Section */}
                                    {result && (
                                        <div className="p-6 bg-blue-50 dark:bg-blue-900/10 border-b border-blue-100 dark:border-blue-900/20">
                                            <h4 className="text-sm font-bold text-blue-700 dark:text-blue-400 uppercase mb-2">AI Feedback</h4>
                                            <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{result.feedback}</p>
                                        </div>
                                    )}

                                    <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                                        <div>
                                            <h4 className="text-sm font-semibold text-gray-500 uppercase mb-2">Your Answer</h4>
                                            <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg min-h-[100px] text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                                                {userAnswers[q.id] || <span className="text-gray-400 italic">No answer provided</span>}
                                            </div>
                                        </div>
                                        <div>
                                            <h4 className={`text-sm font-semibold uppercase mb-2 ${textColor}`}>Suggested Answer</h4>
                                            <div className="p-4 rounded-lg min-h-[100px] text-gray-700 dark:text-gray-300 whitespace-pre-wrap bg-gray-50 dark:bg-gray-800/50">
                                                {q.answer}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
                {showGradingInfo && <GradingInfoModal />}
            </div>
        );
    }

    const colorClass = getSubjectColor(currentQuestion.subject);
    const textColor = colorClass.split(' ').find(c => c.startsWith('text-'));

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white dark:bg-dark-card rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col animate-in zoom-in-95 duration-200 border-2 border-transparent">

                {/* Header */}
                <div className="p-6 border-b border-gray-100 dark:border-gray-800 flex justify-between items-start shrink-0">
                    <div>
                        <span className={`inline-block mb-2 text-sm font-bold uppercase tracking-wider ${textColor}`}>
                            {currentQuestion.subject}
                        </span>
                        <div className="flex items-center gap-3">
                            <h3 className="text-xl font-bold text-gray-900 dark:text-white">
                                {currentQuestion.year} Bar Exam Question {currentQuestion.source_label && `(${currentQuestion.source_label})`}
                            </h3>
                            <span className="text-sm text-gray-500 dark:text-gray-400 font-medium px-2 py-0.5 bg-gray-100 dark:bg-gray-800 rounded-full">
                                {currentIndex + 1} / {total}
                            </span>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        {/* Timer Display */}
                        <div className={`flex items-center gap-2 px-4 py-2 rounded-lg font-mono font-bold ${timeLeft < 300 ? 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400' : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'}`}>
                            <Clock size={20} />
                            {formatTime(timeLeft)}
                        </div>

                        <button
                            onClick={onFinish}
                            className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 transition-colors"
                            title="Quit Exam"
                        >
                            <XCircle size={24} />
                        </button>
                    </div>
                </div>

                {/* Content - Scrollable */}
                <div className="flex-1 overflow-y-auto p-6 space-y-8">
                    {/* Question */}
                    <div>
                        <h4 className="text-sm font-semibold text-gray-500 uppercase mb-3">Question</h4>
                        <p className="text-lg leading-relaxed text-gray-800 dark:text-gray-100 whitespace-pre-wrap">
                            {currentQuestion.text}
                        </p>
                    </div>

                    {/* Answer Input */}
                    <div>
                        <label className="block text-sm font-semibold text-gray-500 uppercase mb-3">
                            Your Answer
                        </label>
                        <textarea
                            value={userAnswers[currentQuestion.id] || ''}
                            onChange={handleAnswerChange}
                            placeholder="Type your answer here..."
                            className="w-full p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none transition-shadow min-h-[150px]"
                        />
                    </div>
                </div>

                {/* Footer */}
                <div className="p-6 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50 flex justify-end shrink-0">
                    <button
                        onClick={handleNext}
                        className="flex items-center gap-2 px-8 py-2 rounded-lg bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium shadow-sm transition-all transform hover:scale-105"
                    >
                        {currentIndex === total - 1 ? 'Finish Test' : 'Next Question'}
                        <ChevronRight size={20} />
                    </button>
                </div>
            </div>
        </div>
    );
};

export default MockTest;
