import React, { useState } from 'react';

const LexifySidebar = ({ questions, currentIndex, setCurrentIndex, userAnswers, flaggedQuestions, setFlaggedQuestions }) => {
    const [filter, setFilter] = useState('All'); // 'All', 'Unanswered', 'Answered', 'Flagged'

    const answeredCount = questions.filter((_, i) => !!userAnswers[i]?.replace(/<[^>]*>?/gm, '').trim()).length;
    const flaggedCount = flaggedQuestions.size;
    const unansweredCount = questions.length - answeredCount;

    const handleFlagToggle = (index, e) => {
        e.stopPropagation();
        const newFlags = new Set(flaggedQuestions);
        if (newFlags.has(index)) { newFlags.delete(index); } else { newFlags.add(index); }
        setFlaggedQuestions(newFlags);
    };

    const filteredQuestions = questions.map((q, idx) => {
        const isAnswered = !!userAnswers[idx]?.replace(/<[^>]*>?/gm, '').trim();
        const isFlagged = flaggedQuestions.has(idx);
        if (filter === 'Answered' && !isAnswered) return null;
        if (filter === 'Unanswered' && isAnswered) return null;
        if (filter === 'Flagged' && !isFlagged) return null;
        return { q, idx, isAnswered, isFlagged };
    }).filter(Boolean);

    return (
        <div className="w-60 bg-gray-50 border-r border-gray-200 flex flex-col h-full shadow-sm shrink-0">
            {/* Header with Stats */}
            <div className="px-4 py-3 border-b border-gray-200 bg-white">
                <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-gray-700 text-xs uppercase tracking-wider font-serif">Question List</span>
                    <select
                        value={filter}
                        onChange={(e) => setFilter(e.target.value)}
                        className="text-xs p-1 border border-gray-200 rounded bg-white text-gray-600 outline-none cursor-pointer"
                    >
                        <option value="All">All ({questions.length})</option>
                        <option value="Answered">Answered ({answeredCount})</option>
                        <option value="Unanswered">Unanswered ({unansweredCount})</option>
                        <option value="Flagged">Flagged ({flaggedCount})</option>
                    </select>
                </div>
                {/* Mini progress bar */}
                <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                    <div
                        className="h-full bg-blue-500 rounded-full transition-all"
                        style={{ width: `${(answeredCount / questions.length) * 100}%` }}
                    />
                </div>
                <p className="text-[10px] text-gray-400 mt-1">{answeredCount} of {questions.length} answered</p>
            </div>

            {/* Question List */}
            <div className="flex-1 overflow-y-auto py-2 px-2">
                {filteredQuestions.map(({ q, idx, isAnswered, isFlagged }) => {
                    const isActive = currentIndex === idx;
                    return (
                        <div
                            key={idx}
                            onClick={() => setCurrentIndex(idx)}
                            className={`flex items-center gap-3 px-2 py-2 mb-1 cursor-pointer rounded-xl transition-all ${
                                isActive
                                    ? 'bg-blue-50 border border-blue-200'
                                    : 'hover:bg-gray-100 border border-transparent'
                            }`}
                        >
                            {/* Circle Indicator */}
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 border-2 transition-all ${
                                isFlagged
                                    ? 'bg-orange-100 border-orange-400 text-orange-700'
                                    : isAnswered
                                        ? 'bg-blue-500 border-blue-600 text-white'
                                        : isActive
                                            ? 'bg-white border-blue-400 text-blue-600'
                                            : 'bg-white border-gray-300 text-gray-500'
                            }`}>
                                {idx + 1}
                            </div>

                            {/* Subject Label */}
                            <div className="flex-1 min-w-0">
                                <p className={`text-xs truncate ${isActive ? 'text-blue-700 font-bold' : 'text-gray-500'}`}>
                                    {q.subject || `Question ${idx + 1}`}
                                </p>
                                {isAnswered && <p className="text-[10px] text-green-500">✓ Answered</p>}
                                {!isAnswered && <p className="text-[10px] text-gray-300">Unanswered</p>}
                            </div>

                            {/* Flag Button */}
                            <button
                                onClick={(e) => handleFlagToggle(idx, e)}
                                className={`p-1 rounded-lg hover:bg-gray-200 transition-colors flex-shrink-0 ${isFlagged ? 'text-orange-500' : 'text-gray-300 hover:text-gray-400'}`}
                                title={isFlagged ? "Unflag Question" : "Flag for Review"}
                            >
                                <svg width="13" height="13" viewBox="0 0 24 24" fill={isFlagged ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" /><line x1="4" y1="22" x2="4" y2="15" />
                                </svg>
                            </button>
                        </div>
                    );
                })}
            </div>

            {/* Legend */}
            <div className="px-4 py-3 border-t border-gray-200 bg-white text-[10px] text-gray-400 space-y-1">
                <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-blue-500 flex-shrink-0" /> Answered</div>
                <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full border-2 border-gray-300 flex-shrink-0" /> Unanswered</div>
                <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full border-2 border-orange-400 bg-orange-100 flex-shrink-0" /> Flagged for Review</div>
            </div>
        </div>
    );
};

export default LexifySidebar;
