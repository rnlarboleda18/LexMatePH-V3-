import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import { RefreshCw } from 'lucide-react';
import { getSubjectColor } from '../utils/colors';

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
    onStartBar,
    conceptsLoading = false,
    conceptsError = null,
    deckError = null,
    subjectCounts = {},
    barSubjectCounts = {},
    barAvailable = false,
    onRetryConcepts,
}) => {
    const [subjectFilter, setSubjectFilter] = useState('all');

    const countFor = (key) => {
        if (key === 'all') return subjectCounts.all ?? 0;
        return subjectCounts[key] ?? 0;
    };

    const barCountFor = (key) => {
        if (key === 'all') return barSubjectCounts.all ?? 0;
        return barSubjectCounts[key] ?? 0;
    };

    const visibleSubjects =
        subjectFilter === 'all'
            ? subjects
            : subjects.filter((s) => s === subjectFilter);

    const content = (
        <div className="fixed inset-0 z-[560] flex items-center justify-center p-4 pb-[var(--player-height,0px)] bg-black/50 backdrop-blur-sm animate-in fade-in duration-200 pointer-events-auto">
            <div className="bg-white dark:bg-dark-card rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col animate-in zoom-in-95 duration-200">
                <div className="p-6 sm:p-8 border-b border-gray-100 dark:border-gray-800 text-center">
                    <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-2">
                        Flashcard Mode
                    </h2>
                    <p className="text-gray-500 dark:text-gray-400 text-sm sm:text-base">
                        Deduplicated <span className="font-mono text-indigo-600 dark:text-indigo-400">legal_concepts</span> from Supreme Court digests. Or use bar exam questions.
                    </p>
                </div>

                <div className="px-6 sm:px-8 pt-4 pb-2 border-b border-gray-100 dark:border-gray-800/80">
                    <label
                        htmlFor="flashcard-subject-filter"
                        className="block text-xs font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-2"
                    >
                        Filter by subject (applies to both sections)
                    </label>
                    <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
                        <select
                            id="flashcard-subject-filter"
                            value={subjectFilter}
                            onChange={(e) => setSubjectFilter(e.target.value)}
                            className="w-full sm:max-w-md rounded-xl border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800/80 px-4 py-3 text-sm font-medium text-gray-900 dark:text-white shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                        >
                            <option value="all">All subjects — concepts: {countFor('all')} · bar: {barCountFor('all')}</option>
                            {subjects.map((s) => (
                                <option key={s} value={s}>
                                    {s} — concepts: {countFor(s)} · bar: {barCountFor(s)}
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
                                No digest cards loaded yet. Deploy the latest API (it merges legal_concepts and digest flashcards), then Retry. Use bar questions below anytime.
                            </p>
                        )}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            <button
                                type="button"
                                onClick={() => onStart(null)}
                                disabled={conceptsLoading || countFor('all') === 0}
                                className="group p-6 rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-700 hover:border-primary hover:bg-primary/5 transition-all text-left flex flex-col gap-2 disabled:opacity-50 disabled:pointer-events-none"
                            >
                                <span className="text-lg font-bold text-gray-900 dark:text-white group-hover:text-primary transition-colors">
                                    Random / All subjects
                                </span>
                                <span className="text-sm text-gray-500 dark:text-gray-400">
                                    {countFor('all')} unique concepts
                                </span>
                            </button>

                            {visibleSubjects.map((subject) => {
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
                                        className={`group p-6 rounded-xl border-2 ${borderColor} bg-white dark:bg-gray-800/50 hover:brightness-110 transition-all text-left flex flex-col gap-2 shadow-sm hover:shadow-md disabled:opacity-50 disabled:pointer-events-none`}
                                    >
                                        <span className={`text-lg font-bold ${textColor}`}>{subject}</span>
                                        <span className="text-sm text-gray-500 dark:text-gray-400">{n} concepts</span>
                                    </button>
                                );
                            })}
                        </div>
                    </section>

                    {typeof onStartBar === 'function' && (
                        <section>
                            <h3 className="text-sm font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400 mb-3">
                                Bar exam questions
                            </h3>
                            {!barAvailable && (
                                <p className="mb-4 text-sm text-gray-500 dark:text-gray-400">
                                    Bar questions load with the rest of the app. If the main screen is still loading, wait a moment — then these buttons will enable.
                                </p>
                            )}
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                <button
                                    type="button"
                                    onClick={() => onStartBar(null)}
                                    disabled={!barAvailable || barCountFor('all') === 0}
                                    className="group p-6 rounded-xl border-2 border-dashed border-emerald-300/80 dark:border-emerald-700 hover:border-emerald-500 hover:bg-emerald-50/50 dark:hover:bg-emerald-950/30 transition-all text-left flex flex-col gap-2 disabled:opacity-50 disabled:pointer-events-none"
                                >
                                    <span className="text-lg font-bold text-gray-900 dark:text-white group-hover:text-emerald-700 dark:group-hover:text-emerald-400 transition-colors">
                                        Random / All subjects
                                    </span>
                                    <span className="text-sm text-gray-500 dark:text-gray-400">
                                        {barCountFor('all')} bar questions loaded
                                    </span>
                                </button>

                                {visibleSubjects.map((subject) => {
                                    const colorClass = getSubjectColor(subject);
                                    const textColor = colorClass.split(' ').find((c) => c.startsWith('text-'));
                                    const borderColor = colorClass.split(' ').find((c) => c.startsWith('border-'));
                                    const n = barCountFor(subject);

                                    return (
                                        <button
                                            type="button"
                                            key={`b-${subject}`}
                                            onClick={() => onStartBar(subject)}
                                            disabled={!barAvailable || n === 0}
                                            className={`group p-6 rounded-xl border-2 ${borderColor} bg-white dark:bg-gray-800/50 hover:brightness-110 transition-all text-left flex flex-col gap-2 shadow-sm hover:shadow-md disabled:opacity-50 disabled:pointer-events-none`}
                                        >
                                            <span className={`text-lg font-bold ${textColor}`}>{subject}</span>
                                            <span className="text-sm text-gray-500 dark:text-gray-400">{n} questions</span>
                                        </button>
                                    );
                                })}
                            </div>
                        </section>
                    )}
                </div>

                <div className="p-6 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50 flex justify-center">
                    <button
                        type="button"
                        onClick={() => onStart('CANCEL')}
                        className="px-6 py-2 rounded-lg bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium transition-colors shadow-sm"
                    >
                        Cancel
                    </button>
                </div>
            </div>
        </div>
    );

    return createPortal(content, document.body);
};

export default FlashcardSetup;
