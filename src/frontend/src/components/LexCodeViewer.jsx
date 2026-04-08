import React, { useState, useEffect, useRef, useCallback, useMemo, Suspense } from 'react';
import { createPortal } from 'react-dom';
import { Book, Calendar, Menu, X, Gavel, ChevronDown, ChevronRight, Info, Search, ArrowUp, ArrowDown, ChevronLeft, Maximize, Minimize, Lock } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import LexCodeStream from './LexCodeStream';
import LexCodeJurisSidebar from './LexCodeJurisSidebar';
import { toTitleCase } from '../utils/textUtils';
import { lexCache } from '../utils/cache';
import { useSubscription } from '../context/SubscriptionContext';


// Recursive TOC Node Component
const TocNode = ({ node, expanded, onToggle, onArticleClick }) => {
    const isExpanded = expanded[node.id] === true;
    const hasChildren = node.children.length > 0 || node.articles.length > 0;

    return (
        <div className="mb-1">
            <button
                onClick={() => {
                    if (hasChildren) onToggle(node.id);
                    if (node.targetId) onArticleClick(node.targetId);
                }}
                className={`w-full text-left flex items-center justify-between text-[16px] font-bold text-gray-900 dark:text-gray-100 py-1.5 hover:bg-gray-50 dark:hover:bg-gray-800 rounded px-1 transition-colors group ${!hasChildren ? 'cursor-default opacity-80' : ''}`}
            >
                <span className="truncate mr-1">{toTitleCase(node.label.replace(/TITLE/i, 'Title').replace(/CHAPTER/i, 'Chapter'))}</span>
                {hasChildren && (
                    <span className="text-gray-400 group-hover:text-amber-600 transition-colors">
                        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    </span>
                )}
            </button>

            {isExpanded && (
                <div className="flex flex-col gap-0.5 ml-3 border-l border-gray-100 dark:border-gray-800 pl-2">
                    {node.articles.map(art => (
                        <button
                            key={art.id}
                            onClick={() => onArticleClick(art.id)}
                            className="px-2 py-1.5 text-xs font-sans text-left text-gray-700 dark:text-gray-400 hover:text-amber-800 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded transition-colors truncate w-full"
                            title={art.label}
                        >
                            {art.label}
                        </button>
                    ))}
                    {node.children.map(child => (
                        <TocNode
                            key={child.id}
                            node={child}
                            expanded={expanded}
                            onToggle={onToggle}
                            onArticleClick={onArticleClick}
                        />
                    ))}
                </div>
            )}
        </div>
    );
};

