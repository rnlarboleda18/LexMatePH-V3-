import React from 'react';
import { getSubjectColor } from '../utils/colors';
import { normalizeBarQuestionSubject } from '../utils/subjectNormalize';
import { SubjectIcon } from '../utils/subjectIcons';

import { HighlightText } from '../utils/highlight';
import CardVioletInnerWash from './CardVioletInnerWash';
import { CHROME_INTERACTIVE_TILE_HOVER } from '../utils/filterChromeClasses';

const QuestionCard = ({ question, onClick, searchQuery }) => {
    const subjectKey = normalizeBarQuestionSubject(question) || question.subject;
    const colorClass = getSubjectColor(subjectKey);
    const textColor = colorClass.split(' ').find((c) => c.startsWith('text-'));
    const borderColor = colorClass.split(' ').find((c) => c.startsWith('border-'));

    return (
        <div
            className={`group relative flex w-full flex-col sm:flex-row overflow-hidden rounded-lg border border-lex bg-white p-4 shadow-sm dark:border-lex dark:bg-zinc-900 gap-4 sm:gap-6 ${CHROME_INTERACTIVE_TILE_HOVER}`}
        >
            <CardVioletInnerWash />
            <div className="relative z-[1] flex w-full flex-col sm:flex-row gap-4 sm:gap-6 min-h-0">
                {/* Left Block: Metadata */}
                <div className="flex flex-col sm:w-[200px] md:w-[240px] shrink-0 sm:border-r sm:border-lex sm:pr-4 gap-3">
                    {/* Header: ID & Subject */}
                    <div className={`flex items-start gap-2.5 ${textColor}`}>
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-lex-strong bg-slate-50 dark:border-lex-strong dark:bg-zinc-800 shadow-sm">
                            <SubjectIcon subject={subjectKey} className="h-4 w-4" />
                        </span>
                        <div className="flex flex-col min-w-0">
                            <span className="text-[10px] font-bold tracking-wider uppercase text-neutral-400 dark:text-zinc-500">
                                Question #{question.id}
                            </span>
                            <span className="text-sm font-bold leading-tight truncate">
                                {subjectKey}
                            </span>
                        </div>
                    </div>

                    {/* Source & Year Info */}
                    <div className="flex flex-col gap-1.5">
                        <span
                            className={`inline-flex self-start rounded-full border px-2 py-0.5 text-[11px] font-semibold bg-white dark:bg-zinc-800/80 ${textColor} ${borderColor}`}
                        >
                            {question.year} Bar Exam
                        </span>
                        {question.source_label && (
                            <span className="text-xs text-neutral-500 dark:text-zinc-400 font-medium">
                                {question.source_label}
                            </span>
                        )}
                    </div>

                    {/* Desktop/Tablet Action Button */}
                    <div className="hidden sm:block mt-auto pt-3">
                        <button
                            type="button"
                            onClick={onClick}
                            className={`w-full rounded-lg border border-lex-strong bg-white py-2 text-sm font-semibold shadow-sm transition-colors hover:bg-slate-50 dark:border-lex-strong dark:bg-zinc-800 dark:hover:bg-zinc-700 ${textColor}`}
                        >
                            View Details
                        </button>
                    </div>
                </div>

                {/* Right Block: Question Preview */}
                <div className="flex flex-col flex-1 min-h-0 justify-center">
                    <p className="text-gray-800 dark:text-gray-200 text-sm leading-relaxed line-clamp-5 sm:line-clamp-6">
                        <HighlightText text={question.text} query={searchQuery} />
                    </p>

                    {/* Mobile Action Button */}
                    <div className="block sm:hidden mt-4">
                        <button
                            type="button"
                            onClick={onClick}
                            className={`w-full rounded-lg border border-lex-strong bg-white py-2 text-sm font-semibold shadow-sm transition-colors hover:bg-slate-50 dark:border-lex-strong dark:bg-zinc-800 dark:hover:bg-zinc-700 ${textColor}`}
                        >
                            View Details
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default React.memo(QuestionCard);
