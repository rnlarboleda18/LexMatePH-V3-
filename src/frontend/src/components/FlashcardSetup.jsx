import React from 'react';
import { createPortal } from 'react-dom';
import { RefreshCw } from 'lucide-react';
import { getSubjectColor } from '../utils/colors';
import { SubjectIcon, AllSubjectsIcon } from '../utils/subjectIcons';

const subjects = [
    'Civil Law',
    'Commercial Law',
    'Criminal Law',
    'Labor Law',
    'Legal Ethics',
    'Political Law',
    'Remedial Law',
    'Taxation Law',
];

const FlashcardSetup = ({
    onStart,
    conceptsLoading = false,
    conceptsError = null,
    deckError = null,
    subjectCounts = {},
    onRetryConcepts,
    embedded = false,
    relaxedBarMatch = false,
    onRelaxedBarMatchChange,
    bar2026Only = false,
    onBar2026OnlyChange,
}) => {
    const countFor = (key) => {
        if (key === 'all') return subjectCounts.all ?? 0;
        return subjectCounts[key] ?? 0;
    };

    const content = (
            <div
                className={
                    embedded
                        ? 'relative flex w-full max-w-full min-w-0 flex-col gap-4 lg:rounded-lg lg:border lg:border-lex lg:bg-white lg:p-5 lg:shadow-lg dark:lg:border-lex dark:lg:bg-zinc-900 lg:sm:p-6'
                        : 'lex-modal-card relative flex max-w-4xl flex-col overflow-hidden rounded-lg border border-lex bg-white shadow-xl animate-in zoom-in-95 duration-200 dark:border-lex dark:bg-zinc-900'
                }
            >
                {(conceptsLoading || conceptsError || deckError) && (
                    <div
                        className={`flex flex-col gap-2 border-b border-lex px-1 pb-3 pt-0 dark:border-lex sm:px-0 ${
                            embedded
                                ? 'max-lg:rounded-lg max-lg:border-2 max-lg:border-lex max-lg:bg-white max-lg:p-4 max-lg:shadow-sm dark:max-lg:border-lex dark:max-lg:bg-zinc-900 lg:rounded-none lg:border-0 lg:border-b lg:bg-transparent lg:p-0 lg:px-1 lg:pb-3 lg:pt-0 lg:shadow-none dark:lg:bg-transparent'
                                : ''
                        }`}
                    >
                        {conceptsLoading && (
                            <p className="text-sm text-gray-500 dark:text-gray-400">Loading SC concepts…</p>
                        )}
                        {conceptsError && (
                            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                                <p className="flex-1 text-sm text-rose-600 dark:text-rose-400">{conceptsError}</p>
                                {typeof onRetryConcepts === 'function' && (
                                    <button
                                        type="button"
                                        onClick={() => onRetryConcepts()}
                                        className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-800 hover:bg-rose-100 dark:border-rose-700 dark:bg-rose-950/50 dark:text-rose-200 dark:hover:bg-rose-900/50"
                                    >
                                        <RefreshCw className="h-4 w-4" />
                                        Retry
                                    </button>
                                )}
                            </div>
                        )}
                        {deckError && !conceptsError && (
                            <p className="text-sm text-amber-700 dark:text-amber-400">{deckError}</p>
                        )}
                    </div>
                )}

                <div className={embedded ? 'min-w-0 flex-1 space-y-6' : 'flex-1 space-y-10 overflow-y-auto p-6 sm:p-8'}>
                    <section className="min-w-0 max-w-full">
                        {embedded ? (
                            <div className="mb-4 max-lg:rounded-lg max-lg:border-2 max-lg:border-lex max-lg:bg-white max-lg:p-4 max-lg:shadow-sm dark:max-lg:border-lex dark:max-lg:bg-zinc-900 sm:max-lg:p-5 lg:mb-6 lg:rounded-none lg:border-0 lg:bg-transparent lg:p-0 lg:shadow-none dark:lg:bg-transparent">
                                <h3 className="mb-3 text-balance text-base font-bold uppercase tracking-wide text-black dark:text-violet-300">
                                    Legal concepts (SC digests)
                                </h3>
                                <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                                    <span className="font-medium text-slate-700 dark:text-slate-300">Legal concepts</span>{' '}
                                    are short, exam-style distillations of doctrines and holdings drawn from Supreme Court
                                    digest summaries in the app. They are tagged to the Philippine Bar’s{' '}
                                    <span className="font-medium text-slate-700 dark:text-slate-300">
                                        Table of Specifications
                                    </span>{' '}
                                    so you drill what the syllabus actually weights—useful for quick recall and
                                    issue-spotting under time pressure. The default deck favors strong syllabus matches;
                                    clearly peripheral items stay out unless you widen the deck with the options below.
                                </p>
                            </div>
                        ) : (
                            <>
                                <h3 className="mb-3 text-balance text-base font-bold uppercase tracking-wide text-black dark:text-violet-300">
                                    Legal concepts (SC digests)
                                </h3>
                                <p className="mb-4 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                                    <span className="font-medium text-slate-700 dark:text-slate-300">Legal concepts</span>{' '}
                                    are short, exam-style distillations of doctrines and holdings drawn from Supreme Court
                                    digest summaries in the app. They are tagged to the Philippine Bar’s{' '}
                                    <span className="font-medium text-slate-700 dark:text-slate-300">
                                        Table of Specifications
                                    </span>{' '}
                                    so you drill what the syllabus actually weights—useful for quick recall and
                                    issue-spotting under time pressure. The default deck favors strong syllabus matches;
                                    clearly peripheral items stay out unless you widen the deck with the options below.
                                </p>
                            </>
                        )}
                        {typeof onBar2026OnlyChange === 'function' && (
                            <label className="mb-3 flex cursor-pointer items-start gap-3 rounded-xl border border-lex bg-white px-3 py-2.5 dark:border-lex dark:bg-zinc-800/80">
                                <input
                                    type="checkbox"
                                    className="mt-0.5 h-4 w-4 shrink-0 rounded border-slate-300 text-violet-600 focus:ring-violet-500 dark:border-slate-600"
                                    checked={bar2026Only}
                                    onChange={(e) => onBar2026OnlyChange(e.target.checked)}
                                    disabled={conceptsLoading}
                                />
                                <span className="text-sm text-gray-700 dark:text-gray-300">
                                    <span className="font-semibold text-gray-900 dark:text-gray-100">
                                        2026 Bar syllabus only
                                    </span>
                                    <span className="block text-xs font-normal text-gray-500 dark:text-gray-400">
                                        Only concepts AI-labeled against your 2026 syllabi files (smaller deck). Leave off
                                        if you have not run the Gemini labeler yet.
                                    </span>
                                </span>
                            </label>
                        )}
                        {typeof onRelaxedBarMatchChange === 'function' && (
                            <label className="mb-4 flex cursor-pointer items-start gap-3 rounded-xl border border-lex bg-white px-3 py-2.5 dark:border-lex dark:bg-zinc-800/80">
                                <input
                                    type="checkbox"
                                    className="mt-0.5 h-4 w-4 shrink-0 rounded border-slate-300 text-violet-600 focus:ring-violet-500 dark:border-slate-600"
                                    checked={relaxedBarMatch}
                                    onChange={(e) => onRelaxedBarMatchChange(e.target.checked)}
                                    disabled={conceptsLoading}
                                />
                                <span className="text-sm text-gray-700 dark:text-gray-300">
                                    <span className="font-semibold text-gray-900 dark:text-gray-100">
                                        Broader deck
                                    </span>
                                    <span className="block text-xs font-normal text-gray-500 dark:text-gray-400">
                                        Also include non-peripheral concepts with weaker syllabus overlap (more cards,
                                        less Bar-focused).
                                    </span>
                                </span>
                            </label>
                        )}
                        {!conceptsLoading && !conceptsError && countFor('all') === 0 && (
                            <p className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
                                No digest cards loaded yet. Deploy the latest API (it merges legal_concepts and digest flashcards), then Retry.
                            </p>
                        )}
                        <div className="grid min-w-0 grid-cols-1 gap-4 sm:gap-5 md:grid-cols-2 md:items-stretch">
                            <button
                                type="button"
                                onClick={() => onStart(null)}
                                disabled={conceptsLoading || countFor('all') === 0}
                                className="group relative flex min-h-[14rem] w-full min-w-0 flex-col justify-between gap-3 rounded-lg border border-lex bg-white p-4 text-left shadow-sm transition-shadow hover:shadow-md dark:border-lex dark:bg-zinc-800/90 disabled:pointer-events-none disabled:opacity-50 md:col-span-2"
                            >
                                <div className="min-w-0 space-y-2">
                                    <span className="flex items-start gap-2.5 text-sm font-bold text-slate-800 dark:text-slate-100">
                                        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-lex bg-white text-violet-700 shadow-sm dark:border-lex dark:bg-zinc-900 dark:text-violet-200">
                                            <AllSubjectsIcon className="h-5 w-5" strokeWidth={2} aria-hidden />
                                        </span>
                                        <span className="min-w-0 pt-0.5 leading-snug">Random / All subjects</span>
                                    </span>
                                    <span className="block pl-[2.75rem] text-sm text-slate-600 dark:text-slate-400">
                                        {countFor('all')} unique concepts
                                    </span>
                                </div>
                                <span className="shrink-0 rounded-xl border-2 border-violet-400/50 bg-gradient-to-r from-violet-600/90 to-purple-600/90 py-2.5 text-center text-sm font-semibold text-white shadow-sm transition group-hover:from-violet-500 group-hover:to-purple-500 dark:border-purple-400/40">
                                    Start deck
                                </span>
                            </button>

                            {subjects.map((subject) => {
                                const colorClass = getSubjectColor(subject);
                                const textColor = colorClass.split(' ').find((c) => c.startsWith('text-'));
                                const borderColor = colorClass.split(' ').find((c) => c.startsWith('border-'));
                                const n = countFor(subject);

                                return (
                                    <button
                                        type="button"
                                        key={`c-${subject}`}
                                        onClick={() => onStart(subject)}
                                        disabled={conceptsLoading || n === 0}
                                        className="group relative flex min-h-[14rem] w-full min-w-0 flex-col justify-between gap-3 rounded-lg border border-lex bg-white p-4 text-left shadow-sm transition-shadow hover:shadow-md dark:border-lex dark:bg-zinc-800/90 disabled:pointer-events-none disabled:opacity-50"
                                    >
                                        <div className="min-w-0 space-y-2">
                                            <span className={`flex items-start gap-2.5 text-sm font-bold ${textColor}`}>
                                                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-lex-strong bg-white shadow-sm dark:border-lex-strong dark:bg-zinc-800">
                                                    <SubjectIcon subject={subject} className="h-5 w-5" />
                                                </span>
                                                <span className="min-w-0 break-words pt-0.5 leading-snug">{subject}</span>
                                            </span>
                                            <span className="block pl-[2.75rem] text-sm text-slate-600 dark:text-slate-400">{n} concepts</span>
                                        </div>
                                        <span
                                            className={`shrink-0 rounded-xl border-2 bg-white/90 py-2.5 text-center text-sm font-semibold shadow-sm transition-colors hover:bg-white dark:bg-slate-900/75 dark:hover:bg-slate-800/90 ${borderColor} ${textColor}`}
                                        >
                                            Start deck
                                        </span>
                                    </button>
                                );
                            })}
                        </div>
                    </section>

                </div>

                {!embedded && (
                    <div className="flex justify-center border-t border-lex bg-slate-50 p-6 dark:border-lex dark:bg-zinc-800/60">
                        <button
                            type="button"
                            onClick={() => onStart('CANCEL')}
                            className="rounded-lg bg-gradient-to-r from-violet-600 to-purple-600 px-6 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:from-violet-500 hover:to-purple-500"
                        >
                            Cancel
                        </button>
                    </div>
                )}
            </div>
    );

    if (embedded) return content;

    return createPortal(
        <div className="fixed inset-0 z-[560] lex-modal-overlay bg-black/50 backdrop-blur-sm animate-in fade-in duration-200 pointer-events-auto">
            {content}
        </div>,
        document.body
    );
};

export default FlashcardSetup;