const LexCodeViewer = ({
    shortName,
    onCaseSelect,
    isFullscreen,
    onToggleFullscreen,
    subscriptionTier,
    codalOptions = null,
    selectedCodal = '',
    onCodalChange,
}) => {
    const { canAccess, openUpgradeModal } = useSubscription();


    // Title mapping (mirrors LexCodeStream — keep in sync)
    const codeTitleMap = {
        'RPC': { title: 'The Revised Penal Code', subtitle: 'Act No. 3815, as amended' },
        'CIV': { title: 'The Civil Code of the Philippines', subtitle: 'Republic Act No. 386, as amended' },
        'CONST': { title: '1987 Philippine Constitution', subtitle: null },
        'FC': { title: 'Family Code of the Philippines', subtitle: 'Executive Order No. 209, as amended' },
        'LABOR': { title: 'Labor Code of the Philippines', subtitle: 'Presidential Decree No. 442, as amended' },
        'ROC': { title: 'Rules of Court of the Philippines', subtitle: 'As amended, 2019' },
    };
    const codeKey = (shortName || '').toUpperCase();
    const codeTitle = codeTitleMap[codeKey]?.title || shortName || '';
    const codeSubtitle = codeTitleMap[codeKey]?.subtitle || null;

    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [viewDate, setViewDate] = useState('');
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const [activeTab, setActiveTab] = useState('toc');
    const [tocData, setTocData] = useState({ id: 'root', children: [], articles: [] });
    const [expandedGroups, setExpandedGroups] = useState({});
    const [tocVersion, setTocVersion] = useState(0);
    const [activeInfo, setActiveInfo] = useState(null);
    const [activeJurisArticle, setActiveJurisArticle] = useState(null); // Article Number for Juris Sidebar
    const [activeJurisParagraph, setActiveJurisParagraph] = useState(null); // Paragraph Index Filter
    const [activeAmendmentArticle, setActiveAmendmentArticle] = useState(null); // For Amendment Sidebar


    // Search States
    const [searchTerm, setSearchTerm] = useState('');
    const [searchMode, setSearchMode] = useState(false);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [searchSuggestions, setSearchSuggestions] = useState([]);
    const [currentHighlightIndex, setCurrentHighlightIndex] = useState(0);
    const [totalHighlights, setTotalHighlights] = useState(0);
    const [highlightedArticleId, setHighlightedArticleId] = useState(null);
    const [suggestionLoading, setSuggestionLoading] = useState(false);
    const [suggestionError, setSuggestionError] = useState(null);

    const searchBoxRef = useRef(null);
    const suggestionsRef = useRef(null);
    const mainContentRef = useRef(null);

    // Body-scroll lock on mobile when any LexCode drawer overlay is open (TOC or juris/amendments)
    const isMobileOverlayOpen =
        isSidebarOpen || !!(activeJurisArticle || activeAmendmentArticle);
    useEffect(() => {
        if (!isMobileOverlayOpen || typeof window === 'undefined' || window.innerWidth >= 1024) return;
        document.body.style.overflow = 'hidden';
        return () => {
            document.body.style.overflow = '';
        };
    }, [isMobileOverlayOpen]);

    // Toggle TOC group expansion
    const toggleGroup = (idx) => {
        setExpandedGroups(prev => ({
            ...prev,
            [idx]: !prev[idx]
        }));
    };

    const [targetArticleId, setTargetArticleId] = useState(null);

    const handleAmendmentClick = useCallback((article) => {
        if (activeAmendmentArticle?.article_num === article.article_num) {
            setActiveAmendmentArticle(null);
        } else {
            setActiveAmendmentArticle(article);
            setActiveJurisArticle(null); // Exclusive: close juris sidebar
        }
    }, [activeAmendmentArticle?.article_num, setActiveAmendmentArticle, setActiveJurisArticle]);

    const handleJurisprudenceClick = useCallback((articleNum, paragraphIndex) => {
        // Gate: Amicus+ only
        if (!canAccess('codex_linked_cases')) {
            openUpgradeModal('codex_linked_cases');
            return;
        }
        setActiveJurisArticle(articleNum);
        setActiveJurisParagraph(paragraphIndex);
        setActiveAmendmentArticle(null);
    }, [canAccess, openUpgradeModal, setActiveJurisArticle, setActiveJurisParagraph, setActiveAmendmentArticle]);


    // Close active info when clicking outside
    useEffect(() => {
        const handleClickOutside = () => {
            if (activeInfo) setActiveInfo(null);
        };
        if (activeInfo) {
            document.addEventListener('click', handleClickOutside);
        }
        return () => {
            document.removeEventListener('click', handleClickOutside);
        };
    }, [activeInfo]);

    useEffect(() => {
        const fetchData = async () => {
            if (!shortName) return;
            setLoading(true);
            setError(null);
            try {
                const url = viewDate
                    ? `/api/codex/versions?short_name=${shortName}&date=${viewDate}`
                    : `/api/codex/versions?short_name=${shortName}`;

                // Reset sidebars and search when switching codals
                setActiveJurisArticle(null);
                setActiveJurisParagraph(null);
                setActiveAmendmentArticle(null);
                setSearchMode(false);
                setSearchTerm('');
                
                const fetcher = async () => {
                    const res = await fetch(url);
                    if (!res.ok) throw new Error('Failed to load LexCode');
                    return await res.json();
                };

                const cacheKey = viewDate ? `${shortName}_${viewDate}` : shortName;

                await lexCache.swr('codals', cacheKey, fetcher, (json, isCached) => {
                    setData(json);

                    // Build TOC
                    const root = { id: 'root', label: 'root', rank: -1, children: [], articles: [] };
                    const stack = [root];
                    let nodeIdCounter = 0;

                    const getRank = (text) => {
                        const t = text.toUpperCase();
                        if (t.startsWith('BOOK') || t.startsWith('PART')) return 0;
                        if (t.startsWith('TITLE') || t.startsWith('PRELIMINARY TITLE') || t.startsWith('RULE')) return 1;
                        if (t.startsWith('CHAPTER')) return 2;
                        if (t.startsWith('SECTION')) return 3;
                        return 4;
                    };

                    const createNode = (label, rank, targetId) => ({
                        id: `node-${nodeIdCounter++}`,
                        label: label.replace(/^##\s+/, ''),
                        rank,
                        targetId,
                        children: [],
                        articles: []
                    });

                    json.articles.forEach(art => {
                        // Filter out sub-articles (e.g., "5(b)")
                        if (art.article_number && art.article_number.includes('(')) return;

                        // 1. Process headers inside article first (usually at the top)
                        // This ensures the current article falls under the header it contains.
                        const headers = [...art.content.matchAll(/^##\s+(.+)$/gm)].map(m => m[1].strip ? m[1].strip() : m[1].trim());
                        headers.forEach(headerText => {
                            const rank = getRank(headerText);
                            const newNode = createNode(headerText, rank, art.id || art.article_number || art.key_id);
                            while (stack.length > 0 && stack[stack.length - 1].rank >= rank) {
                                stack.pop();
                            }
                            const parent = stack.length > 0 ? stack[stack.length - 1] : root;
                            parent.children.push(newNode);
                            stack.push(newNode);
                        });

                        // 2. Build Article Label
                        let label = `Article ${art.article_number}`;
                        if (art.article_number === '0' || !art.article_number) label = 'Preamble';

                        // Try to find title in content if not provided by backend
                        if (!art.article_title) {
                            const titleMatch = art.content.match(/^(?:\*\*)?(Article\s+\w+\.?\s+.*?)(?:\*\*|\.\-|:|\n|$)/i);
                            if (titleMatch && titleMatch[1]) {
                                label = titleMatch[1].trim();
                                if (label.length > 65) label = label.substring(0, 65) + '...';
                            }
                        }

                        let cleanNum = art.article_number;
                        let cleanTitle = art.article_title || label;

                        // Robust Sanitization
                        const isConstitution = shortName && shortName.toUpperCase() === 'CONST';
                        const isROC = shortName && shortName.toUpperCase() === 'ROC';
                        const hasRomanOrWord = /[IVXLCDM]/i.test(cleanNum) || /ARTICLE/i.test(cleanNum) || /RULE/i.test(cleanNum);

                        // Priority 1: If the label already has a structural word at the start, use it as is
                        const hasWordPrefix = /^(Article|Section|Title|Chapter|Preamble|Book|Rule|Part)/i.test(cleanTitle);

                        let tocLabel = cleanTitle;

                        if (!hasWordPrefix && cleanNum && cleanNum !== '0') {
                            if (isConstitution) {
                                // If it's something like "XIII", just use "ARTICLE XIII"
                                if (isNaN(parseInt(cleanNum)) || hasRomanOrWord) {
                                    tocLabel = `${cleanNum}: ${cleanTitle}`;
                                    if (!tocLabel.toUpperCase().startsWith('ARTICLE')) {
                                        tocLabel = `Article ${tocLabel}`;
                                    }
                                } else {
                                    tocLabel = `Section ${cleanNum}: ${cleanTitle}`;
                                }
                            } else if (isROC) {
                                 // For ROC, article_num is often "Rule 1, Section 1"
                                 // Just use it as is, or strip Rule part if we want just section
                                 tocLabel = `${cleanNum}: ${cleanTitle}`;
                            } else {
                                tocLabel = `Article ${cleanNum}: ${cleanTitle}`;
                            }
                        } else if (!hasWordPrefix && (cleanNum === '0' || !cleanNum)) {
                            tocLabel = 'Preamble';
                        }

                        // Final cleanup: remove redundant "Section Article" or "Rule Article"
                        tocLabel = tocLabel.replace(/^(Section|Article|Rule)\s+(Section|Article|Rule)/i, '$1');

                        // 3. Push to current stack top
                        stack[stack.length - 1].articles.push({
                            id: art.id || art.article_number,
                            label: tocLabel
                        });
                    });

                    setTocData(root);

                    const expandAll = (node) => {
                        const expanded = { [node.id]: true };
                        node.children.forEach(child => Object.assign(expanded, expandAll(child)));
                        return expanded;
                    };
                    const allExpanded = {};
                    root.children.forEach(child => Object.assign(allExpanded, expandAll(child)));
                    setExpandedGroups(allExpanded);
                    setTocVersion(prev => prev + 1);
                    setLoading(false);
                });

            } catch (err) {
                console.error("Fetch error:", err);
                setError(err.message);
                setLoading(false);
            }
        };
        fetchData();
    }, [shortName, viewDate]);



    const scrollToArticle = (articleNumber) => {
        // Auto-close sidebar on smaller screens
        if (window.innerWidth < 1400) setIsSidebarOpen(false);

        // Tell LexCodeStream to ensure this article is loaded
        setTargetArticleId(articleNumber);

        // Give React enough time to render
        setTimeout(() => {
            const element = document.getElementById(`article-${articleNumber}`);
            if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }, 300);
    };

    const handlePreviousArticle = () => { };
    const handleNextArticle = () => { };
    if (loading) return <div className="p-8 text-center text-gray-500 animate-pulse">Loading LexCode...</div>;
    if (error) return <div className="p-8 text-center text-red-500">Error: {error}</div>;
    if (!data) return null;

    const renderMainContent = () => {
        if (!data) return null;

        const commonProps = {
            code: shortName,
            hideDocHeader: true,
            onJurisprudenceClick: handleJurisprudenceClick,
            onAmendmentClick: handleAmendmentClick,
            targetArticleId
        };

        return <LexCodeStream {...commonProps} />;
    };

    return (
        <div className="min-h-screen lg:min-h-0">
            <div className="mx-auto max-w-full px-0 sm:px-4 lg:px-6">
                {/*
                  Desktop (lg+): fixed-height row + overflow-y ONLY on center column.
                  Sticky sidebars failed because the page scrolls as a whole; isolating scroll keeps TOC/juris fixed in the row.
                */}
                <div
                    className={`
                        flex flex-col gap-4 bg-transparent p-0 lg:flex-row lg:items-stretch lg:justify-center
                        lg:gap-6 xl:gap-8 lg:overflow-hidden lg:pb-2 lg:min-h-0
                        ${
                            isFullscreen
                                ? 'lg:h-[calc(100dvh-env(safe-area-inset-top,0px)-env(safe-area-inset-bottom,0px)-var(--player-height,0px))] lg:max-h-[calc(100dvh-env(safe-area-inset-top,0px)-env(safe-area-inset-bottom,0px)-var(--player-height,0px))]'
                                : 'lg:h-[calc(100dvh-10.5rem-env(safe-area-inset-top,0px)-env(safe-area-inset-bottom,0px)-var(--player-height,0px))] lg:max-h-[calc(100dvh-10.5rem-env(safe-area-inset-top,0px)-env(safe-area-inset-bottom,0px)-var(--player-height,0px))]'
                        }
                    `}
                >
                    {/* 1. TOC — column height matches row; list scrolls inside (no page scroll) */}
                    <div
                        className={`
                        hidden lg:flex lg:h-full lg:min-h-0 lg:flex-none lg:flex-col lg:overflow-hidden lg:self-stretch
                        z-[45] mt-0 transition-all duration-300 ease-in-out
                        ${isSidebarOpen ? 'w-80 opacity-100 translate-x-0' : 'w-0 opacity-0 -translate-x-10 overflow-hidden'}
                    `}
                    >
                        <div className="flex h-full min-h-0 w-full flex-col">
                            <div className="flex h-full min-h-0 w-80 flex-col glass overflow-hidden rounded-xl border-2 border-slate-300/80 bg-white/40 shadow-[0_30px_60px_-10px_rgba(0,0,0,0.3)] backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/40">
                                <div className="flex-none border-b border-white/20 bg-white/30 p-4 pb-0 dark:border-white/5 dark:bg-slate-800/30">
                                    <div className="mb-4 flex items-center justify-between">
                                        <span className="font-sans font-bold text-gray-800 dark:text-gray-200">Contents</span>
                                        <button onClick={() => setIsSidebarOpen(false)} className="rounded-md p-1 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-700">
                                            <X size={20} />
                                        </button>
                                    </div>
                                </div>

                                <div className="custom-scrollbar min-h-0 flex-1 overflow-y-auto p-4">
                                    <div key={tocVersion} className="space-y-1">
                                        {tocData.articles.map((art) => (
                                            <button
                                                key={art.id}
                                                onClick={() => scrollToArticle(art.id)}
                                                className="w-full truncate rounded px-2 py-1.5 text-left font-sans text-xs text-gray-700 hover:bg-amber-50 hover:text-amber-800 dark:text-gray-400 dark:hover:bg-amber-900/20 dark:hover:text-amber-400"
                                            >
                                                {art.label}
                                            </button>
                                        ))}
                                        {tocData.children.map((node) => (
                                            <TocNode key={node.id} node={node} expanded={expandedGroups} onToggle={toggleGroup} onArticleClick={scrollToArticle} />
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* 2. Main codal — ONLY this column scrolls on desktop */}
                    <div
                        className={`relative z-30 mt-0 flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden transition-all duration-300 lg:min-h-0 ${isFullscreen ? 'max-w-full' : activeJurisArticle || activeAmendmentArticle ? 'max-w-3xl' : 'max-w-4xl'}`}
                    >
                        <div
                            ref={mainContentRef}
                            id="main-content"
                            className={`flex min-h-0 flex-1 flex-col mb-4 w-full overflow-hidden rounded-[2.5rem] border-2 border-slate-300/80 bg-white/95 glass shadow-[0_40px_100px_-20px_rgba(0,0,0,0.15)] backdrop-blur-3xl dark:border-white/10 dark:bg-slate-950/40 dark:shadow-[0_40px_100px_-20px_rgba(0,0,0,0.6)] sm:mb-8 lg:mb-4 lg:overflow-y-auto lg:overscroll-y-contain ${isFullscreen ? 'min-h-0 flex-1' : ''}`}
                        >
                            {/* Not sticky: whole codal card (this bar + articles) scrolls together in #main-content */}
                            <div className="shrink-0 border-b border-white/25 bg-white/70 backdrop-blur-md dark:border-white/10 dark:bg-slate-900/70">
                                {Array.isArray(codalOptions) && codalOptions.length > 0 && typeof onCodalChange === 'function' && (
                                    <div className="border-b border-white/20 px-4 py-3 dark:border-white/10">
                                        <div className="min-w-0 max-w-md">
                                            <label htmlFor="lexcode-codal-filter-inline" className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                                                Codal
                                            </label>
                                            <select
                                                id="lexcode-codal-filter-inline"
                                                value={selectedCodal}
                                                onChange={(e) => {
                                                    const v = e.target.value;
                                                    if (!v) return;
                                                    onCodalChange(v);
                                                }}
                                                className="block w-full rounded-lg border border-stone-400 bg-white/90 py-2 pl-3 pr-8 text-sm shadow-sm focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-500 dark:border-gray-600 dark:bg-gray-900 dark:text-white"
                                            >
                                                {codalOptions.map((opt) => (
                                                    <option key={opt.id} value={opt.id} disabled={opt.disabled}>
                                                        {opt.label}
                                                        {opt.disabled ? ' (Soon)' : ''}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>
                                    </div>
                                )}

                                <div className="flex items-center gap-3 px-4 py-3">
                                    {!isSidebarOpen && (
                                        <button
                                            type="button"
                                            onClick={() => {
                                                if (typeof window !== 'undefined' && window.innerWidth < 1024) {
                                                    setActiveJurisArticle(null);
                                                    setActiveJurisParagraph(null);
                                                    setActiveAmendmentArticle(null);
                                                }
                                                setIsSidebarOpen(true);
                                            }}
                                            className="shrink-0 rounded-lg border border-gray-100 bg-gray-50 p-2 text-amber-700 shadow-sm transition-colors hover:bg-amber-50 dark:border-gray-700 dark:bg-gray-800 dark:text-amber-500 dark:hover:bg-amber-900/30"
                                            title="Table of Contents"
                                        >
                                            <Menu size={20} />
                                        </button>
                                    )}

                                    <div className="min-w-0 flex-1 px-2 text-center">
                                        <h1 className="font-sans text-[16px] font-extrabold leading-tight tracking-wide text-gray-900 dark:text-gray-100">
                                            {toTitleCase(codeTitle)}
                                        </h1>
                                        {codeSubtitle && (
                                            <p className="text-[11px] font-semibold text-amber-700 dark:text-amber-400">
                                                {toTitleCase(codeSubtitle)}
                                            </p>
                                        )}
                                    </div>

                                    {onToggleFullscreen && (
                                        <button
                                            type="button"
                                            onClick={onToggleFullscreen}
                                            className="shrink-0 rounded-lg border border-gray-100 bg-gray-50 p-2 text-amber-700 shadow-sm transition-colors hover:bg-amber-50 dark:border-gray-700 dark:bg-gray-800 dark:text-amber-500 dark:hover:bg-amber-900/30"
                                            title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen Mode'}
                                        >
                                            {isFullscreen ? <Minimize size={20} /> : <Maximize size={20} />}
                                        </button>
                                    )}
                                </div>
                            </div>

                            <div className="p-4 sm:p-8 lg:p-12">
                                <Suspense fallback={<div className="p-12 text-center animate-pulse">Loading Codal Stream...</div>}>
                                    {renderMainContent()}
                                </Suspense>
                            </div>
                        </div>
                    </div>

                    {/* 3. Juris / amendments — same as TOC: fills row height, scrolls inside */}
                    <div
                        className={`
                        hidden lg:flex lg:h-full lg:min-h-0 lg:flex-none lg:flex-col lg:overflow-hidden lg:self-stretch
                        z-[45] mt-0 transition-all duration-300 ease-in-out
                        ${(activeJurisArticle || activeAmendmentArticle) ? 'w-80 opacity-100 translate-x-0' : 'w-0 opacity-0 translate-x-10 overflow-hidden'}
                    `}
                    >
                        <div className="flex h-full min-h-0 w-full flex-col">
                        <div className="flex h-full min-h-0 w-80 flex-col glass overflow-hidden rounded-xl border-2 border-slate-300/80 bg-white/40 shadow-[0_30px_60px_-10px_rgba(0,0,0,0.3)] backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/40">
                            {activeJurisArticle && (
                                <LexCodeJurisSidebar
                                    articleNum={activeJurisArticle}
                                    statuteId={shortName}
                                    paragraphFilter={activeJurisParagraph}
                                    onClose={() => {
                                        setActiveJurisArticle(null);
                                        setActiveJurisParagraph(null);
                                    }}
                                    onSelectRatio={async (caseId, ratioIndex) => {
                                        try {
                                            const res = await fetch(`/api/sc_decisions/${caseId}`);
                                            if (res.ok) {
                                                const caseData = await res.json();
                                                caseData.scrollToRatioIndex = ratioIndex;
                                                onCaseSelect && onCaseSelect(caseData);
                                            }
                                        } catch (err) {
                                            console.error('Failed to fetch case:', err);
                                        }
                                    }}
                                />
                            )}

                            {activeAmendmentArticle && !activeJurisArticle && (
                                <div className="h-full flex flex-col bg-transparent">
                                    <div className="flex-none p-4 border-b border-white/20 dark:border-white/5 flex justify-between items-center bg-white/30 dark:bg-slate-800/30 backdrop-blur-sm">
                                        <div>
                                            <h3 className="font-bold text-lg text-rose-700 dark:text-rose-400 font-serif">
                                                Amendments
                                            </h3>
                                            <div className="text-xs text-stone-500 uppercase tracking-wider font-bold">
                                                Article {activeAmendmentArticle.article_num}
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => setActiveAmendmentArticle(null)}
                                            className="p-1.5 rounded-full hover:bg-stone-200 dark:hover:bg-gray-700 text-stone-400 transition-colors"
                                        >
                                            <X size={18} />
                                        </button>
                                    </div>

                                    <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
                                        {(activeAmendmentArticle.amendment_links || []).map((am, idx) => (
                                            <div key={idx} className="glass bg-white/60 dark:bg-slate-800/40 p-5 rounded-xl shadow-sm border-2 border-slate-300/75 dark:border-white/5 relative overflow-hidden group">
                                                <div className="absolute top-0 left-0 w-1 h-full bg-rose-500/80"></div>
                                                <div className="flex justify-between items-start mb-2 pl-2">
                                                    <h4 className="font-bold text-gray-900 dark:text-gray-100 text-sm leading-tight pr-2">
                                                        {am.amendment_law}
                                                    </h4>
                                                    <span className="text-[10px] items-center px-1.5 py-0.5 rounded bg-rose-50 dark:bg-rose-900/20 text-rose-600 dark:text-rose-400 font-medium whitespace-nowrap border border-rose-100 dark:border-rose-900/30">
                                                        {am.amendment_type}
                                                    </span>
                                                </div>
                                                <div className="pl-2 mb-3">
                                                    <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1.5">
                                                        <Calendar size={12} />
                                                        <span>Effectivity: {am.valid_from || 'N/A'}</span>
                                                    </div>
                                                </div>
                                                <div className="pl-2 text-sm text-gray-700 dark:text-gray-300 leading-relaxed font-sans">
                                                    {am.description}
                                                </div>
                                                {am.source_url && (
                                                    <div className="pl-2 mt-3 pt-3 border-t border-stone-100 dark:border-gray-700/50">
                                                        <a
                                                            href={am.source_url}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="text-xs font-semibold text-rose-600 dark:text-rose-400 hover:text-rose-700 hover:underline flex items-center gap-1 group-hover:translate-x-1 transition-transform"
                                                        >
                                                            View Official Text <ChevronRight size={12} />
                                                        </a>
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Mobile / tablet (<lg): portaled above Layout header — main is z-10 so in-DOM fixed overlays stay under header z-50 and the close control is untappable */}
            {typeof document !== 'undefined' &&
                (activeJurisArticle || activeAmendmentArticle || isSidebarOpen) &&
                createPortal(
                    <div
                        className="lg:hidden fixed inset-0 z-[540] lex-modal-overlay bg-black/60 backdrop-blur-md animate-in fade-in duration-200"
                        role="presentation"
                        onClick={(e) => {
                            if (e.target === e.currentTarget) {
                                setActiveJurisArticle(null);
                                setActiveJurisParagraph(null);
                                setActiveAmendmentArticle(null);
                                setIsSidebarOpen(false);
                            }
                        }}
                    >
                        <div className="lex-modal-card glass relative flex max-w-2xl flex-col overflow-hidden rounded-2xl border-2 border-slate-300/85 bg-white/92 shadow-2xl animate-in zoom-in-95 duration-300 dark:border-white/10 dark:bg-slate-900/45 mx-auto">
                            {activeJurisArticle && (
                                <LexCodeJurisSidebar
                                    articleNum={activeJurisArticle}
                                    statuteId={shortName}
                                    paragraphFilter={activeJurisParagraph}
                                    onClose={() => {
                                        setActiveJurisArticle(null);
                                        setActiveJurisParagraph(null);
                                    }}
                                    onSelectRatio={async (caseId, ratioIndex) => {
                                        try {
                                            const res = await fetch(`/api/sc_decisions/${caseId}`);
                                            if (res.ok) {
                                                const caseData = await res.json();
                                                caseData.scrollToRatioIndex = ratioIndex;
                                                onCaseSelect && onCaseSelect(caseData);
                                            }
                                        } catch (err) {
                                            console.error('Failed to fetch case:', err);
                                        }
                                    }}
                                />
                            )}
                            {activeAmendmentArticle && !activeJurisArticle && (
                                <div className="flex h-full min-h-0 flex-col overflow-y-auto p-4 font-sans">
                                    <div className="mb-4 flex items-center justify-between">
                                        <h3 className="font-bold text-lg text-rose-700">Amendments</h3>
                                        <button type="button" onClick={() => setActiveAmendmentArticle(null)} aria-label="Close">
                                            <X size={18} />
                                        </button>
                                    </div>
                                    <div className="text-sm">Article {activeAmendmentArticle.article_num}</div>
                                </div>
                            )}
                            {isSidebarOpen && !activeJurisArticle && !activeAmendmentArticle && (
                                <div className="flex h-full min-h-0 w-full flex-col font-sans">
                                    <div className="flex-none border-b border-white/20 bg-white/30 p-4 pb-4 dark:border-white/5 dark:bg-slate-800/30">
                                        <div className="flex items-center justify-between">
                                            <span className="font-bold text-gray-800 dark:text-gray-200 text-lg">Table of Contents</span>
                                            <button onClick={() => setIsSidebarOpen(false)} className="rounded-md p-1.5 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors">
                                                <X size={20} />
                                            </button>
                                        </div>
                                    </div>

                                    <div className="custom-scrollbar min-h-0 flex-1 overflow-y-auto p-4 md:p-6">
                                        <div key={tocVersion} className="space-y-1">
                                            {tocData.articles.map((art) => (
                                                <button
                                                    key={art.id}
                                                    onClick={() => scrollToArticle(art.id)}
                                                    className="w-full truncate rounded px-2 py-2 text-left font-sans text-sm font-medium text-gray-700 hover:bg-amber-50 hover:text-amber-800 dark:text-gray-300 dark:hover:bg-amber-900/20 dark:hover:text-amber-400"
                                                >
                                                    {art.label}
                                                </button>
                                            ))}
                                            {tocData.children.map((node) => (
                                                <TocNode key={node.id} node={node} expanded={expandedGroups} onToggle={toggleGroup} onArticleClick={scrollToArticle} />
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>,
                    document.body
                )}
        </div>
    );
};

export default LexCodeViewer;
