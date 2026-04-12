import React, { useState, useEffect } from 'react';
import FeaturePageShell from '../../components/FeaturePageShell';

const PROCTOR_PASSWORD = 'LEXIFY2025';

const LexifyDashboard = ({ onBeginExam, onClose }) => {
    const [exams, setExams] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedExam, setSelectedExam] = useState(null);
    const [showPasswordModal, setShowPasswordModal] = useState(false);
    const [showPrefsModal, setShowPrefsModal] = useState(false);
    const [showDetailsModal, setShowDetailsModal] = useState(null); // Holds the exam object for the details modal
    const [password, setPassword] = useState('');
    const [passwordError, setPasswordError] = useState('');
    const [alarmTime, setAlarmTime] = useState('00:30:00');
    
    const EXAM_WEIGHTS = {
        'political-pil': 0.15,
        'commercial-tax': 0.20,
        'civil-land': 0.20,
        'labor-social': 0.10,
        'criminal': 0.10,
        'remedial-ethics': 0.25
    };

    const calculateGeneralAverage = (subjectMap) => {
        let score = 0;
        Object.entries(subjectMap || {}).forEach(([examId, data]) => {
            const weight = EXAM_WEIGHTS[examId] || 0;
            score += parseFloat(data.score) * weight;
        });
        return score;
    };
    const [showMenu, setShowMenu] = useState(false);
    const [showSampleSubmenu, setShowSampleSubmenu] = useState(false); // Holds Sample Q&A toggle status
    const [attempts, setAttempts] = useState({ current: 1, history: {} });
    const [activeTab, setActiveTab] = useState('exams'); // 'exams' | 'history'

    // Fallback if batch classifier hasn't run with 2026 Official Dates
    const getFallbackExams = () => [
        { id: 'political-pil',   label: 'Political and Public International Law',  day: 'Sept 6, 2026 (Sun AM)',   weight: '15%', total_questions: 20, available: 0, ready: false, breakdown: [{ sub_topic: 'Political Law', count: 17, available: 0 }, { sub_topic: 'Public International Law', count: 3, available: 0 }] },
        { id: 'commercial-tax',  label: 'Commercial and Taxation Laws',             day: 'Sept 6, 2026 (Sun PM)',   weight: '20%', total_questions: 20, available: 0, ready: false, breakdown: [{ sub_topic: 'Commercial Law', count: 15, available: 0 }, { sub_topic: 'Taxation', count: 5, available: 0 }] },
        { id: 'civil-land',      label: 'Civil Law and Land Titles and Deeds',      day: 'Sept 9, 2026 (Wed AM)',   weight: '20%', total_questions: 20, available: 0, ready: false, breakdown: [{ sub_topic: 'Civil Law', count: 16, available: 0 }, { sub_topic: 'Land Titles and Deeds', count: 4, available: 0 }] },
        { id: 'labor-social',    label: 'Labor Law and Social Legislation',         day: 'Sept 9, 2026 (Wed PM)',   weight: '10%', total_questions: 20, available: 0, ready: false, breakdown: [{ sub_topic: 'Labor Law', count: 16, available: 0 }, { sub_topic: 'Social Legislation', count: 4, available: 0 }] },
        { id: 'criminal',        label: 'Criminal Law',                             day: 'Sept 13, 2026 (Sun AM)',  weight: '10%', total_questions: 20, available: 0, ready: false, breakdown: [{ sub_topic: 'Criminal Law', count: 16, available: 0 }, { sub_topic: 'Special Penal Laws', count: 4, available: 0 }] },
        { id: 'remedial-ethics', label: 'Remedial Law, Legal and Judicial Ethics, with Practical Exercises', day: 'Sept 13, 2026 (Sun PM)', weight: '25%', total_questions: 20, available: 0, ready: false, breakdown: [{ sub_topic: 'Remedial Law', count: 14, available: 0 }, { sub_topic: 'Legal and Judicial Ethics', count: 4, available: 0 }, { sub_topic: 'Practical Exercises', count: 2, available: 0 }] },
    ];

    // Load attempt history from localStorage on mount
    useEffect(() => {
        try {
            const stored = localStorage.getItem('lexify_attempts');
            if (stored) setAttempts(JSON.parse(stored));
        } catch (e) {
            console.error("Failed to load attempt history", e);
        }
    }, []);

    const handleBeginClick = (exam) => {
        setSelectedExam(exam);
        setShowPasswordModal(true);
        setPassword('');
        setPasswordError('');
    };

    const handlePasswordSubmit = () => {
        if (password.toUpperCase() === PROCTOR_PASSWORD) {
            setShowPasswordModal(false);
            onBeginExam(selectedExam.id, alarmTime);
        } else {
            setPasswordError('Incorrect password. Please ask your proctor for the correct password.');
        }
    };

    // Fetch live exam list from API
    useEffect(() => {
        const fetchExams = async () => {
            try {
                const res = await fetch('/api/lexify_exams');
                if (res.ok) {
                    const data = await res.json();
                    setExams(data);
                } else {
                    setExams(getFallbackExams());
                }
            } catch {
                setExams(getFallbackExams());
            } finally {
                setLoading(false);
            }
        };
        fetchExams();
    }, []);

    const handleStartNewAttempt = () => {
        const proceed = window.confirm("Are you sure you want to start a new Mock Bar Attempt? This will reset all subjects to 'Ready' for the new attempt.");
        if (!proceed) return;

        const next = (attempts.current || 1) + 1;
        const updated = { current: next, history: { ...attempts.history, [next]: {} } };
        setAttempts(updated);
        localStorage.setItem('lexify_attempts', JSON.stringify(updated));
        setShowMenu(false);
        setActiveTab('exams');

        const roster = exams.length > 0 ? exams : getFallbackExams();
        const pick = roster.find((e) => e.ready) || roster[0];
        if (pick) {
            handleBeginClick(pick);
        } else {
            window.alert('No exams are available yet. Wait for the roster to load, then try again.');
        }
    };

    const DAY_COLORS = {
        'Sept 6, 2026 (Sun AM)':   'from-sky-50 to-blue-50/90 border-sky-200/70 dark:from-blue-950/40 dark:to-slate-900/60 dark:border-blue-500/25',
        'Sept 6, 2026 (Sun PM)':   'from-indigo-50 to-violet-50/90 border-indigo-200/70 dark:from-indigo-950/40 dark:to-slate-900/60 dark:border-indigo-500/25',
        'Sept 9, 2026 (Wed AM)':   'from-purple-50 to-fuchsia-50/80 border-purple-200/70 dark:from-purple-950/40 dark:to-slate-900/60 dark:border-purple-500/25',
        'Sept 9, 2026 (Wed PM)':   'from-fuchsia-50 to-pink-50/80 border-fuchsia-200/70 dark:from-fuchsia-950/35 dark:to-slate-900/60 dark:border-fuchsia-500/25',
        'Sept 13, 2026 (Sun AM)':  'from-rose-50 to-orange-50/80 border-rose-200/70 dark:from-rose-950/40 dark:to-slate-900/60 dark:border-rose-500/25',
        'Sept 13, 2026 (Sun PM)':  'from-amber-50 to-orange-50/80 border-amber-200/70 dark:from-orange-950/35 dark:to-slate-900/60 dark:border-orange-500/25',
    };

    const WEIGHT_COLOR = (w) =>
        w === '25%'
            ? 'text-amber-700 dark:text-amber-400'
            : parseInt(w, 10) >= 20
              ? 'text-emerald-700 dark:text-emerald-400'
              : 'text-indigo-700 dark:text-indigo-400';

    return (
        <FeaturePageShell>
            {/* Dashboard only: full-screen exam UI lives in LexifyApp (other exam states). */}
            <div className="flex flex-col overflow-hidden rounded-2xl border-2 border-slate-300/80 bg-white/45 font-sans text-gray-900 shadow-sm backdrop-blur-md dark:border-white/10 dark:bg-slate-900/35 dark:text-gray-100">
            <div className="flex h-12 shrink-0 select-none items-center justify-between border-b-2 border-slate-300/85 bg-white/50 px-4 sm:px-6 dark:border-white/10 dark:bg-slate-900/50">
                <div className="relative z-50 flex items-center gap-3">
                    <button type="button" onClick={() => setShowMenu(!showMenu)} className="flex flex-col gap-1 rounded-lg p-2 transition hover:bg-white/70 dark:hover:bg-white/10">
                        <span className="block h-0.5 w-5 bg-gray-600 dark:bg-white/70" /><span className="block h-0.5 w-5 bg-gray-600 dark:bg-white/70" /><span className="block h-0.5 w-5 bg-gray-600 dark:bg-white/70" />
                    </button>
                    {showMenu && (
                        <div className="absolute left-0 top-full z-50 mt-1 w-56 overflow-hidden rounded-xl border-2 border-slate-300/80 bg-white/95 py-2 shadow-xl backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/95">
                            <button onClick={() => { setShowPrefsModal(true); setShowMenu(false); }} className="w-full px-4 py-2.5 text-left text-sm text-gray-800 transition hover:bg-indigo-50 dark:text-gray-100 dark:hover:bg-white/10">⚙️ Preferences</button>
                            <button onClick={handleStartNewAttempt} className="w-full px-4 py-2.5 text-left text-sm text-emerald-700 transition hover:bg-emerald-50 dark:text-emerald-400 dark:hover:bg-white/10">✨ Start New Attempt</button>
                            
                            {/* Sample Q&A Toggle */}
                            <button 
                                onClick={(e) => { e.stopPropagation(); setShowSampleSubmenu(!showSampleSubmenu); }} 
                                className="flex w-full items-center justify-between px-4 py-2.5 text-left text-sm text-gray-800 transition hover:bg-indigo-50 dark:text-gray-100 dark:hover:bg-white/10"
                            >
                                <span>📚 Sample Q&A</span>
                                <span className={`text-[10px] text-gray-400 transition-transform dark:text-white/40 ${showSampleSubmenu ? 'rotate-180' : ''}`}>▼</span>
                            </button>

                            {showSampleSubmenu && (
                                <div className="max-h-48 overflow-y-auto border-y border-gray-100 bg-slate-50/50 py-1 dark:border-white/5 dark:bg-black/20">
                                    {[
                                        { id: 'political-pil',   short: 'Political & PIL' },
                                        { id: 'commercial-tax',  short: 'Commercial & Tax' },
                                        { id: 'civil-land',      short: 'Civil & Land Titles' },
                                        { id: 'labor-social',    short: 'Labor & Social Leg' },
                                        { id: 'criminal',        short: 'Criminal Law' },
                                        { id: 'remedial-ethics', short: 'Remedial & Ethics' }
                                    ].map(sub => (
                                        <button 
                                            key={sub.id}
                                            onClick={() => { onBeginExam(sub.id, alarmTime, true); setShowMenu(false); }}
                                            className="w-full truncate py-1.5 pl-7 pr-3 text-left text-xs text-gray-600 transition hover:bg-white hover:text-gray-900 dark:text-gray-300 dark:hover:bg-white/5 dark:hover:text-white"
                                        >
                                            • {sub.short}
                                        </button>
                                    ))}
                                </div>
                            )}

                            <hr className="my-1 border-gray-200 dark:border-white/10" />
                            <button onClick={onClose} className="w-full px-4 py-2.5 text-left text-sm text-rose-600 transition hover:bg-rose-50 dark:text-rose-400 dark:hover:bg-white/10">✕ Exit to LexMatePH</button>
                        </div>
                    )}
                    <span className="hidden text-xs font-semibold uppercase tracking-widest text-gray-500 dark:text-gray-400 sm:inline">Bar exam simulator</span>
                </div>
                <div className="flex items-center gap-3">
                    <span className="text-xs text-gray-500 dark:text-gray-400">2026 Philippine Bar</span>
                    <div className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
                </div>
            </div>
            <div className="mx-auto w-full max-w-5xl flex-1 overflow-y-auto px-4 py-4 sm:px-6">
                {/* Tabs Selection Navbar */}
                <div className="mb-6 flex select-none justify-center gap-6 border-b border-gray-200 dark:border-white/10">
                    <button 
                        onClick={() => setActiveTab('exams')} 
                        className={`px-4 pb-2 text-sm font-bold transition-all focus:outline-none ${activeTab === 'exams' ? 'border-b-2 border-indigo-600 text-indigo-700 dark:border-indigo-400 dark:text-indigo-300' : 'text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200'}`}
                    >
                        My Exams
                    </button>
                    <button 
                        onClick={() => setActiveTab('history')} 
                        className={`px-4 pb-2 text-sm font-bold transition-all focus:outline-none ${activeTab === 'history' ? 'border-b-2 border-indigo-600 text-indigo-700 dark:border-indigo-400 dark:text-indigo-300' : 'text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200'}`}
                    >
                        Attempts History
                    </button>
                </div>

                {activeTab === 'exams' ? (
                    <>
                        <div className="mb-6 text-center">
                            <div className="mb-2 inline-block rounded-xl border border-rose-200/80 bg-rose-50/90 px-5 py-1.5 dark:border-rose-500/30 dark:bg-rose-950/30">
                                <span className="text-xs font-bold uppercase tracking-widest text-rose-800 dark:text-rose-300">Simulated secure testing environment</span>
                            </div>
                            <h1 className="font-serif text-2xl font-bold text-gray-900 dark:text-white">My Exams</h1>
                            <p className="mt-0.5 text-sm text-gray-600 dark:text-gray-400">6 Core Bar Subjects · 20 Questions Each</p>
                            <p className="mt-2 text-xs font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400">Mock Bar Attempt No. {attempts.current}</p>
                        </div>

                        {/* Final Average Banner */}
                        {(() => {
                            const currentSubjectMap = attempts.history[attempts.current] || {};
                            const isComplete = Object.keys(currentSubjectMap).length === 6;
                            const finalAverage = calculateGeneralAverage(currentSubjectMap);
                            if (!isComplete) return null;

                            return (
                                <div className="mb-6 rounded-2xl border border-emerald-200/80 bg-gradient-to-r from-emerald-50 to-teal-50/80 p-5 text-center shadow-sm dark:border-emerald-500/25 dark:from-emerald-950/40 dark:to-slate-900/50">
                                    <h2 className="mb-1 font-serif text-sm font-bold uppercase tracking-wider text-gray-800 dark:text-gray-100">Consolidated Mock Bar Attempt Completed!</h2>
                                    <p className="text-3xl font-extrabold text-emerald-700 dark:text-emerald-400">{finalAverage.toFixed(2)}%</p>
                                    <p className="mt-1 text-xs uppercase tracking-wider text-gray-600 dark:text-gray-400">Final General Average</p>
                                    <div className="mt-3 inline-block rounded-full border border-emerald-200/60 bg-white/80 px-4 py-1.5 text-xs text-gray-800 dark:border-white/10 dark:bg-white/5 dark:text-gray-200">
                                         {finalAverage >= 75 ? '🟢 PASSED (#SuccessAchievedthroughMerit)' : '🔴 FAILED (Threshold is 75%)'}
                                    </div>
                                </div>
                            );
                        })()}

                        {loading ? (
                            <div className="py-20 text-center text-gray-500 dark:text-gray-400">Loading exam roster...</div>
                        ) : (
                            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                                {exams.map((exam) => {
                                    const dayColor = DAY_COLORS[exam.day] || 'from-slate-50 to-gray-50/90 border-gray-200/80 dark:from-slate-900/50 dark:to-slate-900/40 dark:border-white/10';
                                    const isTaken = attempts.history[attempts.current]?.[exam.id];

                                    return (
                                        <div key={exam.id} className={`flex flex-col justify-between overflow-hidden rounded-2xl border bg-gradient-to-br shadow-sm transition-transform duration-200 hover:-translate-y-0.5 hover:shadow-md ${dayColor}`}>
                                            {/* Card Header */}
                                            <div className="min-h-[85px] flex-1 p-5">
                                                <div className="mb-3 flex items-start justify-between gap-3">
                                                    <h3 className="font-serif text-base font-bold leading-snug text-gray-900 dark:text-gray-100">{exam.label}</h3>
                                                    <span className={`shrink-0 font-mono text-lg font-extrabold ${WEIGHT_COLOR(exam.weight)}`}>{exam.weight}</span>
                                                </div>
                                                <div className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
                                                    <span>📅 {exam.day}</span>
                                                    <span>·</span>
                                                    <span>📝 {exam.total_questions} Q's</span>
                                                </div>
                                            </div>

                                            {/* Action footer */}
                                            <div className="flex items-center justify-between border-t border-gray-200/80 bg-white/50 px-5 py-3.5 dark:border-white/10 dark:bg-black/20">
                                                <div className="flex items-center gap-2">
                                                    {isTaken ? (
                                                        <span className="rounded-full border border-emerald-300/80 bg-emerald-50 px-2 py-0.5 text-[11px] text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-950/40 dark:text-emerald-300">
                                                            ✅ Score: {isTaken.score}%
                                                        </span>
                                                    ) : (
                                                        <span className={`rounded-full border px-2 py-0.5 text-[11px] ${exam.ready ? 'border-emerald-300/80 bg-emerald-50 text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-950/40 dark:text-emerald-300' : 'border-amber-300/80 bg-amber-50 text-amber-900 dark:border-amber-500/30 dark:bg-amber-950/40 dark:text-amber-300'}`}>
                                                            {exam.ready ? '● Ready' : '⏳ Pending'}
                                                        </span>
                                                    )}
                                                    <button 
                                                        onClick={() => setShowDetailsModal(exam)}
                                                        className="text-xs font-bold text-sky-700 underline-offset-2 hover:underline dark:text-sky-400"
                                                    >
                                                        Details
                                                    </button>
                                                </div>
                                                <button
                                                    onClick={() => !isTaken && handleBeginClick(exam)}
                                                    disabled={isTaken}
                                                    className={`rounded-xl px-5 py-1.5 text-sm font-bold shadow-sm transition-all ${isTaken ? 'cursor-not-allowed border border-gray-200 bg-gray-100 text-gray-400 dark:border-white/10 dark:bg-white/5 dark:text-gray-500' : 'bg-amber-600 text-white hover:bg-amber-700 active:scale-95 dark:bg-amber-600 dark:hover:bg-amber-500'}`}
                                                >
                                                    {isTaken ? 'Already Taken' : 'Begin →'}
                                                </button>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}

                        {/* Legend */}
                        <div className="mt-6 flex flex-wrap justify-center gap-5 text-xs text-gray-500 dark:text-gray-400">
                            <span className="font-bold text-emerald-700 dark:text-emerald-400">● Ready</span> — questions available
                            <span className="font-bold text-amber-700 dark:text-amber-400">⏳ Pending</span> — classifier pending
                        </div>
                    </>
                ) : (
                    /* History Tab */
                    <div className="space-y-4">
                        <div className="mb-6 text-center">
                            <h1 className="font-serif text-2xl font-bold text-gray-900 dark:text-white">Attempts History</h1>
                            <p className="mt-0.5 text-sm text-gray-600 dark:text-gray-400">Past graded Mock Bar iterations</p>
                        </div>

                        {Object.keys(attempts.history || {}).length === 0 ? (
                            <div className="flex flex-col items-center gap-3 py-20 text-center text-gray-500 dark:text-gray-400">
                                <span className="text-3xl">🗓️</span>
                                <p>No completed attempts recorded yet.</p>
                                <p className="text-xs text-gray-400 dark:text-gray-500">Submit an exam session to start populating records.</p>
                            </div>
                        ) : (
                            Object.entries(attempts.history).reverse().map(([attemptNum, subjectMap]) => (
                                <div key={attemptNum} className="rounded-2xl border-2 border-slate-300/80 bg-white/50 p-5 shadow-sm dark:border-white/10 dark:bg-slate-800/40">
                                    <div className="mb-4 flex items-center justify-between border-b border-gray-200 pb-2 dark:border-white/10">
                                        <h3 className="text-base font-bold text-amber-800 dark:text-amber-400">Mock Bar Attempt No. {attemptNum}</h3>
                                        <span className="rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-[10px] text-gray-600 dark:border-white/10 dark:bg-white/5 dark:text-gray-400">
                                            {Object.keys(subjectMap).length} Subjects Completed
                                        </span>
                                    </div>
                                    <div className="space-y-2">
                                        {Object.entries(subjectMap).map(([examId, data]) => {
                                            const exam = exams.find(e => e.id === examId);
                                            const label = exam ? exam.label : examId.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                                            return (
                                                <div key={examId} className="flex items-center justify-between rounded-xl border border-gray-100 bg-white/60 px-4 py-3 transition-colors hover:bg-white dark:border-white/5 dark:bg-white/5 dark:hover:bg-white/10">
                                                    <div>
                                                        <p className="text-sm font-bold text-gray-900 dark:text-gray-100">{label}</p>
                                                        <p className="mt-0.5 flex items-center gap-2 text-[10px] text-gray-500 dark:text-gray-400">
                                                            <span>📅 Taken: {data.date}</span>
                                                            {data.answered !== undefined && <span>| 📝 {data.answered}/{data.total} Ans.</span>}
                                                        </p>
                                                    </div>
                                                    <div className="text-right">
                                                        <p className="text-sm font-extrabold text-emerald-700 dark:text-emerald-400">{data.score}%</p>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>

                                    {/* Final Average For Completed Attempts */}
                                    {Object.keys(subjectMap).length === 6 && (
                                        <div className="mt-4 rounded-xl border border-emerald-200/80 bg-gradient-to-r from-emerald-50 to-teal-50/80 p-4 text-center dark:border-emerald-500/25 dark:from-emerald-950/40 dark:to-slate-900/50">
                                            <p className="text-xs font-bold uppercase tracking-wider text-emerald-800 dark:text-emerald-400">Final General Average</p>
                                            <p className="mt-1 text-2xl font-extrabold text-gray-900 dark:text-white">{calculateGeneralAverage(subjectMap).toFixed(2)}%</p>
                                            <p className={`mt-1 text-[11px] ${calculateGeneralAverage(subjectMap) >= 75 ? 'text-emerald-700 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
                                                {calculateGeneralAverage(subjectMap) >= 75 ? '🎉 PASSED (#SuccessAchievedthroughMerit)' : '❌ FAILED (Threshold is 75%)'}
                                            </p>
                                        </div>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
                )}
            </div>
            </div>

            {/* Exam Details & Grading Info Modal */}
            {showDetailsModal && (
                <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
                    <div className="relative w-full max-w-md rounded-2xl border-2 border-slate-300/80 bg-white/95 p-6 shadow-2xl dark:border-white/10 dark:bg-slate-900/95">
                        <button type="button" onClick={() => setShowDetailsModal(null)} className="absolute right-4 top-4 text-gray-400 transition hover:text-gray-900 dark:text-gray-500 dark:hover:text-white">✕</button>
                        
                        <div className="mb-4">
                            <h3 className="pr-6 font-serif text-lg font-bold text-gray-900 dark:text-white">{showDetailsModal.label}</h3>
                            <p className="text-xs text-gray-500 dark:text-gray-400">{showDetailsModal.day} | Weight: {showDetailsModal.weight}</p>
                        </div>

                        {/* Breakdown */}
                        <div className="mb-4 rounded-xl border border-gray-100 bg-gray-50/90 p-4 dark:border-white/10 dark:bg-white/5">
                            <h4 className="mb-2 text-xs font-bold uppercase tracking-wider text-gray-600 dark:text-gray-400">Subject Sub-topics Breakdown</h4>
                            <div className="space-y-2">
                                {showDetailsModal.breakdown.map((b, i) => (
                                    <div key={i} className="flex items-center justify-between text-xs">
                                        <span className="text-gray-800 dark:text-gray-200">{b.sub_topic}</span>
                                        <div className="flex items-center gap-2">
                                            <span className="text-gray-500 dark:text-gray-400">{b.count} Q's</span>
                                            {b.available !== undefined && (
                                                <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${b.available >= b.count ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-400' : 'bg-rose-100 text-rose-800 dark:bg-rose-500/20 dark:text-rose-400'}`}>
                                                    {b.available >= b.count ? 'Available' : 'Missing'}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Grading Information */}
                        <div className="rounded-xl border border-indigo-200/80 bg-indigo-50/90 p-4 text-sm text-indigo-900 dark:border-indigo-500/30 dark:bg-indigo-950/40 dark:text-indigo-100">
                            <h4 className="mb-2 text-xs font-bold uppercase tracking-wider text-indigo-800 dark:text-indigo-300">Grading System (2026)</h4>
                            <div className="space-y-2 text-xs leading-relaxed text-indigo-800/95 dark:text-indigo-200/90">
                                <p>This exam is **AI-Graded using Google Gemini**, evaluating your answers against **Suggested Answers** using the 2026 qualitative 0-5 criteria on precision and succinctness (#SuccessAchievedthroughMerit).</p>
                                <div className="mt-2 space-y-1 border-t border-indigo-200/60 pt-2 text-[11px] text-indigo-700/90 dark:border-indigo-500/20 dark:text-indigo-300/80">
                                    <p><strong>• Layer A (Raw Score)</strong>: 20 Questions sums to an absolute max 100%.</p>
                                    <p><strong>• Layer B (Weights)</strong>: Multiplies Raw % by official 2026 category weight factors (e.g. 15%, 20%, 25%).</p>
                                    <p><strong>• Layer C (General Average)</strong>: Total sum sum across Layer B slots with 75% passing threshold. Rule 138 disqualification kicks in if any Layer A falls below 50%.</p>
                                </div>
                            </div>
                        </div>

                        <button type="button" onClick={() => setShowDetailsModal(null)} className="mt-5 w-full rounded-xl border border-rose-200 bg-rose-50 py-2.5 text-sm font-bold text-rose-800 transition hover:bg-rose-100 dark:border-rose-500/30 dark:bg-rose-950/50 dark:text-rose-200 dark:hover:bg-rose-950/70">
                            Close
                        </button>
                    </div>
                </div>
            )}

            {/* Proctor Password Modal */}
            {showPasswordModal && selectedExam && (
                <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
                    <div className="w-full max-w-md rounded-2xl border-2 border-slate-300/80 bg-white/95 p-8 shadow-2xl dark:border-white/10 dark:bg-slate-900/95">
                        <div className="mb-6 text-center">
                            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-amber-100 text-2xl dark:bg-amber-500/15">🔒</div>
                            <h3 className="font-serif text-lg font-bold text-gray-900 dark:text-white">Proctor Authorization</h3>
                            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">Enter the password provided by your proctor to begin:</p>
                            <p className="mt-1 text-sm font-bold text-amber-700 dark:text-amber-400">{selectedExam.label}</p>
                        </div>
                        <input
                            autoFocus
                            type="text"
                            value={password}
                            onChange={(e) => { setPassword(e.target.value); setPasswordError(''); }}
                            onKeyDown={(e) => e.key === 'Enter' && handlePasswordSubmit()}
                            placeholder="Enter proctor password"
                            className="mb-2 w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-center font-mono text-lg tracking-widest text-gray-900 outline-none transition focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20 dark:border-white/10 dark:bg-slate-800/80 dark:text-white dark:focus:border-amber-500"
                        />
                        <p className="mb-2 text-center text-xs text-gray-500 dark:text-gray-500">Hint: ask your proctor after the second bell</p>
                        {passwordError && <div className="mb-2 rounded-lg border border-rose-200 bg-rose-50 px-4 py-2 text-center text-sm text-rose-800 dark:border-rose-500/30 dark:bg-rose-950/40 dark:text-rose-300">{passwordError}</div>}
                        <div className="mt-4 flex gap-3">
                            <button type="button" onClick={() => setShowPasswordModal(false)} className="flex-1 rounded-xl border border-gray-200 py-2 text-sm text-gray-600 transition hover:bg-gray-50 dark:border-white/10 dark:text-gray-300 dark:hover:bg-white/5">Cancel</button>
                            <button type="button" onClick={handlePasswordSubmit} className="flex-1 rounded-xl bg-amber-600 py-2 text-sm font-bold text-white shadow-sm transition hover:bg-amber-700 dark:bg-amber-600 dark:hover:bg-amber-500">Confirm</button>
                        </div>
                    </div>
                </div>
            )}

            {/* Preferences Modal */}
            {showPrefsModal && (
                <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
                    <div className="w-full max-w-sm rounded-2xl border-2 border-slate-300/80 bg-white/95 p-8 shadow-2xl dark:border-white/10 dark:bg-slate-900/95">
                        <h3 className="mb-5 font-serif text-lg font-bold text-gray-900 dark:text-white">Preferences</h3>
                        <label className="mb-1 block text-xs font-bold text-gray-600 dark:text-gray-400">⏰ Alarm Reminder (HH:MM:SS)</label>
                        <p className="mb-2 text-xs text-gray-500 dark:text-gray-500">Alert when this much time remains</p>
                        <input type="text" value={alarmTime} onChange={(e) => setAlarmTime(e.target.value)} placeholder="00:30:00"
                            className="w-full rounded-xl border border-gray-200 bg-white px-4 py-2 text-center font-mono text-gray-900 outline-none transition focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20 dark:border-white/10 dark:bg-slate-800/80 dark:text-white" />
                        <button type="button" onClick={() => setShowPrefsModal(false)} className="mt-5 w-full rounded-xl bg-amber-600 py-2 text-sm font-bold text-white shadow-sm transition hover:bg-amber-700 dark:bg-amber-600 dark:hover:bg-amber-500">Save</button>
                    </div>
                </div>
            )}
        </FeaturePageShell>
    );
};

export default LexifyDashboard;
