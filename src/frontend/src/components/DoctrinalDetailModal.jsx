import React, { useState } from 'react';
import { X, BookOpen, Scale, Gavel, AlertCircle, Zap } from 'lucide-react';
import { getSubjectColor } from '../utils/colors';

const DoctrinalDetailModal = ({ caseData, onClose, searchQuery }) => {
    if (!caseData) return null;

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
    const [isCompactView, setIsCompactView] = useState(false);

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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pb-[var(--player-height,0px)] bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white dark:bg-dark-card rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col animate-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="p-6 border-b border-gray-100 dark:border-gray-800 flex justify-between items-start bg-gradient-to-r from-gray-50 to-white dark:from-gray-800 dark:to-gray-800/50">
                    <div className="flex-1 pr-4">
                        <div className={`flex flex-wrap items-center gap-2 mb-2 ${isCompactView ? 'hidden sm:flex' : 'flex'}`}>
                            <span className={`px-2 py-0.5 text-[10px] sm:text-xs font-bold border rounded-full ${subjectColorClass}`}>
                                {subject}
                            </span>
                            <span className="px-2 py-0.5 text-[10px] sm:text-xs font-bold bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 rounded-full">
                                {year}
                            </span>
                            <span className="px-2 py-0.5 text-[10px] sm:text-xs font-bold bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300 rounded-full">
                                {topic}
                            </span>
                            {(isPIL || sourceLabel === 'PIL') && (
                                <span className="px-2 py-0.5 text-[10px] sm:text-xs font-bold bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300 rounded-full">
                                    PIL
                                </span>
                            )}
                        </div>
                        <h3 className={`text-base sm:text-lg md:text-xl font-bold text-gray-900 dark:text-white leading-tight ${isCompactView ? 'line-clamp-1' : ''}`}>
                            {highlightText(caseTitle, searchQuery)}
                        </h3>
                    </div>
                    <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
                        <button
                            className="p-1.5 rounded-full text-gray-400 hover:text-amber-600 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-all border border-transparent shadow-sm"
                            onClick={() => setIsCompactView(v => !v)}
                            title={isCompactView ? 'Show Full Labels' : 'Compact View (Hide Labels)'}
                        >
                            <Zap size={18} className={isCompactView ? 'text-amber-500 fill-amber-500' : ''} />
                        </button>
                        <button
                            onClick={onClose}
                            className="p-1.5 sm:p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 transition-colors"
                        >
                            <X size={24} />
                        </button>
                    </div>
                </div>

                {/* Content - Scrollable */}
                <div className={`flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 sm:space-y-6`}>

                    {/* Doctrine */}
                    <div className="bg-blue-50 dark:bg-blue-900/10 p-4 rounded-xl border border-blue-100 dark:border-blue-800/30">
                        <div className="flex items-center gap-2 mb-2 text-blue-700 dark:text-blue-400 font-bold uppercase tracking-wide text-xs sm:text-sm">
                            <Scale size={18} />
                            {!isCompactView && <span>Doctrine</span>}
                        </div>
                        <p className={`text-gray-800 dark:text-gray-200 italic leading-relaxed ${isCompactView ? 'text-base' : 'text-lg'}`}>
                            {highlightText(doctrine, searchQuery)}
                        </p>
                    </div>

                    {/* Digest Sections */}
                    {digestSections ? (
                        <div className={isCompactView ? "space-y-4" : "space-y-6"}>
                            <div>
                                <h4 className="font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-2 uppercase text-xs sm:text-sm tracking-wide">
                                    <BookOpen size={18} className="text-gray-400" /> {!isCompactView && "FACTS"}
                                </h4>
                                <p className={`text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap ${isCompactView ? 'text-[15px]' : 'text-base'}`}>
                                    {digestSections.facts}
                                </p>
                            </div>
                            <div>
                                <h4 className="font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-2 uppercase text-xs sm:text-sm tracking-wide">
                                    <AlertCircle size={18} className="text-gray-400" /> {!isCompactView && "ISSUE"}
                                </h4>
                                <p className={`text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap ${isCompactView ? 'text-[15px]' : 'text-base'}`}>
                                    {digestSections.issue}
                                </p>
                            </div>
                            <div>
                                <h4 className="font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-2 uppercase text-xs sm:text-sm tracking-wide">
                                    <Gavel size={18} className="text-gray-400" /> {!isCompactView && "RULING"}
                                </h4>
                                <p className={`text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap ${isCompactView ? 'text-[15px]' : 'text-base'}`}>
                                    {digestSections.ruling}
                                </p>
                            </div>
                        </div>
                    ) : (
                        <div className="text-center py-8 text-gray-400 italic">
                            Digest generation in progress...
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-6 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50 flex justify-end">
                    <button
                        onClick={onClose}
                        className="px-6 py-2.5 rounded-lg bg-gray-900 dark:bg-white text-white dark:text-gray-900 font-medium hover:opacity-90 transition-opacity"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
};

export default DoctrinalDetailModal;
