import React, { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import { useAuth } from '@clerk/clerk-react';
import { apiUrl } from '../utils/apiUrl';
import CardVioletInnerWash from './CardVioletInnerWash';
import { CHROME_INTERACTIVE_TILE_ELEVATE } from '../utils/filterChromeClasses';

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

/** Year from `sc_decided_cases.date` for sidebar display; null if missing or not parseable. */
function scLinkedCaseYear(raw) {
    if (raw == null || raw === '') return null;
    const d = new Date(raw);
    if (Number.isNaN(d.getTime())) return null;
    return d.getFullYear();
}

/**
 * Client-side paragraph filter for juris rows.
 * RPC linker rows often use target_paragraph_index NULL or -1 for whole-article / general links,
 * while LexCode opens the sidebar with paragraphFilter -1 for the header gavel. Strict !== would
 * drop every row (null !== -1). For a specific paragraph, NULL/-1 still means the case ties to
 * the whole article and should appear (same idea as Civil / Family paragraph-level browsing).
 */
function linkMatchesParagraphFilter(targetParagraphIndex, paragraphFilter) {
    if (paragraphFilter === null || paragraphFilter === undefined) return true;
    const f = Number(paragraphFilter);
    if (Number.isNaN(f)) return true;

    const raw = targetParagraphIndex;
    const li =
        raw === null || raw === undefined ? null : Number(raw);
    const liNorm = li !== null && Number.isNaN(li) ? null : li;

    if (f === -1) {
        return liNorm === null || liNorm === -1;
    }
    if (liNorm === null || liNorm === -1) return true;
    return liNorm === f;
}

const LexCodeJurisSidebar = ({ articleNum, statuteId = 'RPC', subject, onClose, onSelectRatio, paragraphFilter }) => {
    const { getToken } = useAuth();
    const [groupedLinks, setGroupedLinks] = useState([]);
    const [availablePonentes, setAvailablePonentes] = useState([]);
    const [availableDivisions, setAvailableDivisions] = useState([]);
    const [ponenteFilter, setPonenteFilter] = useState('');
    const [divisionFilter, setDivisionFilter] = useState('');
    /** Start true: first paint must not show the empty state before useEffect runs (fetch is async). */
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const provisionLabel = statuteId === 'RCC' ? 'Section' : 'Article';

    useEffect(() => {
        if (!articleNum) return;

        const ctrl = new AbortController();
        const cacheKey = _jurisSidebarCacheKey(statuteId, articleNum, subject, paragraphFilter);
        const cached = _jurisSidebarCacheGet(cacheKey);
        if (cached) {
            setGroupedLinks(cached.sortedGroups);
            setAvailablePonentes(cached.pentes);
            setAvailableDivisions(cached.divs ?? []);
            setLoading(false);
            setError(null);
            return () => ctrl.abort();
        }

        setLoading(true);
        setError(null);
        setGroupedLinks([]);
        setAvailablePonentes([]);
        setAvailableDivisions([]);

        const fetchLinks = async () => {
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
                const rows = Array.isArray(data) ? data : [];

                // Group by Case ID
                const groups = {};
                rows.forEach(link => {
                    if (!linkMatchesParagraphFilter(link.target_paragraph_index, paragraphFilter)) {
                        return;
                    }

                    const cid = link.case_id;
                    if (!groups[cid]) {
                        groups[cid] = {
                            caseId: cid,
                            shortTitle: link.short_title,
                            date: link.case_date,
                            ponente: link.ponente,
                            division: link.division,
                            ratios: []
                        };
                    }
                    groups[cid].ratios.push(link);
                });

                // Convert to array and Sort by Date DESC
                const sortedGroups = Object.values(groups).sort((a, b) => {
                    const ya = scLinkedCaseYear(a.date);
                    const yb = scLinkedCaseYear(b.date);
                    const na = ya === null;
                    const nb = yb === null;
                    if (na && nb) return 0;
                    if (na) return 1;
                    if (nb) return -1;
                    return yb - ya;
                });

                // Extract unique ponentes, filtering out falsy values
                const ponentes = [...new Set(sortedGroups.map(g => g.ponente).filter(Boolean))].sort();

                // Extract unique deciding bodies with canonical sort order
                const DIVISION_ORDER = ['En Banc', 'First Division', 'Second Division', 'Third Division', 'Fourth Division', 'Fifth Division', 'Sixth Division'];
                const rawDivisions = [...new Set(sortedGroups.map(g => g.division).filter(Boolean))];
                const divisions = rawDivisions.sort((a, b) => {
                    const ia = DIVISION_ORDER.indexOf(a);
                    const ib = DIVISION_ORDER.indexOf(b);
                    if (ia !== -1 && ib !== -1) return ia - ib;
                    if (ia !== -1) return -1;
                    if (ib !== -1) return 1;
                    return a.localeCompare(b);
                });

                setGroupedLinks(sortedGroups);
                setAvailablePonentes(ponentes);
                setAvailableDivisions(divisions);
                _jurisSidebarCacheSet(cacheKey, { sortedGroups, pentes: ponentes, divs: divisions });
            } catch (err) {
                if (err?.name === 'AbortError') return;
                console.error(err);
                setError(err.message);
            } finally {
                if (!ctrl.signal.aborted) {
                    setLoading(false);
                }
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
                        <p className="text-xs text-slate-500 dark:text-gray-400">
                            Atomic ratios for {provisionLabel} {articleNum}
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1 hover:bg-slate-200 dark:hover:bg-gray-800 rounded-full text-slate-500 dark:text-gray-400 transition-colors"
                    >
                        ✕
                    </button>
                </div>
                {/* Deciding Body Filter */}
                {availableDivisions.length > 0 && (
                    <select
                        value={divisionFilter}
                        onChange={(e) => setDivisionFilter(e.target.value)}
                        className="w-full mt-1 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-xs rounded-lg px-2 py-1.5 outline-none shadow-sm cursor-pointer"
                    >
                        <option value="">All Deciding Bodies</option>
                        {availableDivisions.map(d => (
                            <option key={d} value={d}>{d}</option>
                        ))}
                    </select>
                )}
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
                    <div
                        className="flex flex-col items-center justify-center gap-3 py-12 text-slate-600 dark:text-slate-400"
                        role="status"
                        aria-live="polite"
                        aria-busy="true"
                    >
                        <Loader2 className="h-8 w-8 shrink-0 animate-spin text-indigo-500 dark:text-indigo-400" aria-hidden />
                        <p className="text-center text-sm font-medium">Loading linked cases…</p>
                    </div>
                )}

                {error && (
                    <div className="p-4 bg-red-50 text-red-600 rounded-lg text-sm">
                        ⚠️ {error}
                    </div>
                )}

                {!loading && !error && groupedLinks.length === 0 && (
                    <div className="text-center p-8 text-gray-500 text-sm">
                        No jurisprudence linked to {provisionLabel} {articleNum} yet.
                    </div>
                )}

                {groupedLinks
                    .filter(group => (!divisionFilter || group.division === divisionFilter) && (!ponenteFilter || group.ponente === ponenteFilter))
                    .map((group) => {
                    const firstLink = group.ratios[0];
                    const year = scLinkedCaseYear(group.date);
                    return (
                        <div
                            key={group.caseId}
                            className={`group relative overflow-hidden rounded-lg border-2 border-slate-300/75 bg-white/90 shadow-sm dark:border-white/5 dark:bg-slate-800/70 ${CHROME_INTERACTIVE_TILE_ELEVATE}`}
                        >
                            <CardVioletInnerWash />
                            <div className="relative z-[1]">
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
                                    {year != null && (
                                        <span className="font-semibold text-slate-600 dark:text-slate-300">{year}</span>
                                    )}
                                    {group.division && (
                                        <>
                                            {year != null && <span>•</span>}
                                            <span className="font-medium text-indigo-600 dark:text-indigo-400 truncate max-w-[110px]">{group.division}</span>
                                        </>
                                    )}
                                    {group.ponente && (
                                        <>
                                            {(year != null || group.division) && <span>•</span>}
                                            <span className="font-medium text-slate-600 dark:text-slate-300 truncate max-w-[120px]">{group.ponente}</span>
                                        </>
                                    )}
                                    {(year != null || group.division || group.ponente) && <span>•</span>}
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
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default LexCodeJurisSidebar;
