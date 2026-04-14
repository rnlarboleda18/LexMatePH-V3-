import React from 'react';
import { getSubjectColor, getSubjectAnswerColor } from '../utils/colors';
import { normalizeBarSubject } from '../utils/subjectNormalize';
import { SubjectIcon } from '../utils/subjectIcons';

import { HighlightText } from '../utils/highlight';

const QuestionCard = ({ question, onClick, searchQuery }) => {
    const subjectKey = normalizeBarSubject(question.subject) || question.subject;
    const colorClass = getSubjectColor(subjectKey);
    const textColor = colorClass.split(' ').find((c) => c.startsWith('text-'));
    const borderColor = colorClass.split(' ').find((c) => c.startsWith('border-'));
    const surfaceClass = getSubjectAnswerColor(subjectKey);

    return (
        <div
            className={`group relative flex h-[15rem] flex-col overflow-hidden rounded-xl border-2 p-3 shadow-sm ring-1 ring-violet-300/35 backdrop-blur-[1px] transition-all hover:shadow-[0_18px_44px_-16px_rgba(109,40,217,0.22)] dark:ring-purple-500/20 ${surfaceClass} border-l-[5px] ${borderColor}`}
        >
            {/* Header: ID - Subject (Year) */}
            <div className={`flex items-center gap-2 mb-2 ${textColor}`}>
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-white/60 bg-white/80 dark:border-white/10 dark:bg-slate-900/50">
                    <SubjectIcon subject={subjectKey} className="h-4 w-4" />
                </span>
                <span className="min-w-0 text-sm font-bold leading-tight">
                    #{question.id} – {subjectKey} ({question.year})
                </span>
            </div>

            {/* Source Label */}
            <div className="flex items-center gap-2 mb-2">
                <span
                    className={`px-2 py-0.5 rounded-full text-[11px] font-semibold border bg-white/75 dark:bg-slate-900/60 ${textColor} ${borderColor}`}
                >
                    {question.year} Bar Exam Question {question.source_label && `(${question.source_label})`}
                </span>
            </div>

            {/* Question Preview */}
            <div className="mb-3 min-h-0 flex-1">
                <p className="text-gray-800 dark:text-gray-200 text-sm leading-relaxed line-clamp-4">
                    <HighlightText text={question.text} query={searchQuery} />
                </p>
            </div>

            {/* Footer Button — subject outline to match modal accents */}
            <button
                type="button"
                onClick={onClick}
                className={`w-full rounded-lg border-2 py-2 text-sm font-semibold transition-colors shadow-sm bg-white/90 hover:bg-white dark:bg-slate-900/70 dark:hover:bg-slate-800/90 ${borderColor} ${textColor}`}
            >
                View Details
            </button>
        </div>
    );
};

export default React.memo(QuestionCard);
