import React, { useState, useEffect, useCallback } from 'react';

const LexifyControls = ({ onSubmit, onHide, onExit, onToggleNotes, notesOpen, answeredCount, totalCount, spellCheck, onToggleSpellCheck, alarmTime, examLabel }) => {
    const [timeLeft, setTimeLeft] = useState(4 * 60 * 60); // 4 Hours
    const [alarmFired, setAlarmFired] = useState(false);
    const [showExamMenu, setShowExamMenu] = useState(false);
    const [showToolKitMenu, setShowToolKitMenu] = useState(false);

    const alarmSeconds = useCallback(() => {
        if (!alarmTime) return 30 * 60;
        const parts = alarmTime.split(':').map(Number);
        if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
        return 30 * 60;
    }, [alarmTime]);

    useEffect(() => {
        const timer = setInterval(() => {
            setTimeLeft(prev => {
                const next = prev > 0 ? prev - 1 : 0;
                if (next === alarmSeconds() && !alarmFired) {
                    setAlarmFired(true);
                    alert(`⏰ ALARM: ${alarmTime || '00:30:00'} remaining in your exam!`);
                }
                return next;
            });
        }, 1000);
        return () => clearInterval(timer);
    }, [alarmFired, alarmSeconds, alarmTime]);

    const formatTime = (seconds) => {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    };

    const timerColor = timeLeft <= 5 * 60
        ? 'text-red-400 animate-pulse'
        : timeLeft <= 10 * 60
            ? 'text-red-400'
            : timeLeft <= 30 * 60
                ? 'text-yellow-400'
                : 'text-white/60';

    return (
        <div className="h-12 bg-[#212b36] text-white fixed top-0 w-full z-[110] flex items-center justify-between px-6 shadow select-none font-sans">
            {/* Left: Examplify Branding | Subject */}
            <div className="flex items-center gap-2">
                {/* Examplify Logo Checkmark (Simulated with SVG) */}
                <div className="w-5 h-5 flex items-center justify-center bg-transparent">
                    <svg className="w-4 h-4 text-[#3fa9f5]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                </div>
                <span className="font-bold text-base tracking-tight text-white">Examplify</span>
                <span className="text-white/40 text-sm">|</span>
                <span className="text-sm font-semibold tracking-wide uppercase text-white/90">
                    {examLabel ? examLabel.split(' (')[0] : 'EXAM'}
                </span>
            </div>

            {/* Center: Timer (Centered implicitly) */}
            <div className="absolute left-1/2 transform -translate-x-1/2 flex items-center gap-2">
                <span className={`font-sans text-sm font-semibold ${timerColor}`}>{formatTime(timeLeft)}</span>
                <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" title="Secure Mode" />
            </div>

            {/* Right: Exam Controls & Tool Kit */}
            <div className="flex items-center gap-6">
                
                {/* Exam Controls Menu */}
                <div className="relative">
                    <button
                        onClick={() => { setShowExamMenu(!showExamMenu); setShowToolKitMenu(false); }}
                        className="flex items-center gap-1 text-xs font-bold uppercase tracking-wide text-white/80 hover:text-white transition-colors"
                    >
                        EXAM CONTROLS <span className="text-xs">▾</span>
                    </button>
                    {showExamMenu && (
                        <div className="absolute right-0 top-7 z-50 bg-[#212b36] border border-gray-600 rounded shadow-xl w-44 py-1 overflow-hidden">
                            <button onClick={() => { alert('Pre-Assessment Notices loaded.'); setShowExamMenu(false); }} className="w-full text-left px-4 py-2 text-xs hover:bg-white/10 transition text-white/90">Pre-Assessment Notices</button>
                            <button onClick={() => { onHide(); setShowExamMenu(false); }} className="w-full text-left px-4 py-2 text-xs hover:bg-white/10 transition text-white/90">Hide Exam</button>
                            <hr className="border-gray-600 my-1" />
                            <button onClick={() => { onSubmit(); setShowExamMenu(false); }} className="w-full text-left px-4 py-2 text-xs hover:bg-white/10 transition text-green-400 font-bold">Submit Exam</button>
                        </div>
                    )}
                </div>

                {/* Tool Kit Menu */}
                <div className="relative">
                    <button
                        onClick={() => { setShowToolKitMenu(!showToolKitMenu); setShowExamMenu(false); }}
                        className="flex items-center gap-1 text-xs font-bold uppercase tracking-wide text-white/80 hover:text-white transition-colors"
                    >
                        TOOL KIT <span className="text-xs">⋮</span>
                    </button>
                    {showToolKitMenu && (
                        <div className="absolute right-0 top-7 z-50 bg-[#212b36] border border-gray-600 rounded shadow-xl w-44 py-1 overflow-hidden">
                            <button onClick={() => { onToggleNotes(); setShowToolKitMenu(false); }} className="w-full text-left px-4 py-2 text-xs hover:bg-white/10 transition text-white/90 flex justify-between">
                                <span>Notes</span>
                                {notesOpen && <span className="text-amber-400">●</span>}
                            </button>
                            <button onClick={() => { onToggleSpellCheck(); setShowToolKitMenu(false); }} className="w-full text-left px-4 py-2 text-xs hover:bg-white/10 transition text-white/90 flex justify-between">
                                <span>Spell Check</span>
                                {spellCheck && <span className="text-blue-400">✓</span>}
                            </button>
                            <button onClick={() => { alert(`Alarm threshold: ${alarmTime || '00:30:00'}`); setShowToolKitMenu(false); }} className="w-full text-left px-4 py-2 text-xs hover:bg-white/10 transition text-white/90">Alarm</button>
                            <button onClick={() => { alert('Calculator opened.'); setShowToolKitMenu(false); }} className="w-full text-left px-4 py-2 text-xs hover:bg-white/10 transition text-white/90">Calculator</button>
                        </div>
                    )}
                </div>

                {/* Exit Exam safely tucked away or separate */}
                <button 
                    onClick={onExit}
                    className="text-xs font-bold text-red-400/80 hover:text-red-400 transition-colors uppercase"
                    title="Exit Exam"
                >
                    Exit
                </button>
            </div>
        </div>
    );
};

export default LexifyControls;
