import React, { useState, useEffect, useRef } from 'react';
import { jsPDF } from "jspdf";
import { Search, Calendar, Gavel, FileText, X, Filter, BookOpen, Clock, Hash, AlertTriangle, Lightbulb, Layers, Book, Star, Zap } from 'lucide-react';




import { formatDate } from '../utils/dateUtils';
import { getSubjectColor, getSubjectAnswerColor } from '../utils/colors';
import ReactMarkdown from 'react-markdown';

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

// Helper to normalize subject string to a valid color key
const normalizeSubjectForColor = (subject) => {
    if (!subject) return 'Political Law'; // Default
    let s = subject.toString();

    // If matches "Primary: X; Secondary: Y", extract just "X"
    // Regex: look for Primary: until semicolon or end of string
    const primaryMatch = s.match(/Primary:\s*([^;]+)/i);
    if (primaryMatch) {
        s = primaryMatch[1];
    }

    if (s.includes("Political") || s.includes("Constitutional") || s.includes("Admin") || s.includes("Election") || s.includes("Public Corp")) return "Political Law";
    if (s.includes("Labor")) return "Labor Law";
    if (s.includes("Civil") || s.includes("Family") || s.includes("Property") || s.includes("Succession") || s.includes("Obligations")) return "Civil Law";
    if (s.includes("Taxation") || s.includes("Tax")) return "Taxation Law";
    if (s.includes("Commercial") || s.includes("Mercantile") || s.includes("Corporate") || s.includes("Insurance") || s.includes("Transportation")) return "Commercial Law";
    if (s.includes("Criminal")) return "Criminal Law";
    if (s.includes("Remedial") || s.includes("Procedure") || s.includes("Evidence")) return "Remedial Law";
    if (s.includes("Ethics") || s.includes("Legal Ethics") || s.includes("Judicial")) return "Legal Ethics";

    // Fallback logic if still effectively 'Political' but might be something else? 
    // Actually the original fallback was Political Law.
    return "Political Law";
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
                            {header && <strong className="font-bold text-gray-900 dark:text-gray-100 mr-1">{header}</strong>}
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
            <h4 className="text-md font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2 mb-4">
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
        <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
            <h4 className="text-lg font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <Lightbulb className="w-5 h-5 text-yellow-500 dark:text-amber-500" />
                Study Flashcards
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {cards.map((card, idx) => (
                    <div key={idx} className="bg-yellow-50 dark:bg-yellow-900/10 border border-yellow-200 dark:border-yellow-700 p-4 rounded-lg shadow-sm hover:shadow-md transition-shadow">
                        <div className="text-xs font-bold text-yellow-700 dark:text-yellow-400 uppercase tracking-wide mb-2">{card.type}</div>
                        <div className="font-sans font-bold text-gray-800 dark:text-gray-100 mb-3">{card.q}</div>
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

// Icon mapping for significance categories
const getCategoryIcon = (cat) => {
    const c = cat?.toUpperCase() || 'REITERATION';
    const iconMap = {
        'NEW DOCTRINE': '✨', // Sparkles for new
        'MODIFICATION': '⚡', // Lightning for change with pulse
        'ABANDONMENT': '🚫', // Prohibited for abandoning doctrine
        'REVERSAL': '🔄', // Reverse arrows for reversal
        'CLARIFICATION': '🔍', // Magnifying glass for clarifying
        'REITERATION': '📘', // Book for repeating established doctrine
    };
    return iconMap[c] || '📘';
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
            <h4 className="text-md font-bold text-gray-900 dark:text-gray-100 border-b border-gray-200 dark:border-gray-700 pb-3 mb-4 uppercase tracking-wide flex items-center justify-between">
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

            <div className="bg-gradient-to-br from-white to-amber-50/50 dark:from-gray-800 dark:to-amber-900/10 p-5 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm relative overflow-hidden">
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
        strong: ({ children }) => <strong className="font-bold text-gray-900 dark:text-gray-100">{children}</strong>,
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
    const [searchTerm, setSearchTerm] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [selectedDecision, setSelectedDecision] = useState(null);
    const [viewMode, setViewMode] = useState('digest'); // 'digest' or 'full'
    const [fullText, setFullText] = useState(null);
    const [fullTextHtml, setFullTextHtml] = useState(null);
    const [loadingFullText, setLoadingFullText] = useState(false);
    const [showMockExam, setShowMockExam] = useState(false);
    const [mockExamQuestions, setMockExamQuestions] = useState(null);
    const [loadingMockExam, setLoadingMockExam] = useState(false);

    // Filter states
    const [showMobileFilters, setShowMobileFilters] = useState(false);
    const [selectedYear, setSelectedYear] = useState('');
    const [selectedMonth, setSelectedMonth] = useState('');
    const [selectedPonente, setSelectedPonente] = useState('');
    const [selectedSubject, setSelectedSubject] = useState('');
    const [selectedDivision, setSelectedDivision] = useState('');
    const [selectedSignificance, setSelectedSignificance] = useState('');

    const [isDoctrinal, setIsDoctrinal] = useState(false);

    // Pagination
    const [currentPage, setCurrentPage] = useState(1);
    const [totalCount, setTotalCount] = useState(0);
    const [debugUrl, setDebugUrl] = useState('');
    const ITEMS_PER_PAGE = 20;

    // Available options
    const [availableYears, setAvailableYears] = useState([]);
    const [availablePonentes, setAvailablePonentes] = useState([]);
    const [availableDivisions, setAvailableDivisions] = useState([]);


    useEffect(() => {
        fetchAvailableFilters();
        fetchPonentes();
        fetchDivisions();

    }, []);

    // AbortController Ref
    const abortControllerRef = useRef(null);
    // Track active request ID to manage loading state safely
    const activeRequestRef = useRef(0);

    // Debounced Search Effect
    useEffect(() => {
        // Cancel previous request if it exists
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        const delayDebounceFn = setTimeout(() => {
            fetchDecisions();
        }, 300); // 300ms delay for snappier live search

        return () => {
            clearTimeout(delayDebounceFn);
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
            // SAFETY: Force loading false on unmount/cleanup to prevent stuck spinners
            setLoading(false);
        };
    }, [searchTerm, selectedYear, selectedPonente, selectedSubject, selectedDivision, selectedSignificance, isDoctrinal, currentPage]);

    // Sync external case selection from App.jsx
    useEffect(() => {
        if (externalSelectedCase && externalSelectedCase.id !== selectedDecision?.id) {
            handleCaseClick(externalSelectedCase);
        }
    }, [externalSelectedCase]);


    const fetchPonentes = async () => {
        try {
            const response = await fetch('/api/sc_decisions/ponentes');
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
            const response = await fetch('/api/sc_decisions/divisions');
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
        try {
            let query = `/api/sc_decisions?search=${encodeURIComponent(searchTerm)}&page=${currentPage}&limit=${ITEMS_PER_PAGE}`;
            if (selectedYear) query += `&year=${selectedYear}`;
            if (selectedMonth) query += `&month=${selectedMonth}`;
            if (selectedPonente) query += `&ponente=${encodeURIComponent(selectedPonente)}`;
            if (selectedSubject) query += `&subject=${encodeURIComponent(selectedSubject)}`;
            if (selectedDivision) query += `&division=${encodeURIComponent(selectedDivision)}`;
            if (selectedSignificance) query += `&significance=${encodeURIComponent(selectedSignificance)}`;

            if (isDoctrinal) query += `&doctrinal=true`;

            setDebugUrl(query);

            const response = await fetch(query, { signal });
            const data = await response.json();

            if (signal.aborted) return; // Double check

            if (data.error) {
                console.error("Backend Error:", data.error);
                // Only alert if it's the latest request
                if (requestId === activeRequestRef.current) {
                    alert(`Backend Error: ${data.error}`);
                    setSearchResults([]);
                }
                return;
            }

            // Only update state if this is still the active request
            if (requestId === activeRequestRef.current) {
                setSearchResults(data.data || []);
                setTotalCount(parseInt(data.total, 10) || 0);
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('Search aborted');
                return;
            }
            console.error("Search failed", error);
        } finally {
            // Turn off loading ONLY if we are the latest request
            // This prevents "zombie" loading states from aborted requests
            // while preserving loading state if a newer request has started
            if (requestId === activeRequestRef.current) {
                setLoading(false);
            }
        }
    };


    const [loadingDetails, setLoadingDetails] = useState(false);

    const fetchDecisionDetails = async (id, currentDecision) => {
        setLoadingDetails(true);
        try {
            const response = await fetch(`/api/sc_decisions/${id}`);
            const data = await response.json();

            // Merge current lightweight decision with full details
            const fullDecision = { ...currentDecision, ...data };
            setSelectedDecision(fullDecision);

            if (data.full_text_html) setFullTextHtml(data.full_text_html);
            if (data.full_text_md) setFullText(data.full_text_md);

        } catch (error) {
            console.error("Failed to fetch details", error);
        } finally {
            setLoadingDetails(false);
        }
    };

    const handleCaseClick = async (decision) => {
        // Delegate to parent (App.jsx) which handles the Global Modal
        if (onCaseSelect) {
            onCaseSelect(decision);
        } else {
            // Fallback (shouldn't happen in new architecture)
            setSelectedDecision(decision);
        }
    };

    const handleViewFullText = async (e, decision) => {
        e.stopPropagation();
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
            let response = await fetch(`/api/sc_decisions?search=${encodeURIComponent(caseRef)}&limit=1`);
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
                response = await fetch(`/api/sc_decisions?search=${encodeURIComponent(cleanedTitle)}&limit=1`);
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
                const retryResp = await fetch(`/api/sc_decisions?search=${encodeURIComponent(caseNoMatch[0])}&limit=1`);
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





    const handleDownloadDigestPDF = () => {
        if (!selectedDecision) return;
        const doc = new jsPDF();

        doc.setFontSize(16);
        doc.text("Supreme Court Decision Digest", 105, 20, null, null, "center");

        doc.setFontSize(12);
        doc.setFont(undefined, 'bold');
        doc.text(selectedDecision.title, 105, 30, null, null, "center");

        doc.setFont(undefined, 'normal');
        doc.setFontSize(10);
        doc.text(`G.R. No. ${selectedDecision.case_number} | ${formatDate(selectedDecision.date_str)}`, 105, 40, null, null, "center");

        let y = 50;
        const addSection = (title, content) => {
            if (!content) return;
            if (y > 270) { doc.addPage(); y = 20; }
            doc.setFont(undefined, 'bold');
            doc.text(title, 20, y);
            y += 7;
            doc.setFont(undefined, 'normal');
            const splitText = doc.splitTextToSize(content, 170);
            doc.text(splitText, 20, y);
            y += splitText.length * 5 + 10;
        };

        addSection("FACTS", selectedDecision.digest_facts);
        addSection("ISSUE", selectedDecision.digest_issues);
        addSection("RULING", selectedDecision.digest_ruling);
        addSection("RATIO DECIDENDI", selectedDecision.digest_ratio);

        doc.save(`${selectedDecision.case_number}_digest.pdf`);
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
        <div className="min-h-screen bg-transparent text-gray-900 dark:text-gray-100 font-sans">
            {/* Header */}
            <header className="glass bg-white/40 dark:bg-slate-900/40 backdrop-blur-xl shadow-sm sticky top-0 z-10 border-b border-white/20 dark:border-white/10">
                <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <Gavel className="h-8 w-8 text-blue-600 dark:text-blue-400" />
                        <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">
                            Supreme Court Decisions
                        </h1>
                    </div>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
                {/* Search & Filter Section */}
                <div className="glass bg-white/40 dark:bg-slate-900/40 backdrop-blur-xl rounded-xl shadow-[0_30px_60px_-10px_rgba(0,0,0,0.3)] p-6 mb-8 border border-white/40 dark:border-white/10">
                    <div className="space-y-4">
                        {/* Main Search Input */}
                        <div className="relative">
                            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                <Search className="h-5 w-5 text-gray-400" />
                            </div>
                            <input
                                type="text"
                                className="block w-full pl-10 pr-10 py-3 border border-stone-400 dark:border-gray-600 shadow-sm rounded-lg leading-5 bg-gray-50 dark:bg-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-amber-500 sm:text-base dark:text-white transition-colors"
                                placeholder="Start typing to search cases..."
                                value={searchTerm}
                                onFocus={() => {
                                    // Auto-reset filters for global search experience
                                    setSelectedYear('');
                                    setSelectedMonth('');
                                    setSelectedPonente('');
                                    setSelectedSubject('');
                                    setSelectedSubject('');
                                    setSelectedDivision('');
                                    setSelectedSignificance('');
                                    setSelectedModel('');
                                    // Optional: Keep isDoctrinal or reset it? 
                                    // "Automatically set the year filter to 'all years' for global search"
                                    // implies resetting restrictive filters.
                                }}
                                onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
                            />
                            {loading && (
                                <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                                </div>
                            )}
                        </div>

                        {/* Mobile Filter Toggle */}
                        <div className="md:hidden">
                            <button
                                onClick={() => setShowMobileFilters(!showMobileFilters)}
                                className="w-full flex items-center justify-center gap-2 py-2 px-4 border border-white/40 dark:border-white/10 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-200 glass bg-white/40 dark:bg-slate-800/40 hover:bg-white/60 dark:hover:bg-slate-700/60 transition-colors shadow-sm"
                            >
                                <Filter className="h-4 w-4" />
                                {showMobileFilters ? "Hide Filters" : "Filter Results"}
                            </button>
                        </div>

                        {/* Filters Grid */}
                        <div className={`grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 ${showMobileFilters ? 'grid' : 'hidden md:grid'}`}>
                            {/* Year Filter */}
                            <div className="relative">
                                <label className="block text-xs font-medium text-gray-500 mb-1">Year</label>
                                <select
                                    className="block w-full pl-3 pr-8 py-2 text-sm border border-stone-400 dark:border-gray-600 shadow-sm focus:outline-none focus:ring-amber-500 focus:border-amber-500 rounded-md dark:bg-gray-900 dark:text-white"
                                    value={selectedYear}
                                    onChange={(e) => { setSelectedYear(e.target.value); setCurrentPage(1); }}
                                >
                                    <option value="">All Years</option>
                                    {availableYears.map(year => (
                                        <option key={year} value={year}>{year}</option>
                                    ))}
                                </select>
                            </div>

                            {/* Ponente Filter */}
                            <div className="relative">
                                <label className="block text-xs font-medium text-gray-500 mb-1">Ponente</label>
                                <select
                                    className="block w-full pl-3 pr-8 py-2 text-sm border border-stone-400 dark:border-gray-600 shadow-sm focus:outline-none focus:ring-amber-500 focus:border-amber-500 rounded-md dark:bg-gray-900 dark:text-white"
                                    value={selectedPonente}
                                    onChange={(e) => { setSelectedPonente(e.target.value); setCurrentPage(1); }}
                                >
                                    <option value="">All Ponentes</option>
                                    {availablePonentes.map((ponente, idx) => (
                                        <option key={idx} value={ponente}>{ponente}</option>
                                    ))}
                                </select>
                            </div>

                            {/* Subject Filter */}
                            <div className="relative">
                                <label className="block text-xs font-medium text-gray-500 mb-1">Bar Subject</label>
                                <select
                                    className="block w-full pl-3 pr-8 py-2 text-sm border border-stone-400 dark:border-gray-600 shadow-sm focus:outline-none focus:ring-amber-500 focus:border-amber-500 rounded-md dark:bg-gray-900 dark:text-white"
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

                            {/* Significance Filter */}
                            <div className="relative">
                                <label className="block text-xs font-medium text-gray-500 mb-1">Significance</label>
                                <select
                                    className="block w-full pl-3 pr-8 py-2 text-sm border border-stone-400 dark:border-gray-600 shadow-sm focus:outline-none focus:ring-amber-500 focus:border-amber-500 rounded-md dark:bg-gray-900 dark:text-white"
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

                            {/* Division Filter */}
                            <div className="relative">
                                <label className="block text-xs font-medium text-gray-500 mb-1">Court Body</label>
                                <select
                                    className="block w-full pl-3 pr-8 py-2 text-sm border border-stone-400 dark:border-gray-600 shadow-sm focus:outline-none focus:ring-amber-500 focus:border-amber-500 rounded-md dark:bg-gray-900 dark:text-white"
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
                </div>

                {/* Status Indicator */}
                {loading && (
                    <div className="flex justify-center mb-6">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    </div>
                )}

                {/* Results Section - Stacked List */}
                <div className="flex flex-col space-y-4">
                    {searchResults.length === 0 && !loading && (
                        <div className="text-center py-10 text-gray-500">
                            <FileText className="h-12 w-12 mx-auto text-gray-300 mb-2" />
                            <p>No decisions found. Adjust your search or filters.</p>
                        </div>
                    )}
                    {searchResults.map((decision) => (
                        <div
                            key={decision.id}
                            onClick={() => handleCaseClick(decision)}
                            className="glass bg-white/60 dark:bg-slate-800/40 backdrop-blur-md rounded-xl shadow-[0_4px_20px_rgba(0,0,0,0.15)] border border-white/40 dark:border-white/10 p-6 cursor-pointer transition-all hover:shadow-[0_8px_30px_rgba(0,0,0,0.2)] hover:border-amber-300 dark:hover:border-amber-700 hover:bg-white/80 dark:hover:bg-slate-700/60 group relative"
                        >
                            <div className="flex justify-between items-start gap-4 mb-4">
                                <div className="flex-grow">
                                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                                        <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 leading-snug group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                                            {(decision.short_title && decision.short_title.trim()) || (decision.title && decision.title.trim()) || decision.case_number}
                                        </h3>
                                        {decision.significance_category && (
                                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide ${getCategoryColor(decision.significance_category)} flex items-center gap-1`}>
                                                <span>{getCategoryIcon(decision.significance_category)}</span>
                                                <span>{decision.significance_category}</span>
                                            </span>
                                        )}
                                        {decision.document_type && (
                                            <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 border border-gray-300 dark:border-gray-600">
                                                {decision.document_type}
                                            </span>
                                        )}
                                    </div>
                                    <div className="flex flex-wrap items-center gap-2 mb-3">
                                        <span className="font-mono text-xs bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded text-gray-700 dark:text-gray-300">
                                            #{decision.id} • {decision.case_number}
                                        </span>
                                        <span className="text-xs text-gray-500">•</span>
                                        <span className="text-sm text-gray-600 dark:text-gray-400 font-medium">
                                            {formatDate(decision.date_str)}
                                        </span>
                                        {decision.ponente && (
                                            <>
                                                <span className="text-xs text-gray-500">•</span>
                                                <span className="text-xs bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-2 py-1 rounded-full italic">
                                                    {decision.ponente}
                                                </span>
                                            </>
                                        )}
                                        {decision.subject && (() => {
                                            const s = decision.subject.toString();
                                            // Check for "Primary: X; Secondary: Y" pattern
                                            const complexMatch = s.match(/Primary:\s*([^;]+)(;\s*Secondary:\s*(.*))?/i);

                                            if (complexMatch) {
                                                const primaryRaw = complexMatch[1].trim();
                                                const secondaryRaw = complexMatch[3] ? complexMatch[3].trim() : null;

                                                // Function to render a styled subject span
                                                const renderSubject = (subj) => {
                                                    const norm = normalizeSubjectForColor(subj);
                                                    const colorClass = getSubjectColor(norm); // Text color class
                                                    return <span className={`${colorClass} font-bold`}>{subj}</span>;
                                                };

                                                return (
                                                    <>
                                                        <span className="text-xs text-gray-500">•</span>
                                                        <span className="text-xs px-3 py-1 rounded-full font-medium border bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700">
                                                            <span className="text-gray-500 dark:text-gray-400">Primary: </span>
                                                            {renderSubject(primaryRaw)}
                                                            {secondaryRaw && (
                                                                <>
                                                                    <span className="text-gray-400 mx-1">; </span>
                                                                    <span className="text-gray-500 dark:text-gray-400">Secondary: </span>
                                                                    {/* Split secondary items if they are comma separated? Or just render whole block colored based on first? 
                                                                        User said "secondary colors font should as well follow their respective colors".
                                                                        So we should split secondary by comma.
                                                                    */}
                                                                    {secondaryRaw.split(',').map((sec, idx) => (
                                                                        <React.Fragment key={idx}>
                                                                            {idx > 0 && <span className="text-gray-400 mr-1">,</span>}
                                                                            {renderSubject(sec.trim())}
                                                                        </React.Fragment>
                                                                    ))}
                                                                </>
                                                            )}
                                                        </span>
                                                    </>
                                                );
                                            }

                                            // Fallback for simple subjects (no Primary/Secondary prefix)
                                            const normalizedSubject = normalizeSubjectForColor(decision.subject);
                                            const bgClass = getSubjectAnswerColor(normalizedSubject);
                                            const textClass = getSubjectColor(normalizedSubject);

                                            return (
                                                <>
                                                    <span className="text-xs text-gray-500">•</span>
                                                    <span className={`text-xs ${bgClass} ${textClass} px-2 py-1 rounded-full font-medium border`}>
                                                        {decision.subject}
                                                    </span>
                                                </>
                                            );
                                        })()}
                                        {decision.division && (
                                            <>
                                                <span className="text-xs text-gray-500">•</span>
                                                <span className="text-xs bg-orange-50 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 px-2 py-1 rounded-full">
                                                    {decision.division}
                                                </span>
                                            </>
                                        )}
                                    </div>
                                    {/* Statutes & Citations Summary Code */}
                                    {(decision.statutes_involved || decision.cited_cases) && (
                                        <div className="flex flex-wrap gap-3 mb-3 text-xs">
                                            {/* Statutes Summary */}
                                            {decision.statutes_involved && (() => {
                                                try {
                                                    const s = typeof decision.statutes_involved === 'string' ? JSON.parse(decision.statutes_involved) : decision.statutes_involved;
                                                    if (Array.isArray(s) && s.length > 0) {
                                                        const count = s.length;
                                                        const top2 = s.slice(0, 2).map(i => i.law).join(", ");
                                                        return (
                                                            <div className="flex items-center gap-1.5 text-teal-700 dark:text-teal-400 bg-teal-50 dark:bg-teal-900/20 px-2 py-1 rounded border border-teal-100 dark:border-teal-800">
                                                                <Book className="w-3 h-3" />
                                                                <span className="font-semibold">{count} Statutes:</span>
                                                                <span className="truncate max-w-[200px]">{top2}{count > 2 ? '...' : ''}</span>
                                                            </div>
                                                        );
                                                    }
                                                } catch (e) { return null; }
                                            })()}

                                            {/* Citations Summary */}
                                            {decision.cited_cases && (() => {
                                                try {
                                                    const c = typeof decision.cited_cases === 'string' ? JSON.parse(decision.cited_cases) : decision.cited_cases;
                                                    if (Array.isArray(c) && c.length > 0) {
                                                        return (
                                                            <div className="flex items-center gap-1.5 text-indigo-700 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/20 px-2 py-1 rounded border border-indigo-100 dark:border-indigo-800">
                                                                <Gavel className="w-3 h-3" />
                                                                <span className="font-semibold">{c.length} Citations</span>
                                                            </div>
                                                        );
                                                    }
                                                } catch (e) { return null; }
                                            })()}
                                        </div>
                                    )}

                                    {/* Main Doctrine / Snippet Display */}
                                    {(() => {
                                        const subject = decision.subject || 'Political Law';
                                        const normalizedSubject = normalizeSubjectForColor(subject);
                                        const bgClass = getSubjectAnswerColor(normalizedSubject);
                                        const textClass = getSubjectColor(normalizedSubject);

                                        return (
                                            <div className={`mb-4 ${bgClass} rounded-lg p-3 border-l-4 ${textClass} border-l-current border-t-0 border-r-0 border-b-0`}>
                                                {(decision.main_doctrine || decision.snippet) && (
                                                    <div className={`text-xs font-bold ${textClass} uppercase tracking-wider mb-1`}>
                                                        Main Doctrine
                                                    </div>
                                                )}
                                                <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-3 leading-relaxed">
                                                    {decision.main_doctrine || decision.snippet || "No snippet available."}
                                                </p>
                                            </div>
                                        );
                                    })()}

                                    {/* Action Button */}
                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={(e) => handleViewFullText(e, decision)}
                                            className="inline-flex items-center px-3 py-1.5 border border-blue-600 text-blue-600 dark:text-blue-400 dark:border-blue-400 text-xs font-semibold rounded hover:bg-blue-50 dark:hover:bg-blue-900/40 transition-colors z-10"
                                        >
                                            <BookOpen className="w-3 h-3 mr-1" />
                                            View Full Text
                                        </button>
                                    </div>
                                </div>
                                {/* Optional: Chevron or Icon to indicate clickability */}
                                <div className="hidden sm:block text-gray-300 dark:text-gray-600 group-hover:text-blue-400 dark:group-hover:text-blue-500 transition-colors self-center">
                                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                                </div>
                            </div>
                        </div>
                    ))}
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
                                className="px-5 py-2.5 glass bg-white/40 dark:bg-slate-700/40 backdrop-blur-sm border border-white/20 dark:border-white/5 rounded-lg shadow-sm text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-white/60 dark:hover:bg-slate-600/60 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
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
                                className="px-5 py-2.5 glass bg-white/40 dark:bg-slate-700/40 backdrop-blur-sm border border-white/20 dark:border-white/5 rounded-lg shadow-sm text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-white/60 dark:hover:bg-slate-600/60 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                            >
                                Next
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                            </button>
                        </div>

                    </div>
                )}
            </main>

            {/* Detail Modal moved to Global App.jsx Level */}
        </div>
    );
};
const SeparateOpinionCard = ({ op, idx }) => {
    const [expanded, setExpanded] = useState(false);

    return (
        <div id={`sep-op-${idx}`} className="bg-gray-50 dark:bg-gray-700/30 p-4 rounded-lg border border-gray-100 dark:border-gray-700/50">
            <div className="flex items-center justify-between mb-2">
                <span className="font-bold text-gray-800 dark:text-gray-200 flex items-center gap-2">
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
                            <div className="bg-white dark:bg-gray-800 p-4 rounded-md border border-gray-200 dark:border-gray-600 text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap leading-relaxed max-h-[400px] overflow-y-auto">
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
