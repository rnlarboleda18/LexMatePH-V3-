import React, { useState, useEffect } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { apiUrl } from '../utils/apiUrl';

/** Short-lived in-memory cache so reopening the same article avoids a round-trip. */
const JURIS_SIDEBAR_CACHE_MS = 90_000;
const _jurisSidebarCache = new Map();

function _jurisSidebarCacheKey(statuteId, articleNum, subject, paragraphFilter) {
    return `${statuteId || ''}\t${articleNum || ''}\t${subject || ''}\t${paragraphFilter ?? '\x00'}`;
}

function _jurisSidebarCacheGet(key) {
    const e = _jurisSidebarCache.get(key);
    if (!e) return null;
    if (Date.now() > e.exp) {
        _jurisSidebarCache.delete(key);
        return null;
    }
    return e.value;
}

function _jurisSidebarCacheSet(key, value) {
    _jurisSidebarCache.set(key, { exp: Date.now() + JURIS_SIDEBAR_CACHE_MS, value });
}

const LexCodeJurisSidebar = ({ articleNum, statuteId = 'RPC', subject, onClose, onSelectRatio, paragraphFilter }) => {
    const { getToken } = useAuth();
    const [groupedLinks, setGroupedLinks] = useState([]);
    const [availablePonentes, setAvailablePonentes] = useState([]);
    const [ponenteFilter, setPonenteFilter] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!articleNum) return;

        const ctrl = new AbortController();
        const cacheKey = _jurisSidebarCacheKey(statuteId, articleNum, subject, paragraphFilter);
        const cached = _jurisSidebarCacheGet(cacheKey);
        if (cached) {
            setGroupedLinks(cached.sortedGroups);
            setAvailablePonentes(cached.pentes);
            setLoading(false);
            setError(null);
            return () => ctrl.abort();
        }

        const fetchLinks = async () => {
            setLoading(true);
            setError(null);
            try {
                let path = `/api/codex/jurisprudence?statute_id=${encodeURIComponent(statuteId)}&provision_id=${encodeURIComponent(articleNum)}`;
                if (subject) path += `&subject=${encodeURIComponent(subject)}`;
                const url = apiUrl(path);

                let token = null;
                try { token = await getToken(); } catch (_) { /* ignore */ }
                const headers = token ? { 'X-Clerk-Authorization': `Bearer ${token}` } : {};

                const res = await fetch(url, { headers, signal: ctrl.signal });
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

                    const cid = link.case_id;
                    if (!groups[cid]) {
                        groups[cid] = {
                            caseId: cid,
                            shortTitle: link.short_title,
                            date: link.case_date,
                            ponente: link.ponente,
                            ratios: []
                        };
                    }
                    groups[cid].ratios.push(link);
                });

                // Convert to array and Sort by Date DESC
                const sortedGroups = Object.values(groups).sort((a, b) => {
                    const dateA = new Date(a.date);
                    const dateB = new Date(b.date);
                    return dateB - dateA; // Newest first
                });

                // Extract unique ponentes, filtering out falsy values
                const ponentes = [...new Set(sortedGroups.map(g => g.ponente).filter(Boolean))].sort();

                setGroupedLinks(sortedGroups);
                setAvailablePonentes(ponentes);
                _jurisSidebarCacheSet(cacheKey, { sortedGroups, pentes: ponentes });
            } catch (err) {
                if (err?.name === 'AbortError') return;
                console.error(err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        void fetchLinks();
        return () => ctrl.abort();
    // getToken is a stable function reference from Clerk — safe to omit
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [articleNum, statuteId, subject, paragraphFilter]);

    if (!articleNum) return null;

    return (
        <div className="h-full min-h-0 flex flex-col bg-transparent transition-all duration-300">
            {/* Header */}
            <div className="p-3 bg-slate-50 dark:bg-zinc-800 border-b border-lex flex flex-col gap-2 sticky top-0 z-10">
                <div className="flex justify-between items-center">
                    <div>
                        <h3 className="text-[16px] font-bold text-black dark:text-zinc-100 uppercase tracking-wide">Jurisprudence</h3>
                        <p className="text-xs text-slate-500 dark:text-gray-400">Atomic Ratios for Art. {articleNum}</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1 hover:bg-slate-200 dark:hover:bg-gray-800 rounded-full text-slate-500 dark:text-gray-400 transition-colors"
                    >
                        ✕
                    </button>
                </div>
                {/* Ponente Filter */}
                {availablePonentes.length > 0 && (
                    <select
                        value={ponenteFilter}
                        onChange={(e) => setPonenteFilter(e.target.value)}
                        className="w-full mt-1 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-xs rounded-lg px-2 py-1.5 outline-none shadow-sm cursor-pointer"
                    >
                        <option value="">All Ponentes</option>
                        {availablePonentes.map(p => (
                            <option key={p} value={p}>{p}</option>
                        ))}
                    </select>
                )}
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

                {!loading && !error && groupedLinks.length === 0 && (
                    <div className="text-center p-8 text-gray-500 text-sm">
                        No jurisprudence linked to Article {articleNum} yet.
                    </div>
                )}

                {groupedLinks
                    .filter(group => !ponenteFilter || group.ponente === ponenteFilter)
                    .map((group) => {
                    const firstLink = group.ratios[0];
                    return (
                        <div
                            key={group.caseId}
                            className="bg-white/90 dark:bg-slate-800/70 rounded-lg border-2 border-slate-300/75 dark:border-white/5 shadow-sm hover:shadow-md transition-shadow group overflow-hidden"
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
                                <div className="text-xs text-gray-500 dark:text-gray-400 flex flex-wrap items-center gap-1.5 mt-1">
                                    <span className="font-semibold text-slate-600 dark:text-slate-300">{new Date(group.date).getFullYear()}</span>
                                    {group.ponente && (
                                        <>
                                            <span>•</span>
                                            <span className="font-medium text-slate-600 dark:text-slate-300 truncate max-w-[120px]">{group.ponente}</span>
                                        </>
                                    )}
                                    <span>•</span>
                                    <span className="truncate flex-1">{firstLink.subject_area}</span>
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

export default LexCodeJurisSidebar;
