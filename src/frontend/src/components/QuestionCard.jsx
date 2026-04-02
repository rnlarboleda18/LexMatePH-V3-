import React from 'react';
import { getSubjectColor, getSubjectAnswerColor } from '../utils/colors';
import { normalizeBarSubject } from '../utils/subjectNormalize';

import { HighlightText } from '../utils/highlight';

const QuestionCard = ({ question, onClick, searchQuery }) => {
    const subjectKey = normalizeBarSubject(question.subject) || question.subject;
    const colorClass = getSubjectColor(subjectKey);
    const textColor = colorClass.split(' ').find((c) => c.startsWith('text-'));
    const borderColor = colorClass.split(' ').find((c) => c.startsWith('border-'));
    const surfaceClass = getSubjectAnswerColor(subjectKey);

    return (
        <div
            className={`group relative flex flex-col h-full overflow-hidden rounded-xl border-2 p-3 shadow-sm transition-all hover:shadow-md ${surfaceClass} border-l-[5px] ${borderColor}`}
        >
            {/* Header: ID - Subject (Year) */}
            <div className={`text-sm font-bold mb-2 ${textColor}`}>
                #{question.id} – {subjectKey} ({question.year})
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

export default QuestionCard;
