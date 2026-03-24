import React, { useState, useEffect } from 'react';
import { ChevronRight, Eye, X, Zap } from 'lucide-react';
import { getSubjectColor, getSubjectAnswerColor } from '../utils/colors';

const Flashcard = ({ question, onNext, currentIndex, total, onClose }) => {
    const [showAnswer, setShowAnswer] = useState(false);
    const [isCompactView, setIsCompactView] = useState(false);

    // Reset state when question changes
    useEffect(() => {
        setShowAnswer(false);
    }, [question]);

    if (!question) return null;

    const colorClass = getSubjectColor(question.subject);
    const textColor = colorClass.split(' ').find(c => c.startsWith('text-'));
    const borderColor = colorClass.split(' ').find(c => c.startsWith('border-'));

    const answerBgClass = getSubjectAnswerColor(question.subject);

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pb-[var(--player-height,0px)] bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <div className={`glass bg-white/50 dark:bg-slate-900/50 backdrop-blur-3xl rounded-3xl shadow-[0_10px_50px_rgba(0,0,0,0.4)] w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col animate-in zoom-in-95 duration-300 border border-white/50 dark:border-white/20 relative`}>

                {/* Ambient glow orbs inside the modal to drive the glass effect */}
                <div className="absolute top-[-20%] left-[-10%] w-[400px] h-[400px] bg-blue-500/20 rounded-full blur-[100px] pointer-events-none z-0"></div>
                <div className="absolute bottom-[-20%] right-[-10%] w-[400px] h-[400px] bg-purple-500/20 rounded-full blur-[100px] pointer-events-none z-0"></div>

                {/* Header */}
                <div className="p-4 sm:p-6 md:p-8 border-b border-white/30 dark:border-white/10 flex justify-between items-start shrink-0 relative z-10 bg-white/20 dark:bg-black/10 backdrop-blur-sm">
                    <div className="min-w-0 flex-1">
                        <span className={`inline-block mb-2 sm:mb-3 px-3 py-1 rounded-md text-[10px] sm:text-[11px] md:text-xs font-black uppercase tracking-widest glass bg-white/40 dark:bg-white/10 border border-white/40 dark:border-white/10 shadow-sm ${textColor} ${isCompactView ? 'hidden sm:inline-block' : 'inline-block'}`}>
                            {question.subject}
                        </span>
                        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                            <h3 className="text-base sm:text-lg md:text-xl font-extrabold text-gray-900 dark:text-white flex items-center gap-2 leading-tight">
                                {isCompactView ? `${question.year} ${question.subject}` : `${question.year} Bar Exam Question`} 
                                {question.source_label && !isCompactView && <span className="text-gray-500 font-medium text-xs sm:text-sm ml-2">({question.source_label})</span>}
                            </h3>
                            <span className="text-[10px] sm:text-xs md:text-sm text-gray-800 dark:text-gray-200 font-bold px-2 sm:px-3 py-0.5 sm:py-1 glass bg-white/60 dark:bg-black/30 border border-white/50 dark:border-white/10 shadow-inner rounded-full shrink-0">
                                {currentIndex + 1} <span className="opacity-50 mx-1">/</span> {total}
                            </span>
                        </div>
                    </div>
                    <div className="flex items-center gap-1 sm:gap-2 shrink-0 ml-2">
                         <button
                            className="p-1.5 rounded-full text-gray-400 hover:text-amber-600 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-all border border-transparent shadow-sm"
                            onClick={() => setIsCompactView(v => !v)}
                            title={isCompactView ? 'Show Full Labels' : 'Compact View (Hide Labels)'}
                        >
                            <Zap size={18} className={isCompactView ? 'text-amber-500 fill-amber-500' : ''} />
                        </button>
                        <button
                            onClick={onClose}
                            className="p-1.5 sm:p-2 rounded-full glass hover:bg-white/60 dark:hover:bg-white/20 text-gray-800 dark:text-gray-300 transition-all border border-transparent shadow-sm hover:scale-105"
                        >
                            <X size={20} sm={24} />
                        </button>
                    </div>
                </div>

                {/* Content - Scrollable */}
                <div className={`flex-1 overflow-y-auto p-4 sm:p-6 md:p-8 relative z-10 custom-scrollbar ${isCompactView ? 'space-y-6' : 'space-y-10'}`}>
                    {/* Question */}
                    <div className={isCompactView ? "space-y-3" : "space-y-5"}>
                        <h4 className={`text-[13px] font-black text-gray-500 dark:text-gray-400 uppercase tracking-widest px-1 drop-shadow-sm ${isCompactView ? 'hidden' : 'block'}`}>Question</h4>
                        <p className={`${isCompactView ? 'text-[16px]' : 'text-[17px]'} leading-relaxed text-gray-800 dark:text-gray-100 whitespace-pre-wrap font-medium`}>
                            {question.text}
                        </p>
                        
                        {/* Render extra sub-questions if available */}
                        {question.subQuestions && question.subQuestions.map((sub, i) => (
                          <div key={i} className={`relative ${isCompactView ? 'pt-4 mt-2' : 'pt-6 mt-4'}`}>
                            <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-gray-300 via-gray-200 to-transparent dark:from-white/20 dark:via-white/5 dark:to-transparent"></div>
                            <p className={`${isCompactView ? 'text-[16px]' : 'text-[17px]'} leading-relaxed text-gray-800 dark:text-gray-100 whitespace-pre-wrap font-medium`}>
                              {sub.text}
                            </p>
                          </div>
                        ))}
                    </div>

                    {/* Answer (Conditional) */}
                    {showAnswer && (
                        <div className={`animate-in fade-in slide-in-from-bottom-4 duration-500 ${isCompactView ? 'space-y-4' : 'space-y-6'}`}>
                            <div>
                                <h4 className={`text-[13px] font-black uppercase tracking-widest ${isCompactView ? 'mb-2' : 'mb-4'} ${textColor} px-1 drop-shadow-sm`}>
                                    {isCompactView ? "" : "Suggested Answers"}
                                </h4>
                                <div className={`relative overflow-hidden glass bg-gradient-to-br from-blue-50/60 to-white/40 dark:from-slate-800/60 dark:to-slate-900/40 p-5 sm:p-6 md:p-8 rounded-2xl border border-white/60 dark:border-white/10 shadow-[0_8px_30px_rgb(0,0,0,0.12)] ${isCompactView ? 'space-y-4' : 'space-y-6'}`}>
                                    <div className="absolute top-0 left-0 w-1.5 h-full bg-gradient-to-b from-blue-400 to-indigo-600"></div>
                                    <p className={`${isCompactView ? 'text-[16px]' : 'text-[17px]'} leading-relaxed text-gray-800 dark:text-gray-100 whitespace-pre-wrap`}>
                                        {question.answer || "Answer not available."}
                                    </p>
                                    
                                    {/* Render answers for sub-questions if they exist */}
                                    {question.subQuestions && question.subQuestions.map((sub, i) => (
                                      <div key={i} className={`relative ${isCompactView ? 'pt-4' : 'pt-6'}`}>
                                        <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-gray-300 via-gray-200 to-transparent dark:from-white/20 dark:via-white/5 dark:to-transparent"></div>
                                        <p className={`${isCompactView ? 'text-[16px]' : 'text-[17px]'} leading-relaxed text-gray-800 dark:text-gray-100 whitespace-pre-wrap`}>
                                          {sub.answer || "Answer not available."}
                                        </p>
                                      </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer Actions */}
                <div className="p-5 md:p-6 border-t border-white/30 dark:border-white/10 bg-white/40 dark:bg-slate-900/60 flex justify-center gap-4 shrink-0 backdrop-blur-2xl relative z-20 shadow-[0_-10px_40px_rgba(0,0,0,0.05)]">
                    {!showAnswer && (
                        <button
                            onClick={() => setShowAnswer(true)}
                            className="flex items-center gap-2 px-8 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-sm font-extrabold shadow-lg shadow-blue-500/30 transition-all transform hover:scale-[1.03] active:scale-95 border border-blue-400/50"
                        >
                            <Eye size={20} />
                            Show Answer
                        </button>
                    )}

                    <button
                        onClick={onNext}
                        className={`flex items-center gap-2 px-8 py-3 rounded-xl text-sm font-extrabold shadow-lg transition-all transform hover:scale-[1.03] active:scale-95 ${showAnswer
                            ? "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-blue-500/30 border border-blue-400/50"
                            : "glass bg-white/60 dark:bg-white/10 backdrop-blur-md border border-white/60 dark:border-white/10 text-gray-800 dark:text-gray-200 hover:bg-white/80 dark:hover:bg-white/20 hover:shadow-xl"
                            }`}
                    >
                        {showAnswer ? "Next Question" : "Skip Question"}
                        <ChevronRight size={20} />
                    </button>
                </div>
            </div>
        </div>
    );
};

export default Flashcard;
