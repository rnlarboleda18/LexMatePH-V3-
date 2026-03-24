import React, { useState, useRef } from 'react';

const LexifyNotes = ({ onClose }) => {
    const [notes, setNotes] = useState('');
    const [isFullscreen, setIsFullscreen] = useState(false);
    const textAreaRef = useRef(null);

    const charCount = notes.length;
    const wordCount = notes.trim() ? notes.trim().split(/\s+/).length : 0;

    return (
        <div className={`
            fixed z-[150] bg-[#1e293b] border border-white/10 shadow-2xl flex flex-col
            transition-all duration-300 ease-in-out
            ${isFullscreen
                ? 'inset-0 rounded-none'
                : 'bottom-6 right-6 w-[420px] h-[380px] rounded-2xl'
            }
        `}>
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 select-none">
                <div className="flex items-center gap-2">
                    <span className="text-base">📋</span>
                    <span className="text-sm font-bold text-white">Scratchpad / Notes</span>
                    <span className="text-xs text-white/30 ml-1">— not saved to exam</span>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setIsFullscreen(!isFullscreen)}
                        className="p-1.5 text-white/40 hover:text-white hover:bg-white/10 rounded-lg transition text-xs"
                        title={isFullscreen ? 'Minimize' : 'Maximize'}
                    >
                        {isFullscreen ? '⊟' : '⊞'}
                    </button>
                    <button
                        onClick={onClose}
                        className="p-1.5 text-white/40 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition"
                        title="Close Scratchpad"
                    >
                        ✕
                    </button>
                </div>
            </div>

            {/* Warning Banner */}
            <div className="px-3 py-1.5 bg-amber-500/10 border-b border-amber-500/20">
                <p className="text-xs text-amber-400">⚠ Draft notes only — this scratchpad is <strong>NOT</strong> submitted with your exam.</p>
            </div>

            {/* Notes Textarea */}
            <textarea
                ref={textAreaRef}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Use this scratchpad to outline your answers, jot down key laws, or organize your thoughts before writing. This content will NOT be submitted.

Example:
Q1 Civil Law — Contract of Sale
- Art. 1458 CC
- Consent, Object, Cause
- Defects: Voidable, Void...
"
                className="flex-1 bg-transparent text-white/80 text-sm p-4 resize-none outline-none leading-relaxed placeholder:text-white/20 font-mono"
                spellCheck={false}
            />

            {/* Footer Stats */}
            <div className="flex items-center justify-between px-4 py-2 border-t border-white/10 text-xs text-white/30 select-none">
                <span>{wordCount} words • {charCount} characters</span>
                <button
                    onClick={() => {
                        if (window.confirm('Clear all scratchpad notes?')) setNotes('');
                    }}
                    className="text-red-400/60 hover:text-red-400 transition"
                >
                    Clear
                </button>
            </div>
        </div>
    );
};

export default LexifyNotes;
