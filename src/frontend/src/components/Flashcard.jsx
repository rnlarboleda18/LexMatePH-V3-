import React, { useState, useEffect, useCallback } from 'react';
import { ChevronRight, RotateCcw, X } from 'lucide-react';
import { getSubjectColor } from '../utils/colors';
import { normalizeBarSubject } from '../utils/subjectNormalize';
import { SubjectIcon } from '../utils/subjectIcons';

/** Meta + actions repeated on front/back so nothing sits outside the flip as a separate “bar”. */
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
            onClose?.();
        },
        [onClose]
    );

    const renderMetaRow = () => (
        <div className="grid shrink-0 grid-cols-[1fr_auto_1fr] items-center gap-2 px-4 pt-4 pb-2 sm:px-5 md:px-6">
            <div className="flex min-w-0 items-center gap-2 sm:gap-2.5">
                <div
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-white/50 bg-white/70 shadow-sm dark:border-white/10 dark:bg-slate-800/80 ${textColor}`}
                    title={primarySubject}
                >
                    <SubjectIcon subject={primarySubject} className="h-[18px] w-[18px] md:h-5 md:w-5" />
                </div>
                <span className={`min-w-0 truncate text-[15px] font-medium leading-snug md:text-[17px] ${textColor}`}>
                    {primarySubject}
                </span>
                {isBar && (
                    <span className="shrink-0 rounded-md bg-emerald-500/15 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-emerald-800 dark:text-emerald-300">
                        Bar
                    </span>
                )}
            </div>
            <span className="tabular-nums text-[13px] font-medium text-gray-600 dark:text-gray-400 md:text-sm">
                {currentIndex + 1} / {total}
            </span>
            <div className="flex items-center justify-end gap-2">
                <span className="shrink-0 tabular-nums text-[15px] font-medium text-gray-900 dark:text-white md:text-[17px]">
                    {headerDate}
                </span>
                <button
                    type="button"
                    onClick={handleClose}
                    className="touch-manipulation flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-red-200/70 bg-red-50/90 text-red-500 transition-all hover:bg-red-100 active:scale-95 dark:border-red-800/60 dark:bg-red-950/50 dark:text-red-400 dark:hover:bg-red-900/50"
                    aria-label="Close"
                >
                    <X className="h-4 w-4" strokeWidth={2.25} />
                </button>
            </div>
        </div>
    );

    const renderActionRow = () => (
        <div
            className="flex shrink-0 flex-col gap-2 px-4 pb-4 pt-3 sm:flex-row sm:justify-between sm:gap-3 sm:px-5 md:px-6"
            onClick={(e) => e.stopPropagation()}
        >
            <button
                type="button"
                onClick={(e) => {
                    e.stopPropagation();
                    setIsFlipped((f) => !f);
                }}
                className="touch-manipulation flex min-h-[48px] w-full items-center justify-center gap-2 rounded-xl border border-white/50 bg-white/85 px-5 py-3 text-sm font-extrabold text-gray-800 shadow-sm transition-all hover:bg-white active:scale-[0.98] dark:border-white/15 dark:bg-slate-800/90 dark:text-gray-200 dark:hover:bg-slate-700/90 sm:w-auto md:px-7"
            >
                <RotateCcw size={20} className="shrink-0 md:h-5 md:w-5" />
                {isFlipped ? 'Show front' : 'Flip card'}
            </button>
            <button
                type="button"
                onClick={(e) => {
                    e.stopPropagation();
                    onNext();
                }}
                className="touch-manipulation flex min-h-[48px] w-full items-center justify-center gap-2 rounded-xl border border-blue-400/50 bg-gradient-to-r from-blue-600 to-indigo-600 px-5 py-3 text-sm font-extrabold text-white shadow-md transition-all hover:from-blue-500 hover:to-indigo-500 active:scale-[0.98] sm:w-auto md:px-7"
            >
                Next card
                <ChevronRight size={20} className="shrink-0 md:h-5 md:w-5" />
            </button>
        </div>
    );

    return (
        <div
            className="relative z-[1] flex h-full min-h-0 w-full max-w-none flex-col border border-slate-200 bg-white shadow-[0_8px_40px_rgba(0,0,0,0.14)] dark:border-white/10 dark:bg-slate-900"
            style={{ borderRadius: '24px', clipPath: 'inset(0 round 24px)' }}
            role="region"
            aria-label="Flashcard"
        >
            <div className="flex h-full min-h-0 w-full flex-col">
                <div className="relative min-h-0 flex-1 [perspective:1200px]">
                    <div
                        className="relative h-full min-h-0 w-full transition-transform duration-500 [transform-style:preserve-3d]"
                        style={{ transform: isFlipped ? 'rotateY(180deg)' : 'rotateY(0deg)' }}
                    >
                        {/* Front — meta + content + actions; no outer top/bottom bars */}
                        <div
                            className="absolute inset-0 flex h-full min-h-full flex-col overflow-hidden rounded-3xl bg-gradient-to-br from-slate-50/95 to-white/85 [backface-visibility:hidden] dark:from-slate-800/95 dark:to-slate-900/90"
                            style={{ WebkitBackfaceVisibility: 'hidden' }}
                        >
                            {renderMetaRow()}
                            <div className="flex min-h-0 flex-1 flex-col px-4 pb-2 sm:px-5 md:px-6">
                                <span
                                    className={`mb-2 shrink-0 text-[10px] font-black uppercase tracking-widest text-indigo-600 dark:text-indigo-400 ${!isBar ? 'text-center' : ''}`}
                                >
                                    {isBar ? 'Question' : 'Key legal concept'}
                                </span>
                                <div
                                    role="button"
                                    tabIndex={0}
                                    className="flex min-h-0 flex-1 cursor-pointer flex-col justify-center rounded-lg py-3 outline-none ring-indigo-400/30 focus-visible:ring-2"
                                    onClick={() => setIsFlipped(true)}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter' || e.key === ' ') {
                                            e.preventDefault();
                                            setIsFlipped(true);
                                        }
                                    }}
                                >
                                    <p
                                        className={`text-[17px] font-semibold leading-relaxed text-gray-900 dark:text-gray-50 md:text-xl whitespace-pre-wrap break-words ${isBar ? 'text-left' : 'text-center'}`}
                                    >
                                        {isBar ? card.text : card.term}
                                    </p>
                                    {isBar &&
                                        card.subQuestions?.map((sub, i) => (
                                            <p
                                                key={i}
                                                className="mt-4 border-t-2 border-slate-300/80 pt-4 text-left text-[15px] font-medium leading-relaxed text-gray-800 dark:border-white/10 dark:text-gray-200 whitespace-pre-wrap break-words"
                                            >
                                                {sub.text}
                                            </p>
                                        ))}
                                </div>
                                <span className="shrink-0 pb-1 text-center text-xs text-gray-500 dark:text-gray-400">
                                    Tap the card to see the back
                                </span>
                            </div>
                            {renderActionRow()}
                        </div>

                        {/* Back — same meta + actions; scroll definition only */}
                        <div
                            className="absolute inset-0 flex h-full min-h-full flex-col overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-50/95 to-violet-50/85 [backface-visibility:hidden] [transform:rotateY(180deg)] dark:from-indigo-950/65 dark:to-slate-900/90"
                            style={{ WebkitBackfaceVisibility: 'hidden' }}
                        >
                            {renderMetaRow()}
                            {isBar ? (
                                <div className="flex min-h-0 flex-1 flex-col overflow-y-auto overflow-x-hidden px-4 pb-2 sm:px-5 md:px-6 custom-scrollbar">
                                    <span className={`mb-3 shrink-0 text-[10px] font-black uppercase tracking-widest ${textColor}`}>
                                        Suggested answers
                                    </span>
                                    <p className="text-[15px] leading-relaxed text-gray-800 dark:text-gray-100 md:text-[17px] whitespace-pre-wrap break-words">
                                        {card.answer || 'Answer not available.'}
                                    </p>
                                    {card.subQuestions?.map((sub, i) => (
                                        <div key={i} className="relative mt-4 border-t-2 border-slate-300/75 pt-4 dark:border-white/10">
                                            <p className="text-[15px] leading-relaxed text-gray-800 dark:text-gray-100 md:text-[17px] whitespace-pre-wrap break-words">
                                                {sub.answer || 'Answer not available.'}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="flex min-h-0 flex-1 flex-col overflow-y-auto overflow-x-hidden px-4 pb-2 sm:px-5 md:px-6 custom-scrollbar">
                                    <span className={`mb-3 shrink-0 text-[10px] font-black uppercase tracking-widest ${textColor}`}>
                                        Definition
                                    </span>
                                    <p className="text-[15px] leading-relaxed text-gray-800 dark:text-gray-100 md:text-[17px] whitespace-pre-wrap break-words">
                                        {card.definition || 'No definition stored for this concept.'}
                                    </p>
                                    {sources.length > 0 && (
                                        <>
                                            <span className="mb-2 mt-6 block text-[10px] font-black uppercase tracking-widest text-gray-500 dark:text-gray-400">
                                                Latest case
                                            </span>
                                            <div className="rounded-lg border-2 border-slate-300/80 bg-white/90 p-3 text-sm dark:border-white/10 dark:bg-black/30">
                                                {sources.map((src) => (
                                                    <div key={`${src.case_id}-${src.case_number}`}>
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
                                                    </div>
                                                ))}
                                            </div>
                                        </>
                                    )}
                                </div>
                            )}
                            {renderActionRow()}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Flashcard;
