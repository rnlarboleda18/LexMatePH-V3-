import React, { useState, useEffect } from 'react';
import { Download, X, FileText } from 'lucide-react';
import { formatDate } from '../utils/dateUtils';
import { toTitleCase } from '../utils/textUtils';

import ReactMarkdown from 'react-markdown';

const DigestHtmlViewer = ({ decision, onClose, onDownload }) => {
    // Defer the heavy ReactMarkdown render so the overlay paints first (prevents main-thread freeze on open).
    const [contentReady, setContentReady] = useState(false);
    useEffect(() => {
        const id = requestAnimationFrame(() =>
            requestAnimationFrame(() => setContentReady(true))
        );
        return () => cancelAnimationFrame(id);
    }, []);

    if (!decision) return null;

    // Helper to ensure markdown bold patterns get properly spaced into paragraphs
    const formatContent = (content) => {
        if (!content) return '';
        let formatted = content.replace(/^\s*[\*\-]\s+/gm, '\n\n');
        // If a bold header lacks a double newline before it, enforce one
        formatted = formatted.replace(/([^\n])\n?(\*\*.*?\*\*[:?]?)/g, '$1\n\n$2');
        return formatted.trim();
    };

    const Section = ({ title, content, isItalic }) => {
        if (!content || !content.trim()) return null;
        const formattedContent = formatContent(content);

        return (
            <div className="mb-6 page-break-inside-avoid">
                <h3 className="text-[14px] font-bold text-black mb-2 uppercase">{title}</h3>
                <div className={`text-[13px] text-gray-900 text-justify leading-relaxed ${isItalic ? 'italic' : ''}`}>
                    <ReactMarkdown components={{
                        p: ({ node, ...props }) => <p className="mb-3 last:mb-0" {...props} />,
                        strong: ({ node, ...props }) => <strong className="font-bold text-black" {...props} />
                    }}>
                        {formattedContent}
                    </ReactMarkdown>
                </div>
            </div>
        );
    };

    return (
        <div className="fixed inset-0 z-[100] bg-gray-100 dark:bg-gray-900 flex flex-col animate-in fade-in duration-200">
            {/* STICKY TOP ACTION BAR */}
            <div className="bg-white dark:bg-slate-800 border-b border-gray-200 dark:border-gray-700 p-4 flex items-center justify-between shadow-sm z-10 shrink-0">
                <div className="flex items-center gap-3">
                    <button
                        onClick={onClose}
                        className="p-2 -ml-2 rounded-full hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 dark:text-gray-400 transition-colors"
                        title="Close Preview"
                    >
                        <X size={24} />
                    </button>
                    <div className="flex flex-col">
                        <h2 className="text-md font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                            <FileText size={18} className="text-blue-500" />
                            Case Digest Preview
                        </h2>
                        <span className="text-xs text-gray-500 font-mono hidden sm:inline-block">
                            {decision.case_number || decision.gr_number}
                        </span>
                    </div>
                </div>

                <button
                    type="button"
                    onClick={onDownload}
                    className="hidden items-center gap-2 rounded-lg bg-amber-500 px-5 py-2.5 text-sm font-bold text-white shadow-md transition-all hover:bg-amber-600 hover:shadow-lg active:scale-95 md:inline-flex"
                >
                    <Download size={18} aria-hidden />
                    Download PDF
                </button>
            </div>

            {/* SCROLLABLE A4 CANVAS CONTAINER */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-8 bg-gray-200 dark:bg-slate-900/80 custom-scrollbar">
                {!contentReady ? (
                    <div className="flex flex-col items-center gap-4 py-24 text-gray-500 dark:text-gray-400">
                        <div className="h-8 w-8 animate-spin rounded-full border-4 border-purple-300 border-t-purple-600 dark:border-purple-700 dark:border-t-purple-300" />
                        <span className="text-sm">Preparing digest…</span>
                    </div>
                ) : (
                    /* A4 PAPER SIMULATION */
                    <div className="bg-white w-full max-w-[210mm] min-h-[297mm] mx-auto shadow-2xl p-[20mm] font-sans text-black box-border relative h-max">
                        
                        {/* Header: Centered */}
                        <div className="text-center mb-8 border-b-2 border-black pb-4">
                            <h1 className="text-[22px] font-bold mb-2">Supreme Court Decision Digest</h1>
                            
                            <h2 className="text-[18px] font-bold leading-snug mx-auto max-w-[90%] mb-2">
                                {toTitleCase(decision.short_title || decision.title || '')}
                            </h2>
                            
                            <div className="text-[14px]">
                                G.R. No. {decision.case_number || decision.gr_number} | {formatDate(decision.date_str || decision.date)}
                            </div>
                        </div>

                        {/* Content Sections */}
                        <div className="w-full">
                            <Section title="MAIN DOCTRINE" content={decision.main_doctrine} isItalic={true} />
                            <Section title="FACTS" content={decision.digest_facts} />
                            <Section title="ISSUE(S)" content={decision.digest_issues} />
                            <Section title="RULING" content={decision.digest_ruling} />
                            <Section title="RATIO DECIDENDI" content={decision.digest_ratio} />
                        </div>
                        
                    </div>
                )}
            </div>
        </div>
    );
};

export default DigestHtmlViewer;
