import React, { useState, useEffect, useCallback } from 'react';

const LexifyControls = ({ onSubmit, onHide, onExit, onToggleNotes, notesOpen, answeredCount, totalCount, spellCheck, onToggleSpellCheck, alarmTime }) => {
    const [timeLeft, setTimeLeft] = useState(4 * 60 * 60); // 4 Hours in seconds
    const [alarmFired, setAlarmFired] = useState(false);
    const [showExamMenu, setShowExamMenu] = useState(false);

    // Parse alarmTime string (HH:MM:SS) into seconds
    const alarmSeconds = useCallback(() => {
        if (!alarmTime) return 30 * 60; // default 30 min
        const parts = alarmTime.split(':').map(Number);
        if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
        return 30 * 60;
    }, [alarmTime]);

    useEffect(() => {
        const timer = setInterval(() => {
            setTimeLeft(prev => {
                const next = prev > 0 ? prev - 1 : 0;
                // Fire alarm when time reaches the alarm threshold
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

    // Timer color logic
    const timerColor = timeLeft <= 5 * 60
        ? 'text-red-400 animate-pulse'
        : timeLeft <= 10 * 60
            ? 'text-red-400'
            : timeLeft <= 30 * 60
                ? 'text-yellow-400'
                : 'text-white';

    return (
        <div className="h-14 bg-[#1e293b] text-[#f8fafc] fixed top-0 w-full z-[110] flex items-center justify-between px-4 shadow-sm select-none border-b border-gray-700">
            {/* Left: Branding & Status */}
            <div className="flex items-center gap-4">
                <span className="font-bold tracking-widest text-[#94a3b8]">LEXIFY<span className="text-[#e94560]">OS</span></span>
                <div className="w-px h-6 bg-gray-600" />
                <div className="flex items-center gap-2 text-sm text-green-400">
                    <span className="w-2.5 h-2.5 rounded-full bg-green-500 animate-pulse" />
                    Secure Mode
                </div>
            </div>

            {/* Center: Timer */}
            <div className="absolute left-1/2 transform -translate-x-1/2 flex flex-col items-center">
                <span className={`font-mono text-xl font-bold tracking-widest ${timerColor}`}>{formatTime(timeLeft)}</span>
                {timeLeft <= 30 * 60 && (
                    <span className="text-[10px] text-white/40 uppercase tracking-widest">
                        {timeLeft <= 5 * 60 ? '⚠ CRITICAL' : timeLeft <= 10 * 60 ? '⚠ Low Time' : '⏰ 30min Warning'}
                    </span>
                )}
            </div>

            {/* Right: Controls */}
            <div className="flex items-center gap-4">
                {/* Progress */}
                <div className="text-xs text-gray-400 text-right hidden sm:block">
                    <p>Progress</p>
                    <p className="text-white font-bold">{answeredCount}/{totalCount} answered</p>
                </div>

                <div className="w-px h-6 bg-gray-600" />

                {/* Spell Check Toggle */}
                <button
                    onClick={onToggleSpellCheck}
                    className={`px-3 py-1.5 text-xs rounded border transition-colors ${spellCheck ? 'bg-blue-600/30 border-blue-500/50 text-blue-300' : 'bg-gray-700 border-gray-600 text-gray-400'}`}
                    title="Toggle Spell Check"
                >
                    {spellCheck ? 'ABC✓' : 'ABC'}
                </button>

                {/* Tool Kit (Scratchpad) */}
                <button
                    onClick={onToggleNotes}
                    className={`px-3 py-1.5 text-xs rounded border transition-colors ${notesOpen ? 'bg-amber-500/20 border-amber-500/40 text-amber-300' : 'bg-gray-700 border-gray-600 text-gray-400 hover:text-white'}`}
                    title="Open Scratchpad / Notes"
                >
                    📋 Tool Kit
                </button>

                {/* Exam Menu Dropdown */}
                <div className="relative">
                    <button
                        onClick={() => setShowExamMenu(!showExamMenu)}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 rounded border border-gray-600 text-gray-300 transition-colors"
                    >
                        Exam ▾
                    </button>
                    {showExamMenu && (
                        <div className="absolute right-0 top-9 z-50 bg-[#1e293b] border border-gray-600 rounded-xl shadow-2xl w-40 py-1 overflow-hidden">
                            <button onClick={() => { onHide(); setShowExamMenu(false); }} className="w-full text-left px-4 py-2 text-sm hover:bg-white/5 transition text-gray-300">Hide Exam</button>
                            <button onClick={() => { onSubmit(); setShowExamMenu(false); }} className="w-full text-left px-4 py-2 text-sm hover:bg-white/5 transition text-green-400 font-bold">Submit Exam</button>
                            <hr className="border-gray-600 my-1" />
                            <button onClick={() => { onExit(); setShowExamMenu(false); }} className="w-full text-left px-4 py-2 text-sm hover:bg-red-500/10 transition text-red-400">Exit Exam</button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default LexifyControls;
