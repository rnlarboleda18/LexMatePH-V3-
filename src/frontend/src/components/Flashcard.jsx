import React, { useState, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { ChevronRight, RotateCcw, X } from 'lucide-react';
import { getSubjectColor } from '../utils/colors';
import { normalizeBarSubject } from '../utils/subjectNormalize';
import { closeModalAbsorbingGhostTap } from '../utils/modalClose';

const Flashcard = ({ variant = 'concepts', card, onNext, currentIndex, total, onClose }) => {
    const [isFlipped, setIsFlipped] = useState(false);

    useEffect(() => {
        setIsFlipped(false);
    }, [card]);

    if (!card) return null;

    const isBar = variant === 'bar';

    const sources = card.sources || [];
    const primarySubject = isBar
        ? normalizeBarSubject(card.subject) || card.subject || '—'
        : sources.length
          ? normalizeBarSubject(sources[0].subject) || sources[0].subject || '—'
          : '—';
    const headerDate = isBar ? String(card.year ?? '—') : sources[0]?.date_str || '—';

    const colorClass = getSubjectColor(primarySubject);
    const textColor = colorClass.split(' ').find((c) => c.startsWith('text-'));

    const handleClose = useCallback(
        (e) => {
            e?.preventDefault?.();
            e?.stopPropagation?.();
            closeModalAbsorbingGhostTap(onClose);
        },
        [onClose]
    );

    return createPortal(
        <div className="fixed inset-0 z-[520] lex-modal-overlay animate-in fade-in duration-200">
            <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" aria-hidden onClick={handleClose} />
            <div
                className="glass absolute bottom-[var(--player-height,0px)] left-1/2 flex w-full max-w-3xl -translate-x-1/2 flex-col overflow-hidden rounded-t-2xl border-x border-t border-white/50 bg-white/50 shadow-[0_10px_50px_rgba(0,0,0,0.4)] backdrop-blur-3xl animate-in zoom-in-95 duration-300 dark:border-white/20 dark:bg-slate-900/50 top-[max(0.75rem,env(safe-area-inset-top,0px))] min-h-0 max-h-[calc(100dvh-var(--player-height,0px)-max(0.75rem,env(safe-area-inset-top,0px)))] sm:rounded-xl sm:border md:bottom-auto md:top-1/2 md:h-[min(92dvh,calc(100dvh-var(--player-height,0px)-1.25rem))] md:max-h-[min(92dvh,calc(100dvh-var(--player-height,0px)-1.25rem))] md:min-h-0 md:-translate-y-1/2 md:rounded-3xl"
                role="dialog"
                aria-modal="true"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="pointer-events-none absolute top-[-20%] left-[-10%] z-0 h-[400px] w-[400px] rounded-full bg-blue-500/20 blur-[100px]" />
                <div className="pointer-events-none absolute right-[-10%] bottom-[-20%] z-0 h-[400px] w-[400px] rounded-full bg-purple-500/20 blur-[100px]" />

                <div className="relative z-10 grid shrink-0 grid-cols-[1fr_auto_1fr] items-center gap-1 border-b border-white/30 bg-white/25 px-1.5 py-1.5 backdrop-blur-sm dark:border-white/10 dark:bg-black/15 sm:px-2 md:px-3">
                    <div className="flex min-w-0 items-center gap-1.5 sm:gap-2">
                        <span className={`min-w-0 truncate text-[15px] font-medium leading-snug md:text-[17px] ${textColor}`}>
                            {primarySubject}
                        </span>
                        {isBar && (
                            <span className="shrink-0 rounded-md bg-emerald-500/15 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-emerald-800 dark:text-emerald-300">
                                Bar
                            </span>
                        )}
                    </div>
                    <div className="flex justify-center justify-self-center">
                        <span className="tabular-nums text-[13px] font-medium text-gray-600 dark:text-gray-400 md:text-sm">
                            {currentIndex + 1} / {total}
                        </span>
                    </div>
                    <div className="flex items-center justify-end gap-1.5 sm:gap-2">
                        <span className="shrink-0 tabular-nums text-[15px] font-medium leading-snug text-gray-900 dark:text-white md:text-[17px]">
                            {headerDate}
                        </span>
                        <button
                            type="button"
                            onClick={handleClose}
                            className="touch-manipulation flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-red-200/70 bg-red-50/80 text-red-500 transition-all hover:bg-red-100 active:scale-95 dark:border-red-800/60 dark:bg-red-950/40 dark:text-red-400 dark:hover:bg-red-900/50"
                            aria-label="Close"
                        >
                            <X className="h-3.5 w-3.5" strokeWidth={2.25} />
                        </button>
                    </div>
                </div>

                <div className="relative z-10 flex min-h-0 flex-1 flex-col overflow-hidden p-3 sm:p-6 md:p-8">
                    <div className="relative mx-auto flex min-h-0 w-full max-w-xl flex-1 flex-col [perspective:1200px]">
                        <button
                            type="button"
                            onClick={() => setIsFlipped((f) => !f)}
                            className="relative flex h-full min-h-0 w-full flex-1 flex-col text-left outline-none transition-transform duration-500 [transform-style:preserve-3d] sm:min-h-[280px]"
                            style={{
                                transform: isFlipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
                            }}
                            aria-label={isFlipped ? 'Show front' : 'Show back'}
                        >
                            {/* Front */}
                            <div
                                className="absolute inset-0 flex h-full min-h-full flex-col overflow-hidden rounded-2xl border border-white/60 bg-gradient-to-br from-slate-50/90 to-white/80 p-5 shadow-lg backdrop-blur-sm [backface-visibility:hidden] dark:border-white/10 dark:from-slate-800/90 dark:to-slate-900/80 md:p-8"
                                style={{ WebkitBackfaceVisibility: 'hidden' }}
                            >
                                <span className="mb-2 shrink-0 text-[10px] font-black uppercase tracking-widest text-indigo-600 dark:text-indigo-400">
                                    {isBar ? 'Question' : 'Key legal concept'}
                                </span>
                                <div className="flex min-h-0 flex-1 flex-col justify-center py-4">
                                    <p className="text-center text-[17px] font-semibold leading-relaxed text-gray-900 dark:text-gray-50 md:text-xl whitespace-pre-wrap break-words sm:text-left">
                                        {isBar ? card.text : card.term}
                                    </p>
                                    {isBar &&
                                        card.subQuestions?.map((sub, i) => (
                                            <p
                                                key={i}
                                                className="mt-4 border-t border-gray-200 pt-4 text-left text-[15px] font-medium leading-relaxed text-gray-800 dark:text-gray-200 dark:border-white/10 whitespace-pre-wrap break-words"
                                            >
                                                {sub.text}
                                            </p>
                                        ))}
                                </div>
                                <span className="mt-auto shrink-0 pt-2 text-center text-xs text-gray-500 dark:text-gray-400">
                                    Tap card to flip
                                </span>
                            </div>
                            {/* Back */}
                            <div
                                className="absolute inset-0 flex h-full min-h-full flex-col overflow-hidden rounded-2xl border border-white/60 bg-gradient-to-br from-indigo-50/90 to-violet-50/80 shadow-lg [backface-visibility:hidden] [transform:rotateY(180deg)] dark:border-white/10 dark:from-indigo-950/50 dark:to-slate-900/80"
                                style={{ WebkitBackfaceVisibility: 'hidden' }}
                            >
                                {isBar ? (
                                    <div className="flex h-full min-h-0 flex-col overflow-y-auto overflow-x-hidden p-5 md:p-8 lex-modal-scroll custom-scrollbar">
                                        <span className={`mb-3 shrink-0 text-[10px] font-black uppercase tracking-widest ${textColor}`}>
                                            Suggested answers
                                        </span>
                                        <p className="text-[15px] leading-relaxed text-gray-800 dark:text-gray-100 md:text-[17px] whitespace-pre-wrap break-words">
                                            {card.answer || 'Answer not available.'}
                                        </p>
                                        {card.subQuestions?.map((sub, i) => (
                                            <div key={i} className="relative mt-4 border-t border-gray-200 pt-4 dark:border-white/10">
                                                <p className="text-[15px] leading-relaxed text-gray-800 dark:text-gray-100 md:text-[17px] whitespace-pre-wrap break-words">
                                                    {sub.answer || 'Answer not available.'}
                                                </p>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    /* One scroll region fills the card back: grow to use all space, scroll only when content exceeds it */
                                    <div className="flex h-full min-h-0 flex-col overflow-y-auto overflow-x-hidden px-5 py-5 md:px-8 md:py-6 lex-modal-scroll custom-scrollbar">
                                        <span className={`mb-3 shrink-0 text-[10px] font-black uppercase tracking-widest ${textColor}`}>
                                            Definition
                                        </span>
                                        <p className="text-[15px] leading-relaxed text-gray-800 dark:text-gray-100 md:text-[17px] whitespace-pre-wrap break-words">
                                            {card.definition || 'No definition stored for this concept.'}
                                        </p>
                                        {sources.length > 0 && (
                                            <>
                                                <span className="mb-2 mt-8 block text-[10px] font-black uppercase tracking-widest text-gray-500 dark:text-gray-400">
                                                    Mentioned in
                                                </span>
                                                <ul className="space-y-3 pb-2">
                                                    {sources.map((src) => (
                                                        <li
                                                            key={`${src.case_id}-${src.case_number}`}
                                                            className="rounded-lg border border-white/50 bg-white/40 p-3 text-sm dark:border-white/10 dark:bg-black/20"
                                                        >
                                                            <div className="font-semibold text-gray-900 dark:text-gray-100 line-clamp-2">
                                                                {src.title || '—'}
                                                            </div>
                                                            <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-600 dark:text-gray-300">
                                                                <span className="font-mono tabular-nums">{src.case_number || '—'}</span>
                                                                <span>{src.date_str || '—'}</span>
                                                                <span className="font-medium text-indigo-700 dark:text-indigo-300">
                                                                    {normalizeBarSubject(src.subject) || src.subject || '—'}
                                                                </span>
                                                            </div>
                                                        </li>
                                                    ))}
                                                </ul>
                                            </>
                                        )}
                                    </div>
                                )}
                            </div>
                        </button>
                    </div>
                </div>

                <div className="relative z-20 flex shrink-0 flex-col-reverse justify-center gap-2 border-t border-white/30 bg-white/40 p-3 backdrop-blur-2xl shadow-[0_-10px_40px_rgba(0,0,0,0.05)] dark:border-white/10 dark:bg-slate-900/60 sm:flex-row sm:gap-2 md:gap-4 md:p-5">
                    <button
                        type="button"
                        onClick={() => setIsFlipped((f) => !f)}
                        className="touch-manipulation flex min-h-[48px] w-full items-center justify-center gap-2 rounded-xl border border-white/60 bg-white/70 px-6 py-3 text-sm font-extrabold text-gray-800 shadow-md backdrop-blur-md transition-all hover:bg-white active:scale-[0.98] dark:border-white/10 dark:bg-white/10 dark:text-gray-200 dark:hover:bg-white/20 sm:w-auto md:px-8 md:py-3"
                    >
                        <RotateCcw size={20} className="shrink-0 md:h-5 md:w-5" />
                        {isFlipped ? 'Show front' : 'Flip card'}
                    </button>

                    <button
                        type="button"
                        onClick={onNext}
                        className="touch-manipulation flex min-h-[48px] w-full items-center justify-center gap-2 rounded-xl border border-blue-400/50 bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-3 text-sm font-extrabold text-white shadow-lg shadow-blue-500/30 transition-all hover:from-blue-500 hover:to-indigo-500 active:scale-[0.98] sm:w-auto md:px-8 md:py-3"
                    >
                        Next card
                        <ChevronRight size={20} className="shrink-0 md:h-5 md:w-5" />
                    </button>
                </div>
            </div>
        </div>,
        document.body
    );
};

export default Flashcard;
