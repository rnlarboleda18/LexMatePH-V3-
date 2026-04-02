import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import { RefreshCw } from 'lucide-react';
import { getSubjectColor, getSubjectAnswerColor } from '../utils/colors';

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
    const [subjectFilter, setSubjectFilter] = useState('all');

    const countFor = (key) => {
        if (key === 'all') return subjectCounts.all ?? 0;
        return subjectCounts[key] ?? 0;
    };

    const visibleSubjects =
        subjectFilter === 'all'
            ? subjects
            : subjects.filter((s) => s === subjectFilter);

    const content = (
            <div className={`glass w-full ${embedded ? 'max-w-7xl' : 'max-w-4xl max-h-[90vh]'} overflow-hidden flex flex-col rounded-2xl border border-white/40 bg-white/55 shadow-2xl dark:border-white/10 dark:bg-slate-900/45 animate-in zoom-in-95 duration-200`}>
                <div className="px-6 sm:px-8 pt-4 pb-2 border-b border-white/25 dark:border-white/10">
                    <label
                        htmlFor="flashcard-subject-filter"
                        className="block text-xs font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-2"
                    >
                        Filter by subject
                    </label>
                    <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
                        <select
                            id="flashcard-subject-filter"
                            value={subjectFilter}
                            onChange={(e) => setSubjectFilter(e.target.value)}
                            className="w-full sm:max-w-md rounded-xl border border-white/40 dark:border-white/15 bg-white/70 dark:bg-slate-800/70 px-4 py-3 text-sm font-medium text-gray-900 dark:text-white shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                        >
                            <option value="all">All subjects — concepts: {countFor('all')}</option>
                            {subjects.map((s) => (
                                <option key={s} value={s}>
                                    {s} — concepts: {countFor(s)}
                                </option>
                            ))}
                        </select>
                        {conceptsLoading && (
                            <span className="text-sm text-gray-500 dark:text-gray-400">Loading SC concepts…</span>
                        )}
                    </div>
                    {conceptsError && (
                        <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                            <p className="text-sm text-rose-600 dark:text-rose-400 flex-1">{conceptsError}</p>
                            {typeof onRetryConcepts === 'function' && (
                                <button
                                    type="button"
                                    onClick={() => onRetryConcepts()}
                                    className="inline-flex items-center justify-center gap-2 shrink-0 rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-800 hover:bg-rose-100 dark:border-rose-700 dark:bg-rose-950/50 dark:text-rose-200 dark:hover:bg-rose-900/50"
                                >
                                    <RefreshCw className="h-4 w-4" />
                                    Retry
                                </button>
                            )}
                        </div>
                    )}
                    {deckError && !conceptsError && (
                        <p className="mt-2 text-sm text-amber-700 dark:text-amber-400">{deckError}</p>
                    )}
                </div>

                <div className="flex-1 overflow-y-auto p-6 sm:p-8 space-y-10">
                    <section>
                        <h3 className="text-sm font-bold uppercase tracking-wider text-indigo-700 dark:text-indigo-400 mb-3">
                            Key legal concepts (SC digests)
                        </h3>
                        {!conceptsLoading && !conceptsError && countFor('all') === 0 && (
                            <p className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
                                No digest cards loaded yet. Deploy the latest API (it merges legal_concepts and digest flashcards), then Retry.
                            </p>
                        )}
                        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                            <button
                                type="button"
                                onClick={() => onStart(null)}
                                disabled={conceptsLoading || countFor('all') === 0}
                                className="group relative flex h-full flex-col overflow-hidden rounded-xl border-2 border-l-[5px] border-gray-400 bg-gray-50 p-3 shadow-sm transition-all hover:shadow-md dark:border-gray-600 dark:bg-gray-900/30 disabled:pointer-events-none disabled:opacity-50"
                            >
                                <span className="mb-2 text-sm font-bold text-gray-700 dark:text-gray-200">
                                    Random / All subjects
                                </span>
                                <span className="mb-3 flex-1 text-sm text-gray-600 dark:text-gray-300">
                                    {countFor('all')} unique concepts
                                </span>
                                <span className="w-full rounded-lg border-2 border-gray-400 bg-white/90 py-2 text-center text-sm font-semibold text-gray-700 shadow-sm transition-colors hover:bg-white dark:border-gray-600 dark:bg-slate-900/70 dark:text-gray-200 dark:hover:bg-slate-800/90">
                                    Start deck
                                </span>
                            </button>

                            {visibleSubjects.map((subject) => {
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
                                        className={`group relative flex h-full flex-col overflow-hidden rounded-xl border-2 border-l-[5px] p-3 shadow-sm transition-all hover:shadow-md ${surfaceClass} ${borderColor} disabled:pointer-events-none disabled:opacity-50`}
                                    >
                                        <span className={`mb-2 text-sm font-bold ${textColor}`}>{subject}</span>
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
        <div className="fixed inset-0 z-[560] flex items-center justify-center p-4 pb-[var(--player-height,0px)] bg-black/50 backdrop-blur-sm animate-in fade-in duration-200 pointer-events-auto">
            {content}
        </div>,
        document.body
    );
};

export default FlashcardSetup;
