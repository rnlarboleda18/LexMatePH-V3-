import React from 'react';
import { getSubjectColor } from '../utils/colors';

import { HighlightText } from '../utils/highlight';

const QuestionCard = ({ question, onClick, searchQuery }) => {
    const colorClass = getSubjectColor(question.subject);
    const textColor = colorClass.split(' ').find(c => c.startsWith('text-'));
    const borderColor = colorClass.split(' ').find(c => c.startsWith('border-'));

    return (
        <div
            className={`group bg-white dark:bg-dark-card rounded-xl shadow-sm hover:shadow-md border-2 ${borderColor} p-4 flex flex-col h-full border-l-[6px]`}
        >
            {/* Header: ID - Subject (Year) */}
            <div className={`text-sm font-bold mb-2 ${textColor}`}>
                #{question.id} – {question.subject} ({question.year})
            </div>

            {/* Source Label */}
            <div className="flex items-center gap-2 mb-2">
                <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-slate-300 dark:border-gray-700">
                    {question.year} Bar Exam Question {question.source_label && `(${question.source_label})`}
                </span>
            </div>

            {/* Question Preview */}
            <div className="flex-grow mb-3">
                <p className="text-gray-600 dark:text-gray-300 text-sm leading-relaxed line-clamp-4">
                    <HighlightText text={question.text} query={searchQuery} />
                </p>
            </div>

            {/* Footer Button */}
            <button
                onClick={onClick}
                className="w-full py-2 rounded-lg bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium transition-colors shadow-sm"
            >
                View Details
            </button>
        </div>
    );
};

export default QuestionCard;
