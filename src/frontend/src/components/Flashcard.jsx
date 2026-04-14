import React, { useState, useEffect, useCallback } from 'react';
import { ChevronRight, RotateCcw, X, Headphones, Lock } from 'lucide-react';
import { getSubjectColor } from '../utils/colors';
import { normalizeBarSubject } from '../utils/subjectNormalize';
import { SubjectIcon } from '../utils/subjectIcons';
import { useLexPlayApi } from '../features/lexplay/useLexPlay';
import { useSubscription } from '../context/SubscriptionContext';

const FLIP_MS = 650;
const FLIP_EASE = 'cubic-bezier(0.4, 0.2, 0.2, 1)';

/** Physical flashcard: subject / progress / date / close live inside each face; no outer modal shell. */
const Flashcard = ({ variant = 'concepts', card, onNext, currentIndex, total, onClose }) => {
    const [isFlipped, setIsFlipped] = useState(false);
    const { playNow } = useLexPlayApi();
    const { canAccess, openUpgradeModal } = useSubscription();
    const canLexPlay = canAccess('lexplay_flashcard');

    useEffect(() => {
        setIsFlipped(false);
    }, [card]);

    if (!card) return null;

    const isBar = variant === 'bar';

    const sources = card.sources || [];
    const rawSubjectLabel = isBar
        ? String(card.subject || '').trim() || '—'
        : String(sources[0]?.subject || '').trim() || '—';
    const subjectForColor =
        normalizeBarSubject(rawSubjectLabel) || rawSubjectLabel || '—';
    const headerDate = isBar ? String(card.year ?? '—') : sources[0]?.date_str || '—';

    const colorClass = getSubjectColor(subjectForColor);
    const textColor = colorClass.split(' ').find((c) => c.startsWith('text-'));

    const handleClose = useCallback(
        (e) => {
            e?.preventDefault?.();
            e?.stopPropagation?.();
            onClose?.();
        },
        [onClose]
    );

    const handleLexPlay = useCallback(
        (e) => {
            e?.stopPropagation?.();
            if (!canLexPlay) {
                openUpgradeModal('lexplay_flashcard');
                return;
            }
            if (isBar) {
                // Bar flashcards share the questions table; reuse the 'question' audio type
                playNow({
                    id: card.id,
                    type: 'question',
                    title: `${card.year} Bar — ${rawSubjectLabel}`,
                    subtitle: 'Bar Flashcard',
                });
            } else {
                // Concept flashcards: look up by term in flashcard_concepts
                playNow({
                    id: encodeURIComponent(card.term || ''),
                    type: 'flashcard',
                    title: card.term || 'Flashcard',
                    subtitle: rawSubjectLabel || 'Legal Concept',
                });
            }
        },
        [canLexPlay, openUpgradeModal, isBar, card, rawSubjectLabel, playNow]
    );

    const renderFaceHeader = (faceBorderClass) => (
        <div
            className={`flex shrink-0 items-start gap-1.5 border-b px-2.5 pb-2 pt-2 sm:px-3 sm:pb-2 sm:pt-2 ${faceBorderClass}`}
            onClick={(e) => e.stopPropagation()}
        >
            <div
                className={`mt-px flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-stone-300/80 bg-white/90 shadow-sm dark:border-white/10 dark:bg-slate-800/90 ${textColor}`}
                title={rawSubjectLabel}
            >
                <SubjectIcon subject={subjectForColor} className="h-3 w-3 sm:h-3.5 sm:w-3.5" />
            </div>
            <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-1">
                    <p className="line-clamp-2 text-left text-[13px] font-semibold leading-tight text-stone-800 [text-rendering:optimizeLegibility] dark:text-stone-100 sm:text-sm">
                        {rawSubjectLabel}
                    </p>
                    {isBar && (
                        <span className="shrink-0 rounded bg-emerald-500/15 px-1 py-px text-[7px] font-bold uppercase tracking-wide text-emerald-800 dark:text-emerald-300">
                            Bar
                        </span>
                    )}
                </div>
                <p className="mt-0.5 text-[10px] tabular-nums leading-none text-stone-500 dark:text-stone-400">
                    {currentIndex + 1} / {total}
                    <span className="mx-1.5 text-stone-300 dark:text-stone-600">·</span>
                    {headerDate}
                </p>
            </div>
            <button
                type="button"
                onClick={handleClose}
                className="touch-manipulation -mr-0.5 -mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-red-200/80 bg-red-50 text-red-600 transition-colors hover:bg-red-100 dark:border-red-800/60 dark:bg-red-950/60 dark:text-red-400 dark:hover:bg-red-900/50"
                aria-label="Close"
            >
                <X className="h-3.5 w-3.5" strokeWidth={2.25} />
            </button>
        </div>
    );

    const faceTypography = 'antialiased [text-rendering:optimizeLegibility] [-webkit-font-smoothing:antialiased]';

    const renderFaceActions = (tone) => {
        const bar =
            tone === 'front'
                ? 'border-t border-violet-200/70 bg-violet-50/40 dark:border-purple-500/20 dark:bg-black/25'
                : 'border-t border-purple-200/80 bg-purple-100/35 dark:border-fuchsia-500/15 dark:bg-black/30';
        return (
            <div className={`flex shrink-0 items-center gap-1.5 px-2 py-2 sm:gap-2 sm:px-2.5 sm:py-2 ${bar}`} onClick={(e) => e.stopPropagation()}>
                {/* LexPlay button — gated at Juris */}
                <button
                    type="button"
                    onClick={handleLexPlay}
                    title={canLexPlay ? 'Play in LexPlay' : 'Juris plan required — LexPlay Flashcard'}
                    className={`touch-manipulation flex h-[36px] w-[36px] shrink-0 items-center justify-center rounded-lg border shadow-sm transition-colors active:scale-[0.99] sm:h-[38px] sm:w-[38px] ${
                        canLexPlay
                            ? 'border-purple-300/80 bg-purple-50 text-purple-700 hover:bg-purple-100 dark:border-purple-700/60 dark:bg-purple-900/30 dark:text-purple-300 dark:hover:bg-purple-900/50'
                            : 'border-stone-300/70 bg-white/70 text-stone-400 dark:border-white/10 dark:bg-white/5 dark:text-white/30'
                    }`}
                >
                    {canLexPlay ? (
                        <Headphones size={15} strokeWidth={2.25} />
                    ) : (
                        <Lock size={13} strokeWidth={2.25} />
                    )}
                </button>
                <button
                    type="button"
                    onClick={(e) => {
                        e.stopPropagation();
                        setIsFlipped((f) => !f);
                    }}
                    className="touch-manipulation flex min-h-[36px] flex-1 items-center justify-center gap-1.5 rounded-lg border border-violet-300/80 bg-white/95 px-2 py-1.5 text-[11px] font-bold leading-tight text-violet-950 shadow-sm transition-colors hover:bg-violet-50 active:scale-[0.99] dark:border-purple-500/30 dark:bg-slate-800 dark:text-violet-100 dark:hover:bg-slate-700/90 sm:min-h-[38px] sm:text-xs"
                >
                    <RotateCcw size={14} className="shrink-0" strokeWidth={2.25} />
                    {isFlipped ? 'Front' : 'Flip'}
                </button>
                <button
                    type="button"
                    onClick={(e) => {
                        e.stopPropagation();
                        onNext();
                    }}
                    className="touch-manipulation flex min-h-[36px] flex-1 items-center justify-center gap-1.5 rounded-lg border border-violet-500/40 bg-gradient-to-r from-violet-600 to-purple-600 px-2 py-1.5 text-[11px] font-bold leading-tight text-white shadow-sm transition-colors hover:from-violet-500 hover:to-fuchsia-600 active:scale-[0.99] sm:min-h-[38px] sm:text-xs"
                >
                    Next
                    <ChevronRight size={14} className="shrink-0" strokeWidth={2.25} />
                </button>
            </div>
        );
    };

    const renderFrontFace = () => (
        <div
            className={`absolute inset-0 flex flex-col overflow-hidden rounded-xl border-2 border-violet-200/90 bg-gradient-to-b from-white via-violet-50/40 to-fuchsia-50/30 shadow-[0_22px_48px_-18px_rgba(109,40,217,0.22),0_2px_6px_rgba(0,0,0,0.06)] dark:border-purple-500/30 dark:from-slate-800 dark:via-purple-950/40 dark:to-slate-950 dark:shadow-[0_20px_40px_-10px_rgba(0,0,0,0.55)] ${faceTypography}`}
            style={{
                backfaceVisibility: 'hidden',
                WebkitBackfaceVisibility: 'hidden',
                transform: 'rotateY(0deg)',
            }}
        >
            {renderFaceHeader('border-violet-200/80 dark:border-purple-500/25')}
            <div className="flex min-h-0 flex-1 flex-col px-2.5 pb-1.5 pt-2 sm:px-3 sm:pb-2 sm:pt-2.5">
                <span
                    className={`mb-1 shrink-0 text-[10px] font-bold uppercase tracking-[0.14em] text-amber-900/85 dark:text-amber-400/95 ${!isBar ? 'text-center' : ''}`}
                >
                    {isBar ? 'Question' : 'Legal concept'}
                </span>
                <div
                    role="button"
                    tabIndex={0}
                    className="flex min-h-0 flex-1 cursor-pointer flex-col justify-center rounded-lg py-1 outline-none ring-violet-500/25 focus-visible:ring-2 dark:ring-purple-400/30"
                    onClick={() => setIsFlipped(true)}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            setIsFlipped(true);
                        }
                    }}
                >
                    <p
                        className={`text-[17px] font-semibold leading-snug text-stone-900 dark:text-stone-50 sm:text-[18px] sm:leading-normal md:text-[19px] whitespace-pre-wrap break-words ${isBar ? 'text-left' : 'text-center'}`}
                    >
                        {isBar ? card.text : card.term}
                    </p>
                    {isBar &&
                        card.subQuestions?.map((sub, i) => (
                            <p
                                key={i}
                                className="mt-4 border-t border-stone-300/70 pt-4 text-left text-[15px] font-medium leading-relaxed text-stone-800 dark:border-white/10 dark:text-stone-200 whitespace-pre-wrap break-words"
                            >
                                {sub.text}
                            </p>
                        ))}
                </div>
                <span className="shrink-0 pt-0.5 text-center text-[9px] text-stone-500 dark:text-stone-400">
                    Tap to flip
                </span>
            </div>
            {renderFaceActions('front')}
        </div>
    );

    const renderBackFace = () => (
        <div
            className={`absolute inset-0 flex flex-col overflow-hidden rounded-xl border-2 border-purple-300/85 bg-gradient-to-b from-violet-50 via-purple-50/80 to-fuchsia-50/70 shadow-[0_22px_48px_-16px_rgba(109,40,217,0.28),0_2px_6px_rgba(0,0,0,0.05)] dark:border-purple-500/35 dark:from-purple-950/95 dark:via-slate-950 dark:to-slate-950 dark:shadow-[0_20px_40px_-10px_rgba(0,0,0,0.55)] ${faceTypography}`}
            style={{
                backfaceVisibility: 'hidden',
                WebkitBackfaceVisibility: 'hidden',
                transform: 'rotateY(180deg)',
            }}
        >
            {renderFaceHeader('border-purple-200/75 dark:border-purple-500/25')}
            <div className="flex min-h-0 flex-1 flex-col overflow-hidden px-2.5 pb-2 pt-2 sm:px-3 sm:pb-2 sm:pt-2.5">
                {isBar ? (
                    <>
                        <span className={`mb-1 shrink-0 text-[10px] font-bold uppercase tracking-[0.14em] ${textColor}`}>
                            Suggested answers
                        </span>
                        <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden pr-1 custom-scrollbar">
                            <p className="text-[15px] font-normal leading-relaxed text-stone-900 dark:text-stone-100 sm:text-[16px] sm:leading-relaxed whitespace-pre-wrap break-words">
                                {card.answer || 'Answer not available.'}
                            </p>
                            {card.subQuestions?.map((sub, i) => (
                                <div key={i} className="relative mt-4 border-t border-violet-200/80 pt-4 dark:border-purple-500/20">
                                    <p className="text-[15px] font-normal leading-relaxed text-stone-900 dark:text-stone-100 sm:text-[16px] whitespace-pre-wrap break-words">
                                        {sub.answer || 'Answer not available.'}
                                    </p>
                                </div>
                            ))}
                        </div>
                    </>
                ) : (
                    <>
                        <span className={`mb-1 shrink-0 text-[10px] font-bold uppercase tracking-[0.14em] ${textColor}`}>
                            Definition
                        </span>
                        <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden pr-1 custom-scrollbar">
                            <p className="text-[15px] font-normal leading-relaxed text-stone-900 dark:text-stone-100 sm:text-[16px] sm:leading-relaxed whitespace-pre-wrap break-words">
                                {card.definition || 'No definition stored for this concept.'}
                            </p>
                            {sources.length > 0 && (
                                <>
                                    <span className="mb-1 mt-3 block text-[8px] font-bold uppercase tracking-[0.14em] text-stone-500 dark:text-stone-400">
                                        Latest case
                                    </span>
                                    <div className="rounded-lg border border-stone-300/90 bg-white p-2 text-xs shadow-sm dark:border-white/10 dark:bg-slate-900/40">
                                        {sources.map((src) => (
                                            <div key={`${src.case_id}-${src.case_number}`}>
                                                <div className="font-semibold text-stone-900 dark:text-stone-100 line-clamp-2">
                                                    {src.title || '—'}
                                                </div>
                                                <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-stone-600 dark:text-stone-300">
                                                    <span className="font-mono tabular-nums">{src.case_number || '—'}</span>
                                                    <span>{src.date_str || '—'}</span>
                                                    <span className="font-medium text-violet-700 dark:text-violet-300">
                                                        {normalizeBarSubject(src.subject) || src.subject || '—'}
                                                    </span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </>
                            )}
                        </div>
                    </>
                )}
            </div>
            {renderFaceActions('back')}
        </div>
    );

    return (
        <div
            className="relative z-[1] flex w-full min-h-0 flex-1 flex-col justify-center max-md:min-h-0 md:justify-center md:px-2"
            role="region"
            aria-label="Flashcard"
        >
            {/*
              Mobile: fill the same lex-modal-card shell as Case digest / Bar question (full insets from overlay).
              md+: centered square; size capped for header + LexPlayer.
            */}
            <div
                className="relative z-0 mx-auto min-h-0 w-full max-md:h-full max-md:min-h-0 max-md:flex-1 max-md:max-w-full [perspective:1400px] max-md:aspect-auto md:aspect-square md:max-h-full md:w-[min(30rem,calc(100dvh-14rem),calc(100vw-2.5rem))] md:[perspective:1900px] md:shrink-0 lg:w-[min(34rem,calc(100dvh-14rem),calc(100vw-3rem))] lg:[perspective:2100px]"
            >
                <div
                    className="relative h-full w-full [transform-style:preserve-3d]"
                    style={{
                        transition: `transform ${FLIP_MS}ms ${FLIP_EASE}`,
                        transform: isFlipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
                    }}
                >
                    {renderFrontFace()}
                    {renderBackFace()}
                </div>
            </div>
        </div>
    );
};

export default Flashcard;
