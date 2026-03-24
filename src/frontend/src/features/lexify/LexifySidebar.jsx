import React, { useState } from 'react';

const LexifySidebar = ({ questions, currentIndex, setCurrentIndex, userAnswers, flaggedQuestions, setFlaggedQuestions }) => {
    const [filter, setFilter] = useState('All'); // 'All', 'Unanswered', 'Answered', 'Flagged'
    const [showFilterDropdown, setShowFilterDropdown] = useState(false);

    const answeredCount = questions.filter((_, i) => !!userAnswers[i]?.replace(/<[^>]*>?/gm, '').trim()).length;
    const flaggedCount = flaggedQuestions.size;

    const filteredQuestions = questions.map((q, idx) => {
        const isAnswered = !!userAnswers[idx]?.replace(/<[^>]*>?/gm, '').trim();
        const isFlagged = flaggedQuestions.has(idx);
        if (filter === 'Answered' && !isAnswered) return null;
        if (filter === 'Unanswered' && isAnswered) return null;
        if (filter === 'Flagged' && !isFlagged) return null;
        return { q, idx, isAnswered, isFlagged };
    }).filter(Boolean);

    return (
        <div className="w-16 bg-[#f4f6f8] border-r border-[#d5dbe1] flex flex-col h-full shadow-sm select-none relative font-sans">
            
            {/* Filter Header Item 3 */}
            <div className="relative border-b border-[#d5dbe1] bg-[#f4f6f8]">
                <button 
                    onClick={() => setShowFilterDropdown(!showFilterDropdown)}
                    className="w-full text-left px-2 py-3 text-[10px] font-extrabold text-slate-500 hover:text-slate-700 tracking-wider flex items-center justify-between uppercase"
                >
                    FILTER <span className="text-[10px] scale-90 text-slate-400">❯</span>
                </button>
                
                {showFilterDropdown && (
                    <div className="absolute left-16 top-0 z-50 bg-[#212b36] border border-gray-600 rounded shadow-xl w-36 py-1 overflow-hidden">
                        {['All', 'Answered', 'Unanswered', 'Flagged'].map(t => (
                            <button 
                                key={t}
                                onClick={() => { setFilter(t); setShowFilterDropdown(false); }}
                                className={`w-full text-left px-4 py-1.5 text-xs hover:bg-white/10 transition text-white ${filter === t ? 'font-bold text-[#3fa9f5]' : ''}`}
                            >
                                {t}
                            </button>
                        ))}
                    </div>
                )}
            </div>

            {/* Question List Item 4 */}
            <div className="flex-1 overflow-y-auto py-3 flex flex-col items-center gap-3 overflow-x-hidden">
                {filteredQuestions.map(({ idx, isAnswered, isFlagged }) => {
                    const isActive = currentIndex === idx;

                    return (
                        <div
                            key={idx}
                            onClick={() => setCurrentIndex(idx)}
                            className="relative flex items-center justify-center cursor-pointer group"
                        >
                            {/* Blue active left-bar border guide (if applicable in real app, useful indicator) */}
                            {isActive && <div className="absolute left-0 top-0 bottom-0 w-1 bg-[#3fa9f5]" />}

                            {/* Circular Frame item 4 and 5 */}
                            <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold flex-shrink-0 border-2 transition-all relative ${
                                isAnswered
                                    ? 'bg-[#3fa9f5] border-[#3fa9f5] text-white shadow-sm'
                                    : 'bg-white border-[#b0bbc5] text-[#2c3e50]'
                            } ${isActive ? 'ring-2 ring-offset-1 ring-[#3fa9f5]/60' : ''}`}>
                                {idx + 1}

                                {/* Orange Flag Badge (Overlap bottom-right item 5) */}
                                {isFlagged && (
                                    <div className="absolute bottom-[-3px] right-[-3px] w-4 h-4 bg-orange-500 rounded-sm flex items-center justify-center shadow" title="Flagged">
                                        <svg className="w-2.5 h-2.5 text-white" fill="currentColor" viewBox="0 0 24 24">
                                            <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
                                        </svg>
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
            
            {/* Legend or Indicator for answered if need to save space, otherwise it floats implicitly */}
        </div>
    );
};

export default LexifySidebar;
