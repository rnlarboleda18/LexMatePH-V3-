import React, { useState, useEffect } from 'react';

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

    // Load attempt history from localStorage on mount
    useEffect(() => {
        try {
            const stored = localStorage.getItem('lexify_attempts');
            if (stored) setAttempts(JSON.parse(stored));
        } catch (e) {
            console.error("Failed to load attempt history", e);
        }
    }, []);

    const handleStartNewAttempt = () => {
        const proceed = window.confirm("Are you sure you want to start a new Mock Bar Attempt? This will reset all subjects to 'Ready' for the new attempt.");
        if (!proceed) return;

        const next = (attempts.current || 1) + 1;
        const updated = { current: next, history: { ...attempts.history, [next]: {} } };
        setAttempts(updated);
        localStorage.setItem('lexify_attempts', JSON.stringify(updated));
        setShowMenu(false);
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

    // Fallback if batch classifier hasn't run with 2026 Official Dates
    const getFallbackExams = () => [
        { id: 'political-pil',   label: 'Political and Public International Law',  day: 'Sept 6, 2026 (Sun AM)',   weight: '15%', total_questions: 20, available: 0, ready: false, breakdown: [{ sub_topic: 'Political Law', count: 17, available: 0 }, { sub_topic: 'Public International Law', count: 3, available: 0 }] },
        { id: 'commercial-tax',  label: 'Commercial and Taxation Laws',             day: 'Sept 6, 2026 (Sun PM)',   weight: '20%', total_questions: 20, available: 0, ready: false, breakdown: [{ sub_topic: 'Commercial Law', count: 15, available: 0 }, { sub_topic: 'Taxation', count: 5, available: 0 }] },
        { id: 'civil-land',      label: 'Civil Law and Land Titles and Deeds',      day: 'Sept 9, 2026 (Wed AM)',   weight: '20%', total_questions: 20, available: 0, ready: false, breakdown: [{ sub_topic: 'Civil Law', count: 16, available: 0 }, { sub_topic: 'Land Titles and Deeds', count: 4, available: 0 }] },
        { id: 'labor-social',    label: 'Labor Law and Social Legislation',         day: 'Sept 9, 2026 (Wed PM)',   weight: '10%', total_questions: 20, available: 0, ready: false, breakdown: [{ sub_topic: 'Labor Law', count: 16, available: 0 }, { sub_topic: 'Social Legislation', count: 4, available: 0 }] },
        { id: 'criminal',        label: 'Criminal Law',                             day: 'Sept 13, 2026 (Sun AM)',  weight: '10%', total_questions: 20, available: 0, ready: false, breakdown: [{ sub_topic: 'Criminal Law', count: 16, available: 0 }, { sub_topic: 'Special Penal Laws', count: 4, available: 0 }] },
        { id: 'remedial-ethics', label: 'Remedial Law, Legal and Judicial Ethics, with Practical Exercises', day: 'Sept 13, 2026 (Sun PM)', weight: '25%', total_questions: 20, available: 0, ready: false, breakdown: [{ sub_topic: 'Remedial Law', count: 14, available: 0 }, { sub_topic: 'Legal and Judicial Ethics', count: 4, available: 0 }, { sub_topic: 'Practical Exercises', count: 2, available: 0 }] },
    ];

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

    const DAY_COLORS = {
        'Sept 6, 2026 (Sun AM)':   'from-blue-900/40 to-blue-800/20 border-blue-500/30',
        'Sept 6, 2026 (Sun PM)':   'from-indigo-900/40 to-indigo-800/20 border-indigo-500/30',
        'Sept 9, 2026 (Wed AM)':   'from-purple-900/40 to-purple-800/20 border-purple-500/30',
        'Sept 9, 2026 (Wed PM)':   'from-fuchsia-900/40 to-fuchsia-800/20 border-fuchsia-500/30',
        'Sept 13, 2026 (Sun AM)':  'from-rose-900/40 to-rose-800/20 border-rose-500/30',
        'Sept 13, 2026 (Sun PM)':  'from-orange-900/40 to-orange-800/20 border-orange-500/30',
    };

    const WEIGHT_COLOR = (w) => w === '25%' ? 'text-amber-400' : w >= '20%' ? 'text-green-400' : 'text-blue-400';

    return (
        <div className="fixed inset-0 z-[100] bg-[#0d1117] text-white flex flex-col font-sans">
            {/* Top Bar */}
            <div className="h-12 bg-[#161b22] border-b border-white/10 flex items-center justify-between px-6 select-none shrink-0">
                <div className="flex items-center gap-3">
                    <button onClick={() => setShowMenu(!showMenu)} className="flex flex-col gap-1 p-2 hover:bg-white/10 rounded transition">
                        <span className="w-5 h-0.5 bg-white/70 block" /><span className="w-5 h-0.5 bg-white/70 block" /><span className="w-5 h-0.5 bg-white/70 block" />
                    </button>
                    {showMenu && (
                        <div className="absolute top-12 left-0 z-50 bg-[#161b22] border border-white/10 rounded-xl shadow-2xl w-56 py-2 overflow-hidden">
                            <button onClick={() => { setShowPrefsModal(true); setShowMenu(false); }} className="w-full text-left px-4 py-2.5 text-sm hover:bg-white/10 transition">⚙️ Preferences</button>
                            <button onClick={handleStartNewAttempt} className="w-full text-left px-4 py-2.5 text-sm hover:bg-white/10 transition text-green-400">✨ Start New Attempt</button>
                            
                            {/* Sample Q&A Toggle */}
                            <button 
                                onClick={(e) => { e.stopPropagation(); setShowSampleSubmenu(!showSampleSubmenu); }} 
                                className="w-full text-left px-4 py-2.5 text-sm hover:bg-white/10 transition flex items-center justify-between"
                            >
                                <span>📚 Sample Q&A</span>
                                <span className={`text-[10px] text-white/30 transition-transform ${showSampleSubmenu ? 'rotate-180' : ''}`}>▼</span>
                            </button>

                            {showSampleSubmenu && (
                                <div className="bg-black/20 py-1 border-y border-white/5 max-h-48 overflow-y-auto">
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
                                            className="w-full text-left pl-7 pr-3 py-1.5 text-xs hover:bg-white/5 transition text-white/70 hover:text-white truncate"
                                        >
                                            • {sub.short}
                                        </button>
                                    ))}
                                </div>
                            )}

                            <hr className="border-white/10 my-1" />
                            <button onClick={onClose} className="w-full text-left px-4 py-2.5 text-sm hover:bg-white/10 transition text-red-400">✕ Exit to LexMatePH</button>
                        </div>
                    )}
                    <span className="font-bold text-sm tracking-widest text-[#e94560]">LEXIFY</span>
                    <span className="text-xs text-white/30 tracking-widest hidden sm:block">BAR EXAM SIMULATOR</span>
                </div>
                <div className="flex items-center gap-3">
                    <span className="text-xs text-white/30">2026 Philippine Bar</span>
                    <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                </div>
            </div>
                 {/* Main */}
            <div className="flex-1 overflow-y-auto px-6 py-4 max-w-5xl mx-auto w-full">
                {/* Tabs Selection Navbar */}
                <div className="flex justify-center border-b border-white/10 mb-6 gap-6 select-none">
                    <button 
                        onClick={() => setActiveTab('exams')} 
                        className={`pb-2 px-4 font-bold text-sm transition-all focus:outline-none ${activeTab === 'exams' ? 'text-[#e94560] border-b-2 border-[#e94560]' : 'text-white/40 hover:text-white'}`}
                    >
                        My Exams
                    </button>
                    <button 
                        onClick={() => setActiveTab('history')} 
                        className={`pb-2 px-4 font-bold text-sm transition-all focus:outline-none ${activeTab === 'history' ? 'text-[#e94560] border-b-2 border-[#e94560]' : 'text-white/40 hover:text-white'}`}
                    >
                        Attempts History
                    </button>
                </div>

                {activeTab === 'exams' ? (
                    <>
                        <div className="text-center mb-6">
                            <div className="inline-block bg-[#e94560]/10 border border-[#e94560]/30 rounded-xl px-5 py-1.5 mb-2">
                                <span className="text-[#e94560] text-xs font-bold tracking-widest uppercase">Simulated Secure Testing Environment</span>
                            </div>
                            <h1 className="text-2xl font-bold font-serif">My Exams</h1>
                            <p className="text-white/40 text-sm mt-0.5">6 Core Bar Subjects · 20 Questions Each</p>
                            <p className="text-[#f7941d] text-xs font-bold mt-2 uppercase tracking-wider">Mock Bar Attempt No. {attempts.current}</p>
                        </div>

                        {/* Final Average Banner */}
                        {(() => {
                            const currentSubjectMap = attempts.history[attempts.current] || {};
                            const isComplete = Object.keys(currentSubjectMap).length === 6;
                            const finalAverage = calculateGeneralAverage(currentSubjectMap);
                            if (!isComplete) return null;

                            return (
                                <div className="bg-gradient-to-r from-green-500/10 to-emerald-500/5 border border-green-500/20 rounded-2xl p-5 mb-6 text-center shadow-lg">
                                    <h2 className="text-sm font-bold font-serif text-white mb-1 uppercase tracking-wider">Consolidated Mock Bar Attempt Completed!</h2>
                                    <p className="text-green-400 text-3xl font-extrabold">{finalAverage.toFixed(2)}%</p>
                                    <p className="text-white/40 text-xs mt-1 uppercase tracking-wider">Final General Average</p>
                                    <div className="mt-3 inline-block bg-white/5 px-4 py-1.5 rounded-full border border-white/5 text-xs text-white/80">
                                         {finalAverage >= 75 ? '🟢 PASSED (#SuccessAchievedthroughMerit)' : '🔴 FAILED (Threshold is 75%)'}
                                    </div>
                                </div>
                            );
                        })()}

                        {loading ? (
                            <div className="text-center py-20 text-white/30">Loading exam roster...</div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {exams.map((exam) => {
                                    const dayColor = DAY_COLORS[exam.day] || 'from-gray-900/40 to-gray-800/20 border-gray-500/20';
                                    const isTaken = attempts.history[attempts.current]?.[exam.id];

                                    return (
                                        <div key={exam.id} className={`bg-gradient-to-br ${dayColor} border rounded-2xl overflow-hidden shadow-lg flex flex-col justify-between transition-transform duration-200 hover:-translate-y-1`}>
                                            {/* Card Header */}
                                            <div className="p-5 flex-1 min-h-[85px]">
                                                <div className="flex items-start justify-between gap-3 mb-3">
                                                    <h3 className="font-bold text-base font-serif leading-snug">{exam.label}</h3>
                                                    <span className={`text-lg font-extrabold font-mono shrink-0 ${WEIGHT_COLOR(exam.weight)}`}>{exam.weight}</span>
                                                </div>
                                                <div className="flex items-center gap-2 text-xs text-white/50">
                                                    <span>📅 {exam.day}</span>
                                                    <span>·</span>
                                                    <span>📝 {exam.total_questions} Q's</span>
                                                </div>
                                            </div>

                                            {/* Action footer */}
                                            <div className="px-5 py-3.5 flex items-center justify-between border-t border-white/5 bg-black/15">
                                                <div className="flex items-center gap-2">
                                                    {isTaken ? (
                                                        <span className="text-[11px] px-2 py-0.5 rounded-full bg-green-500/10 text-green-400 border border-green-500/20">
                                                            ✅ Score: {isTaken.score}%
                                                        </span>
                                                    ) : (
                                                        <span className={`text-[11px] px-2 py-0.5 rounded-full border ${exam.ready ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'}`}>
                                                            {exam.ready ? '● Ready' : '⏳ Pending'}
                                                        </span>
                                                    )}
                                                    <button 
                                                        onClick={() => setShowDetailsModal(exam)}
                                                        className="text-[#3fa9f5] hover:underline text-xs font-bold"
                                                    >
                                                        Details
                                                    </button>
                                                </div>
                                                <button
                                                    onClick={() => !isTaken && handleBeginClick(exam)}
                                                    disabled={isTaken}
                                                    className={`px-5 py-1.5 font-bold text-sm rounded-xl transition-all shadow-md ${isTaken ? 'bg-white/5 text-white/30 cursor-not-allowed border border-white/5' : 'bg-[#e94560] hover:bg-[#c73652] text-white active:scale-95'}`}
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
                        <div className="mt-6 flex flex-wrap justify-center gap-5 text-xs text-white/30">
                            <span className="text-green-400 font-bold">● Ready</span> — questions available
                            <span className="text-amber-400 font-bold">⏳ Pending</span> — classifier pending
                        </div>
                    </>
                ) : (
                    /* History Tab */
                    <div className="space-y-4">
                        <div className="text-center mb-6">
                            <h1 className="text-2xl font-bold font-serif">Attempts History</h1>
                            <p className="text-white/40 text-sm mt-0.5">Past graded Mock Bar iterations</p>
                        </div>

                        {Object.keys(attempts.history || {}).length === 0 ? (
                            <div className="text-center py-20 text-white/30 flex flex-col items-center gap-3">
                                <span className="text-3xl">🗓️</span>
                                <p>No completed attempts recorded yet.</p>
                                <p className="text-xs text-white/20">Submit an exam session to start populating records.</p>
                            </div>
                        ) : (
                            Object.entries(attempts.history).reverse().map(([attemptNum, subjectMap]) => (
                                <div key={attemptNum} className="bg-[#161b22] border border-white/10 rounded-2xl p-5 shadow">
                                    <div className="flex justify-between items-center mb-4 border-b border-white/5 pb-2">
                                        <h3 className="font-bold text-base text-amber-400">Mock Bar Attempt No. {attemptNum}</h3>
                                        <span className="text-[10px] bg-white/5 px-2 py-0.5 rounded-full border border-white/10 text-white/40">
                                            {Object.keys(subjectMap).length} Subjects Completed
                                        </span>
                                    </div>
                                    <div className="space-y-2">
                                        {Object.entries(subjectMap).map(([examId, data]) => {
                                            const exam = exams.find(e => e.id === examId);
                                            const label = exam ? exam.label : examId.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                                            return (
                                                <div key={examId} className="flex justify-between items-center bg-white/3 px-4 py-3 rounded-xl border border-white/5 hover:bg-white/5 transition-colors">
                                                    <div>
                                                        <p className="font-bold text-sm text-white/90">{label}</p>
                                                        <p className="text-white/30 text-[10px] flex items-center gap-2 mt-0.5">
                                                            <span>📅 Taken: {data.date}</span>
                                                            {data.answered !== undefined && <span>| 📝 {data.answered}/{data.total} Ans.</span>}
                                                        </p>
                                                    </div>
                                                    <div className="text-right">
                                                        <p className="font-extrabold text-green-400 text-sm">{data.score}%</p>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>

                                    {/* Final Average For Completed Attempts */}
                                    {Object.keys(subjectMap).length === 6 && (
                                        <div className="mt-4 bg-gradient-to-r from-green-500/10 to-emerald-500/5 border border-green-500/20 rounded-xl p-4 text-center">
                                            <p className="text-xs text-green-400 font-bold uppercase tracking-wider">Final General Average</p>
                                            <p className="text-2xl font-extrabold text-white mt-1">{calculateGeneralAverage(subjectMap).toFixed(2)}%</p>
                                            <p className={`text-[11px] mt-1 ${calculateGeneralAverage(subjectMap) >= 75 ? 'text-green-400' : 'text-red-400'}`}>
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

            {/* Exam Details & Grading Info Modal */}
            {showDetailsModal && (
                <div className="fixed inset-0 z-[200] bg-black/80 flex items-center justify-center p-4">
                    <div className="bg-[#161b22] border border-white/10 rounded-2xl w-full max-w-md p-6 shadow-2xl relative">
                        <button onClick={() => setShowDetailsModal(null)} className="absolute top-4 right-4 text-white/40 hover:text-white">✕</button>
                        
                        <div className="mb-4">
                            <h3 className="text-lg font-bold font-serif pr-6">{showDetailsModal.label}</h3>
                            <p className="text-xs text-white/40">{showDetailsModal.day} | Weight: {showDetailsModal.weight}</p>
                        </div>

                        {/* Breakdown */}
                        <div className="bg-white/5 rounded-xl p-4 mb-4">
                            <h4 className="text-xs font-bold uppercase tracking-wider text-white/60 mb-2">Subject Sub-topics Breakdown</h4>
                            <div className="space-y-2">
                                {showDetailsModal.breakdown.map((b, i) => (
                                    <div key={i} className="flex items-center justify-between text-xs">
                                        <span className="text-white/70">{b.sub_topic}</span>
                                        <div className="flex items-center gap-2">
                                            <span className="text-white/40">{b.count} Q's</span>
                                            {b.available !== undefined && (
                                                <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${b.available >= b.count ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                                                    {b.available >= b.count ? 'Available' : 'Missing'}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Grading Information */}
                        <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4 text-sm text-blue-300">
                            <h4 className="text-xs font-bold uppercase tracking-wider text-blue-400 mb-2">Grading System (2026)</h4>
                            <div className="text-xs leading-relaxed text-blue-200/80 space-y-2">
                                <p>This exam is **AI-Graded using Google Gemini**, evaluating your answers against **Suggested Answers** using the 2026 qualitative 0-5 criteria on precision and succinctness (#SuccessAchievedthroughMerit).</p>
                                <div className="border-t border-blue-500/10 pt-2 mt-2 space-y-1 text-[11px] text-blue-200/60">
                                    <p><strong>• Layer A (Raw Score)</strong>: 20 Questions sums to an absolute max 100%.</p>
                                    <p><strong>• Layer B (Weights)</strong>: Multiplies Raw % by official 2026 category weight factors (e.g. 15%, 20%, 25%).</p>
                                    <p><strong>• Layer C (General Average)</strong>: Total sum sum across Layer B slots with 75% passing threshold. Rule 138 disqualification kicks in if any Layer A falls below 50%.</p>
                                </div>
                            </div>
                        </div>

                        <button onClick={() => setShowDetailsModal(null)} className="w-full mt-5 py-2.5 bg-[#e94560] hover:bg-[#c73652] text-white font-bold rounded-xl text-sm transition">
                            Close
                        </button>
                    </div>
                </div>
            )}

            {/* Proctor Password Modal */}
            {showPasswordModal && selectedExam && (
                <div className="fixed inset-0 z-[200] bg-black/80 flex items-center justify-center p-4">
                    <div className="bg-[#161b22] border border-white/10 rounded-2xl w-full max-w-md p-8 shadow-2xl">
                        <div className="text-center mb-6">
                            <div className="w-14 h-14 bg-[#e94560]/10 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl">🔒</div>
                            <h3 className="text-lg font-bold font-serif">Proctor Authorization</h3>
                            <p className="text-white/40 text-sm mt-1">Enter the password provided by your proctor to begin:</p>
                            <p className="text-[#e94560] text-sm font-bold mt-1">{selectedExam.label}</p>
                        </div>
                        <input
                            autoFocus
                            type="text"
                            value={password}
                            onChange={(e) => { setPassword(e.target.value); setPasswordError(''); }}
                            onKeyDown={(e) => e.key === 'Enter' && handlePasswordSubmit()}
                            placeholder="Enter proctor password"
                            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-center text-lg font-mono tracking-widest outline-none focus:border-[#e94560]/50 transition mb-2"
                        />
                        <p className="text-center text-xs text-white/20 mb-2">Hint: ask your proctor after the second bell</p>
                        {passwordError && <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2 text-red-400 text-sm text-center mb-2">{passwordError}</div>}
                        <div className="flex gap-3 mt-4">
                            <button onClick={() => setShowPasswordModal(false)} className="flex-1 py-2 border border-white/10 rounded-xl text-sm text-white/40 hover:text-white transition">Cancel</button>
                            <button onClick={handlePasswordSubmit} className="flex-1 py-2 bg-[#e94560] hover:bg-[#c73652] text-white font-bold rounded-xl text-sm transition">Confirm</button>
                        </div>
                    </div>
                </div>
            )}

            {/* Preferences Modal */}
            {showPrefsModal && (
                <div className="fixed inset-0 z-[200] bg-black/80 flex items-center justify-center p-4">
                    <div className="bg-[#161b22] border border-white/10 rounded-2xl w-full max-w-sm p-8 shadow-2xl">
                        <h3 className="text-lg font-bold font-serif mb-5">Preferences</h3>
                        <label className="block text-xs font-bold text-white/50 mb-1">⏰ Alarm Reminder (HH:MM:SS)</label>
                        <p className="text-xs text-white/30 mb-2">Alert when this much time remains</p>
                        <input type="text" value={alarmTime} onChange={(e) => setAlarmTime(e.target.value)} placeholder="00:30:00"
                            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 font-mono text-center outline-none focus:border-[#e94560]/50 transition" />
                        <button onClick={() => setShowPrefsModal(false)} className="w-full mt-5 py-2 bg-[#e94560] hover:bg-[#c73652] text-white font-bold rounded-xl text-sm transition">Save</button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default LexifyDashboard;
