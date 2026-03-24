import React, { useState, useEffect } from 'react';

const PROCTOR_PASSWORD = 'LEXIFY2025';

const LexifyDashboard = ({ onBeginExam, onClose }) => {
    const [exams, setExams] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedExam, setSelectedExam] = useState(null);
    const [showPasswordModal, setShowPasswordModal] = useState(false);
    const [showPrefsModal, setShowPrefsModal] = useState(false);
    const [password, setPassword] = useState('');
    const [passwordError, setPasswordError] = useState('');
    const [alarmTime, setAlarmTime] = useState('00:30:00');
    const [showMenu, setShowMenu] = useState(false);

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

    // Fallback if batch classifier hasn't run (sub_topics not yet tagged)
    const getFallbackExams = () => [
        { id: 'political-pil',   label: 'Political and Public International Law',  day: 'Day 1 Morning',   weight: '15%', total_questions: 20, available: 0, ready: false, breakdown: [{ sub_topic: 'Political Law', count: 17, available: 0 }, { sub_topic: 'Public International Law', count: 3, available: 0 }] },
        { id: 'commercial-tax',  label: 'Commercial and Taxation Laws',             day: 'Day 1 Afternoon', weight: '20%', total_questions: 20, available: 0, ready: false, breakdown: [{ sub_topic: 'Commercial Law', count: 15, available: 0 }, { sub_topic: 'Taxation', count: 5, available: 0 }] },
        { id: 'civil-land',      label: 'Civil Law and Land Titles and Deeds',      day: 'Day 2 Morning',   weight: '20%', total_questions: 20, available: 0, ready: false, breakdown: [{ sub_topic: 'Civil Law', count: 16, available: 0 }, { sub_topic: 'Land Titles and Deeds', count: 4, available: 0 }] },
        { id: 'labor-social',    label: 'Labor Law and Social Legislation',         day: 'Day 2 Afternoon', weight: '10%', total_questions: 20, available: 0, ready: false, breakdown: [{ sub_topic: 'Labor Law', count: 16, available: 0 }, { sub_topic: 'Social Legislation', count: 4, available: 0 }] },
        { id: 'criminal',        label: 'Criminal Law',                             day: 'Day 3 Morning',   weight: '10%', total_questions: 20, available: 0, ready: false, breakdown: [{ sub_topic: 'Criminal Law', count: 16, available: 0 }, { sub_topic: 'Special Penal Laws', count: 4, available: 0 }] },
        { id: 'remedial-ethics', label: 'Remedial Law, Legal and Judicial Ethics, with Practical Exercises', day: 'Day 3 Afternoon', weight: '25%', total_questions: 20, available: 0, ready: false, breakdown: [{ sub_topic: 'Remedial Law', count: 14, available: 0 }, { sub_topic: 'Legal and Judicial Ethics', count: 4, available: 0 }, { sub_topic: 'Practical Exercises', count: 2, available: 0 }] },
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
        'Day 1 Morning':   'from-blue-900/40 to-blue-800/20 border-blue-500/20',
        'Day 1 Afternoon': 'from-indigo-900/40 to-indigo-800/20 border-indigo-500/20',
        'Day 2 Morning':   'from-purple-900/40 to-purple-800/20 border-purple-500/20',
        'Day 2 Afternoon': 'from-fuchsia-900/40 to-fuchsia-800/20 border-fuchsia-500/20',
        'Day 3 Morning':   'from-rose-900/40 to-rose-800/20 border-rose-500/20',
        'Day 3 Afternoon': 'from-orange-900/40 to-orange-800/20 border-orange-500/20',
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
                        <div className="absolute top-12 left-0 z-50 bg-[#161b22] border border-white/10 rounded-xl shadow-2xl w-52 py-2">
                            <button onClick={() => { setShowPrefsModal(true); setShowMenu(false); }} className="w-full text-left px-4 py-2.5 text-sm hover:bg-white/10 transition">⚙️ Preferences</button>
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
            <div className="flex-1 overflow-y-auto px-6 py-8 max-w-5xl mx-auto w-full">
                <div className="text-center mb-8">
                    <div className="inline-block bg-[#e94560]/10 border border-[#e94560]/30 rounded-xl px-5 py-1.5 mb-4">
                        <span className="text-[#e94560] text-xs font-bold tracking-widest uppercase">Simulated Secure Testing Environment</span>
                    </div>
                    <h1 className="text-2xl font-bold font-serif">My Exams</h1>
                    <p className="text-white/40 text-sm mt-1">6 Core Bar Subjects · 20 Questions Each · 4 Hours Per Exam</p>
                </div>

                {loading ? (
                    <div className="text-center py-20 text-white/30">Loading exam roster...</div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {exams.map((exam) => {
                            const dayColor = DAY_COLORS[exam.day] || 'from-gray-900/40 to-gray-800/20 border-gray-500/20';
                            return (
                                <div key={exam.id} className={`bg-gradient-to-br ${dayColor} border rounded-2xl overflow-hidden`}>
                                    {/* Card Header */}
                                    <div className="p-5 border-b border-white/5">
                                        <div className="flex items-start justify-between gap-3 mb-3">
                                            <h3 className="font-bold text-sm font-serif leading-snug">{exam.label}</h3>
                                            <span className={`text-lg font-extrabold font-mono shrink-0 ${WEIGHT_COLOR(exam.weight)}`}>{exam.weight}</span>
                                        </div>
                                        <div className="flex items-center gap-2 text-xs text-white/40">
                                            <span>📅 {exam.day}</span>
                                            <span>·</span>
                                            <span>📝 {exam.total_questions} Questions</span>
                                        </div>
                                    </div>

                                    {/* Sub-topic breakdown */}
                                    <div className="px-5 py-3 space-y-2">
                                        {exam.breakdown.map((b, i) => (
                                            <div key={i} className="flex items-center justify-between text-xs">
                                                <span className="text-white/60">{b.sub_topic}</span>
                                                <div className="flex items-center gap-2">
                                                    <span className="text-white/30">{b.count} Q's</span>
                                                    {b.available !== undefined && (
                                                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${b.available >= b.count ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                                                            {b.available >= b.count ? '✓' : `${b.available} avail`}
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>

                                    {/* Action */}
                                    <div className="px-5 py-4 flex items-center justify-between">
                                        <span className={`text-xs px-2 py-1 rounded-full border ${exam.ready ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'}`}>
                                            {exam.ready ? '● Ready' : '⏳ Classifier Pending'}
                                        </span>
                                        <button
                                            onClick={() => handleBeginClick(exam)}
                                            className="px-5 py-2 bg-[#e94560] hover:bg-[#c73652] text-white font-bold text-sm rounded-xl transition-all shadow-lg shadow-[#e94560]/20 active:scale-95"
                                        >
                                            Begin →
                                        </button>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}

                {/* Legend */}
                <div className="mt-8 flex flex-wrap justify-center gap-6 text-xs text-white/30">
                    <span className="text-green-400 font-bold">● Ready</span> — questions are classified and available
                    <span className="text-amber-400 font-bold">⏳ Classifier Pending</span> — run <code className="bg-white/5 px-1 rounded">classify_subtopics.py</code> first
                </div>
            </div>

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
