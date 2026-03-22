import React, { useState } from 'react';

const LexifySidebar = ({ questions, currentIndex, setCurrentIndex, userAnswers, flaggedQuestions, setFlaggedQuestions }) => {
    const [filter, setFilter] = useState('All'); // 'All', 'Unanswered', 'Answered', 'Flagged'

    const handleFlagToggle = (index, e) => {
        e.stopPropagation();
        const newFlags = new Set(flaggedQuestions);
        if (newFlags.has(index)) {
            newFlags.delete(index);
        } else {
            newFlags.add(index);
        }
        setFlaggedQuestions(newFlags);
    };

    return (
        <div className="w-64 bg-white border-r border-gray-300 flex flex-col h-full shadow-sm">
            <div className="p-4 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
                <span className="font-bold text-gray-700 uppercase tracking-wider text-sm">Questions</span>
                <select 
                    value={filter} 
                    onChange={(e) => setFilter(e.target.value)}
                    className="text-xs p-1 border border-gray-300 rounded bg-white text-gray-700 outline-none"
                >
                    <option value="All">All</option>
                    <option value="Answered">Answered</option>
                    <option value="Unanswered">Unanswered</option>
                    <option value="Flagged">Flagged</option>
                </select>
            </div>

            <div className="flex-1 overflow-y-auto p-2">
                {questions.map((q, idx) => {
                    const isAnswered = !!userAnswers[idx] && userAnswers[idx].trim().length > 0;
                    const isFlagged = flaggedQuestions.has(idx);
                    const isActive = currentIndex === idx;

                    // Filtering Logic
                    if (filter === 'Answered' && !isAnswered) return null;
                    if (filter === 'Unanswered' && isAnswered) return null;
                    if (filter === 'Flagged' && !isFlagged) return null;

                    return (
                        <div 
                            key={idx}
                            onClick={() => setCurrentIndex(idx)}
                            className={`flex items-center gap-3 p-2 mb-1 cursor-pointer rounded transition-colors ${isActive ? 'bg-blue-100 font-bold' : 'hover:bg-gray-100'}`}
                        >
                            <div className="relative flex items-center justify-center">
                                {/* The Circle Indicator */}
                                <div className={`w-8 h-8 rounded-full border-2 flex items-center justify-center text-sm
                                    ${isAnswered ? 'bg-blue-500 border-blue-600 text-white' : 'bg-gray-100 border-gray-400 text-gray-600'}
                                    ${isActive && !isAnswered ? 'border-blue-500' : ''}
                                `}>
                                    {idx + 1}
                                </div>
                            </div>
                            
                            {/* The Question Preview Label */}
                            <div className="flex-1 min-w-0">
                                <p className="text-xs text-gray-600 truncate">
                                    {q.subject || "Question"}
                                </p>
                            </div>

                            {/* Flag Icon */}
                            <button 
                                onClick={(e) => handleFlagToggle(idx, e)}
                                className={`p-1 rounded hover:bg-gray-200 transition-colors ${isFlagged ? 'text-orange-500' : 'text-gray-300'}`}
                                title={isFlagged ? "Unflag Question" : "Flag Question"}
                            >
                                <svg width="16" height="16" viewBox="0 0 24 24" fill={isFlagged ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"></path>
                                    <line x1="4" y1="22" x2="4" y2="15"></line>
                                </svg>
                            </button>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default LexifySidebar;
