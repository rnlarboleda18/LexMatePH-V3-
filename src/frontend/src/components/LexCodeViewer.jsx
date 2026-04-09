import React, { useState, useEffect, useLayoutEffect, useRef, useCallback, useMemo } from 'react';
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

const CodexViewer = ({ shortName, onCaseSelect, isFullscreen, onToggleFullscreen, subscriptionTier, codalOptions = [], selectedCodal, onCodalChange }) => {
    const { canAccess, openUpgradeModal } = useSubscription();


    // Title mapping (mirrors CodalStream ΓÇö keep in sync)
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
    /** Spacers measure horizontal position for fixed side panels (sticky breaks with body overflow-x + transforms). */
    const tocSpacerRef = useRef(null);
    const jurisSpacerRef = useRef(null);
    const [tocFixedLeft, setTocFixedLeft] = useState(null);
    const [jurisFixedLeft, setJurisFixedLeft] = useState(null);

    const syncFixedPanelPositions = useCallback(() => {
        if (typeof window === 'undefined' || window.innerWidth < 1024) {
            setTocFixedLeft(null);
            setJurisFixedLeft(null);
            return;
        }
        const tocEl = tocSpacerRef.current;
        const jurEl = jurisSpacerRef.current;
        if (tocEl && isSidebarOpen) {
            setTocFixedLeft(tocEl.getBoundingClientRect().left);
        } else {
            setTocFixedLeft(null);
        }
        if (jurEl && (activeJurisArticle || activeAmendmentArticle)) {
            setJurisFixedLeft(jurEl.getBoundingClientRect().left);
        } else {
            setJurisFixedLeft(null);
        }
    }, [isSidebarOpen, activeJurisArticle, activeAmendmentArticle]);

    useLayoutEffect(() => {
        syncFixedPanelPositions();
        const ro = new ResizeObserver(() => syncFixedPanelPositions());
        if (tocSpacerRef.current) ro.observe(tocSpacerRef.current);
        if (jurisSpacerRef.current) ro.observe(jurisSpacerRef.current);
        window.addEventListener('resize', syncFixedPanelPositions);
        return () => {
            window.removeEventListener('resize', syncFixedPanelPositions);
            ro.disconnect();
        };
    }, [syncFixedPanelPositions]);

    /** Re-measure after fullscreen toggles (main padding / width change). */
    useLayoutEffect(() => {
        syncFixedPanelPositions();
    }, [isFullscreen, syncFixedPanelPositions]);

    const fixedPanelStyle = useMemo(
        () => ({
            top: isFullscreen
                ? 'calc(env(safe-area-inset-top, 0px) + 4.25rem)'
                : 'calc(5rem + env(safe-area-inset-top, 0px) + 4.25rem)',
            maxHeight: isFullscreen
                ? 'calc(100dvh - var(--player-height, 0px) - 5.5rem - env(safe-area-inset-top, 0px) - env(safe-area-inset-bottom, 0px))'
                : 'calc(100dvh - var(--player-height, 0px) - 10.25rem - env(safe-area-inset-top, 0px) - env(safe-area-inset-bottom, 0px))',
        }),
        [isFullscreen]
    );

    // Body-scroll lock ΓÇö simple overflow:hidden (no reflow, no scrollTo)
    // Only lock on mobile screens (<1024px) where the sidebar renders as a full-screen overlay
    const isSidebarActive = !!(activeJurisArticle || activeAmendmentArticle);
    useEffect(() => {
        if (!isSidebarActive || window.innerWidth >= 1024) return;
        document.body.style.overflow = 'hidden';
        return () => { document.body.style.overflow = ''; };
    }, [isSidebarActive]);

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
                    if (!res.ok) throw new Error('Failed to load Codex');
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
        // Auto-close sidebar on smaller screens (up to iPad Pro 12.9 Landscape ~1366px)
        if (window.innerWidth < 1400) setIsSidebarOpen(false);

        // Tell CodalStream to ensure this article is loaded
        setTargetArticleId(articleNumber);

        // Give React enough time to expand the visibleCount and render the new DOM chunk
        setTimeout(() => {
            const element = document.getElementById(`article-${articleNumber}`);
            if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else {
                console.warn(`[Scroll] Target element 'article-${articleNumber}' not found in DOM.`);
            }
        }, 300);
    };

    // Dummy search handlers (simplified for reconstruction)
    const handleSearchSubmit = (e) => { e.preventDefault(); };
    const handleSearchInputChange = (e) => setSearchTerm(e.target.value);
    const handleClearSearch = () => setSearchTerm('');
    const handleKeyDown = () => { };
    const handleSuggestionClick = () => { };
    const handlePreviousHighlight = () => { };
    const handleNextHighlight = () => { };
    const clearAllSearchStates = () => { };
    const handlePreviousArticle = () => { };
    const handleNextArticle = () => { };
    const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);

    // Derived Data
    const bookTitle = data?.metadata?.full_name || '';
    const chapterTitle = '';
    const sectionTitle = '';
    const isFirstArticle = false;
    const isLastArticle = false;

    if (loading) return <div className="p-8 text-center text-gray-500 animate-pulse">Loading Codex...</div>;
    if (error) return <div className="p-8 text-center text-red-500">Error: {error}</div>;
    if (!data) return null;

    // Renderers
    const renderers = {
        h1: ({ node, children, ...props }) => <h1 className="text-center font-extrabold text-amber-900 dark:text-gray-100 mt-10 mb-8 text-[16px] tracking-wide" {...props}>{toTitleCase(String(children))}</h1>,
        h2: ({ node, children, ...props }) => <h2 className="text-center font-bold text-amber-800 dark:text-gray-200 mt-10 mb-6 text-[16px] tracking-wide border-b-2 border-amber-200 dark:border-gray-700 pb-3" {...props}>{toTitleCase(String(children))}</h2>,
        h3: ({ node, children, ...props }) => {
            let text = '';
            const extractText = (c) => {
                if (typeof c === 'string') return c;
                if (Array.isArray(c)) return c.map(extractText).join('');
                if (c?.props?.children) return extractText(c.props.children);
                return '';
            };
            text = extractText(children);
            const match = text.match(/^((?:Article|Art\.?)\s+\d+[.:]?)\s*(.*)$/s);
            if (match) {
                const prefix = match[1];
                let suffix = match[2];
                let titlePart = null;
                const titleMatch = suffix.match(/^(.+?\.\s*-)(.*)/s);
                if (titleMatch && titleMatch[1].length < 150) {
                    titlePart = titleMatch[1].trim();
                    suffix = titleMatch[2] || '';
                }
                return (
                    <div className="mt-8 mb-4 leading-relaxed text-gray-900 dark:text-white text-justify" {...props}>
                        <span className="text-amber-700 dark:text-gray-200 font-extrabold text-[16px] mr-2">{prefix}</span>
                        {titlePart && <span className="text-amber-700 dark:text-gray-200 font-extrabold text-[16px] mr-2">{titlePart}</span>}
                        <span className="text-[16px]">{suffix}</span>
                    </div>
                );
            }
            return <h3 className="text-left font-bold text-gray-900 dark:text-white mt-8 mb-4 text-[16px]" {...props}>{children}</h3>;
        },
        h4: ({ node, children, ...props }) => <h4 className="text-left font-semibold text-gray-800 dark:text-gray-200 mt-6 mb-3 text-[16px]" {...props}>{toTitleCase(String(children))}</h4>,
        p: ({ node, children, ...props }) => {
            // Simplified P renderer logic for rescue
            return <p className="mb-4 leading-relaxed text-lg text-gray-900 dark:text-white text-justify" style={{ maxWidth: 'none' }} {...props}>{children}</p>;
        },
        ul: ({ node, ...props }) => <ul className="list-disc pl-8 space-y-2 my-3" {...props} />,
        ol: ({ node, ...props }) => <ol className="list-decimal pl-8 space-y-2 my-3" {...props} />,
        li: ({ node, ...props }) => <li className="pl-2 text-gray-900 dark:text-white" {...props} />,
        blockquote: ({ node, ...props }) => <blockquote className="border-l-4 border-amber-500 pl-4 italic my-4 text-gray-600 dark:text-gray-400 bg-amber-50/50 dark:bg-gray-800/50 py-2 rounded-r" {...props} />,
        strong: ({ node, children, ...props }) => <span className="font-normal text-gray-900 dark:text-white" {...props}>{children}</span>,
        em: ({ node, ...props }) => <em className="italic text-gray-700 dark:text-gray-300" {...props} />
    };

    const renderMainContent = () => {
        if (!data) return null;
        if (searchMode) return renderSearchResults();

        const commonProps = {
            code: shortName,
            hideDocHeader: true,   // title is now shown in the sticky header bar
            onJurisprudenceClick: handleJurisprudenceClick,
            onAmendmentClick: handleAmendmentClick,
            targetArticleId
        };

        return <LexCodeStream {...commonProps} />;
    };

    /** Fixed panels (portals): `position:fixed` avoids sticky breaking from `html,body{overflow-x:hidden}` and other ancestors. */
    const desktopTocPortal =
        typeof document !== 'undefined' &&
        tocFixedLeft != null &&
        isSidebarOpen &&
        createPortal(
            <div
                className="fixed z-[28] flex w-80 max-w-[min(20rem,calc(100vw-1.5rem))] min-h-0 flex-col overflow-hidden rounded-xl border border-white/40 bg-white/40 shadow-[0_30px_60px_-10px_rgba(0,0,0,0.3)] backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/40"
                style={{ left: tocFixedLeft, top: fixedPanelStyle.top, maxHeight: fixedPanelStyle.maxHeight }}
            >
                <div className="flex-none border-b border-white/20 bg-white/30 p-4 pb-0 dark:border-white/5 dark:bg-slate-800/30">
                    <div className="mb-4 flex items-center justify-between">
                        <span className="font-sans font-bold text-gray-800 dark:text-gray-200">Contents</span>
                        <button type="button" onClick={() => setIsSidebarOpen(false)} className="rounded-md p-1 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-700">
                            <X size={20} />
                        </button>
                    </div>
                </div>
                <div className="custom-scrollbar min-h-0 flex-1 overflow-y-auto p-4">
                    {activeTab === 'toc' && tocData && (
                        <div key={tocVersion} className="space-y-1">
                            {tocData.articles.map((art) => (
                                <button
                                    key={art.id}
                                    type="button"
                                    onClick={() => scrollToArticle(art.id)}
                                    className="w-full truncate rounded px-2 py-1.5 text-left text-xs font-sans text-gray-700 transition-colors hover:bg-amber-50 hover:text-amber-800 dark:text-gray-400 dark:hover:bg-amber-900/20 dark:hover:text-amber-400"
                                >
                                    {art.label}
                                </button>
                            ))}
                            {tocData.children.map((node) => (
                                <TocNode key={node.id} node={node} expanded={expandedGroups} onToggle={toggleGroup} onArticleClick={scrollToArticle} />
                            ))}
                        </div>
                    )}
                </div>
            </div>,
            document.body
        );

    const desktopJurisPortal =
        typeof document !== 'undefined' &&
        jurisFixedLeft != null &&
        (activeJurisArticle || activeAmendmentArticle) &&
        createPortal(
            <div
                className="fixed z-[28] flex w-80 max-w-[min(20rem,calc(100vw-1.5rem))] min-h-0 flex-col overflow-hidden rounded-xl border border-white/40 bg-white/40 shadow-[0_30px_60px_-10px_rgba(0,0,0,0.3)] backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/40"
                style={{ left: jurisFixedLeft, top: fixedPanelStyle.top, maxHeight: fixedPanelStyle.maxHeight }}
            >
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
                    <div className="flex min-h-0 flex-1 flex-col bg-transparent">
                        <div className="flex flex-none items-center justify-between border-b border-white/20 bg-white/30 p-4 backdrop-blur-sm dark:border-white/5 dark:bg-slate-800/30">
                            <div>
                                <h3 className="font-serif text-lg font-bold text-rose-700 dark:text-rose-400">Amendments</h3>
                                <div className="text-xs font-bold uppercase tracking-wider text-stone-500">Article {activeAmendmentArticle.article_num}</div>
                            </div>
                            <button type="button" onClick={() => setActiveAmendmentArticle(null)} className="rounded-full p-1.5 text-stone-400 hover:bg-stone-200 dark:hover:bg-gray-700">
                                <X size={18} />
                            </button>
                        </div>
                        <div className="custom-scrollbar flex-1 space-y-4 overflow-y-auto p-4">
                            {(activeAmendmentArticle.amendment_links || []).map((am, idx) => (
                                <div
                                    key={idx}
                                    className="group relative overflow-hidden rounded-xl border border-white/40 bg-white/60 p-5 shadow-sm dark:border-white/5 dark:bg-slate-800/40 glass"
                                >
                                    <div className="absolute left-0 top-0 h-full w-1 bg-rose-500/80" />
                                    <div className="mb-2 flex items-start justify-between pl-2">
                                        <h4 className="pr-2 text-sm font-bold leading-tight text-gray-900 dark:text-gray-100">{am.amendment_law}</h4>
                                        <span className="whitespace-nowrap rounded border border-rose-100 px-1.5 py-0.5 text-[10px] font-medium text-rose-600 dark:border-rose-900/30 dark:bg-rose-900/20 dark:text-rose-400">
                                            {am.amendment_type}
                                        </span>
                                    </div>
                                    <div className="mb-3 pl-2">
                                        <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
                                            <Calendar size={12} />
                                            <span>Effectivity: {am.valid_from || 'N/A'}</span>
                                        </div>
                                    </div>
                                    <div className="pl-2 font-sans text-sm leading-relaxed text-gray-700 dark:text-gray-300">{am.description}</div>
                                    {am.source_url && (
                                        <div className="mt-3 border-t border-stone-100 pt-3 pl-2 dark:border-gray-700/50">
                                            <a
                                                href={am.source_url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="flex items-center gap-1 text-xs font-semibold text-rose-600 transition-transform hover:text-rose-700 hover:underline dark:text-rose-400"
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
            </div>,
            document.body
        );

    return (
        <div className="flex w-full max-w-full flex-col items-stretch justify-center gap-4 bg-transparent p-0 pb-8 lg:flex-row lg:items-start lg:gap-6 lg:px-8 xl:gap-8">
            {/* TOC layout spacer — real panel is `position:fixed` via portal */}
            <div
                ref={tocSpacerRef}
                className={`hidden shrink-0 transition-[width,opacity] duration-300 ease-in-out lg:block ${isSidebarOpen ? 'w-80' : 'pointer-events-none w-0 overflow-hidden opacity-0'}`}
                aria-hidden
            />

            {/* Mobile/Overlay Sidebar (for smaller screens) */}
            {isSidebarOpen && (
                <div className="lg:hidden fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-start p-4" onClick={(e) => { if (e.target === e.currentTarget) setIsSidebarOpen(false); }}>
                    <div className="w-80 max-h-[80vh] flex flex-col glass bg-white dark:bg-slate-900 rounded-xl border border-white/40 dark:border-white/10 shadow-2xl overflow-hidden animate-in slide-in-from-left duration-300">
                        <div className="p-4 border-b border-white/20 dark:border-white/5 flex justify-between items-center bg-white/30 dark:bg-slate-800/30">
                            <span className="font-bold">Contents</span>
                            <button onClick={() => setIsSidebarOpen(false)}><X size={20} /></button>
                        </div>
                        <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
                            {tocData && (
                                <div key={tocVersion} className="space-y-1">
                                    {tocData.articles.map(art => (
                                        <button key={art.id} onClick={() => scrollToArticle(art.id)} className="px-2 py-1.5 text-xs font-sans text-left text-gray-700 dark:text-gray-400 hover:text-amber-800 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded transition-colors truncate w-full">{art.label}</button>
                                    ))}
                                    {tocData.children.map(node => <TocNode key={node.id} node={node} expanded={expandedGroups} onToggle={toggleGroup} onArticleClick={scrollToArticle} />)}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Codal stream — grows with content; scrolls with the main page */}
            <div className={`relative z-30 mt-0 min-w-0 flex-1 transition-all duration-300 ${isFullscreen ? 'max-w-full' : (activeJurisArticle || activeAmendmentArticle) ? 'max-w-3xl' : 'max-w-4xl'}`}>
                {/* Outer shell keeps shadow; inner clips body text to rounded corners */}
                <div className="rounded-2xl shadow-[0_30px_60px_-10px_rgba(0,0,0,0.3)] dark:shadow-[0_30px_60px_-10px_rgba(0,0,0,0.45)]">
                    <div
                        ref={mainContentRef}
                        id="main-content"
                        className="relative flex min-w-0 w-full flex-col overflow-hidden rounded-2xl border border-white/40 bg-white/40 backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/40 glass"
                    >

                    {/* Toolbar (scrolls with article text) */}
                    <div className="flex flex-col rounded-t-2xl border-b border-white/20 bg-white/60 backdrop-blur-md dark:border-white/5 dark:bg-slate-900/60">
                        
                        {/* Row 1: Codal Filter Dropdown */}
                        {codalOptions && codalOptions.length > 0 && onCodalChange && (
                            <div className="px-4 py-2.5 border-b border-white/20 dark:border-white/5 bg-white/30 dark:bg-slate-800/30">
                                <select
                                    value={selectedCodal || shortName?.toLowerCase()}
                                    onChange={(e) => onCodalChange(e.target.value)}
                                    className="w-full text-sm font-semibold rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-slate-800 text-gray-800 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-amber-500 transition-colors cursor-pointer"
                                    title="Switch Codal"
                                >
                                    {codalOptions.filter(o => !o.disabled).map(o => (
                                        <option key={o.id} value={o.id}>{o.label}</option>
                                    ))}
                                </select>
                            </div>
                        )}

                        {/* Row 2: Title and Controls */}
                        <div className="px-4 py-3 flex items-center gap-3">
                            {/* TOC / Menu Button */}
                            {!isSidebarOpen && (
                                <button
                                    onClick={() => setIsSidebarOpen(true)}
                                    className="shrink-0 p-2 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-amber-50 dark:hover:bg-amber-900/30 text-amber-700 dark:text-amber-500 transition-colors shadow-sm border border-gray-100 dark:border-gray-700"
                                    title="Table of Contents"
                                >
                                    <Menu size={20} />
                                </button>
                            )}

                            {/* Document Title ΓÇö centred in remaining space */}
                            <div className="flex-1 text-center min-w-0 px-2">
                                <h1 className="text-[16px] font-extrabold text-gray-900 dark:text-gray-100 tracking-wide font-sans leading-tight">
                                    {toTitleCase(codeTitle)}
                                </h1>
                                {codeSubtitle && (
                                    <p className="text-[11px] font-semibold text-amber-700 dark:text-amber-400">
                                        {toTitleCase(codeSubtitle)}
                                    </p>
                                )}
                            </div>

                            {/* Fullscreen Toggle */}
                            {onToggleFullscreen && (
                                <button
                                    onClick={onToggleFullscreen}
                                    className="shrink-0 p-2 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-amber-50 dark:hover:bg-amber-900/30 text-amber-700 dark:text-amber-500 transition-colors shadow-sm border border-gray-100 dark:border-gray-700"
                                    title={isFullscreen ? "Exit Fullscreen" : "Fullscreen Mode"}
                                >
                                    {isFullscreen ? <Minimize size={20} /> : <Maximize size={20} />}
                                </button>
                            )}
                        </div>
                    </div>

                    <div className="custom-scrollbar min-w-0 max-w-full rounded-b-2xl px-2 pt-4 pb-24 [overflow-wrap:anywhere] [word-break:break-word]">
                        {renderMainContent()}
                    </div>
                    </div>
                </div>
            </div>

            {/* Juris / amendments layout spacer — real panel is `position:fixed` via portal */}
            <div
                ref={jurisSpacerRef}
                className={`hidden shrink-0 transition-[width,opacity] duration-300 ease-in-out lg:block ${activeJurisArticle || activeAmendmentArticle ? 'w-80' : 'pointer-events-none w-0 overflow-hidden opacity-0'}`}
                aria-hidden
            />

            {desktopTocPortal}
            {desktopJurisPortal}

            {/* Mobile Overlay for Right Sidebar */}
            {(activeJurisArticle || activeAmendmentArticle) && (
                <div
                    className="lg:hidden fixed inset-0 z-50 bg-black/50 backdrop-blur-md flex items-start justify-end p-4"
                    onClick={(e) => { if (e.target === e.currentTarget) { setActiveJurisArticle(null); setActiveAmendmentArticle(null); } }}
                >
                    <div className="w-80 h-[82vh] flex flex-col glass bg-white dark:bg-slate-900 rounded-xl border border-white/40 dark:border-white/10 shadow-2xl overflow-hidden animate-in slide-in-from-right duration-300">
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
                            <div className="h-full flex flex-col p-4 overflow-y-auto font-sans">
                                <div className="flex justify-between items-center mb-4">
                                    <h3 className="font-bold text-lg text-rose-700">Amendments</h3>
                                    <button onClick={() => setActiveAmendmentArticle(null)}><X size={18} /></button>
                                </div>
                                <div className="text-sm">Article {activeAmendmentArticle.article_num}</div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default CodexViewer;
