import React from 'react';

import { getSubjectColor } from '../utils/colors';

const DoctrinalCard = ({ caseData, searchQuery, onClick }) => {
    const {
        'Case Title': caseTitle,
        'Year': year,
        'Key Topic': topic,
        'Doctrine / Ruling': doctrine,
        'Digest': digest,
        'Subject': subject,
        'source_label': sourceLabel
    } = caseData;

    const subjectColorClass = getSubjectColor(subject);
    const textColor = subjectColorClass.split(' ').find(c => c.startsWith('text-'));
    const borderColor = subjectColorClass.split(' ').find(c => c.startsWith('border-'));

    // Helper to highlight search terms
    const highlightText = (text, query) => {
        if (!query || !text) return text;
        const parts = text.toString().split(new RegExp(`(${query})`, 'gi'));
        return parts.map((part, i) =>
            part.toLowerCase() === query.toLowerCase() ? (
                <span key={i} className="bg-yellow-200 dark:bg-yellow-900 text-black dark:text-white px-0.5 rounded">
                    {part}
                </span>
            ) : (
                part
            )
        );
    };

    // Parse Digest sections (FACTS, ISSUE, RULING)
    const parseDigest = (digestText) => {
        if (!digestText) return null;

        const sections = {
            facts: '',
            issue: '',
            ruling: ''
        };

        // Simple parsing based on the expected format
        const factsMatch = digestText.match(/\*\*FACTS:\*\*\s*([\s\S]*?)(?=\*\*ISSUE:|$)/i);
        const issueMatch = digestText.match(/\*\*ISSUE:\*\*\s*([\s\S]*?)(?=\*\*RULING:|$)/i);
        const rulingMatch = digestText.match(/\*\*RULING:\*\*\s*([\s\S]*)/i);

        if (factsMatch) sections.facts = factsMatch[1].trim();
        if (issueMatch) sections.issue = issueMatch[1].trim();
        if (rulingMatch) sections.ruling = rulingMatch[1].trim();

        return sections;
    };

    const digestSections = parseDigest(digest);
    const isPIL = sourceLabel === 'PIL';

    return (
        <div className={`group bg-white dark:bg-dark-card rounded-xl shadow-sm hover:shadow-md border-2 ${borderColor} p-4 flex flex-col h-full border-l-[6px] transition-all duration-200`}>
            {/* Header: ID - Subject (Year) */}
            <div className={`text-sm font-bold mb-2 ${textColor}`}>
                {subject} ({year})
            </div>

            <div className="flex items-center gap-2 mb-2 flex-wrap">
                <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-slate-300 dark:border-gray-700">
                    {topic}
                </span>
                {(isPIL || sourceLabel === 'PIL') && (
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300 border border-orange-300 dark:border-orange-800">
                        PIL
                    </span>
                )}
            </div>

            {/* Case Title */}
            <h3 className="text-sm font-bold text-gray-900 dark:text-white mb-2 leading-tight line-clamp-2">
                {highlightText(caseTitle, searchQuery)}
            </h3>

            {/* Doctrine Preview */}
            <div className="flex-grow mb-3">
                <p className="text-gray-600 dark:text-gray-300 text-sm leading-relaxed line-clamp-4">
                    <span className="font-semibold text-blue-600 dark:text-blue-400 mr-1">Doctrine:</span>
                    {highlightText(doctrine, searchQuery)}
                </p>
            </div>

            {/* Footer Button */}
            <button
                onClick={() => onClick(caseData)}
                className="w-full py-2 rounded-lg bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium transition-colors shadow-sm mt-auto"
            >
                View Details
            </button>
        </div>
    );
};

export default DoctrinalCard;
