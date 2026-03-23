
import React, { useState, useEffect } from 'react';

const CodexJurisSidebar = ({ articleNum, statuteId = 'RPC', subject, onClose, onSelectRatio, paragraphFilter }) => {
    const [groupedLinks, setGroupedLinks] = useState({});
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!articleNum) return;

        const fetchLinks = async () => {
            setLoading(true);
            setError(null);
            try {
                // Construct URL
                let url = `/api/codex/jurisprudence?statute_id=${statuteId}&provision_id=${articleNum}`;
                if (subject) url += `&subject=${subject}`;

                const res = await fetch(url);
                if (!res.ok) throw new Error("Failed to fetch jurisprudence");

                const data = await res.json();

                // Group by Case ID
                const groups = {};
                data.forEach(link => {
                    // Filter by paragraph if specified
                    // Note: paragraphFilter can be 0, so check strict null/undefined
                    if (paragraphFilter !== null && paragraphFilter !== undefined) {
                        // API returns integer indices
                        if (link.target_paragraph_index !== paragraphFilter) return;
                    }

                    if (!groups[link.case_id]) {
                        groups[link.case_id] = {
                            caseId: link.case_id,
                            shortTitle: link.short_title,
                            date: link.case_date,
                            ratios: []
                        };
                    }
                    groups[link.case_id].ratios.push(link);
                });

                // Convert to array and Sort by Date DESC
                const sortedGroups = Object.values(groups).sort((a, b) => {
                    const dateA = new Date(a.date);
                    const dateB = new Date(b.date);
                    return dateB - dateA; // Newest first
                });

                setGroupedLinks(sortedGroups);
            } catch (err) {
                console.error(err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchLinks();
    }, [articleNum, statuteId, subject, paragraphFilter]);

    if (!articleNum) return null;

    return (
        <div className="h-full min-h-0 flex flex-col bg-transparent transition-all duration-300">
            {/* Header */}
            <div className="p-3 bg-white/30 dark:bg-slate-800/30 backdrop-blur-sm border-b border-white/20 dark:border-white/5 flex justify-between items-center sticky top-0 z-10">
                <div>
                    <h3 className="text-[16px] font-bold text-gray-800 dark:text-gray-200 uppercase tracking-wide">Jurisprudence</h3>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Atomic Ratios for Art. {articleNum}</p>
                </div>
                <button
                    onClick={onClose}
                    className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full text-gray-500 dark:text-gray-400"
                >
                    ✕
                </button>
            </div>

            {/* Content List */}
            <div
                className="flex-1 min-h-0 overflow-y-scroll overscroll-contain p-3 space-y-4"
                style={{ WebkitOverflowScrolling: 'touch', touchAction: 'pan-y' }}
            >
                {loading && (
                    <div className="flex justify-center p-8">
                        <div className="animate-spin h-6 w-6 border-2 border-indigo-500 rounded-full border-t-transparent"></div>
                    </div>
                )}

                {error && (
                    <div className="p-4 bg-red-50 text-red-600 rounded-lg text-sm">
                        ⚠️ {error}
                    </div>
                )}

                {!loading && !error && Object.keys(groupedLinks).length === 0 && (
                    <div className="text-center p-8 text-gray-500 text-sm">
                        No jurisprudence linked to Article {articleNum} yet.
                    </div>
                )}

                {Object.values(groupedLinks).map((group) => {
                    const firstLink = group.ratios[0];
                    return (
                        <div
                            key={group.caseId}
                            className="glass bg-white/60 dark:bg-slate-800/40 rounded-lg border border-white/40 dark:border-white/5 shadow-sm hover:shadow-md transition-shadow group overflow-hidden"
                        >
                            {/* Card Header: Case Info (Clickable for whole Digest) */}
                            <div
                                onClick={() => onSelectRatio && onSelectRatio(group.caseId, firstLink.ratio_index)}
                                className="p-3 bg-white/40 dark:bg-slate-800/60 border-b border-white/20 dark:border-white/5 cursor-pointer hover:bg-white/60 dark:hover:bg-slate-700/60 transition-colors"
                            >
                                <div className="flex justify-between items-start mb-1">
                                    <h4 className="font-semibold text-indigo-700 dark:text-indigo-400 text-[16px] leading-tight group-hover:underline">
                                        {group.shortTitle}
                                    </h4>
                                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${firstLink.citation_rank <= 10 ? 'bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-500' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
                                        }`}>
                                        #{firstLink.citation_rank}
                                    </span>
                                </div>
                                <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center space-x-2">
                                    <span>{new Date(group.date).getFullYear()}</span>
                                    <span>•</span>
                                    <span className="truncate">{firstLink.subject_area}</span>
                                </div>
                            </div>

                            {/* List of Atomic Ratios */}
                            <div className="p-2 space-y-3 bg-transparent">
                                {group.ratios.map((ratio, idx) => (
                                    <div
                                        key={ratio.link_id}
                                        onClick={(e) => {
                                            e.stopPropagation(); // Don't trigger header click
                                            onSelectRatio && onSelectRatio(group.caseId, ratio.ratio_index);
                                        }}
                                        className="relative pl-3 cursor-pointer hover:bg-indigo-50/50 dark:hover:bg-indigo-900/20 rounded transition-colors -ml-1 p-1"
                                    >
                                        <div className="absolute left-0 top-2 bottom-2 w-0.5 bg-indigo-200 dark:bg-indigo-700"></div>
                                        <p className="text-sm text-gray-800 dark:text-gray-300 leading-relaxed font-serif">
                                            "{ratio.specific_ruling}"
                                        </p>

                                        {/* Status Tags per Ratio */}
                                        <div className="flex gap-2 mt-1">
                                            {ratio.is_resolved ? (
                                                <span className="text-[9px] text-green-600 dark:text-green-400 font-medium flex items-center gap-1">
                                                    {ratio.target_paragraph_index !== undefined && ratio.target_paragraph_index !== null && ratio.target_paragraph_index >= 0 ? (
                                                        <span className="bg-green-100 dark:bg-green-900/50 px-1 rounded flex items-center">
                                                            ¶ {ratio.target_paragraph_index + 1}
                                                        </span>
                                                    ) : (
                                                        <span className="bg-blue-100 dark:bg-blue-900/50 px-1 rounded text-green-600 dark:text-green-400">General Concept</span>
                                                    )}
                                                </span>
                                            ) : (
                                                <span className="text-[9px] text-gray-400 dark:text-gray-500">Unverified</span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default CodexJurisSidebar;
