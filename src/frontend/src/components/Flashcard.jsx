import React, { useState, useEffect } from 'react';
import { ChevronRight, Eye, X } from 'lucide-react';
import { getSubjectColor } from '../utils/colors';

const Flashcard = ({ question, onNext, currentIndex, total, onClose }) => {
    const [showAnswer, setShowAnswer] = useState(false);

    useEffect(() => {
        setShowAnswer(false);
    }, [question]);

    if (!question) return null;

    const colorClass = getSubjectColor(question.subject);
    const textColor = colorClass.split(' ').find((c) => c.startsWith('text-'));

    return (
        <div className="fixed inset-0 z-[150] lex-modal-overlay animate-in fade-in duration-200">
            <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" aria-hidden onClick={onClose} />
            <div
                className="glass absolute bottom-[var(--player-height,0px)] left-1/2 flex w-full max-w-3xl -translate-x-1/2 flex-col overflow-hidden rounded-t-2xl border-x border-t border-white/50 bg-white/50 shadow-[0_10px_50px_rgba(0,0,0,0.4)] backdrop-blur-3xl animate-in zoom-in-95 duration-300 dark:border-white/20 dark:bg-slate-900/50 top-[max(0.75rem,env(safe-area-inset-top,0px))] min-h-0 sm:rounded-xl sm:border md:bottom-auto md:top-1/2 md:max-h-[min(90vh,calc(100dvh-var(--player-height,0px)-min(5vh,3rem)))] md:min-h-0 md:-translate-y-1/2 md:rounded-3xl"
                role="dialog"
                aria-modal="true"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="pointer-events-none absolute top-[-20%] left-[-10%] z-0 h-[400px] w-[400px] rounded-full bg-blue-500/20 blur-[100px]" />
                <div className="pointer-events-none absolute right-[-10%] bottom-[-20%] z-0 h-[400px] w-[400px] rounded-full bg-purple-500/20 blur-[100px]" />

                {/* Header — match Bar question modal: subject | counter | year + close */}
                <div className="relative z-10 grid shrink-0 grid-cols-[1fr_auto_1fr] items-center gap-1 border-b border-white/30 bg-white/25 px-1.5 py-1.5 backdrop-blur-sm dark:border-white/10 dark:bg-black/15 sm:px-2 md:px-3">
                    <div className="flex min-w-0 items-center gap-1.5 sm:gap-2">
                        <span className={`min-w-0 truncate text-[15px] font-medium leading-snug md:text-[17px] ${textColor}`}>
                            {question.subject}
                        </span>
                    </div>
                    <div className="flex justify-center justify-self-center">
                        <span className="tabular-nums text-[13px] font-medium text-gray-600 dark:text-gray-400 md:text-sm">
                            {currentIndex + 1} / {total}
                        </span>
                    </div>
                    <div className="flex items-center justify-end gap-1.5 sm:gap-2">
                        <span className="shrink-0 tabular-nums text-[15px] font-medium leading-snug text-gray-900 dark:text-white md:text-[17px]">
                            {question.year}
                        </span>
                        <button
                            type="button"
                            onClick={onClose}
                            className="touch-manipulation flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-red-200/70 bg-red-50/80 text-red-500 transition-all hover:bg-red-100 active:scale-95 dark:border-red-800/60 dark:bg-red-950/40 dark:text-red-400 dark:hover:bg-red-900/50"
                            aria-label="Close"
                        >
                            <X className="h-3.5 w-3.5" strokeWidth={2.25} />
                        </button>
                    </div>
                </div>

                <div className="relative z-10 flex min-h-0 flex-1 flex-col space-y-6 overflow-y-auto p-3 lex-modal-scroll custom-scrollbar sm:p-6 md:space-y-10 md:p-8">
                    <div className="space-y-3 md:space-y-5">
                        <div className="mb-1.5 flex items-center gap-2 drop-shadow-sm md:mb-4">
                            <h4 className="m-0 px-1 text-[10px] font-black uppercase tracking-widest text-gray-500 dark:text-gray-400 md:text-[12px] lg:text-[13px]">
                                Question
                            </h4>
                            <div className="h-px flex-1 bg-gradient-to-r from-gray-200 to-transparent dark:from-white/10 dark:to-transparent" />
                        </div>
                        <p className="px-1 text-[15px] font-medium leading-relaxed text-gray-800 dark:text-gray-100 md:text-[17px] whitespace-pre-wrap">
                            {question.text}
                        </p>

                        {question.subQuestions &&
                            question.subQuestions.map((sub, i) => (
                                <div key={i} className="relative mt-3 pt-4 md:mt-4 md:pt-6">
                                    <div className="absolute top-0 left-0 h-px w-full bg-gradient-to-r from-gray-300 via-gray-200 to-transparent dark:from-white/20 dark:via-white/5 dark:to-transparent" />
                                    <p className="px-1 text-[15px] font-medium leading-relaxed text-gray-800 dark:text-gray-100 md:text-[17px] whitespace-pre-wrap">
                                        {sub.text}
                                    </p>
                                </div>
                            ))}
                    </div>

                    {showAnswer && (
                        <div className="mt-4 animate-in fade-in slide-in-from-bottom-4 space-y-4 duration-500 md:mt-0 md:space-y-6">
                            <div>
                                <div className="mt-2 mb-1.5 flex items-center gap-2 drop-shadow-sm md:mb-4">
                                    <h4 className={`m-0 px-1 text-[10px] font-black uppercase tracking-widest md:text-[12px] lg:text-[13px] ${textColor}`}>
                                        Suggested Answers
                                    </h4>
                                    <div className={`h-px flex-1 bg-gradient-to-r to-transparent ${textColor.replace('text-', 'from-')}`} />
                                </div>
                                <div className="relative overflow-hidden rounded-xl border border-white/60 bg-gradient-to-br from-blue-50/60 to-white/40 p-3 glass shadow-[0_8px_30px_rgb(0,0,0,0.12)] dark:border-white/10 dark:from-slate-800/60 dark:to-slate-900/40 sm:p-5 md:rounded-2xl md:p-8">
                                    <div className="absolute top-0 left-0 h-full w-[4px] bg-gradient-to-b from-blue-400 to-indigo-600 md:w-1.5" />
                                    <p className="text-[15px] leading-relaxed text-gray-800 dark:text-gray-100 md:text-[17px] whitespace-pre-wrap">
                                        {question.answer || 'Answer not available.'}
                                    </p>

                                    {question.subQuestions &&
                                        question.subQuestions.map((sub, i) => (
                                            <div key={i} className="relative pt-4 md:pt-6">
                                                <div className="absolute top-0 left-0 h-px w-full bg-gradient-to-r from-gray-300 via-gray-200 to-transparent dark:from-white/20 dark:via-white/5 dark:to-transparent" />
                                                <p className="text-[15px] leading-relaxed text-gray-800 dark:text-gray-100 md:text-[17px] whitespace-pre-wrap">
                                                    {sub.answer || 'Answer not available.'}
                                                </p>
                                            </div>
                                        ))}
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                <div className="relative z-20 flex shrink-0 flex-col-reverse justify-center gap-2 border-t border-white/30 bg-white/40 p-3 backdrop-blur-2xl shadow-[0_-10px_40px_rgba(0,0,0,0.05)] dark:border-white/10 dark:bg-slate-900/60 sm:flex-row sm:gap-2 md:gap-4 md:p-5">
                    {!showAnswer && (
                        <button
                            type="button"
                            onClick={() => setShowAnswer(true)}
                            className="touch-manipulation flex min-h-[48px] w-full items-center justify-center gap-2 rounded-xl border border-blue-400/50 bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-3 text-sm font-extrabold text-white shadow-lg shadow-blue-500/30 transition-all hover:from-blue-500 hover:to-indigo-500 active:scale-[0.98] sm:w-auto md:px-8 md:py-3"
                        >
                            <Eye size={20} className="shrink-0 md:h-5 md:w-5" />
                            Show Answer
                        </button>
                    )}

                    <button
                        type="button"
                        onClick={onNext}
                        className={`touch-manipulation flex min-h-[48px] w-full items-center justify-center gap-2 rounded-xl px-6 py-3 text-sm font-extrabold shadow-lg transition-all active:scale-[0.98] sm:w-auto md:px-8 md:py-3 ${
                            showAnswer
                                ? 'border border-blue-400/50 bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-blue-500/30 hover:from-blue-500 hover:to-indigo-500'
                                : 'glass border border-white/60 bg-white/60 text-gray-800 backdrop-blur-md hover:bg-white/80 hover:shadow-xl dark:border-white/10 dark:bg-white/10 dark:text-gray-200 dark:hover:bg-white/20'
                        }`}
                    >
                        {showAnswer ? 'Next Question' : 'Skip Question'}
                        <ChevronRight size={20} className="shrink-0 md:h-5 md:w-5" />
                    </button>
                </div>
            </div>
        </div>
    );
};

export default Flashcard;
