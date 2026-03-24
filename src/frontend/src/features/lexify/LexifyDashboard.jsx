import React, { useState } from 'react';

const EXAM_DATA = {
    id: 'bar-2025',
    title: '2025 Philippine Bar Examination',
    subtitle: 'Simulated Examplify Environment',
    subjects: [
        'Political Law & Public International Law',
        'Labor Law & Social Legislation',
        'Civil Law',
        'Taxation Law',
        'Mercantile & Commercial Law',
        'Criminal Law',
        'Remedial Law',
        'Legal Ethics & Practical Exercises'
    ],
    date: 'September 7, 10, and 14, 2025',
    duration: '4 Hours',
    totalItems: 20,
    status: 'ready', // 'ready' | 'completed'
};

const PROCTOR_PASSWORD = 'LEXIFY2025'; // Simulated proctor password

const LexifyDashboard = ({ onBeginExam, onClose }) => {
    const [showPasswordModal, setShowPasswordModal] = useState(false);
    const [showPrefsModal, setShowPrefsModal] = useState(false);
    const [password, setPassword] = useState('');
    const [passwordError, setPasswordError] = useState('');
    const [alarmTime, setAlarmTime] = useState('00:30:00'); // Default: 30 min warning
    const [showMenu, setShowMenu] = useState(false);

    const handleBeginClick = () => {
        setShowPasswordModal(true);
        setPassword('');
        setPasswordError('');
    };

    const handlePasswordSubmit = () => {
        if (password.toUpperCase() === PROCTOR_PASSWORD) {
            setShowPasswordModal(false);
            onBeginExam(alarmTime);
        } else {
            setPasswordError('Incorrect password. Please ask your proctor for the correct password.');
        }
    };

    return (
        <div className="fixed inset-0 z-[100] bg-[#1a1a2e] text-white flex flex-col font-sans">
            {/* Top Bar */}
            <div className="h-12 bg-[#16213e] border-b border-white/10 flex items-center justify-between px-6 select-none">
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => setShowMenu(!showMenu)}
                        className="flex flex-col gap-1 p-2 hover:bg-white/10 rounded transition"
                    >
                        <span className="w-5 h-0.5 bg-white/70 block" />
                        <span className="w-5 h-0.5 bg-white/70 block" />
                        <span className="w-5 h-0.5 bg-white/70 block" />
                    </button>
                    {showMenu && (
                        <div className="absolute top-12 left-0 z-50 bg-[#0f3460] border border-white/10 rounded-lg shadow-2xl w-56 py-2">
                            <button onClick={() => { setShowPrefsModal(true); setShowMenu(false); }} className="w-full text-left px-4 py-2 text-sm hover:bg-white/10 transition">⚙️ Preferences</button>
                            <button onClick={() => setShowMenu(false)} className="w-full text-left px-4 py-2 text-sm hover:bg-white/10 transition">📋 Exam History</button>
                            <hr className="border-white/10 my-1" />
                            <button onClick={onClose} className="w-full text-left px-4 py-2 text-sm hover:bg-white/10 transition text-red-400">✕ Exit to LexMatePH</button>
                        </div>
                    )}
                    <span className="font-bold text-sm tracking-widest text-[#e94560]">LEXIFY</span>
                    <span className="text-xs text-white/40 tracking-widest">BAR EXAM SIMULATOR</span>
                </div>
                <span className="text-xs text-white/30">v3.8.0 • Philippine Standard Time</span>
            </div>

            {/* Main Content */}
            <div className="flex-1 flex flex-col items-center justify-center p-8">
                <div className="text-center mb-10">
                    <div className="inline-block bg-[#e94560]/10 border border-[#e94560]/30 rounded-xl px-6 py-2 mb-4">
                        <span className="text-[#e94560] text-xs font-bold tracking-widest uppercase">Simulated Secure Testing Environment</span>
                    </div>
                    <h1 className="text-3xl font-bold mb-2 font-serif">My Exams</h1>
                    <p className="text-white/40 text-sm">Select an available exam to begin</p>
                </div>

                {/* Exam Card */}
                <div className="w-full max-w-2xl bg-[#16213e] border border-white/10 rounded-2xl overflow-hidden shadow-2xl">
                    {/* Exam Header */}
                    <div className="bg-gradient-to-r from-[#0f3460] to-[#16213e] p-6 border-b border-white/10">
                        <div className="flex items-start justify-between">
                            <div>
                                <h2 className="text-lg font-bold font-serif">{EXAM_DATA.title}</h2>
                                <p className="text-white/50 text-sm mt-1">{EXAM_DATA.subtitle}</p>
                            </div>
                            <span className={`px-3 py-1 rounded-full text-xs font-bold ${EXAM_DATA.status === 'ready' ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 'bg-gray-500/20 text-gray-400 border border-gray-500/30'}`}>
                                {EXAM_DATA.status === 'ready' ? '● Ready' : '✓ Completed'}
                            </span>
                        </div>
                    </div>

                    {/* Exam Details */}
                    <div className="p-6">
                        <div className="grid grid-cols-3 gap-4 mb-6 text-center">
                            <div className="bg-white/5 rounded-xl p-3">
                                <p className="text-xs text-white/40 mb-1">Duration</p>
                                <p className="font-bold text-sm">{EXAM_DATA.duration}</p>
                            </div>
                            <div className="bg-white/5 rounded-xl p-3">
                                <p className="text-xs text-white/40 mb-1">Questions</p>
                                <p className="font-bold text-sm">{EXAM_DATA.totalItems} Items</p>
                            </div>
                            <div className="bg-white/5 rounded-xl p-3">
                                <p className="text-xs text-white/40 mb-1">Format</p>
                                <p className="font-bold text-sm">Essay</p>
                            </div>
                        </div>

                        {/* Subjects */}
                        <div className="mb-6">
                            <p className="text-xs font-bold text-white/40 uppercase tracking-widest mb-3">Subjects Covered</p>
                            <div className="flex flex-wrap gap-2">
                                {EXAM_DATA.subjects.map((sub, i) => (
                                    <span key={i} className="px-2 py-1 bg-white/5 border border-white/10 rounded-lg text-xs text-white/60">{sub}</span>
                                ))}
                            </div>
                        </div>

                        {/* Warning */}
                        <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 mb-6 text-xs text-amber-300">
                            <strong>Important:</strong> Ensure your laptop is fully charged and connected to power. This exam entering secure mode. Contact your proctor if you experience any issues.
                        </div>

                        {/* Actions */}
                        <div className="flex gap-3 justify-end">
                            <button onClick={onClose} className="px-5 py-2 text-sm text-white/50 hover:text-white border border-white/10 rounded-lg transition">
                                Cancel
                            </button>
                            {EXAM_DATA.status === 'ready' && (
                                <button
                                    onClick={handleBeginClick}
                                    className="px-8 py-2 text-sm bg-[#e94560] hover:bg-[#c73652] text-white font-bold rounded-lg transition-all shadow-lg shadow-[#e94560]/30 active:scale-95"
                                >
                                    Begin Exam →
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Password Modal */}
            {showPasswordModal && (
                <div className="fixed inset-0 z-[200] bg-black/80 flex items-center justify-center p-4">
                    <div className="bg-[#16213e] border border-white/10 rounded-2xl w-full max-w-md p-8 shadow-2xl">
                        <div className="text-center mb-6">
                            <div className="w-16 h-16 bg-[#e94560]/10 rounded-full flex items-center justify-center mx-auto mb-4">
                                <span className="text-2xl">🔒</span>
                            </div>
                            <h3 className="text-xl font-bold font-serif">Proctor Authorization</h3>
                            <p className="text-white/50 text-sm mt-2">Enter the password provided by your proctor to begin the exam.</p>
                        </div>

                        <input
                            autoFocus
                            type="text"
                            value={password}
                            onChange={(e) => {
                                setPassword(e.target.value);
                                setPasswordError('');
                            }}
                            onKeyDown={(e) => e.key === 'Enter' && handlePasswordSubmit()}
                            placeholder="Enter proctor password"
                            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-center text-lg font-mono tracking-widest outline-none focus:border-[#e94560]/50 transition mb-3"
                        />
                        <p className="text-center text-xs text-white/30 mb-1">Hint: <span className="italic">Ask your proctor for the password after the second bell</span></p>

                        {passwordError && (
                            <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2 text-red-400 text-sm text-center mt-3 mb-1">
                                {passwordError}
                            </div>
                        )}

                        <div className="flex gap-3 mt-6">
                            <button onClick={() => setShowPasswordModal(false)} className="flex-1 py-2 border border-white/10 rounded-xl text-sm text-white/50 hover:text-white transition">Cancel</button>
                            <button onClick={handlePasswordSubmit} className="flex-1 py-2 bg-[#e94560] hover:bg-[#c73652] text-white font-bold rounded-xl text-sm transition">Begin Exam</button>
                        </div>
                    </div>
                </div>
            )}

            {/* Preferences Modal */}
            {showPrefsModal && (
                <div className="fixed inset-0 z-[200] bg-black/80 flex items-center justify-center p-4">
                    <div className="bg-[#16213e] border border-white/10 rounded-2xl w-full max-w-md p-8 shadow-2xl">
                        <h3 className="text-xl font-bold font-serif mb-6">Preferences</h3>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-bold text-white/60 mb-2">⏰ Default Alarm Reminder</label>
                                <p className="text-xs text-white/30 mb-2">Alert me when this much time is remaining (HH:MM:SS)</p>
                                <input
                                    type="text"
                                    value={alarmTime}
                                    onChange={(e) => setAlarmTime(e.target.value)}
                                    placeholder="00:30:00"
                                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 font-mono text-center outline-none focus:border-[#e94560]/50 transition"
                                />
                            </div>
                        </div>
                        <button onClick={() => setShowPrefsModal(false)} className="w-full mt-6 py-2 bg-[#e94560] hover:bg-[#c73652] text-white font-bold rounded-xl text-sm transition">Save & Close</button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default LexifyDashboard;
