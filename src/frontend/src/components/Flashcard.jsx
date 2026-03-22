import React, { useState, useEffect } from 'react';
import { ChevronRight, Eye, X } from 'lucide-react';
import { getSubjectColor, getSubjectAnswerColor } from '../utils/colors';

const Flashcard = ({ question, onNext, currentIndex, total, onClose }) => {
    const [showAnswer, setShowAnswer] = useState(false);

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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <div className={`bg-white dark:bg-dark-card rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col animate-in zoom-in-95 duration-200 border-2 ${borderColor}`}>

                {/* Header */}
                <div className="p-6 border-b border-gray-100 dark:border-gray-800 flex justify-between items-start shrink-0">
                    <div>
                        <span className={`inline-block mb-2 text-sm font-bold uppercase tracking-wider ${textColor}`}>
                            {question.subject}
                        </span>
                        <div className="flex items-center gap-3">
                            <h3 className="text-xl font-bold text-gray-900 dark:text-white">
                                {question.year} Bar Exam Question {question.source_label && `(${question.source_label})`}
                            </h3>
                            <span className="text-sm text-gray-500 dark:text-gray-400 font-medium px-2 py-0.5 bg-gray-100 dark:bg-gray-800 rounded-full">
                                {currentIndex + 1} / {total}
                            </span>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 transition-colors"
                    >
                        <X size={24} />
                    </button>
                </div>

                {/* Content - Scrollable */}
                <div className="flex-1 overflow-y-auto p-6 space-y-8">
                    {/* Question */}
                    <div className="space-y-4">
                        <h4 className="text-sm font-semibold text-gray-500 uppercase mb-3 px-1">Question</h4>
                        <p className="text-lg leading-relaxed text-gray-800 dark:text-gray-100 whitespace-pre-wrap">
                            {question.text}
                        </p>
                        
                        {/* Render extra sub-questions if available */}
                        {question.subQuestions && question.subQuestions.map((sub, i) => (
                          <p key={i} className="text-lg leading-relaxed text-gray-800 dark:text-gray-100 whitespace-pre-wrap border-t border-gray-100 dark:border-gray-800 pt-4">
                            {sub.text}
                          </p>
                        ))}
                    </div>

                    {/* Answer (Conditional) */}
                    {showAnswer && (
                        <div className="animate-in fade-in slide-in-from-bottom-4 duration-300 space-y-6">
                            <div>
                                <h4 className={`text-sm font-semibold uppercase mb-3 ${textColor} px-1`}>Suggested Answers</h4>
                                <div className={`p-6 rounded-xl ${answerBgClass} border border-transparent dark:border-white/5 space-y-6`}>
                                    <p className="text-base leading-relaxed text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
                                        {question.answer || "Answer not available."}
                                    </p>
                                    
                                    {/* Render answers for sub-questions if they exist */}
                                    {question.subQuestions && question.subQuestions.map((sub, i) => (
                                      <div key={i} className="pt-6 border-t border-black/10 dark:border-white/10">
                                        <p className="text-base leading-relaxed text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
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
                <div className="p-6 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50 flex justify-center gap-4 shrink-0">
                    {!showAnswer && (
                        <button
                            onClick={() => setShowAnswer(true)}
                            className="flex items-center gap-2 px-8 py-2 rounded-lg bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium shadow-sm transition-all transform hover:scale-105"
                        >
                            <Eye size={20} />
                            Show Answer
                        </button>
                    )}

                    <button
                        onClick={onNext}
                        className={`flex items-center gap-2 px-8 py-2 rounded-lg text-sm font-medium shadow-sm transition-all transform hover:scale-105 ${showAnswer
                            ? "bg-blue-500 hover:bg-blue-600 text-white"
                            : "bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700"
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
