import React, { useState, useEffect } from 'react';

const LexifyControls = ({ onSubmit, onHide, onExit, answeredCount, totalCount }) => {
    const [timeLeft, setTimeLeft] = useState(4 * 60 * 60); // 4 Hours

    useEffect(() => {
        const timer = setInterval(() => {
            setTimeLeft(prev => prev > 0 ? prev - 1 : 0);
        }, 1000);
        return () => clearInterval(timer);
    }, []);

    const formatTime = (seconds) => {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    };

    return (
        <div className="h-14 bg-[#1e293b] text-[#f8fafc] fixed top-0 w-full z-[110] flex items-center justify-between px-4 shadow-sm select-none border-b border-gray-700">
            {/* System Info / Branding */}
            <div className="flex items-center gap-4">
                <span className="font-bold tracking-widest text-[#94a3b8]">LEXIFY<span className="text-white">OS</span></span>
                <div className="w-px h-6 bg-gray-600"></div>
                <div className="flex items-center gap-2 text-sm text-green-400">
                    <span className="w-2.5 h-2.5 rounded-full bg-green-500 animate-pulse"></span>
                    Connected
                </div>
            </div>

            {/* Timer (Center Aligned) */}
            <div className="absolute left-1/2 transform -translate-x-1/2 flex flex-col items-center justify-center">
                <span className="font-mono text-xl font-bold tracking-widest">{formatTime(timeLeft)}</span>
            </div>

            {/* Controls Menu */}
            <div className="flex items-center gap-6">
                <div className="text-xs text-gray-400 text-right">
                    <p>Exam Progress</p>
                    <p className="text-white font-bold">{Math.round((answeredCount / totalCount) * 100) || 0}% ({answeredCount}/{totalCount})</p>
                </div>
                
                <div className="flex items-center gap-3">
                    <button onClick={onExit} className="px-3 py-1.5 text-sm bg-red-900/80 hover:bg-red-800 rounded text-red-100 border border-red-700 transition-colors">
                        Exit Exam
                    </button>
                    <button onClick={onHide} className="px-4 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 rounded text-white border border-gray-500 transition-colors">
                        Hide Exam
                    </button>
                    <button onClick={onSubmit} className="px-4 py-1.5 text-sm bg-green-600 hover:bg-green-500 rounded text-white font-bold transition-colors">
                        Submit Exam
                    </button>
                </div>
            </div>
        </div>
    );
};

export default LexifyControls;
