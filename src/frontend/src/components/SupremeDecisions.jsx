import React, { useState, useEffect, useRef, useLayoutEffect } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { createPortal } from 'react-dom';
import { jsPDF } from "jspdf";
import { Search, Gavel, FileText, X, Filter, BookOpen, AlertTriangle, Lightbulb, Layers, Book, Star, Zap, User, ChevronRight, Scale, ChevronDown, ChevronUp, Landmark } from 'lucide-react';
import { lexCache } from '../utils/cache';




import { formatDate } from '../utils/dateUtils';
import { apiUrl } from '../utils/apiUrl';
import { consumeFreeTierUsage, notifyUsageBlocked } from '../utils/freeTierUsage';
import { getSubjectColor, getSubjectAnswerColor, normalizeSubjectForColor } from '../utils/colors';
import ReactMarkdown from 'react-markdown';
import { useSubscription } from '../context/SubscriptionContext';
import { useDebounce } from '../hooks/useDebounce';
import { HighlightText } from '../utils/highlight';
import PurpleGlassAmbient from './PurpleGlassAmbient';
import CardVioletInnerWash from './CardVioletInnerWash';
import {
    FILTER_CHROME_SURFACE,
    FILTER_SELECT,
    FILTER_SEARCH_INPUT,
    FILTER_TOGGLE_BUTTON,
    FILTER_CHROME_DIVIDER,
    FILTER_SEARCH_ICON_CLASS,
    FILTER_FIELD_LABEL,
} from '../utils/filterChromeClasses';

/** Read fetch body as JSON once; throws with actionable text if empty or non-JSON (common when API is down or returns HTML). */
async function parseResponseJson(response) {
    const text = await response.text();
    if (text == null || !String(text).trim()) {
        throw new Error(
            `Empty response (HTTP ${response.status}). Start Azure Functions on http://localhost:7071. If you use http://localhost:4280 (SWA CLI), ensure swa-cli.config.json has apiLocation "api" and apiDevserverUrl "http://127.0.0.1:7071". Or set VITE_API_BASE_URL=http://127.0.0.1:7071 and restart Vite.`
        );
    }
    try {
        return JSON.parse(text);
    } catch {
        const preview = String(text).replace(/\s+/g, ' ').slice(0, 180);
        throw new Error(
            `Non-JSON response (HTTP ${response.status}): ${preview}${text.length > 180 ? '…' : ''}`
        );
    }
}

const BAR_SUBJECTS = [
    "Political Law",
    "Labor Law",
    "Civil Law",
    "Taxation Law",
    "Commercial Law",
    "Criminal Law",
    "Remedial Law",
    "Legal Ethics"
];



const SmartLink = ({ text, onCaseClick }) => {
    if (!text) return null;

    // Regex to detect G.R. Nos and Republic Acts
    const regex = /(G\.R\. Nos?\.\s?\d+[\w\,&\s-]*)|(Republic Act No\.\s?\d+)/gi;

    // Split by regex but keep delimiters (capturing groups)
    const parts = text.split(regex).filter(p => p !== undefined);

    if (parts.length === 1) return <span>{text}</span>;

    return (
        <span>
            {parts.map((part, i) => {
                const isMatch = typeof part === 'string' && part.match(regex);
                if (isMatch) {
                    return (
                        <span
                            key={i}
                            className="text-blue-600 dark:text-amber-400 cursor-pointer hover:underline font-medium relative group"
                            onClick={(e) => {
                                e.stopPropagation();
                                onCaseClick(part);
                            }}
                        >
                            {part}
                        </span>
                    );
                }
                return <span key={i}>{part}</span>;
            })}
        </span>
    );
};

const BulletedText = ({ text, onCaseClick }) => {
    if (!text) return null;

    // 1. Initial split by newline
    let initialLines = text.split('\n');

    // 2. Heuristic: If it looks like a single block with inline numbering "1. ... 2. ...", force a split
    // Regex matches "1. ", "2. ", "1) ", "2) "
    const numberingRegex = /(?=\b\d+[\.\)]\s+)/;

    // Check if the first chunk contains multiple numbering patterns
    if (initialLines.length <= 1 && text.match(/\b\d+[\.\)]\s+/g)?.length > 1) {
        initialLines = text.split(numberingRegex).filter(l => l.trim().length > 0);
    }

    // 3. Clean up lines
    const lines = initialLines.filter(line => line.trim().length > 0);

    return (
        <ul className="space-y-2">
            {lines.map((line, idx) => {
                // Formatting Pipeline:
                // 1. Remove lead numbering (eg "1. ", "1)")
                let cleanLine = line.replace(/^\s*[\d\(\)\.\-]+\s+/, '').trim();

                // 2. Remove markdown bullet points (* or -) at start
                cleanLine = cleanLine.replace(/^[\*\-]\s+/, '').trim();

                // 3. Detect Markdown Bold Header: **Title:** or *Title:*
                // Regex: Start of line, optional *, then **(content)**, then optional *
                let header = null;
                let content = cleanLine;

                // Match **Title:** pattern
                // regex removed removed to fix build error. Using colonMatch logic below.
                // Simple heuristic: check if line starts with ** or * and has a colon early on

                // Better approach: Regex for "Header:" pattern
                const colonMatch = cleanLine.match(/^([^\:]+)\:\s*(.*)/);

                if (colonMatch) {
                    const rawHeader = colonMatch[1];
                    const rest = colonMatch[2];

                    // Clean the header of markdown artifacts (* and **)
                    const cleanHeader = rawHeader.replace(/[\*\_]/g, '').trim();

                    if (cleanHeader.length < 100) { // Safety check length
                        header = cleanHeader + ":";
                        content = rest;
                    }
                }

                return (
                    <li key={idx} className="flex items-start gap-3 group">
                        {/* Standard Bullet matching Jurisprudence Mapping */}
                        <div className="mt-2 w-1.5 h-1.5 rounded-full bg-gray-400 dark:bg-gray-500 flex-shrink-0" />
                        <span className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed">
                            {header && <strong className="font-bold text-black dark:text-gray-100 mr-1">{header}</strong>}
                            <SmartLink text={content} onCaseClick={onCaseClick} />
                        </span>
                    </li>
                );
            })}
        </ul>
    );
};

const TimelineSection = ({ timeline }) => {
    if (!timeline || timeline.length === 0) return null;
    // Parse json if it's a string, else use as is
    let events = [];
    try {
        events = typeof timeline === 'string' ? JSON.parse(timeline) : timeline;
    } catch (e) { return null; }

    return (
        <div className="mb-8">
            <h4 className="text-md font-bold text-black dark:text-gray-100 flex items-center gap-2 mb-4">
                <Clock className="w-5 h-5 text-blue-500 dark:text-amber-500" />
                TIMELINE OF EVENTS
            </h4>
            <div className="border-l-2 border-blue-200 dark:border-blue-800 ml-3 space-y-6">
                {events.map((t, idx) => (
                    <div key={idx} className="relative pl-6">
                        <span className="absolute -left-[9px] top-1 h-4 w-4 rounded-full bg-blue-100 dark:bg-amber-900 border-2 border-blue-500 dark:border-amber-500"></span>
                        <div className="text-sm font-bold text-blue-700 dark:text-amber-300 mb-1">{t.date}</div>
                        <div className="text-gray-700 dark:text-gray-300 text-sm">{t.event}</div>
                    </div>
                ))}
            </div>
        </div>
    );
};

const FlashcardSection = ({ flashcards }) => {
    if (!flashcards) return null;
    let cards = [];
    try {
        cards = typeof flashcards === 'string' ? JSON.parse(flashcards) : flashcards;
    } catch (e) { return null; }
    if (cards.length === 0) return null;

    return (
        <div className="mt-8 pt-6 border-t border-lex">
            <h4 className="text-lg font-bold text-black dark:text-white mb-4 flex items-center gap-2">
                <Lightbulb className="w-5 h-5 text-yellow-500 dark:text-amber-500" />
                Study Flashcards
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {cards.map((card, idx) => (
                    <div key={idx} className="bg-yellow-50 dark:bg-yellow-900/10 border border-yellow-200 dark:border-yellow-700 p-4 rounded-lg shadow-sm hover:shadow-md transition-shadow">
                        <div className="text-xs font-bold text-yellow-700 dark:text-yellow-400 uppercase tracking-wide mb-2">{card.type}</div>
                        <div className="font-sans font-bold text-black dark:text-gray-100 mb-3">{card.q}</div>
                        <div className="text-sm text-gray-700 dark:text-gray-300 border-t border-yellow-200 dark:border-yellow-700 pt-2">{card.a}</div>
                    </div>
                ))}
            </div>
        </div>
    );
};

