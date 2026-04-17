import React from 'react';
import { getSubjectColor } from '../utils/colors';
import { normalizeBarQuestionSubject } from '../utils/subjectNormalize';
import { SubjectIcon } from '../utils/subjectIcons';

import { HighlightText } from '../utils/highlight';
import CardVioletInnerWash from './CardVioletInnerWash';

const QuestionCard = ({ question, onClick, searchQuery }) => {
    const subjectKey = normalizeBarQuestionSubject(question) || question.subject;
    const colorClass = getSubjectColor(subjectKey);
    const textColor = colorClass.split(' ').find((c) => c.startsWith('text-'));
    const borderColor = colorClass.split(' ').find((c) => c.startsWith('border-'));

    return (
        <div
            className="group relative flex w-full flex-col overflow-hidden rounded-lg border border-lex bg-white p-3 shadow-sm transition-shadow hover:shadow-md dark:border-lex dark:bg-zinc-900 max-sm:mx-auto max-sm:aspect-square max-sm:min-h-0 max-sm:min-w-0 max-sm:max-w-[min(30rem,calc(100dvh-14rem),calc(100vw-2.5rem))] sm:aspect-auto sm:h-[15rem] sm:max-w-none sm:mx-0"
        >
            <CardVioletInnerWash />
            <div className="relative z-[1] flex min-h-0 flex-1 flex-col">
            {/* Header: ID - Subject (Year) */}
            <div className={`mb-2 flex items-center gap-2 ${textColor}`}>
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-lex-strong bg-slate-50 dark:border-lex-strong dark:bg-zinc-800">
                    <SubjectIcon subject={subjectKey} className="h-4 w-4" />
                </span>
                <span className="min-w-0 text-sm font-bold leading-tight">
                    #{question.id} – {subjectKey} ({question.year})
                </span>
            </div>

            {/* Source Label */}
            <div className="mb-2 flex items-center gap-2">
                <span
                    className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold bg-white dark:bg-zinc-800/80 ${textColor} ${borderColor}`}
                >
                    {question.year} Bar Exam Question {question.source_label && `(${question.source_label})`}
                </span>
            </div>

            {/* Question Preview */}
            <div className="mb-3 min-h-0 flex-1">
                <p className="text-gray-800 dark:text-gray-200 text-sm leading-relaxed line-clamp-4 max-sm:line-clamp-8">
                    <HighlightText text={question.text} query={searchQuery} />
                </p>
            </div>

            {/* Footer — neutral frame; subject color on label text only */}
            <button
                type="button"
                onClick={onClick}
                className={`w-full rounded-lg border border-lex-strong bg-white py-2 text-sm font-semibold shadow-sm transition-colors hover:bg-slate-50 dark:border-lex-strong dark:bg-zinc-800 dark:hover:bg-zinc-700 ${textColor}`}
            >
                View Details
            </button>
            </div>
        </div>
    );
};

export default React.memo(QuestionCard);
