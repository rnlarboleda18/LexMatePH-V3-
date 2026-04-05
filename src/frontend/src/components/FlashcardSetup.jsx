import React from 'react';
import { createPortal } from 'react-dom';
import { RefreshCw } from 'lucide-react';
import { getSubjectColor, getSubjectAnswerColor } from '../utils/colors';
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
}) => {
    const countFor = (key) => {
        if (key === 'all') return subjectCounts.all ?? 0;
        return subjectCounts[key] ?? 0;
    };

    const content = (
            <div className={`${embedded ? 'w-full max-w-7xl' : 'lex-modal-card relative max-w-4xl'} glass overflow-hidden flex flex-col rounded-2xl border-2 border-slate-300/85 bg-white/92 shadow-2xl dark:border-white/10 dark:bg-slate-900/45 animate-in zoom-in-95 duration-200`}>
                {(conceptsLoading || conceptsError || deckError) && (
                    <div className="flex flex-col gap-2 border-b border-white/25 px-6 pb-3 pt-4 dark:border-white/10 sm:px-8">
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

                <div className="flex-1 space-y-10 overflow-y-auto p-6 sm:p-8">
                    <section>
                        <h3 className="text-sm font-bold uppercase tracking-wider text-indigo-700 dark:text-indigo-400 mb-3">
                            Key legal concepts (SC digests)
                        </h3>
                        {!conceptsLoading && !conceptsError && countFor('all') === 0 && (
                            <p className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
                                No digest cards loaded yet. Deploy the latest API (it merges legal_concepts and digest flashcards), then Retry.
                            </p>
                        )}
                        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 md:items-stretch">
                            <button
                                type="button"
                                onClick={() => onStart(null)}
                                disabled={conceptsLoading || countFor('all') === 0}
                                className="group relative flex min-h-[148px] w-full flex-col overflow-hidden rounded-xl border-2 border-l-[5px] border-gray-400 bg-gray-50 p-3 shadow-sm transition-all hover:shadow-md dark:border-gray-600 dark:bg-gray-900/30 disabled:pointer-events-none disabled:opacity-50 md:col-span-2"
                            >
                                <span className="mb-2 flex items-center gap-2 text-sm font-bold text-gray-700 dark:text-gray-200">
                                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-gray-300 bg-white/90 text-gray-600 dark:border-gray-600 dark:bg-slate-800/80 dark:text-gray-300">
                                        <AllSubjectsIcon className="h-5 w-5" strokeWidth={2} aria-hidden />
                                    </span>
                                    Random / All subjects
                                </span>
                                <span className="mb-3 flex-1 text-sm text-gray-600 dark:text-gray-300">
                                    {countFor('all')} unique concepts
                                </span>
                                <span className="w-full rounded-lg border-2 border-gray-400 bg-white/90 py-2 text-center text-sm font-semibold text-gray-700 shadow-sm transition-colors hover:bg-white dark:border-gray-600 dark:bg-slate-900/70 dark:text-gray-200 dark:hover:bg-slate-800/90">
                                    Start deck
                                </span>
                            </button>

                            {subjects.map((subject) => {
                                const colorClass = getSubjectColor(subject);
                                const textColor = colorClass.split(' ').find((c) => c.startsWith('text-'));
                                const borderColor = colorClass.split(' ').find((c) => c.startsWith('border-'));
                                const surfaceClass = getSubjectAnswerColor(subject);
                                const n = countFor(subject);

                                return (
                                    <button
                                        type="button"
                                        key={`c-${subject}`}
                                        onClick={() => onStart(subject)}
                                        disabled={conceptsLoading || n === 0}
                                        className={`group relative flex min-h-[148px] flex-col overflow-hidden rounded-xl border-2 border-l-[5px] p-3 shadow-sm transition-all hover:shadow-md ${surfaceClass} ${borderColor} disabled:pointer-events-none disabled:opacity-50`}
                                    >
                                        <span className={`mb-2 flex items-center gap-2 text-sm font-bold ${textColor}`}>
                                            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-white/60 bg-white/80 dark:border-white/10 dark:bg-slate-900/50">
                                                <SubjectIcon subject={subject} className="h-5 w-5" />
                                            </span>
                                            <span className="min-w-0 leading-snug">{subject}</span>
                                        </span>
                                        <span className="mb-3 flex-1 text-sm text-gray-600 dark:text-gray-300">{n} concepts</span>
                                        <span className={`w-full rounded-lg border-2 py-2 text-center text-sm font-semibold shadow-sm transition-colors bg-white/90 hover:bg-white dark:bg-slate-900/70 dark:hover:bg-slate-800/90 ${borderColor} ${textColor}`}>
                                            Start deck
                                        </span>
                                    </button>
                                );
                            })}
                        </div>
                    </section>

                </div>

                <div className="p-6 border-t border-white/25 dark:border-white/10 bg-white/20 dark:bg-black/10 flex justify-center">
                    <button
                        type="button"
                        onClick={() => onStart('CANCEL')}
                        className="px-6 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold transition-colors shadow-sm"
                    >
                        Cancel
                    </button>
                </div>
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