const LegalConceptsSection = ({ concepts }) => {
    if (!concepts) return null;
    let items = [];
    try {
        items = typeof concepts === 'string' ? JSON.parse(concepts) : concepts;
    } catch (e) { return null; }
    if (!items || items.length === 0) return null;

    return (
        <div className="bg-purple-50 dark:bg-purple-900/10 border border-purple-100 dark:border-purple-900/30 p-5 rounded-lg my-6">
            <h4 className="text-md font-bold text-purple-800 dark:text-purple-300 flex items-center gap-2 mb-3">
                <BookOpen className="w-5 h-5" />
                KEY LEGAL CONCEPTS
            </h4>
            <div className="space-y-4">
                {items.map((item, idx) => (
                    <div key={idx} className="text-sm">
                        <span className="font-bold text-purple-900 dark:text-purple-200 block mb-1">
                            {item.term}
                        </span>
                        <div className="text-gray-800 dark:text-gray-200 border-l-2 border-purple-300 dark:border-purple-600 pl-3 leading-relaxed">
                            {item.definition}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

const getCategoryColor = (cat) => {
    const c = cat?.toUpperCase() || 'REITERATION';

    // MODIFICATION gets special pulsing animation treatment
    if (c === 'MODIFICATION') {
        return 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/40 dark:text-yellow-300 dark:border-yellow-700 animate-pulse ring-2 ring-yellow-400 dark:ring-yellow-500 ring-opacity-50';
    }

    // ABANDONMENT gets ring effect
    if (c === 'ABANDONMENT') {
        return 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/40 dark:text-red-300 dark:border-red-700 ring-2 ring-red-400 dark:ring-red-500 ring-opacity-50';
    }

    const map = {
        'NEW DOCTRINE': 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/40 dark:text-green-300 dark:border-green-700 ring-1 ring-green-300',
        'REVERSAL': 'bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/40 dark:text-orange-300 dark:border-orange-700 ring-1 ring-orange-300',
        'CLARIFICATION': 'bg-cyan-100 text-cyan-800 border-cyan-200 dark:bg-cyan-900/40 dark:text-cyan-300 dark:border-cyan-700 ring-1 ring-cyan-300',
        'REITERATION': 'bg-slate-200 text-slate-700 border-slate-300 dark:bg-amber-900/30 dark:text-amber-200 dark:border-amber-700 shadow-sm ring-1 ring-slate-300 dark:ring-amber-800',
        // Legacy fallbacks
        'LANDMARK': 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-300',
        'DOCTRINAL': 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300',
    };
    return map[c] || map['REITERATION'];
};

/** Matches CaseDecisionModal — text color for significance in metadata rows. */
const getCategoryTextClass = (cat) => {
    const c = cat?.toUpperCase() || 'REITERATION';
    if (c === 'MODIFICATION') return 'text-amber-800 dark:text-amber-200';
    if (c === 'ABANDONMENT') return 'text-red-800 dark:text-red-300';
    if (c === 'NEW DOCTRINE') return 'text-emerald-800 dark:text-emerald-300';
    if (c === 'REVERSAL') return 'text-orange-800 dark:text-orange-300';
    if (c === 'CLARIFICATION') return 'text-cyan-800 dark:text-cyan-300';
    if (c === 'LANDMARK') return 'text-amber-900 dark:text-amber-200';
    if (c === 'DOCTRINAL') return 'text-blue-800 dark:text-blue-300';
    return 'text-slate-800 dark:text-slate-200';
};


const SignificanceSection = ({ narrative, category, complexity }) => {
    if (!narrative && !category) return null;

    const processContent = (text) => {
        if (!text) return "";
        let processed = text;
        processed = processed.replace(/^\[.*?\]\s*/, '');
        processed = processed.replace(/(\n\s*)*(\*\*Significance:\*\*|Significance:)/g, '\n\n$2');
        return processed;
    };

    return (
        <section className="mb-8">
            <h4 className="text-md font-bold text-black dark:text-gray-100 border-b border-lex pb-3 mb-4 uppercase tracking-wide flex items-center justify-between">
                <span className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-500" />
                    Jurisprudential Impact and Bar Significance
                </span>
                {category && (
                    <span className={`text-xs px-3 py-1.5 rounded-md border ${getCategoryColor(category)} uppercase tracking-wider font-extrabold ml-2 shadow-sm`}>
                        {category}
                    </span>
                )}
            </h4>

            <div className="bg-gradient-to-br from-white to-amber-50/50 dark:from-gray-800 dark:to-amber-900/10 p-5 rounded-xl border border-lex shadow-sm relative overflow-hidden">
                {/* Decorative background element */}
                <div className="absolute top-0 right-0 w-32 h-32 bg-amber-200/10 dark:bg-amber-500/5 rounded-full blur-3xl -mr-16 -mt-16 pointer-events-none"></div>

                <div className="text-gray-800 dark:text-gray-200 leading-relaxed text-sm relative z-10">
                    <ReactMarkdown components={{
                        p: ({ node, ...props }) => <p className="mb-4 last:mb-0 text-justify leading-7" {...props} />,
                        strong: ({ node, ...props }) => <strong className="font-bold text-amber-900 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/30 px-1 rounded" {...props} />,
                        ul: ({ ...props }) => <ul className="list-disc pl-5 space-y-2 mb-4" {...props} />,
                        li: ({ ...props }) => <li className="pl-1" {...props} />
                    }}>
                        {processContent(narrative)}
                    </ReactMarkdown>
                </div>
            </div>
        </section>
    );
};

const SmartLinkWrapper = ({ children, onCaseClick }) => {
    if (typeof children === 'string') {
        return <SmartLink text={children} onCaseClick={onCaseClick} />;
    }
    if (Array.isArray(children)) {
        return (
            <>
                {children.map((child, idx) => {
                    if (typeof child === 'string') {
                        return <SmartLink key={idx} text={child} onCaseClick={onCaseClick} />;
                    }
                    return <React.Fragment key={idx}>{child}</React.Fragment>;
                })}
            </>
        );
    }
    return <>{children}</>;
};

const formatRatioToParagraphs = (text) => {
    if (!text) return "";

    // If it's already nicely formatted with double newlines, assume it's okay
    // But we want to enforce spacing between "Issue:" blocks if they are stuck together
    let formatted = text;

    // 1. Replace "On the issue of..." bullet points with double newlines
    // Matches: * **On the issue...** or * On the issue...
    formatted = formatted.replace(/^\s*[\*\-]\s+/gm, '\n\n');

    // 2. Ensure bold headers start on new lines
    // Matches: **Header:** content...
    formatted = formatted.replace(/([^\n])\s*(\*\*.*?\*\*[:?])/g, '$1\n\n$2');

    return formatted.trim();
};

const MarkdownText = ({ content, onCaseClick, variant = 'default' }) => {
    if (!content) return null;

    const formatFactsToParagraphs = (text) => {
        if (!text) return "";

        // Pre-process: Ensure our bold headers are preceded by newlines if they aren't already
        // This handles the case where the AI might have missed a double newline or if the split/join logic messed it up
        let normalized = text.replace(/([^\n])\n(\*\*.*?\*\*[:?])/g, '$1\n\n$2');

        // If we detect the "Antecedents" / "Procedural History" structure we explicitly asked for,
        // we should just trust the newlines and not try to aggressively merge lines.
        if (normalized.includes("**The Antecedents:**") || normalized.includes("**Procedural History:**")) {
            return normalized;
        }

        const lines = normalized.split('\n');
        let result = [];
        let currentNum = "";
        let currentHeaderLabel = "";
        let currentBody = [];

        // Expanded regex to catch numbered lists OR bold headers like "**The Antecedents:**"
        const headerRegex = /^\s*(?:(\d+[\.\)])|(\*\*.*?\*\*[:?]?))\s+(.*)/;

        const pushBlock = () => {
            if (currentNum || currentHeaderLabel || currentBody.length > 0) {
                let block = "";
                if (currentNum) block += `${currentNum} `;
                if (currentHeaderLabel) block += `**${currentHeaderLabel.replace(/^\*\*|\*\*$/g, '')}:** `; // Ensure clean header

                if (currentBody.length > 0) {
                    block += currentBody.join(' ').trim();
                }
                // Ensure no double colons
                block = block.replace(/:\s*:\s*$/, ': ');
                result.push(block.trim());
            }
        };

        for (let line of lines) {
            line = line.trim();
            if (!line) continue;

            const headerMatch = line.match(headerRegex);

            if (headerMatch) {
                pushBlock();

                // Reset for new section
                currentBody = [];

                // Group 1: Number (e.g. "1.")
                // Group 2: Bold Header (e.g. "**The Antecedents:**")
                // Group 3: Rest of line
                const numStr = headerMatch[1];
                const headerStr = headerMatch[2];
                let rest = headerMatch[3];

                if (numStr) {
                    currentNum = numStr;
                    // Standard numbered line logic
                    const firstColon = rest.indexOf(':');
                    if (firstColon > -1) {
                        currentHeaderLabel = rest.substring(0, firstColon).trim();
                        let initialBody = rest.substring(firstColon + 1).trim();
                        if (initialBody) currentBody.push(initialBody);
                    } else {
                        currentHeaderLabel = rest.trim();
                    }
                } else if (headerStr) {
                    // Bold Header logic
                    currentNum = ""; // No number
                    currentHeaderLabel = headerStr.replace(/^\*\*|\*\*[:?]?$/g, '').trim();
                    if (rest) currentBody.push(rest);
                }
            } else {
                // Not a header line
                let content = line.replace(/^[\*\-]\s+/, '');
                // We do NOT strip wrapping bolding here anymore, because it might be emphasized text inside a paragraph
                if (content) currentBody.push(content);
            }
        }

        // Final push
        pushBlock();

        if (result.length === 0) return text;
        return result.join('\n\n');
    };




    let processedContent = content;


    // Apply special formatting for Facts
    if (variant === 'facts') {
        processedContent = formatFactsToParagraphs(content);
    }

    const components = {
        p: ({ children }) => <div className="mb-4 text-gray-800 dark:text-gray-200 leading-relaxed text-justify"><SmartLinkWrapper onCaseClick={onCaseClick}>{children}</SmartLinkWrapper></div>,
        // Since we are pre-formatting into paragraphs, headers within markdown might not appear unless we preserved them as ###.
        // But our logic converts headers to "**Term:**" inside keys.
        // So we mostly rely on bold wrapper.
        strong: ({ children }) => <strong className="font-bold text-black dark:text-gray-100">{children}</strong>,
        ul: ({ children }) => <ul className="mb-4 list-disc pl-5 space-y-2 text-gray-800 dark:text-gray-200">{children}</ul>,
        li: ({ children }) => <li className="pl-1 leading-relaxed"><SmartLinkWrapper onCaseClick={onCaseClick}>{children}</SmartLinkWrapper></li>
    };

    return (
        <ReactMarkdown components={components}>
            {processedContent}
        </ReactMarkdown>
    );
};


const SupremeDecisions = ({ externalSelectedCase, onCaseSelect }) => {
    const { getToken, isSignedIn } = useAuth();
    const { openUpgradeModal, canAccess, loading: subscriptionLoading } = useSubscription();

    // Seed from ?q= so direct links and page-refreshes restore the search.
    const [searchTerm, setSearchTerm] = useState(() =>
        window.location.pathname === '/decisions'
            ? (new URLSearchParams(window.location.search).get('q') ?? '')
            : ''
    );
    const [searchResults, setSearchResults] = useState([]);

    // Search dropdown (portal — escapes any overflow-hidden ancestor)
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [searchBoxRect, setSearchBoxRect] = useState(null);
    const searchInputRef = useRef(null);
    const closeSuggestionsTimerRef = useRef(null);

    /** Start true so we never flash "No decisions found" before the first request runs. */
    const [loading, setLoading] = useState(true);
    const [fetchError, setFetchError] = useState(null);
    const [selectedDecision, setSelectedDecision] = useState(null);
    const [viewMode, setViewMode] = useState('digest'); // 'digest' or 'full'
    const [fullText, setFullText] = useState(null);
    const [fullTextHtml, setFullTextHtml] = useState(null);
    const [loadingFullText, setLoadingFullText] = useState(false);
    const [showMockExam, setShowMockExam] = useState(false);
    const [mockExamQuestions, setMockExamQuestions] = useState(null);
    const [loadingMockExam, setLoadingMockExam] = useState(false);

    // Filter states
    /** Custom filter grid (year, ponente, …) — toggled to save space; chrome bar fixed only at xl+ while scrolling. */
    const [showCustomFilters, setShowCustomFilters] = useState(false);
    const filterChromeRef = useRef(null);
    const [filterChromeHeight, setFilterChromeHeight] = useState(52);
    /** Match Tailwind `xl:` (1280px) — fixed filter row only at desktop; mobile/tablet scroll with page. */
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
    const [selectedYear, setSelectedYear] = useState('');
    const [selectedMonth, setSelectedMonth] = useState('');
    const [selectedPonente, setSelectedPonente] = useState('');
    const [selectedSubject, setSelectedSubject] = useState('');
    const [selectedDivision, setSelectedDivision] = useState('');
    const [selectedSignificance, setSelectedSignificance] = useState('');

    const [isDoctrinal, setIsDoctrinal] = useState(false);
    const [hasInitialLoaded, setHasInitialLoaded] = useState(false);

    // Pagination
    const [currentPage, setCurrentPage] = useState(1);
    const [totalCount, setTotalCount] = useState(0);
    const [debugUrl, setDebugUrl] = useState('');
    const ITEMS_PER_PAGE = 20;
    /** When true, shows modal-style metadata labels (dl); default hidden. */
    const [caseDetailsExpandedById, setCaseDetailsExpandedById] = useState({});

    // Available options
    const [availableYears, setAvailableYears] = useState([]);
    const [availablePonentes, setAvailablePonentes] = useState([]);
    const [availableDivisions, setAvailableDivisions] = useState([]);


    useEffect(() => {
        fetchAvailableFilters();
        fetchPonentes();
        fetchDivisions();
    }, []);

    // Keep dropdown anchored when the page scrolls / resizes while it's open.
    useEffect(() => {
        if (!showSuggestions) return;
        const update = () => {
            if (searchInputRef.current) {
                setSearchBoxRect(searchInputRef.current.getBoundingClientRect());
            }
        };
        window.addEventListener('scroll', update, true);
        window.addEventListener('resize', update);
        return () => {
            window.removeEventListener('scroll', update, true);
            window.removeEventListener('resize', update);
        };
    }, [showSuggestions]);

    // Keep main content below the fixed filter bar (height changes when custom filters expand).
    useLayoutEffect(() => {
        const el = filterChromeRef.current;
        if (!el || typeof ResizeObserver === 'undefined') {
            return;
        }
        const measure = () => {
            setFilterChromeHeight(Math.ceil(el.getBoundingClientRect().height));
        };
        measure();
        const ro = new ResizeObserver(measure);
        ro.observe(el);
        return () => ro.disconnect();
    }, [showCustomFilters, loading]);

    // Global pre-fetch cache to make modals "instant" (Disable Lazy Load)
    const [prefetchCache, setPrefetchCache] = useState({});

    // Tracks how many prefetch fetches are in-flight; cap at 3 to avoid flooding setState.
    const prefetchInflightRef = useRef(0);

    const prefetchDetails = async (id) => {
        if (!id || prefetchCache[id] || prefetchInflightRef.current >= 3) return;
        prefetchInflightRef.current += 1;
        try {
            // Check IndexedDB first — no network if already cached from a prior session
            const idbHit = await lexCache.get('cases', id);
            if (idbHit && idbHit.digest_facts) {
                // Strip huge fields from component state; full data lives in IndexedDB
                const { full_text_md: _ft, full_text_html: _fh, ...light } = idbHit;
                setPrefetchCache(prev => ({ ...prev, [id]: light }));
                return;
            }
            const res = await fetch(apiUrl(`/api/sc_decisions/${id}`));
            const data = await res.json();
            // Persist the FULL object to IndexedDB so modal opens get full_text_md instantly.
            lexCache.set('cases', id, data).catch(() => {});
            // Only store lightweight fields in component state to keep state small.
            const { full_text_md: _ft, full_text_html: _fh, ...light } = data;
            setPrefetchCache(prev => ({ ...prev, [id]: light }));
        } catch (err) {
            console.error("Prefetch failed", err);
        } finally {
            prefetchInflightRef.current -= 1;
        }
    };

    // AbortController Ref
    const abortControllerRef = useRef(null);
    // Track active request ID to manage loading state safely
    const activeRequestRef = useRef(0);

    // Debounced Search Effect
    useEffect(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
        setLoading(true);

        const delayDebounceFn = setTimeout(() => {
            fetchDecisions();
        }, 300);

        return () => {
            clearTimeout(delayDebounceFn);
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
        };
    }, [searchTerm, selectedYear, selectedMonth, selectedPonente, selectedSubject, selectedDivision, selectedSignificance, isDoctrinal, currentPage]);

    // Persist search term in URL (?q=) using debounce so we don't spam history.
    const debouncedSearchTerm = useDebounce(searchTerm, 400);
    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        if (debouncedSearchTerm) {
            params.set('q', debouncedSearchTerm);
        } else {
            params.delete('q');
        }
        const qs = params.toString();
        window.history.replaceState(
            null,
            '',
            window.location.pathname + (qs ? `?${qs}` : '')
        );
    }, [debouncedSearchTerm]);

    // Sync external case selection from App.jsx
    useEffect(() => {
        if (externalSelectedCase && externalSelectedCase.id !== selectedDecision?.id) {
            handleCaseClick(externalSelectedCase);
        }
    }, [externalSelectedCase]);


    const fetchPonentes = async () => {
        try {
            const response = await fetch(apiUrl('/api/sc_decisions/ponentes'));
            const data = await response.json();
            if (Array.isArray(data)) {
                setAvailablePonentes(data);
            }
        } catch (error) {
            console.error("Failed to fetch ponentes", error);
        }
    };

    const fetchDivisions = async () => {
        try {
            const response = await fetch(apiUrl('/api/sc_decisions/divisions'));
            const data = await response.json();
            if (Array.isArray(data)) {
                setAvailableDivisions(data);
            }
        } catch (error) {
            console.error("Failed to fetch divisions", error);
        }
    };



    const fetchAvailableFilters = async () => {
        try {
            const currentYear = new Date().getFullYear();
            const years = Array.from({ length: currentYear - 1900 }, (_, i) => currentYear - i);
            setAvailableYears(years);
        } catch (error) {
            console.error("Error fetching filters", error);
        }
    };

    const fetchDecisions = async () => {
        // Increment request ID
        const requestId = ++activeRequestRef.current;

        // Create new controller for this request
        abortControllerRef.current = new AbortController();
        const { signal } = abortControllerRef.current;

        setLoading(true);
        setFetchError(null);
        try {
            let query = `/api/sc_decisions?search=${encodeURIComponent(searchTerm)}&page=${currentPage}&limit=${ITEMS_PER_PAGE}`;
            if (selectedYear) query += `&year=${selectedYear}`;
            if (selectedMonth) query += `&month=${encodeURIComponent(selectedMonth)}`;
            if (selectedPonente) query += `&ponente=${encodeURIComponent(selectedPonente)}`;
            if (selectedSubject) query += `&subject=${encodeURIComponent(selectedSubject)}`;
            if (selectedDivision) query += `&division=${encodeURIComponent(selectedDivision)}`;
            if (selectedSignificance) query += `&significance=${encodeURIComponent(selectedSignificance)}`;

            if (isDoctrinal) query += `&doctrinal=true`;

            setDebugUrl(query);

            const response = await fetch(apiUrl(query), { signal });

            let data;
            try {
                data = await parseResponseJson(response);
            } catch (parseErr) {
                if (requestId === activeRequestRef.current) {
                    setFetchError(parseErr?.message || 'Could not read the server response.');
                    setSearchResults([]);
                    setTotalCount(0);
                }
                return;
            }

            if (signal.aborted) return;

            if (!response.ok || data.error) {
                const msg = data?.error || `Request failed (${response.status})`;
                console.error('sc_decisions error:', msg);
                if (requestId === activeRequestRef.current) {
                    setFetchError(typeof msg === 'string' ? msg : JSON.stringify(msg));
                    setSearchResults([]);
                    setTotalCount(0);
                }
                return;
            }

            const rows = Array.isArray(data.data) ? data.data : [];
            if (requestId === activeRequestRef.current) {
                setSearchResults(rows);
                setTotalCount(parseInt(data.total, 10) || 0);
                setFetchError(null);
                // Save non-trivial search terms to recent-searches history.
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                return;
            }
            console.error('Search failed', error);
            if (requestId === activeRequestRef.current) {
                setFetchError(
                    error.message?.includes('Failed to fetch') || error.name === 'TypeError'
                        ? 'Cannot reach the server. Start the API (e.g. Azure Functions on port 7071) or check your connection.'
                        : error.message || 'Search failed.'
                );
                setSearchResults([]);
                setTotalCount(0);
            }
        } finally {
            if (requestId === activeRequestRef.current) {
                setLoading(false);
                setHasInitialLoaded(true);
            }
        }
    };


    const [loadingDetails, setLoadingDetails] = useState(false);

    const fetchDecisionDetails = async (id, currentDecision) => {
        setLoadingDetails(true);
        try {
            const fetcher = async () => {
                const response = await fetch(apiUrl(`/api/sc_decisions/${id}`));
                return parseResponseJson(response);
            };

            await lexCache.swr('cases', id, fetcher, (data, isCached) => {
                // Merge current lightweight decision with full details
                const fullDecision = { ...currentDecision, ...data };
                setSelectedDecision(fullDecision);

                if (data.full_text_html) setFullTextHtml(data.full_text_html);
                if (data.full_text_md) setFullText(data.full_text_md);
                setLoadingDetails(false);
            });

        } catch (error) {
            console.error("Failed to fetch details", error);
            setLoadingDetails(false);
        }
    };

    const handleCaseClick = async (decision) => {
        // Layer 1: in-memory prefetch cache (same session, fastest) — only if it has full detail
        let fullData = prefetchCache[decision.id];
        const cacheHasFull = fullData && fullData.digest_facts && fullData.full_text_md !== undefined;

        if (!cacheHasFull) {
            // Layer 2: IndexedDB (persists across page reloads — no network needed)
            // The prefetch stores full data here even when it strips it from component state.
            try {
                const idbHit = await lexCache.get('cases', decision.id);
                if (idbHit && idbHit.digest_facts) {
                    fullData = idbHit;
                }
            } catch (_) {}
        }

        if (!fullData || !fullData.digest_facts) {
            // Layer 3: network fetch (Redis-cached on the server — usually fast)
            document.body.style.cursor = 'wait';
            try {
                const res = await fetch(apiUrl(`/api/sc_decisions/${decision.id}`));
                fullData = await parseResponseJson(res);
                if (!res.ok || fullData?.error) {
                    console.error('Case detail error:', fullData?.error || res.status);
                }
                // Persist full data to IndexedDB; keep component state lightweight
                lexCache.set('cases', decision.id, fullData).catch(() => {});
                const { full_text_md: _ft, full_text_html: _fh, ...light } = fullData;
                setPrefetchCache(prev => ({ ...prev, [decision.id]: light }));
            } catch (err) {
                console.error("Manual fetch failed", err);
            } finally {
                document.body.style.cursor = 'default';
            }
        }

        const enrichedDecision = { ...decision, ...fullData };

        if (onCaseSelect) {
            onCaseSelect(enrichedDecision);
        } else {
            const usage = await consumeFreeTierUsage({
                feature: 'case_digest',
                getToken,
                isSignedIn,
                canAccess,
                subscriptionLoading,
            });
            if (!usage.allowed) {
                notifyUsageBlocked(usage, openUpgradeModal, 'case_digest_unlimited');
                return;
            }
            setSelectedDecision(enrichedDecision);
        }
    };

    const handleViewFullText = async (e, decision) => {
        e.stopPropagation();
        const usage = await consumeFreeTierUsage({
            feature: 'case_digest',
            getToken,
            isSignedIn,
            canAccess,
            subscriptionLoading,
        });
        if (!usage.allowed) {
            notifyUsageBlocked(usage, openUpgradeModal, 'case_digest_unlimited');
            return;
        }
        setSelectedDecision(decision);
        setViewMode('full');
        setFullText(null);
        setFullTextHtml(null);
        setShowMockExam(false);

        // Use generalized fetch
        if (!decision.full_text_md && !decision.full_text_html) {
            await fetchDecisionDetails(decision.id, decision);
        }
    };

    const handleSmartCaseClick = async (caseRef) => {
        console.log("SmartLink: Click handler started for", caseRef);

        // Visual feedback immediately
        document.body.style.cursor = 'wait';

        // Safety: Force cursor reset after 10 seconds no matter what
        const cursorTimeout = setTimeout(() => {
            console.warn("SmartLink: Force resetting cursor after 10s timeout");
            document.body.style.cursor = 'default';
        }, 10000);

        try {
            console.log("SmartLink: Searching for", caseRef);

            // Strategy 1: Try strict search first
            console.log("SmartLink: Strategy 1 - Exact search");
            let response = await fetch(apiUrl(`/api/sc_decisions?search=${encodeURIComponent(caseRef)}&limit=1`));
            let data = await response.json();

            if (data.data && data.data.length > 0) {
                console.log("SmartLink: Found match (Exact)", data.data[0].id);
                try {
                    await handleCaseClick(data.data[0]);
                } catch (err) {
                    console.error("SmartLink: handleCaseClick failed:", err);
                    alert(`Failed to open case: ${err.message}`);
                }
                return; // Done
            }

            // Strategy 2: Clean the title (Remove citations like "(435 Phil. 1)")
            const cleanedTitle = caseRef.replace(/\s*\([^)]{5,}\)$/, '').trim();
            if (cleanedTitle !== caseRef) {
                console.log("SmartLink: Strategy 2 - Cleaned title:", cleanedTitle);
                response = await fetch(apiUrl(`/api/sc_decisions?search=${encodeURIComponent(cleanedTitle)}&limit=1`));
                data = await response.json();
                if (data.data && data.data.length > 0) {
                    console.log("SmartLink: Found match (Cleaned)", data.data[0].id);
                    try {
                        await handleCaseClick(data.data[0]);
                    } catch (err) {
                        console.error("SmartLink: handleCaseClick failed:", err);
                        alert(`Failed to open case: ${err.message}`);
                    }
                    return;
                }
            }

            // Strategy 3: Extract Case Number (Broader Regex)
            const caseNoMatch = caseRef.match(/(G\.R\.|A\.M\.|A\.C\.|B\.M\.|U\.D\.K\.|Bar Matter)\s*(No\.)?\s*[\w-]+/i);
            if (caseNoMatch) {
                console.log("SmartLink: Strategy 3 - Case number:", caseNoMatch[0]);
                const retryResp = await fetch(apiUrl(`/api/sc_decisions?search=${encodeURIComponent(caseNoMatch[0])}&limit=1`));
                const retryData = await retryResp.json();
                if (retryData.data && retryData.data.length > 0) {
                    console.log("SmartLink: Found match (Case No)", retryData.data[0].id);
                    try {
                        await handleCaseClick(retryData.data[0]);
                    } catch (err) {
                        console.error("SmartLink: handleCaseClick failed:", err);
                        alert(`Failed to open case: ${err.message}`);
                    }
                    return;
                }
            }

            console.log("SmartLink: No match found.");
            alert(`Case not found: "${caseRef}"\n\nThis case may not be in the database yet.`);

        } catch (error) {
            console.error("SmartLink: Lookup failed:", error);
            alert(`Failed to search for case: ${error.message}`);
        } finally {
            clearTimeout(cursorTimeout);
            document.body.style.cursor = 'default';
            console.log("SmartLink: Handler completed");
        }
    };

    // Kept for backward compatibility if called directly, but now routed through details
    const fetchFullText = async (id) => {
        // logic defined in fetchDecisionDetails
    };





    const handleDownloadDigestPDF = async () => {
        if (!selectedDecision) return;

        const usage = await consumeFreeTierUsage({
            feature: 'case_digest_download',
            getToken,
            isSignedIn,
            canAccess,
            subscriptionLoading,
        });
        if (!usage.allowed) {
            notifyUsageBlocked(usage, openUpgradeModal, 'case_digest_download_unlimited');
            return;
        }

        const doc = new jsPDF({ format: 'a4', unit: 'mm' });
        const pageWidth = doc.internal.pageSize.getWidth();
        const pageHeight = doc.internal.pageSize.getHeight();
        const margin = 20;
        const maxLineWidth = pageWidth - margin * 2;
        let y = margin + 10;

        // Title
        doc.setFont("helvetica", "bold");
        doc.setFontSize(14);
        const titleLines = doc.splitTextToSize((selectedDecision.title || '').toUpperCase(), maxLineWidth);
        titleLines.forEach(line => {
            doc.text(line, pageWidth / 2, y, { align: "center" });
            y += 6;
        });

        // GR Number + Date
        y += 2;
        doc.setFont("helvetica", "normal");
        doc.setFontSize(11);
        doc.text(`G.R. No. ${selectedDecision.case_number || selectedDecision.gr_number} | ${formatDate(selectedDecision.date_str || selectedDecision.date)}`, pageWidth / 2, y, { align: "center" });
        y += 15;

        // Strip markdown asterisks just in case
        const stripMd = (str) => (str || '').replace(/\*/g, '').replace(/_/g, '').trim();

        const addTextSection = (title, content, isItalic = false) => {
            if (!content || !content.trim()) return;
            
            if (y > pageHeight - margin - 15) { doc.addPage(); y = margin + 10; }
            
            doc.setFont("helvetica", "bold");
            doc.setFontSize(11);
            doc.text(title, margin, y);
            y += 6;

            doc.setFont("helvetica", isItalic ? "italic" : "normal");
            doc.setFontSize(10);
            
            const cleanContent = stripMd(content);
            const splitText = doc.splitTextToSize(cleanContent, maxLineWidth);
            
            splitText.forEach(line => {
                if (y > pageHeight - margin) {
                    doc.addPage();
                    y = margin + 10;
                }
                doc.text(line, margin, y, { align: "justify", maxWidth: maxLineWidth });
                y += 5;
            });
            y += 8; // spacing after section
        };

        addTextSection("MAIN DOCTRINE", selectedDecision.main_doctrine, true);
        addTextSection("FACTS", selectedDecision.digest_facts);
        addTextSection("ISSUE(S)", selectedDecision.digest_issues);
        addTextSection("RULING", selectedDecision.digest_ruling);
        addTextSection("RATIO DECIDENDI", selectedDecision.digest_ratio);

        doc.save(`${selectedDecision.case_number || selectedDecision.gr_number}_Digest.pdf`);
    };

    const handleDownloadFullTextPDF = () => {
        if (!fullText) return;
        const doc = new jsPDF();
        const splitText = doc.splitTextToSize(fullText, 170);

        let y = 20;
        splitText.forEach(line => {
            if (y > 280) {
                doc.addPage();
                y = 20;
            }
            doc.text(line, 20, y);
            y += 5;
        });

        doc.save(`${selectedDecision.case_number}_full_text.pdf`);
    };

    return (
        <PurpleGlassAmbient showAmbient className="min-h-screen w-full min-w-0 pb-1 font-sans text-gray-900 dark:text-gray-100">
            {/* Search + optional custom filters — in-flow below xl; fixed under app header at xl+ (xl:left-52 with persistent sidebar) */}
            <div
                ref={filterChromeRef}
                className={`z-20 ${FILTER_CHROME_SURFACE} ${
                    xlFixedChrome
                        ? 'fixed left-0 right-0 top-[calc(var(--app-header-height)+env(safe-area-inset-top,0px))] xl:left-52'
                        : 'relative'
                }`}
            >
                <div className="w-full min-w-0 max-w-7xl px-3 py-2 sm:px-5 lg:px-6">
                    <div className="flex w-full min-w-0 flex-col gap-2">
                        {/* Bar Questions order: filter column first (same width md:w-44), then search */}
                        <div className="flex w-full min-w-0 max-w-full flex-col gap-2 sm:flex-row sm:flex-nowrap sm:items-center sm:gap-2">
                            <div className="flex min-w-0 shrink-0 flex-col sm:w-[min(100%,14rem)] md:w-44">
                                <button
                                    type="button"
                                    onClick={() => setShowCustomFilters((v) => !v)}
                                    className={FILTER_TOGGLE_BUTTON}
                                    aria-expanded={showCustomFilters}
                                    aria-label={showCustomFilters ? 'Hide case digest filters' : 'Show case digest filters'}
                                >
                                    <Filter className="h-3.5 w-3.5 shrink-0" aria-hidden />
                                    {showCustomFilters ? (
                                        <>
                                            <ChevronUp className="h-3.5 w-3.5 shrink-0" aria-hidden />
                                            <span className="max-sm:sr-only">Hide</span>
                                        </>
                                    ) : (
                                        <>
                                            <ChevronDown className="h-3.5 w-3.5 shrink-0" aria-hidden />
                                            <span className="max-sm:sr-only">Filters</span>
                                        </>
                                    )}
                                </button>
                            </div>
                            <div className="relative min-w-0 w-full flex-1 basis-0 sm:w-auto">
                                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-2">
                                    <Search className={FILTER_SEARCH_ICON_CLASS} strokeWidth={2} />
                                </div>
                                <input
                                    ref={searchInputRef}
                                    type="search"
                                    className={FILTER_SEARCH_INPUT}
                                    placeholder="Search cases…"
                                    value={searchTerm}
                                    onFocus={() => {
                                        clearTimeout(closeSuggestionsTimerRef.current);
                                        if (searchInputRef.current) {
                                            setSearchBoxRect(searchInputRef.current.getBoundingClientRect());
                                        }
                                        setShowSuggestions(true);
                                    }}
                                    onBlur={() => {
                                        closeSuggestionsTimerRef.current = setTimeout(
                                            () => setShowSuggestions(false),
                                            160
                                        );
                                    }}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Escape') {
                                            setShowSuggestions(false);
                                            searchInputRef.current?.blur();
                                        }
                                    }}
                                    onChange={(e) => {
                                        setSearchTerm(e.target.value);
                                        setCurrentPage(1);
                                        setShowSuggestions(true);
                                    }}
                                />
                                {loading && (
                                    <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                                        <div className="h-3.5 w-3.5 animate-spin rounded-full border-b-2 border-neutral-600 dark:border-zinc-500" />
                                    </div>
                                )}
                            </div>
                        </div>

                        {showCustomFilters && (
                            <div className={`max-h-[38vh] overflow-y-auto ${FILTER_CHROME_DIVIDER}`}>
                                <div className="grid w-full grid-cols-1 gap-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5">
                                    <div className="min-w-0 flex flex-col">
                                        <label className={FILTER_FIELD_LABEL}>Year</label>
                                        <select
                                            className={FILTER_SELECT}
                                            value={selectedYear}
                                            onChange={(e) => { setSelectedYear(e.target.value); setCurrentPage(1); }}
                                        >
                                            <option value="">All Years</option>
                                            {availableYears.map(year => (
                                                <option key={year} value={year}>{year}</option>
                                            ))}
                                        </select>
                                    </div>
                                    <div className="min-w-0 flex flex-col">
                                        <label className={FILTER_FIELD_LABEL}>Ponente</label>
                                        <select
                                            className={FILTER_SELECT}
                                            value={selectedPonente}
                                            onChange={(e) => { setSelectedPonente(e.target.value); setCurrentPage(1); }}
                                        >
                                            <option value="">All Ponentes</option>
                                            {availablePonentes.map((ponente, idx) => (
                                                <option key={idx} value={ponente}>{ponente}</option>
                                            ))}
                                        </select>
                                    </div>
                                    <div className="min-w-0 flex flex-col">
                                        <label className={FILTER_FIELD_LABEL}>Bar subject</label>
                                        <select
                                            className={FILTER_SELECT}
                                            value={selectedSubject}
                                            onChange={(e) => { setSelectedSubject(e.target.value); setCurrentPage(1); }}
                                        >
                                            <option value="" style={{ color: '#6B7280' }}>All Subjects</option>
                                            <option value="Civil Law" style={{ color: '#3B82F6', fontWeight: '600' }}>Civil Law</option>
                                            <option value="Commercial Law" style={{ color: '#06B6D4', fontWeight: '600' }}>Commercial Law</option>
                                            <option value="Criminal Law" style={{ color: '#EF4444', fontWeight: '600' }}>Criminal Law</option>
                                            <option value="Labor Law" style={{ color: '#EAB308', fontWeight: '600' }}>Labor Law</option>
                                            <option value="Legal Ethics" style={{ color: '#22C55E', fontWeight: '600' }}>Legal Ethics</option>
                                            <option value="Political Law" style={{ color: '#A855F7', fontWeight: '600' }}>Political Law</option>
                                            <option value="Remedial Law" style={{ color: '#EC4899', fontWeight: '600' }}>Remedial Law</option>
                                            <option value="Taxation Law" style={{ color: '#F97316', fontWeight: '600' }}>Taxation Law</option>
                                        </select>
                                    </div>
                                    <div className="min-w-0 flex flex-col">
                                        <label className={FILTER_FIELD_LABEL}>Significance</label>
                                        <select
                                            className={FILTER_SELECT}
                                            value={selectedSignificance}
                                            onChange={(e) => { setSelectedSignificance(e.target.value); setCurrentPage(1); }}
                                        >
                                            <option value="">All Classifications</option>
                                            <option value="NEW DOCTRINE">New Doctrine</option>
                                            <option value="REITERATION">Reiteration</option>
                                            <option value="MODIFICATION">Modification</option>
                                            <option value="CLARIFICATION">Clarification</option>
                                            <option value="ABANDONMENT">Abandonment</option>
                                            <option value="REVERSAL">Reversal</option>
                                        </select>
                                    </div>
                                    <div className="min-w-0 flex flex-col">
                                        <label className={FILTER_FIELD_LABEL}>Court body</label>
                                        <select
                                            className={FILTER_SELECT}
                                            value={selectedDivision}
                                            onChange={(e) => { setSelectedDivision(e.target.value); setCurrentPage(1); }}
                                        >
                                            <option value="">All Court Bodies</option>
                                            {availableDivisions.map((division, idx) => (
                                                <option key={idx} value={division}>{division}</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            <main
                className="w-full min-w-0 max-w-7xl px-3 pb-4 pt-3 sm:px-5 sm:pb-5 lg:px-6 xl:pt-0"
                style={xlFixedChrome ? { paddingTop: `${filterChromeHeight + 12}px` } : undefined}
            >
                {/* Status Indicator */}
                {loading && (
                    <div className="flex justify-center mb-4">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    </div>
                )}

                {fetchError && !loading && (
                    <div
                        className="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-100"
                        role="alert"
                    >
                        <p className="font-semibold">Could not load decisions</p>
                        <p className="mt-1 text-rose-800/90 dark:text-rose-200/90">{fetchError}</p>
                    </div>
                )}

                <div className="flex flex-col gap-4 lg:relative lg:min-w-0 lg:w-full lg:overflow-hidden lg:rounded-xl lg:border lg:border-lex lg:bg-white lg:p-5 lg:shadow-sm lg:dark:bg-zinc-900 lg:sm:p-6">
                <div className="pointer-events-none hidden lg:block">
                    <CardVioletInnerWash />
                </div>
                <div className="relative z-[1] flex min-w-0 flex-col gap-4 lg:gap-0">
                {hasInitialLoaded && !fetchError && (
                    <div className="max-lg:rounded-xl max-lg:border max-lg:border-lex max-lg:bg-white max-lg:p-4 max-lg:shadow-sm dark:max-lg:bg-zinc-900 sm:max-lg:p-5 lg:mb-4 lg:rounded-none lg:border-0 lg:bg-transparent lg:p-0 lg:shadow-none dark:lg:bg-transparent">
                        <p className="mb-0 text-sm leading-relaxed text-neutral-800 dark:text-zinc-200">
                            <span className="font-semibold text-black dark:text-zinc-50">Supreme Court decisions</span>{' '}
                            with structured digests generated by AI from the full decision text. Each digest extracts the{' '}
                            <span className="font-semibold text-black dark:text-zinc-50">
                                main doctrine, facts, issues, ruling, and ratio decidendi
                            </span>{' '}
                            directly from the Court's own language—no paraphrasing of holdings. Entries are tagged by Bar
                            subject and searchable by ponente, year, and significance.
                        </p>
                    </div>
                )}

                {/* Results — codal-style compact cards (two columns on md+) */}
                <div className="grid grid-cols-1 gap-2 sm:gap-3 md:grid-cols-2 md:gap-3">
                    {hasInitialLoaded && !fetchError && searchResults.length === 0 && !loading && (
                        <div className="text-center py-8 text-gray-500">
                            <FileText className="h-10 w-10 mx-auto text-gray-300 mb-2" />
                            <p>No decisions found. Adjust your search or filters.</p>
                        </div>
                    )}
                    {searchResults.map((decision) => {
                        const detailsOpen = !!caseDetailsExpandedById[decision.id];

                        let statutesParsed = null;
                        let citationsParsed = null;
                        try {
                            if (decision.statutes_involved) {
                                const st = typeof decision.statutes_involved === 'string' ? JSON.parse(decision.statutes_involved) : decision.statutes_involved;
                                if (Array.isArray(st) && st.length > 0) statutesParsed = st;
                            }
                        } catch (e) { /* ignore */ }
                        try {
                            if (decision.cited_cases) {
                                const c = typeof decision.cited_cases === 'string' ? JSON.parse(decision.cited_cases) : decision.cited_cases;
                                if (Array.isArray(c) && c.length > 0) citationsParsed = c;
                            }
                        } catch (e) { /* ignore */ }

                        const subjectKey = normalizeSubjectForColor(decision.subject || 'Political Law');
                        const subjectAccentText = getSubjectColor(subjectKey).split(/\s+/)[0];
                        const subjectSurfaceClasses = getSubjectAnswerColor(subjectKey);

                        return (
                            <div
                                key={decision.id}
                                className="group relative min-w-0 overflow-hidden rounded-lg border border-lex bg-white shadow-sm transition-shadow hover:shadow-md dark:bg-zinc-900"
                            >
                                <CardVioletInnerWash />
                                <div className="relative z-[1] min-w-0">
                                <div
                                    role="button"
                                    tabIndex={0}
                                    onClick={() => handleCaseClick(decision)}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter' || e.key === ' ') {
                                            e.preventDefault();
                                            handleCaseClick(decision);
                                        }
                                    }}
                                    onMouseEnter={() => prefetchDetails(decision.id)}
                                    onTouchStart={() => prefetchDetails(decision.id)}
                                    className="p-3 cursor-pointer hover:bg-neutral-50 dark:hover:bg-zinc-800/80 transition-colors"
                                >
                                    <div className="flex flex-col gap-2">
                                        <h3 className="text-base font-bold leading-snug text-black transition-colors group-hover:text-black dark:text-zinc-100 dark:group-hover:text-white">
                                            {(decision.short_title && decision.short_title.trim()) || (decision.title && decision.title.trim()) || decision.case_number}
                                        </h3>

                                        <p className="text-left text-[11px] font-mono text-gray-600 dark:text-gray-400 leading-snug">
                                            {decision.case_number}
                                            {decision.date_str ? (
                                                <span className="text-gray-500 dark:text-gray-500"> · {formatDate(decision.date_str)}</span>
                                            ) : null}
                                        </p>
                                    </div>
                                </div>

                                <div className="border-t border-lex">
                                    <button
                                        type="button"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            setCaseDetailsExpandedById((prev) => ({
                                                ...prev,
                                                [decision.id]: !prev[decision.id],
                                            }));
                                        }}
                                        className="w-full flex items-center justify-between gap-2 px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-600 dark:text-zinc-400 hover:bg-neutral-50 dark:hover:bg-zinc-800 transition-colors"
                                        aria-expanded={detailsOpen}
                                    >
                                        <span>Case details</span>
                                        <ChevronDown
                                            className={`w-4 h-4 text-gray-500 shrink-0 transition-transform ${detailsOpen ? 'rotate-180' : ''}`}
                                            aria-hidden
                                        />
                                    </button>
                                    {detailsOpen && (
                                        <div className="border-t border-lex px-3 pb-3">
                                            <div className="relative mt-2 overflow-hidden rounded-lg border border-lex-strong bg-neutral-50 px-3 py-2.5 dark:bg-zinc-800/90">
                                                <CardVioletInnerWash />
                                                <dl className="relative z-[1] space-y-2.5">
                                                    {decision.significance_category && (
                                                        <div className="flex gap-2.5">
                                                            <Landmark
                                                                className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400"
                                                                strokeWidth={2}
                                                                aria-hidden
                                                            />
                                                            <div className="min-w-0 flex-1">
                                                                <dt className="text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                                                                    Significance
                                                                </dt>
                                                                <dd
                                                                    className={`mt-0.5 text-[13px] font-semibold leading-snug ${getCategoryTextClass(decision.significance_category)}`}
                                                                >
                                                                    {decision.significance_category}
                                                                </dd>
                                                            </div>
                                                        </div>
                                                    )}

                                                    <div
                                                        className={`flex gap-2.5 ${decision.significance_category ? 'border-t border-lex-strong pt-2.5' : ''}`}
                                                    >
                                                        <FileText
                                                            className="mt-0.5 h-4 w-4 shrink-0 text-slate-600 dark:text-slate-400"
                                                            strokeWidth={2}
                                                            aria-hidden
                                                        />
                                                        <div className="min-w-0 flex-1">
                                                            <dt className="text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                                                                Decision / Resolution
                                                            </dt>
                                                            <dd className="mt-0.5 text-[13px] font-medium leading-snug text-gray-900 dark:text-gray-100">
                                                                {decision.document_type?.toString().trim() || '—'}
                                                            </dd>
                                                        </div>
                                                    </div>

                                                    <div
                                                        className="flex gap-2.5 border-t border-lex-strong pt-2.5"
                                                    >
                                                        <Scale
                                                            className="mt-0.5 h-4 w-4 shrink-0 text-indigo-600 dark:text-indigo-400"
                                                            strokeWidth={2}
                                                            aria-hidden
                                                        />
                                                        <div className="min-w-0 flex-1">
                                                            <dt className="text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                                                                Court body
                                                            </dt>
                                                            <dd className="mt-0.5 text-[13px] font-medium leading-snug text-gray-900 dark:text-gray-100">
                                                                {decision.division?.trim() || '—'}
                                                            </dd>
                                                        </div>
                                                    </div>

                                                    <div className="flex gap-2.5 border-t border-lex-strong pt-2.5">
                                                        <BookOpen
                                                            className="mt-0.5 h-4 w-4 shrink-0 text-neutral-600 dark:text-zinc-400"
                                                            strokeWidth={2}
                                                            aria-hidden
                                                        />
                                                        <div className="min-w-0 flex-1">
                                                            <dt className="text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                                                                Subject
                                                            </dt>
                                                            <dd className="mt-0.5 text-[13px] font-medium leading-snug text-gray-900 dark:text-gray-100">
                                                                {decision.subject?.toString().trim() || '—'}
                                                            </dd>
                                                        </div>
                                                    </div>

                                                    {decision.ponente && (
                                                        <div className="flex gap-2.5 border-t border-lex-strong pt-2.5">
                                                            <User
                                                                className="mt-0.5 h-4 w-4 shrink-0 text-sky-600 dark:text-sky-400"
                                                                strokeWidth={2}
                                                                aria-hidden
                                                            />
                                                            <div className="min-w-0 flex-1">
                                                                <dt className="text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                                                                    Ponente
                                                                </dt>
                                                                <dd className="mt-0.5 text-[13px] font-medium leading-snug text-gray-800 dark:text-gray-200">
                                                                    {decision.ponente}
                                                                </dd>
                                                            </div>
                                                        </div>
                                                    )}

                                                    {statutesParsed && (
                                                        <div className="flex gap-2.5 border-t border-lex-strong pt-2.5">
                                                            <Book
                                                                className="mt-0.5 h-4 w-4 shrink-0 text-teal-600 dark:text-teal-400"
                                                                strokeWidth={2}
                                                                aria-hidden
                                                            />
                                                            <div className="min-w-0 flex-1">
                                                                <dt className="text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                                                                    Statutes
                                                                </dt>
                                                                <dd className="mt-0.5 text-[12px] font-medium leading-snug text-teal-800 dark:text-teal-200">
                                                                    {statutesParsed.slice(0, 3).map((i) => i.law).filter(Boolean).join(', ')}
                                                                    {statutesParsed.length > 3 ? ` (+${statutesParsed.length - 3} more)` : ''}
                                                                </dd>
                                                            </div>
                                                        </div>
                                                    )}

                                                    {citationsParsed && (
                                                        <div className="flex gap-2.5 border-t border-lex-strong pt-2.5">
                                                            <Gavel
                                                                className="mt-0.5 h-4 w-4 shrink-0 text-indigo-600 dark:text-indigo-400"
                                                                strokeWidth={2}
                                                                aria-hidden
                                                            />
                                                            <div className="min-w-0 flex-1">
                                                                <dt className="text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                                                                    Citations
                                                                </dt>
                                                                <dd className="mt-0.5 text-[13px] font-medium leading-snug text-gray-900 dark:text-gray-100">
                                                                    {citationsParsed.length} cited case{citationsParsed.length === 1 ? '' : 's'}
                                                                </dd>
                                                            </div>
                                                        </div>
                                                    )}
                                                </dl>
                                            </div>
                                        </div>
                                    )}
                                </div>

                                <div
                                    role="button"
                                    tabIndex={0}
                                    onClick={() => handleCaseClick(decision)}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter' || e.key === ' ') {
                                            e.preventDefault();
                                            handleCaseClick(decision);
                                        }
                                    }}
                                    className="cursor-pointer border-t border-lex p-3 hover:bg-neutral-50 dark:hover:bg-zinc-800/60 transition-colors"
                                >
                                    <div
                                        className={`relative flex h-[15.5rem] max-sm:h-[30rem] flex-col overflow-hidden rounded-xl p-3 shadow-inner sm:p-4 ${subjectSurfaceClasses} border-l-4 border-l-current ${subjectAccentText}`}
                                    >
                                        <h4
                                            className={`mb-2 flex shrink-0 items-center gap-2 text-[11px] font-black uppercase tracking-widest sm:text-[12px] ${subjectAccentText}`}
                                        >
                                            <Lightbulb className={`h-4 w-4 shrink-0 ${subjectAccentText}`} strokeWidth={2} aria-hidden />
                                            Main doctrine
                                        </h4>
                                        <p className="pl-0.5 text-sm leading-relaxed text-gray-800 dark:text-gray-200 line-clamp-8 sm:line-clamp-9 max-sm:line-clamp-[16]">
                                            {decision.main_doctrine || decision.snippet || 'No snippet available.'}
                                        </p>
                                    </div>
                                </div>
                                </div>
                            </div>
                        );
                    })}
                </div>

                {totalCount > 0 && (
                    <div className="flex flex-col items-center gap-2 mt-8 pb-8">
                        <div className="flex justify-center items-center gap-4">
                            <button
                                onClick={() => {
                                    setCurrentPage(prev => Math.max(1, prev - 1));
                                    window.scrollTo({ top: 0, behavior: 'smooth' });
                                }}
                                disabled={currentPage === 1 || loading}
                                className="flex items-center gap-2 rounded-lg border border-lex-strong bg-white px-5 py-2.5 text-sm font-medium text-neutral-800 shadow-sm transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-zinc-900 dark:text-zinc-200 dark:hover:bg-zinc-800"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
                                Previous
                            </button>
                            <span className="text-sm text-gray-600 dark:text-gray-400 font-medium">
                                Page {currentPage} of {Math.ceil(totalCount / ITEMS_PER_PAGE) || 1}
                            </span>
                            <button
                                onClick={() => {
                                    setCurrentPage(prev => prev + 1);
                                    window.scrollTo({ top: 0, behavior: 'smooth' });
                                }}
                                disabled={currentPage * ITEMS_PER_PAGE >= totalCount || loading}
                                className="flex items-center gap-2 rounded-lg border border-lex-strong bg-white px-5 py-2.5 text-sm font-medium text-neutral-800 shadow-sm transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-zinc-900 dark:text-zinc-200 dark:hover:bg-zinc-800"
                            >
                                Next
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                            </button>
                        </div>

                    </div>
                )}
                </div>
                </div>{/* content shell */}
            </main>

            {/* Detail Modal moved to Global App.jsx Level */}

            {/* Search dropdown — portaled to body so it escapes overflow-hidden ancestors */}
            {showSuggestions && searchBoxRect && typeof document !== 'undefined' &&
                createPortal(
                    <div
                        className="fixed z-[200] max-h-80 overflow-y-auto rounded-lg border border-lex bg-white shadow-lg dark:bg-zinc-900"
                        style={{
                            top: searchBoxRect.bottom + 4,
                            left: searchBoxRect.left,
                            width: searchBoxRect.width,
                        }}
                        onMouseDown={(e) => e.preventDefault()}
                    >
                        {/* API results */}
                        <div>
                            <div className="flex items-center justify-between border-b border-lex px-3 py-1.5">
                                <span className="text-[10px] font-bold uppercase tracking-wider text-black dark:text-zinc-300">
                                    Matching cases
                                </span>
                                {searchTerm.trim().length >= 2 && !loading && (
                                    <span className="tabular-nums text-[10px] font-semibold text-gray-400">
                                        {searchResults.length} shown
                                    </span>
                                )}
                            </div>
                            {searchTerm.trim().length < 2 ? (
                                <p className="px-3 py-3 text-center text-xs text-gray-400 dark:text-gray-500">
                                    Type at least 2 characters to search.
                                </p>
                            ) : loading ? (
                                <p className="px-3 py-4 text-center text-xs text-gray-400">Loading…</p>
                            ) : searchResults.length === 0 ? (
                                <p className="px-3 py-3 text-center text-xs text-gray-400 dark:text-gray-500">
                                    No cases match on the current filters / page.
                                </p>
                            ) : (
                                <div className="divide-y divide-lex">
                                    {searchResults.map((r) => (
                                        <button
                                            key={r.id}
                                            type="button"
                                            onClick={async () => {
                                                setShowSuggestions(false);
                                                await handleCaseClick(r);
                                            }}
                                            className="flex w-full flex-col gap-0.5 px-3 py-2.5 text-left transition-colors hover:bg-neutral-100 dark:hover:bg-zinc-800"
                                        >
                                            <span className="line-clamp-2 text-sm font-semibold text-black dark:text-gray-200">
                                                <HighlightText
                                                    text={r.short_title || r.title || r.case_number}
                                                    query={searchTerm}
                                                />
                                            </span>
                                            <span className="font-mono text-xs text-gray-400 dark:text-gray-500">
                                                {r.case_number}
                                            </span>
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>,
                    document.body
                )
            }
        </PurpleGlassAmbient>
    );
};
const SeparateOpinionCard = ({ op, idx }) => {
    const [expanded, setExpanded] = useState(false);

    return (
        <div id={`sep-op-${idx}`} className="bg-gray-50 dark:bg-gray-700/30 p-4 rounded-lg border border-lex">
            <div className="flex items-center justify-between mb-2">
                <span className="font-bold text-black dark:text-gray-200 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                    {op.type ? op.type.toUpperCase() : "OPINION"}
                </span>
                <span className="text-sm font-medium text-gray-500 dark:text-gray-400">{op.justice}</span>
            </div>

            <p className="text-gray-700 dark:text-gray-300 text-sm italic border-l-2 border-gray-300 dark:border-gray-600 pl-3 mb-3">
                "{op.summary}"
            </p>

            {op.text && (
                <div>
                    {!expanded ? (
                        <button
                            onClick={() => setExpanded(true)}
                            className="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
                        >
                            Read Full Opinion <span className="text-xs">▼</span>
                        </button>
                    ) : (
                        <div className="mt-3 animate-fadeIn">
                            <div className="bg-white dark:bg-gray-800 p-4 rounded-md border border-lex-strong text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap leading-relaxed max-h-[400px] overflow-y-auto">
                                {op.text}
                            </div>
                            <button
                                onClick={() => setExpanded(false)}
                                className="mt-2 text-xs font-semibold text-gray-500 dark:text-gray-400 hover:underline"
                            >
                                Collapse Opinion ▲
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default SupremeDecisions;