import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Book, Calendar, Menu, X, Gavel, ChevronDown, ChevronRight, Info, Search, ArrowUp, ArrowDown, ChevronLeft, Maximize, Minimize, Lock } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import CodalStream from './CodalStream';
import CodexJurisSidebar from './CodexJurisSidebar';
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

const CodexViewer = ({ shortName, onCaseSelect, isFullscreen, onToggleFullscreen, subscriptionTier }) => {
    const { canAccess, openUpgradeModal } = useSubscription();


    // Title mapping (mirrors CodalStream — keep in sync)
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

    // Body-scroll lock — simple overflow:hidden (no reflow, no scrollTo)
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

        return <CodalStream {...commonProps} />;
    };

    return (
        <div className="flex bg-transparent gap-4 lg:gap-6 xl:gap-8 p-0 lg:px-8 lg:pb-8 justify-center items-start">
            {/* 1. Floating TOC Sidebar (Left) */}
            <div className={`
                flex-none z-20 sticky top-28 mt-0 transition-all duration-300 ease-in-out
                ${isSidebarOpen ? 'w-80 opacity-100 translate-x-0' : 'w-0 opacity-0 -translate-x-10 overflow-hidden'}
                hidden lg:block
            `}>
                <div className="w-80 flex flex-col glass bg-white/40 dark:bg-slate-900/40 backdrop-blur-xl shadow-[0_30px_60px_-10px_rgba(0,0,0,0.3)] rounded-xl border border-white/40 dark:border-white/10 overflow-hidden max-h-[calc(100vh-100px)]">
                    <div className="flex-none p-4 pb-0 border-b border-white/20 dark:border-white/5 bg-white/30 dark:bg-slate-800/30">
                        <div className="flex justify-between items-center mb-4">
                            <span className="font-sans font-bold text-gray-800 dark:text-gray-200">Contents</span>
                            <button onClick={() => setIsSidebarOpen(false)} className="p-1 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-500"><X size={20} /></button>
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
                        {activeTab === 'toc' && tocData && (
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

            {/* Mobile/Overlay Sidebar (for smaller screens) */}
            {isSidebarOpen && (
                <div className="lg:hidden fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-start p-4">
                    <div className="w-80 max-h-[80vh] flex flex-col glass bg-white/60 dark:bg-slate-900/60 backdrop-blur-2xl rounded-xl border border-white/40 dark:border-white/10 shadow-2xl overflow-hidden animate-in slide-in-from-left duration-300">
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

            {/* Codal Stream Card */}
            <div className={`flex-1 min-w-0 mt-0 transition-all duration-300 relative z-30 ${isFullscreen ? 'max-w-full' : ((activeJurisArticle || activeAmendmentArticle) ? 'max-w-3xl' : 'max-w-4xl')}`}>
                <div ref={mainContentRef} className={`w-full glass bg-white/40 dark:bg-slate-900/40 backdrop-blur-xl shadow-[0_30px_60px_-10px_rgba(0,0,0,0.3)] rounded-xl border border-white/40 dark:border-white/10 min-h-max mb-20 relative`} id="main-content">

                    {/* ── Sticky Header Bar ── */}
                    <div className="sticky top-0 z-10 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md border-b border-white/20 dark:border-white/5 px-4 py-3 flex items-center gap-3">
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

                        {/* Document Title — centred in remaining space */}
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

                    {/* ── Content Body ── */}
                    <div className="px-2 pt-4">
                        {renderMainContent()}
                    </div>
                </div>
            </div>

            {/* 3. Floating Right Sidebar (Jurisprudence/Amendments) */}
            <div className={`
                flex-none z-30 sticky top-28 mt-0 transition-all duration-300 ease-in-out
                ${(activeJurisArticle || activeAmendmentArticle) ? 'w-80 opacity-100 translate-x-0' : 'w-0 opacity-0 translate-x-10 overflow-hidden'}
                hidden lg:block
            `}>
                <div className="w-80 flex flex-col glass bg-white/40 dark:bg-slate-900/40 backdrop-blur-xl shadow-[0_30px_60px_-10px_rgba(0,0,0,0.3)] rounded-xl border border-white/40 dark:border-white/10 overflow-hidden h-[calc(100vh-100px)]">
                    {activeJurisArticle && (
                        <CodexJurisSidebar
                            articleNum={activeJurisArticle}
                            statuteId={shortName} // Pass current Code ID (e.g. RPC)
                            paragraphFilter={activeJurisParagraph}
                            onClose={() => {
                                setActiveJurisArticle(null);
                                setActiveJurisParagraph(null);
                            }}
                            onSelectRatio={async (caseId, ratioIndex) => {
                                // Fetch the full case data and trigger the App-level modal
                                try {
                                    const res = await fetch(`/api/sc_decisions/${caseId}`);
                                    if (res.ok) {
                                        const caseData = await res.json();
                                        // Add ratioIndex for scroll sync
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
                                    <div key={idx} className="glass bg-white/60 dark:bg-slate-800/40 p-5 rounded-xl shadow-sm border border-white/40 dark:border-white/5 relative overflow-hidden group">
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

            {/* Mobile Overlay for Right Sidebar */}
            {(activeJurisArticle || activeAmendmentArticle) && (
                <div
                    className="lg:hidden fixed inset-0 z-50 bg-black/50 backdrop-blur-md flex items-start justify-end p-4"
                    onClick={(e) => { if (e.target === e.currentTarget) { setActiveJurisArticle(null); setActiveAmendmentArticle(null); } }}
                >
                    <div className="w-80 h-[82vh] flex flex-col glass bg-white/60 dark:bg-slate-900/60 backdrop-blur-2xl rounded-xl border border-white/40 dark:border-white/10 shadow-2xl overflow-hidden animate-in slide-in-from-right duration-300">
                        {activeJurisArticle && (
                            <CodexJurisSidebar
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
