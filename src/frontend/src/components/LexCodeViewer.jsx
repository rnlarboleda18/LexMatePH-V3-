import React, { useState, useEffect, useLayoutEffect, useRef, useCallback, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { Book, Calendar, ListTree, X, Gavel, ChevronDown, ChevronRight, Info, Search, ChevronLeft, Lock } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import LexCodeStream from './LexCodeStream';
import LexCodeJurisSidebar from './LexCodeJurisSidebar';
import { toTitleCase } from '../utils/textUtils';
import { lexCache } from '../utils/cache';
import {
    CODAL_LEXCACHE_REVISION,
    repairRccBrokenIncorporatorPipeHeaders,
    stripLegacyCodexArticleRunIn,
} from '../utils/codalMarkdown';
import { useSubscription } from '../context/SubscriptionContext';
import Fuse from 'fuse.js';
import { useDebounce } from '../hooks/useDebounce';
import { HighlightText } from '../utils/highlight';
import PurpleGlassAmbient from './PurpleGlassAmbient';
import CardVioletInnerWash from './CardVioletInnerWash';
import {
    FILTER_CHROME_SURFACE,
    FILTER_SELECT,
    FILTER_SEARCH_INPUT,
    FILTER_SEARCH_ICON_CLASS,
} from '../utils/filterChromeClasses';
import { apiUrl, normalizeScDecisionsRouteId } from '../utils/apiUrl';
import { closeModalAbsorbingGhostTap } from '../utils/modalClose';


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
                    <span className="text-gray-400 transition-colors group-hover:text-violet-600 dark:group-hover:text-zinc-300">
                        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    </span>
                )}
            </button>

            {isExpanded && (
                <div className="flex flex-col gap-0.5 ml-3 border-l border-lex pl-2">
                    {node.articles.map(art => (
                        <button
                            key={art.id}
                            onClick={() => onArticleClick(art.id)}
                            className="w-full truncate rounded px-2 py-1.5 text-left font-sans text-xs text-gray-700 transition-colors hover:bg-violet-50 hover:text-violet-800 dark:text-gray-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100"
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

const CodexViewer = ({ shortName, onCaseSelect, onCaseDetailMerge, subscriptionTier, codalOptions = [], selectedCodal, onCodalChange }) => {
    const { canAccess, openUpgradeModal } = useSubscription();

    // Title mapping (mirrors CodalStream — keep in sync)
    const codeTitleMap = {
        'RPC': { title: 'The Revised Penal Code', subtitle: 'Act No. 3815, as amended' },
        'CIV': { title: 'The Civil Code of the Philippines', subtitle: 'Republic Act No. 386, as amended' },
        'CONST': { title: '1987 Philippine Constitution', subtitle: null },
        'FC': { title: 'Family Code of the Philippines', subtitle: 'Executive Order No. 209, as amended' },
        'LABOR': { title: 'Labor Code of the Philippines', subtitle: 'Presidential Decree No. 442, as amended' },
        'ROC': { title: 'Rules of Court of the Philippines', subtitle: 'As amended, 2019' },
        'RCC': { title: 'Revised Corporation Code of the Philippines', subtitle: 'Republic Act No. 11232' },
    };
    const codeKey = (shortName || '').toUpperCase();
    const codeTitle = codeTitleMap[codeKey]?.title || shortName || '';
    const codeSubtitle = codeTitleMap[codeKey]?.subtitle || null;
    /** RA 11232 uses Sections in the statute; DB column remains article_num. */
    const codalProvisionLabel = codeKey === 'RCC' ? 'Section' : 'Article';
    const isROC = codeKey === 'ROC';

    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [viewDate, setViewDate] = useState('');
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    /** max-width 1023px: TOC uses modal + FAB; lg+ uses side panel + FAB. */
    const [isMobileViewport, setIsMobileViewport] = useState(() =>
        typeof window !== 'undefined' && window.matchMedia('(max-width: 1023px)').matches
    );
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
    const [searchSuggestions, setSearchSuggestions] = useState([]);
    const [showSuggestions, setShowSuggestions] = useState(false);
    /** Measured rect of the search input — used to position the portaled dropdown
     *  outside the overflow-hidden codal shell so it isn't clipped. */
    const [searchBoxRect, setSearchBoxRect] = useState(null);
    const closeSuggestionsTimerRef = useRef(null);
    const searchBoxRef = useRef(null);
    /** Codal picker + search row — in-flow below xl; fixed at xl+; height drives content `padding-top` when fixed. */
    const lexFilterChromeRef = useRef(null);
    const [lexFilterChromeHeight, setLexFilterChromeHeight] = useState(52);
    /** Match Tailwind `xl:` (1280px). */
    const [xlFixedChrome, setXlFixedChrome] = useState(() =>
        typeof window !== 'undefined' && window.matchMedia('(min-width: 1280px)').matches,
    );
    useEffect(() => {
        const mq = window.matchMedia('(min-width: 1280px)');
        const on = () => setXlFixedChrome(mq.matches);
        on();
        mq.addEventListener('change', on);
        return () => mq.removeEventListener('change', on);
    }, []);
    useEffect(() => {
        const mq = window.matchMedia('(max-width: 1023px)');
        const on = () => setIsMobileViewport(mq.matches);
        on();
        mq.addEventListener('change', on);
        return () => mq.removeEventListener('change', on);
    }, []);
    const mainContentRef = useRef(null);
    /** Rounded codal shell root (layout); portaled TOC/juris `top` follows header + sticky filter chrome, not this rect. */
    const codalShellRef = useRef(null);
    /** Spacers measure horizontal position for fixed side panels (sticky breaks with body overflow-x + transforms). */
    const tocSpacerRef = useRef(null);
    const jurisSpacerRef = useRef(null);
    const [tocFixedLeft, setTocFixedLeft] = useState(null);
    const [jurisFixedLeft, setJurisFixedLeft] = useState(null);
    /** Measured viewport `top` (px) for portaled side panels; null = fall back to fixedPanelStyle. */
    const [fixedPanelTopPx, setFixedPanelTopPx] = useState(null);

    const openJurisCaseDetail = useCallback(
        async (caseId, ratioIndex) => {
            const idSeg = normalizeScDecisionsRouteId(caseId);
            if (!idSeg) {
                console.error('LexCode juris: invalid case id', caseId);
                return;
            }
            try {
                const res = await fetch(apiUrl(`/api/sc_decisions/${idSeg}?digest_only=true`));
                const caseData = await res.json().catch(() => ({}));
                if (!res.ok || !caseData || caseData.error) {
                    console.error('LexCode juris: case detail failed', res.status, caseData);
                    return;
                }
                caseData.scrollToRatioIndex = ratioIndex;
                onCaseSelect && onCaseSelect(caseData);
                if (onCaseDetailMerge) {
                    void (async () => {
                        try {
                            const r2 = await fetch(apiUrl(`/api/sc_decisions/${idSeg}`));
                            const full = await r2.json().catch(() => ({}));
                            if (!r2.ok || !full || full.error) return;
                            const { digest_only: _d, ...rest } = full;
                            onCaseDetailMerge(idSeg, { ...rest, scrollToRatioIndex: ratioIndex });
                        } catch (err) {
                            console.error('LexCode juris: full case fetch failed', err);
                        }
                    })();
                }
            } catch (err) {
                console.error('Failed to fetch case:', err);
            }
        },
        [onCaseSelect, onCaseDetailMerge],
    );

    const syncFixedPanelPositions = useCallback(() => {
        if (typeof window === 'undefined' || window.innerWidth < 1024) {
            setTocFixedLeft(null);
            setJurisFixedLeft(null);
            setFixedPanelTopPx(null);
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

        // Match TOC FAB: pin vertical position to viewport below header + sticky LexCode
        // chrome — do not tie to codal shell top (that moves on scroll and drags the panel).
        const wantPanels = isSidebarOpen || !!(activeJurisArticle || activeAmendmentArticle);
        if (wantPanels) {
            const gh = typeof document !== 'undefined' ? document.querySelector('header') : null;
            const headerBottom = gh ? gh.getBoundingClientRect().bottom : (window.innerWidth >= 768 ? 64 : 48);
            const filterEl = lexFilterChromeRef.current;
            const chromeBottom = filterEl ? filterEl.getBoundingClientRect().bottom : headerBottom;
            setFixedPanelTopPx(Math.max(headerBottom, chromeBottom));
        } else {
            setFixedPanelTopPx(null);
        }
    }, [isSidebarOpen, activeJurisArticle, activeAmendmentArticle]);

    useLayoutEffect(() => {
        const el = lexFilterChromeRef.current;
        if (!el || typeof ResizeObserver === 'undefined') {
            return undefined;
        }
        const measure = () => {
            setLexFilterChromeHeight(Math.ceil(el.getBoundingClientRect().height));
        };
        measure();
        const ro = new ResizeObserver(measure);
        ro.observe(el);
        return () => ro.disconnect();
    }, []);

    // Push the global scroll container's top past the fixed filter chrome so its
    // scrollbar track starts below the chrome, not behind it. Reset on unmount.
    useEffect(() => {
        const h = xlFixedChrome ? `${lexFilterChromeHeight}px` : '0px';
        document.documentElement.style.setProperty('--page-chrome-height', h);
        return () => document.documentElement.style.setProperty('--page-chrome-height', '0px');
    }, [xlFixedChrome, lexFilterChromeHeight]);

    useLayoutEffect(() => {
        syncFixedPanelPositions();
        let rafId = 0;
        const scheduleSync = () => {
            if (rafId) return;
            rafId = requestAnimationFrame(() => {
                rafId = 0;
                syncFixedPanelPositions();
            });
        };
        const ro = new ResizeObserver(() => syncFixedPanelPositions());
        if (tocSpacerRef.current) ro.observe(tocSpacerRef.current);
        if (jurisSpacerRef.current) ro.observe(jurisSpacerRef.current);
        if (lexFilterChromeRef.current) ro.observe(lexFilterChromeRef.current);
        window.addEventListener('resize', syncFixedPanelPositions);
        window.addEventListener('scroll', scheduleSync, true);
        return () => {
            window.removeEventListener('resize', syncFixedPanelPositions);
            window.removeEventListener('scroll', scheduleSync, true);
            ro.disconnect();
            if (rafId) cancelAnimationFrame(rafId);
        };
    }, [syncFixedPanelPositions, data, loading, error, lexFilterChromeHeight]);

    /** In-flow anchor for TOC FAB; actual control is `position:fixed` via portal (sticky breaks under page overflow-x / transforms). */
    const tocFabAnchorRef = useRef(null);
    const [tocFabPos, setTocFabPos] = useState(null);

    const syncTocFabPosition = useCallback(() => {
        if (typeof window === 'undefined') return;
        if (isSidebarOpen) {
            setTocFabPos(null);
            return;
        }
        const w = window.innerWidth;
        const narrow = w < 1024;
        let left;
        if (narrow) {
            const shell = codalShellRef.current;
            if (!shell) {
                setTocFabPos(null);
                return;
            }
            left = shell.getBoundingClientRect().left;
        } else {
            const el = tocFabAnchorRef.current;
            if (!el) {
                setTocFabPos(null);
                return;
            }
            left = el.getBoundingClientRect().left;
        }
        const gh = typeof document !== 'undefined' ? document.querySelector('header') : null;
        const headerBottom = gh ? gh.getBoundingClientRect().bottom : (w >= 768 ? 64 : 48);
        const filterEl = lexFilterChromeRef.current;
        const chromeBottom = filterEl ? filterEl.getBoundingClientRect().bottom : headerBottom;
        setTocFabPos({
            left,
            top: Math.max(headerBottom, chromeBottom),
        });
    }, [isSidebarOpen]);

    useLayoutEffect(() => {
        if (loading || error || !data) return undefined;
        syncTocFabPosition();
        let rafId = 0;
        const onScrollOrResize = () => {
            if (rafId) return;
            rafId = requestAnimationFrame(() => {
                rafId = 0;
                syncTocFabPosition();
            });
        };
        const ro = new ResizeObserver(() => syncTocFabPosition());
        const anchor = tocFabAnchorRef.current;
        if (anchor) {
            ro.observe(anchor);
            if (anchor.parentElement) ro.observe(anchor.parentElement);
        }
        // Spacers use width transitions (lg); anchor size stays 48×48 so RO on anchor misses sibling-driven shifts.
        if (tocSpacerRef.current) ro.observe(tocSpacerRef.current);
        if (jurisSpacerRef.current) ro.observe(jurisSpacerRef.current);
        if (codalShellRef.current) ro.observe(codalShellRef.current);
        window.addEventListener('scroll', onScrollOrResize, true);
        window.addEventListener('resize', syncTocFabPosition);
        return () => {
            window.removeEventListener('scroll', onScrollOrResize, true);
            window.removeEventListener('resize', syncTocFabPosition);
            ro.disconnect();
            if (rafId) cancelAnimationFrame(rafId);
        };
    }, [loading, error, data, isSidebarOpen, isMobileViewport, syncTocFabPosition, lexFilterChromeHeight]);

    /** After TOC/juris spacer width finishes transitioning, remeasure FAB (avoids stale coords on first layout frame). */
    useLayoutEffect(() => {
        if (loading || error || !data || isSidebarOpen) return undefined;
        let alive = true;
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                if (alive) syncTocFabPosition();
            });
        });
        const t = window.setTimeout(() => {
            if (alive) syncTocFabPosition();
        }, 340);
        return () => {
            alive = false;
            window.clearTimeout(t);
        };
    }, [isSidebarOpen, activeJurisArticle, activeAmendmentArticle, loading, error, data, syncTocFabPosition]);

    const fixedPanelStyle = useMemo(
        () => ({
            top: 'calc(var(--app-header-offset) + 4.25rem)',
            maxHeight:
                'calc(100dvh - var(--player-height, 0px) - var(--app-header-offset) - 5.25rem - env(safe-area-inset-bottom, 0px))',
        }),
        []
    );

    const fixedSidePanelStyle = useMemo(() => {
        if (fixedPanelTopPx != null) {
            return {
                top: `calc(${fixedPanelTopPx}px + var(--lex-tile-gap))`,
                maxHeight: `calc(100dvh - ${fixedPanelTopPx}px - var(--lex-tile-gap) - var(--player-height, 0px) - env(safe-area-inset-bottom, 0px) - 12px)`,
            };
        }
        return { top: fixedPanelStyle.top, maxHeight: fixedPanelStyle.maxHeight };
    }, [fixedPanelTopPx, fixedPanelStyle.top, fixedPanelStyle.maxHeight]);

    // Body-scroll lock on small viewports when TOC modal or juris/amendment overlay is open
    const isSidebarActive = !!(activeJurisArticle || activeAmendmentArticle);
    useEffect(() => {
        const apply = () => {
            if (typeof window === 'undefined') return;
            if (window.innerWidth >= 1024) {
                document.body.style.overflow = '';
                return;
            }
            if (isSidebarOpen || isSidebarActive) {
                document.body.style.overflow = 'hidden';
            } else {
                document.body.style.overflow = '';
            }
        };
        apply();
        window.addEventListener('resize', apply);
        return () => {
            window.removeEventListener('resize', apply);
            document.body.style.overflow = '';
        };
    }, [isSidebarOpen, isSidebarActive]);

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
        // Gate: Juris+ only
        if (!canAccess('codex_linked_cases')) {
            openUpgradeModal('codex_linked_cases');
            return;
        }
        setActiveJurisArticle(articleNum);
        setActiveJurisParagraph(paragraphIndex);
        setActiveAmendmentArticle(null);
    }, [canAccess, openUpgradeModal, setActiveJurisArticle, setActiveJurisParagraph, setActiveAmendmentArticle]);

    /** Mobile juris/amendments sheet — same stack/ghost-tap pattern as CaseDecisionModal (portaled). */
    const clearMobileLexPanels = useCallback(() => {
        setActiveJurisArticle(null);
        setActiveJurisParagraph(null);
        setActiveAmendmentArticle(null);
    }, []);

    const handleCloseMobileLexPanels = useCallback(() => {
        closeModalAbsorbingGhostTap(clearMobileLexPanels);
    }, [clearMobileLexPanels]);

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
            if (!shortName) {
                setLoading(false);
                setData(null);
                setError(null);
                setTocData({ id: 'root', label: 'root', rank: -1, children: [], articles: [] });
                return;
            }
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
                setSearchTerm('');
                
                const fetcher = async () => {
                    const res = await fetch(url);
                    if (!res.ok) {
                        let msg = `Codex HTTP ${res.status}`;
                        try {
                            const err = await res.json();
                            if (err && typeof err.detail === 'string' && err.detail) msg = err.detail;
                            else if (err && typeof err.error === 'string' && err.error) msg = err.error;
                        } catch {
                            /* ignore */
                        }
                        throw new Error(msg);
                    }
                    const json = await res.json();
                    const articles = (json.articles || []).map((a) => {
                        const num = a.article_num ?? a.article_number ?? a.key_id;
                        const raw = a.content_md || a.content || '';
                        let clean = stripLegacyCodexArticleRunIn(raw, num);
                        if ((shortName || '').toUpperCase() === 'RCC') {
                            clean = repairRccBrokenIncorporatorPipeHeaders(clean);
                        }
                        return { ...a, content: clean, content_md: clean };
                    });
                    return { ...json, articles };
                };

                const cacheKey = (viewDate ? `${shortName}_${viewDate}` : shortName) + CODAL_LEXCACHE_REVISION;

                await lexCache.swr('codals', cacheKey, fetcher, (json, isCached) => {
                    setData(json);
                    setLoading(false); // show content immediately — TOC builds in background

                    // Defer the TOC build so the browser can paint the article list first
                    const scheduleToc = typeof requestIdleCallback === 'function'
                        ? (cb) => requestIdleCallback(cb, { timeout: 500 })
                        : (cb) => setTimeout(cb, 0);

                    scheduleToc(() => {
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
                        if (isROC) return 1;
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

                        const artBody = art.content || art.content_md || '';

                        if (isROC) {
                            // ── ROC-specific TOC builder ──────────────────────────────────────
                            const partLabel = art.book_label || (art.book ? `Part ${art.book}` : null);
                            const ruleNum   = art.title_num;
                            const ruleLabel = art.title_label;

                            if (partLabel) {
                                const currentPart = stack.length > 1 ? stack[1] : null;
                                if (!currentPart || currentPart.label !== partLabel) {
                                    while (stack.length > 1) stack.pop();
                                    const partNode = createNode(partLabel, 0, art.id || art.article_number);
                                    root.children.push(partNode);
                                    stack.push(partNode);
                                }
                            }

                            if (ruleLabel) {
                                const ruleText = ruleNum ? `Rule ${ruleNum} – ${ruleLabel}` : ruleLabel;
                                const currentRule = stack.find(n => n.rank === 1);
                                if (!currentRule || currentRule.label !== ruleText) {
                                    while (stack.length > 2) stack.pop();
                                    const ruleNode = createNode(ruleText, 1, art.id || art.article_number);
                                    const ruleParent = stack[stack.length - 1];
                                    ruleParent.children.push(ruleNode);
                                    stack.push(ruleNode);
                                }
                            }

                            const secNum   = art.section_num ? `Sec. ${art.section_num}` : (art.article_number || '');
                            const secTitle = art.article_title || '';
                            const secLabel = secTitle ? `${secNum}: ${secTitle}` : secNum;

                            stack[stack.length - 1].articles.push({
                                id: art.id || art.article_number,
                                label: secLabel,
                            });

                        } else {
                            // ── Generic TOC builder for all other codals ────────────────────
                            const headers = [...artBody.matchAll(/^##\s+(.+)$/gm)].map(m => m[1].trim());
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

                            let label = `${codalProvisionLabel} ${art.article_number}`;
                            if (art.article_number === '0' || !art.article_number) label = 'Preamble';

                            if (!art.article_title) {
                                const titleMatch = artBody.match(
                                    /^(?:\*\*)?((?:Article|Section)\s+\w+\.?\s+.*?)(?:\*\*|\.\-|:|\n|$)/i
                                );
                                if (titleMatch && titleMatch[1]) {
                                    label = titleMatch[1].trim();
                                    if (label.length > 65) label = label.substring(0, 65) + '...';
                                }
                            }

                            let cleanNum = art.article_number;
                            let cleanTitle = art.article_title || label;

                            const isConstitution = shortName && shortName.toUpperCase() === 'CONST';
                            const hasRomanOrWord = /[IVXLCDM]/i.test(cleanNum) || /ARTICLE/i.test(cleanNum) || /RULE/i.test(cleanNum);
                            const hasWordPrefix = /^(Article|Section|Title|Chapter|Preamble|Book|Rule|Part)/i.test(cleanTitle);

                            let tocLabel = cleanTitle;

                            if (!hasWordPrefix && cleanNum && cleanNum !== '0') {
                                if (isConstitution) {
                                    if (isNaN(parseInt(cleanNum)) || hasRomanOrWord) {
                                        tocLabel = `${cleanNum}: ${cleanTitle}`;
                                        if (!tocLabel.toUpperCase().startsWith('ARTICLE')) tocLabel = `Article ${tocLabel}`;
                                    } else {
                                        tocLabel = `Section ${cleanNum}: ${cleanTitle}`;
                                    }
                                } else {
                                    tocLabel = `${codalProvisionLabel} ${cleanNum}: ${cleanTitle}`;
                                }
                            } else if (!hasWordPrefix && (cleanNum === '0' || !cleanNum)) {
                                tocLabel = 'Preamble';
                            }

                            tocLabel = tocLabel.replace(/^(Section|Article|Rule)\s+(Section|Article|Rule)/i, '$1');

                            stack[stack.length - 1].articles.push({
                                id: art.id || art.article_number,
                                label: tocLabel
                            });
                        }
                    });

                    setTocData(root);

                    // Expand only the top-level nodes (Parts/Books) by default — not full tree
                    const topExpanded = {};
                    root.children.forEach(child => { topExpanded[child.id] = true; });
                    setExpandedGroups(topExpanded);
                    setTocVersion(prev => prev + 1);
                    }); // end scheduleToc
                }); // end swr callback

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

    // --- Search ---
    // Debounce the typed term so we don't recompute on every keystroke.
    const debouncedSearchTerm = useDebounce(searchTerm, 250);

    // Build a Fuse index whenever the codal data changes.
    // Keys are weighted: article_title and article_number surface first;
    // content is included so body text matches (e.g. typing "parricide" or
    // "paricide" still finds Article 246 of the RPC).
    const fuseRef = useRef(null);
    useEffect(() => {
        if (!data?.articles) { fuseRef.current = null; return; }
        // Defer Fuse index build to idle time — it's CPU-heavy and not needed for initial render
        const schedule = typeof requestIdleCallback === 'function'
            ? (cb) => requestIdleCallback(cb, { timeout: 2000 })
            : (cb) => setTimeout(cb, 200);
        schedule(() => {
            const articles = data.articles.filter(
                (art) => !art.article_number?.includes('(')
            );
            fuseRef.current = new Fuse(articles, {
                keys: [
                    { name: 'article_title',  weight: 0.5 },
                    { name: 'article_number', weight: 0.3 },
                    { name: 'content',        weight: 0.2 },
                ],
                threshold: 0.4,
                distance: 200,
                minMatchCharLength: 2,
                includeScore: false,
            });
        });
    }, [data]);

    // Run fuzzy search on the debounced term.
    useEffect(() => {
        if (!debouncedSearchTerm.trim()) {
            setSearchSuggestions([]);
            return;
        }
        if (!fuseRef.current) return;

        const results = fuseRef.current
            .search(debouncedSearchTerm)
            .map((r) => r.item)
            .slice(0, 50);

        setSearchSuggestions(results);
    }, [debouncedSearchTerm]);

    const handleSearchSubmit = (e) => { e?.preventDefault?.(); };

    const handleSearchInputChange = (e) => setSearchTerm(e.target.value);

    const handleClearSearch = () => {
        setSearchTerm('');
        setSearchSuggestions([]);
        setShowSuggestions(false);
        setSearchBoxRect(null);
    };

    // Keep the dropdown anchored correctly when the page scrolls while it's open.
    useEffect(() => {
        if (!showSuggestions) return;
        const update = () => {
            if (searchBoxRef.current) {
                setSearchBoxRect(searchBoxRef.current.getBoundingClientRect());
            }
        };
        window.addEventListener('scroll', update, true);
        window.addEventListener('resize', update);
        return () => {
            window.removeEventListener('scroll', update, true);
            window.removeEventListener('resize', update);
        };
    }, [showSuggestions]);

    const handleKeyDown = (e) => {
        if (e.key === 'Escape') {
            handleClearSearch();
            searchBoxRef.current?.blur();
        }
    };

    // Clicking a suggestion navigates to the article and closes the dropdown.
    const handleSuggestionClick = (articleId) => {
        setSearchTerm('');
        setSearchSuggestions([]);
        setShowSuggestions(false);
        scrollToArticle(articleId);
    };

    const clearAllSearchStates = handleClearSearch;
    const handlePreviousArticle = () => {};
    const handleNextArticle = () => {};
    const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);

    // Derived Data
    const bookTitle = data?.metadata?.full_name || '';
    const chapterTitle = '';
    const sectionTitle = '';
    const isFirstArticle = false;
    const isLastArticle = false;

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
        if (!shortName) {
            return (
                <div className="flex min-h-[40vh] flex-col items-center justify-center px-4 py-12 text-center text-gray-500 dark:text-gray-400">
                    <p className="max-w-md text-sm font-medium leading-relaxed">
                        Choose a codal from the menu above to open the Lex Code viewer.
                    </p>
                </div>
            );
        }
        if (loading) {
            return (
                <div
                    className="flex min-h-[40vh] flex-col items-center justify-center gap-3 p-8 text-gray-500 dark:text-gray-400"
                    role="status"
                    aria-live="polite"
                    aria-busy="true"
                    aria-label="Loading codal"
                >
                    <div
                        className="h-10 w-10 shrink-0 animate-spin rounded-full border-2 border-amber-500/30 border-t-amber-600 dark:border-amber-400/20 dark:border-t-amber-400"
                        aria-hidden
                    />
                    <p className="hidden text-sm font-medium lg:block">Loading Codex…</p>
                </div>
            );
        }
        if (error) {
            return <div className="p-8 text-center text-red-500">Error: {error}</div>;
        }
        if (!data) {
            return (
                <div className="p-8 text-center text-sm text-gray-500 dark:text-gray-400">
                    No codal data loaded.
                </div>
            );
        }

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
                className="fixed z-[28] flex w-80 max-w-[min(20rem,calc(100vw-1.5rem))] min-h-0 flex-col overflow-hidden rounded-xl border border-lex bg-white shadow-lg dark:border-lex dark:bg-zinc-900"
                style={{ left: tocFixedLeft, ...fixedSidePanelStyle }}
            >
                <CardVioletInnerWash />
                <div className="relative z-[1] flex min-h-0 flex-1 flex-col">
                <div className="flex-none border-b border-lex bg-slate-50 p-4 pb-0 dark:border-lex dark:bg-zinc-800/80">
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
                                    className="w-full truncate rounded px-2 py-1.5 text-left font-sans text-xs text-gray-700 transition-colors hover:bg-violet-50 hover:text-violet-800 dark:text-gray-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100"
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
                className="fixed z-[28] flex w-80 max-w-[min(20rem,calc(100vw-1.5rem))] min-h-0 flex-col overflow-hidden rounded-xl border border-lex bg-white shadow-lg dark:border-lex dark:bg-zinc-900"
                style={{ left: jurisFixedLeft, ...fixedSidePanelStyle }}
            >
                <CardVioletInnerWash />
                <div className="relative z-[1] flex min-h-0 min-w-0 flex-1 flex-col">
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
                            await openJurisCaseDetail(caseId, ratioIndex);
                        }}
                    />
                )}
                {activeAmendmentArticle && !activeJurisArticle && (
                    <div className="flex min-h-0 flex-1 flex-col bg-transparent">
                        <div className="flex flex-none items-center justify-between border-b border-lex bg-slate-50 p-4 dark:border-lex dark:bg-zinc-800/80">
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
                                    className="group relative overflow-hidden rounded-xl border border-lex bg-white p-5 shadow-sm dark:border-lex dark:bg-zinc-800"
                                >
                                    <CardVioletInnerWash />
                                    <div className="absolute left-0 top-0 z-[2] h-full w-1 bg-rose-500/80" />
                                    <div className="relative z-[1]">
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
                                </div>
                            ))}
                        </div>
                    </div>
                )}
                </div>
            </div>,
            document.body
        );

    const mobileTocModalPortal =
        typeof document !== 'undefined' &&
        isMobileViewport &&
        isSidebarOpen &&
        createPortal(
            <div
                className="lex-modal-overlay fixed inset-0 z-[540] animate-in bg-black/60 fade-in duration-200 backdrop-blur-sm lg:hidden"
                onClick={(e) => {
                    if (e.target === e.currentTarget) setIsSidebarOpen(false);
                }}
            >
                <div
                    className="lex-modal-card relative flex min-h-0 w-full min-w-0 max-w-5xl flex-col overflow-hidden rounded-2xl border border-lex bg-white shadow-2xl animate-in zoom-in-95 duration-300 dark:border-lex dark:bg-zinc-900"
                    role="dialog"
                    aria-modal="true"
                    aria-label="Table of contents"
                    onClick={(e) => e.stopPropagation()}
                >
                    <CardVioletInnerWash />
                    <div className="relative z-[1] flex min-h-0 w-full min-w-0 max-w-full flex-1 flex-col [max-height:min(90dvh,calc(100dvh-var(--app-header-offset)-var(--player-height,0px)-1.5rem))]">
                        <div className="flex shrink-0 items-center justify-between border-b border-lex bg-slate-50 p-4 dark:border-lex dark:bg-zinc-800/80">
                            <span className="font-sans font-bold text-gray-800 dark:text-gray-200">Contents</span>
                            <button
                                type="button"
                                onClick={() => setIsSidebarOpen(false)}
                                className="rounded-md p-1 text-gray-500 transition-colors hover:bg-gray-200 dark:hover:bg-gray-700"
                                aria-label="Close contents"
                            >
                                <X size={20} />
                            </button>
                        </div>
                        <div className="lex-modal-scroll custom-scrollbar min-h-0 flex-1 overflow-y-auto p-4">
                            {tocData && (
                                <div key={tocVersion} className="space-y-1">
                                    {tocData.articles.map((art) => (
                                        <button
                                            key={art.id}
                                            type="button"
                                            onClick={() => scrollToArticle(art.id)}
                                            className="w-full truncate rounded px-2 py-1.5 text-left font-sans text-xs text-gray-700 transition-colors hover:bg-violet-50 hover:text-violet-800 dark:text-gray-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100"
                                        >
                                            {art.label}
                                        </button>
                                    ))}
                                    {tocData.children.map((node) => (
                                        <TocNode
                                            key={node.id}
                                            node={node}
                                            expanded={expandedGroups}
                                            onToggle={toggleGroup}
                                            onArticleClick={scrollToArticle}
                                        />
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>,
            document.body
        );

    return (
        <>
        <PurpleGlassAmbient showAmbient className="min-h-screen w-full min-w-0 pb-1 font-sans text-gray-900 dark:text-gray-100">
            {/* Codal picker + search — scrolls with page below xl; fixed at xl+ */}
            <div
                ref={lexFilterChromeRef}
                className={`z-[30] ${FILTER_CHROME_SURFACE} ${
                    xlFixedChrome
                        ? 'fixed left-0 right-0 xl:left-52'
                        : 'relative'
                }`}
                style={xlFixedChrome ? { top: 'calc(var(--app-header-offset) + var(--tab-bar-height, 0px))' } : undefined}
            >
                <div className="w-full min-w-0 max-w-7xl px-3 py-2 sm:px-5 lg:px-6">
                    <div className="flex w-full min-w-0 max-w-full flex-col gap-2 sm:flex-row sm:flex-nowrap sm:items-center sm:gap-2">
                        {codalOptions && codalOptions.length > 0 && onCodalChange && (
                            <div className="flex min-w-0 shrink-0 flex-col sm:w-[min(100%,14rem)] md:w-44">
                                <label htmlFor="lexcode-codal-select" className="sr-only">
                                    Choose codal
                                </label>
                                <select
                                    id="lexcode-codal-select"
                                    value={selectedCodal != null && selectedCodal !== '' ? selectedCodal : ''}
                                    onChange={(e) => onCodalChange(e.target.value)}
                                    title="Switch Codal"
                                    className={FILTER_SELECT}
                                >
                                    <option value="">Choose Codal</option>
                                    {codalOptions.filter(o => !o.disabled).map(o => (
                                        <option key={o.id} value={o.id}>{o.label}</option>
                                    ))}
                                </select>
                            </div>
                        )}
                        <form
                            onSubmit={handleSearchSubmit}
                            className="relative min-w-0 w-full flex-1 basis-0 sm:w-auto"
                        >
                            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-2">
                                <Search className={FILTER_SEARCH_ICON_CLASS} strokeWidth={2} aria-hidden />
                            </div>
                            <input
                                ref={searchBoxRef}
                                type="search"
                                value={searchTerm}
                                onChange={(e) => { setSearchTerm(e.target.value); setShowSuggestions(true); }}
                                onFocus={() => {
                                    clearTimeout(closeSuggestionsTimerRef.current);
                                    if (searchBoxRef.current) {
                                        setSearchBoxRect(searchBoxRef.current.getBoundingClientRect());
                                    }
                                    setShowSuggestions(true);
                                }}
                                onBlur={() => {
                                    closeSuggestionsTimerRef.current = setTimeout(() => setShowSuggestions(false), 160);
                                }}
                                onKeyDown={handleKeyDown}
                                placeholder="Search articles…"
                                className={FILTER_SEARCH_INPUT}
                            />
                            {searchTerm && (
                                <button
                                    type="button"
                                    onClick={handleClearSearch}
                                    className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded-full p-1 text-violet-800 transition-colors hover:bg-violet-200/90 hover:text-violet-950 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-white"
                                    aria-label="Clear search"
                                >
                                    <X size={14} />
                                </button>
                            )}
                        </form>
                    </div>
                </div>
            </div>

            <div
                className="relative z-0 w-full min-w-0 max-w-7xl px-3 pb-4 pt-3 sm:px-5 sm:pb-5 lg:px-6 xl:pt-0"
                style={xlFixedChrome ? { paddingTop: 'var(--lex-tile-gap)' } : undefined}
            >
                <div className="flex w-full max-w-full flex-col items-stretch justify-center gap-4 lg:flex-row lg:items-start lg:gap-6">
                    {/* TOC layout spacer — real panel is `position:fixed` via portal */}
                    <div
                        ref={tocSpacerRef}
                        className={`hidden shrink-0 transition-[width,opacity] duration-300 ease-in-out lg:block ${isSidebarOpen ? 'w-80' : 'pointer-events-none w-0 overflow-hidden opacity-0'}`}
                        aria-hidden
                    />

            {/* Codal stream — grows with content; scrolls with the main page */}
            <div className={`relative mt-0 min-w-0 flex-1 transition-all duration-300 ${(activeJurisArticle || activeAmendmentArticle) ? 'max-w-3xl' : 'max-w-4xl'}`}>
                {/* TOC: lg = anchor + side FAB; below-lg = same FAB + portaled modal (matches other lex-modal overlays) */}
                <div className="flex min-w-0 items-start gap-1.5 sm:gap-2 lg:gap-2.5">
                    {!isSidebarOpen && (
                        <div
                            ref={tocFabAnchorRef}
                            className="hidden h-12 w-12 shrink-0 pointer-events-none lg:block"
                            aria-hidden
                        />
                    )}
                    {/* Outer shell keeps shadow; inner clips body text to rounded corners */}
                    <div
                        ref={codalShellRef}
                        className="min-w-0 flex-1 rounded-2xl shadow-[0_28px_60px_-14px_rgba(109,40,217,0.22)] dark:shadow-[0_24px_50px_-16px_rgba(0,0,0,0.45)]"
                    >
                    <div
                        ref={mainContentRef}
                        id="main-content"
                        className="relative flex min-w-0 w-full flex-col overflow-hidden rounded-2xl border border-violet-200/65 bg-white/45 backdrop-blur-xl dark:border-zinc-700 dark:bg-zinc-900/85 glass"
                    >
                    <CardVioletInnerWash />
                    <div className="relative z-[1] flex min-h-0 w-full min-w-0 flex-1 flex-col">

                    {/* Toolbar — codal title + subtitle */}
                    <div className="flex flex-col rounded-t-2xl border-b border-white/20 bg-white/60 backdrop-blur-md dark:border-zinc-800 dark:bg-zinc-950/80">
                        <div className="flex items-center gap-3 px-4 py-3">
                            <div className="min-w-0 flex-1 px-2 text-center">
                                <h1 className="text-[16px] font-extrabold tracking-wide text-gray-900 dark:text-gray-100 font-sans leading-tight">
                                    {codeTitle ? toTitleCase(codeTitle) : 'Lex Code'}
                                </h1>
                                {codeSubtitle && (
                                    <p className="text-[11px] font-semibold text-violet-700 dark:text-zinc-400">
                                        {toTitleCase(codeSubtitle)}
                                    </p>
                                )}
                            </div>
                        </div>
                    </div>

                    <div className="custom-scrollbar min-w-0 max-w-full px-2 pt-4 pb-24 [overflow-wrap:anywhere] [word-break:break-word]">
                        {renderMainContent()}
                    </div>
                    </div>
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
            {mobileTocModalPortal}

            {/* Search dropdown — portaled to body so it escapes overflow-hidden on the codal shell */}
            {showSuggestions && searchBoxRect && typeof document !== 'undefined' &&
                createPortal(
                    <div
                        className="fixed z-[200] max-h-72 overflow-y-auto rounded-xl border border-lex bg-white shadow-lg dark:border-lex dark:bg-zinc-900"
                        style={{
                            top: searchBoxRect.bottom + 4,
                            left: searchBoxRect.left,
                            width: searchBoxRect.width,
                        }}
                        onMouseDown={(e) => e.preventDefault()} // keep focus on input so blur doesn't fire
                    >
                        {!debouncedSearchTerm.trim() ? (
                            <p className="px-3 py-4 text-center text-xs text-gray-400 dark:text-gray-500">
                                Start typing to find articles in this codal…
                            </p>
                        ) : searchSuggestions.length === 0 ? (
                            <div className="flex flex-col items-center gap-2 px-3 py-5 text-center">
                                <p className="text-xs text-gray-500 dark:text-gray-400">
                                    No articles match{' '}
                                    <span className="font-semibold text-gray-700 dark:text-gray-300">
                                        &ldquo;{debouncedSearchTerm}&rdquo;
                                    </span>
                                </p>
                                <button
                                    type="button"
                                    onClick={handleClearSearch}
                                    className="text-xs text-violet-600 hover:underline dark:text-zinc-400 dark:hover:text-zinc-200"
                                >
                                    Clear
                                </button>
                            </div>
                        ) : (
                            <>
                                <div className="border-b border-lex px-3 py-1.5">
                                    <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
                                        {searchSuggestions.length} article{searchSuggestions.length !== 1 ? 's' : ''} found — click to jump
                                    </span>
                                </div>
                                <div className="divide-y divide-lex">
                                    {searchSuggestions.map((art) => {
                                        const titleText =
                                            art.article_title ||
                                            (art.article_number
                                                ? `${codalProvisionLabel} ${art.article_number}`
                                                : codalProvisionLabel);
                                        const rawSnippet = (art.content || art.content_md || '')
                                            .replace(/[#*`_~]/g, '')
                                            .trim()
                                            .slice(0, 180);
                                        return (
                                            <button
                                                key={art.id || art.article_number}
                                                type="button"
                                                onClick={() =>
                                                    handleSuggestionClick(art.id || art.article_number)
                                                }
                                                className="w-full px-3 py-2.5 text-left transition-colors hover:bg-violet-50 dark:hover:bg-zinc-800"
                                            >
                                                <p className="line-clamp-1 text-sm font-bold text-violet-800 dark:text-zinc-200">
                                                    <HighlightText text={titleText} query={debouncedSearchTerm} />
                                                </p>
                                                {rawSnippet && (
                                                    <p className="mt-0.5 line-clamp-2 text-xs leading-relaxed text-gray-500 dark:text-gray-400">
                                                        <HighlightText text={rawSnippet} query={debouncedSearchTerm} />
                                                    </p>
                                                )}
                                            </button>
                                        );
                                    })}
                                </div>
                            </>
                        )}
                    </div>,
                    document.body
                )
            }
            {desktopJurisPortal}

            {typeof document !== 'undefined' &&
                tocFabPos != null &&
                !isSidebarOpen &&
                createPortal(
                    <button
                        type="button"
                        onClick={() => setIsSidebarOpen(true)}
                        /* z-[38]: above codal filter chrome (z-[30]), below Layout nav aside (z-40) */
                        /* Match Layout header logo: h-8 max-sm, h-10 sm–lg, h-12 lg+ (see Layout.jsx brand tile) */
                        className="fixed z-[38] flex h-8 w-8 touch-manipulation items-center justify-center rounded-lg border border-violet-400/80 bg-gradient-to-br from-violet-600 via-purple-600 to-fuchsia-600 text-white shadow-md shadow-purple-600/30 ring-1 ring-white/30 transition-transform hover:scale-[1.04] active:scale-95 sm:h-10 sm:w-10 sm:rounded-xl sm:shadow-lg sm:ring-2 lg:h-12 lg:w-12 lg:shadow-[0_8px_28px_rgba(109,40,217,0.45)] dark:border-zinc-600 dark:from-zinc-700 dark:via-zinc-800 dark:to-zinc-900 dark:ring-zinc-950/50"
                        style={{
                            left: tocFabPos.left,
                            top: `calc(${tocFabPos.top}px + var(--lex-tile-gap))`,
                        }}
                        title="Table of contents"
                        aria-label="Open table of contents"
                    >
                        <ListTree
                            className="h-[0.9375rem] w-[0.9375rem] sm:h-5 sm:w-5 lg:h-6 lg:w-6"
                            strokeWidth={2.25}
                            aria-hidden
                        />
                    </button>,
                    document.body
                )}

            {/* Mobile juris/amendments — portaled + lex-modal-* (same as CaseDecisionModal) */}
            {typeof document !== 'undefined' &&
                (activeJurisArticle || activeAmendmentArticle) &&
                createPortal(
                    <div
                        className="lg:hidden fixed inset-0 z-[540] lex-modal-overlay bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
                        onClick={handleCloseMobileLexPanels}
                    >
                        <div
                            className="lex-modal-card relative flex w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-lex bg-white shadow-2xl animate-in zoom-in-95 duration-300 dark:border-lex dark:bg-zinc-900"
                            role="dialog"
                            aria-modal="true"
                            aria-label={
                                activeJurisArticle
                                    ? 'Jurisprudence linked to this provision'
                                    : 'Amendments for this article'
                            }
                            onClick={(e) => e.stopPropagation()}
                        >
                            <CardVioletInnerWash />
                            <div className="relative z-[1] flex min-h-0 min-w-0 flex-1 flex-col">
                            {activeJurisArticle && (
                                <div className="flex min-h-0 min-w-0 flex-1 flex-col">
                                    <LexCodeJurisSidebar
                                        articleNum={activeJurisArticle}
                                        statuteId={shortName}
                                        paragraphFilter={activeJurisParagraph}
                                        onClose={handleCloseMobileLexPanels}
                                        onSelectRatio={async (caseId, ratioIndex) => {
                                            await openJurisCaseDetail(caseId, ratioIndex);
                                        }}
                                    />
                                </div>
                            )}
                            {activeAmendmentArticle && !activeJurisArticle && (
                                <div className="lex-modal-scroll flex min-h-0 flex-1 flex-col overflow-y-auto p-4 font-sans sm:p-6">
                                    <div className="mb-4 flex shrink-0 items-center justify-between">
                                        <h3 className="text-lg font-bold text-rose-700 dark:text-rose-400">Amendments</h3>
                                        <button
                                            type="button"
                                            onClick={handleCloseMobileLexPanels}
                                            className="touch-manipulation rounded-full p-1.5 text-stone-400 transition-colors hover:bg-stone-200 dark:hover:bg-gray-700"
                                            aria-label="Close"
                                        >
                                            <X size={18} />
                                        </button>
                                    </div>
                                    <div className="text-sm text-gray-700 dark:text-gray-300">
                                        Article {activeAmendmentArticle.article_num}
                                    </div>
                                </div>
                            )}
                            </div>
                        </div>
                    </div>,
                    document.body
                )}
                </div>
            </div>
        </PurpleGlassAmbient>
        </>
    );
};

export default CodexViewer;
