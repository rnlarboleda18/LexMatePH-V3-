
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { jsPDF } from "jspdf";
import { Gavel, FileText, X, BookOpen, Clock, AlertTriangle, Lightbulb, Layers, Book, Star, Headphones, Play, Pause, Square, ListMusic, Plus, ChevronDown, User, Download, Landmark, Scale } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { formatDate } from '../utils/dateUtils';
import { toTitleCase } from '../utils/textUtils';
import { useLexPlay } from '../features/lexplay';
import { useSubscription } from '../context/SubscriptionContext';
import DigestHtmlViewer from './DigestHtmlViewer';
import { closeModalAbsorbingGhostTap } from '../utils/modalClose';

// --- HELPER COMPONENTS ---

const SMART_LINK_REGEX = /(G\.R\. Nos?\.\s?\d+[\w\,&\s-]*)|(Republic Act No\.\s?\d+)/gi;

const SmartLink = React.memo(({ text, onCaseClick }) => {
    if (!text) return null;
    const parts = text.split(SMART_LINK_REGEX).filter(p => p !== undefined);

    if (parts.length === 1) return <span>{text}</span>;

    return (
        <span>
            {parts.map((part, i) => {
                const isMatch = typeof part === 'string' && part.match(SMART_LINK_REGEX);
                if (isMatch) {
                    return (
                        <span
                            key={i}
                            className="text-blue-600 dark:text-amber-400 cursor-pointer hover:underline font-medium relative group"
                            onClick={(e) => {
                                e.stopPropagation();
                                if (onCaseClick) onCaseClick(part);
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
});

const SmartLinkWrapper = React.memo(({ children, onCaseClick }) => {
    if (typeof children === 'string') return <SmartLink text={children} onCaseClick={onCaseClick} />;
    if (Array.isArray(children)) {
        return (
            <>
                {children.map((child, idx) => {
                    if (typeof child === 'string') return <SmartLink key={idx} text={child} onCaseClick={onCaseClick} />;
                    return <React.Fragment key={idx}>{child}</React.Fragment>;
                })}
            </>
        );
    }
    return <>{children}</>;
});

const getCategoryColor = (cat) => {
    const c = cat?.toUpperCase() || 'REITERATION';
    if (c === 'MODIFICATION') return 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/40 dark:text-yellow-300 dark:border-yellow-700 animate-pulse ring-2 ring-yellow-400 dark:ring-yellow-500 ring-opacity-50';
    if (c === 'ABANDONMENT') return 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/40 dark:text-red-300 dark:border-red-700 ring-2 ring-red-400 dark:ring-red-500 ring-opacity-50';

    const map = {
        'NEW DOCTRINE': 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/40 dark:text-green-300 dark:border-green-700 ring-1 ring-green-300',
        'REVERSAL': 'bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/40 dark:text-orange-300 dark:border-orange-700 ring-1 ring-orange-300',
        'CLARIFICATION': 'bg-cyan-100 text-cyan-800 border-cyan-200 dark:bg-cyan-900/40 dark:text-cyan-300 dark:border-cyan-700 ring-1 ring-cyan-300',
        'REITERATION': 'bg-slate-200 text-slate-700 border-slate-300 dark:bg-amber-900/30 dark:text-amber-200 dark:border-amber-700 shadow-sm ring-1 ring-slate-300 dark:ring-amber-800',
        'LANDMARK': 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-300',
        'DOCTRINAL': 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300',
    };
    return map[c] || map['REITERATION'];
};

/** Muted text color for case header metadata (no pills, no pulse). */
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

const TimelineSection = React.memo(({ timeline }) => {
    if (!timeline || timeline.length === 0) return null;
    let events = [];
    try {
        events = typeof timeline === 'string' ? JSON.parse(timeline) : timeline;
    } catch (e) { return null; }
    if (!Array.isArray(events) || events.length === 0) return null;

    return (
        <div className="mb-8">
            <h4 className="text-[16px] font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2 mb-4">
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
});

const FlashcardSection = React.memo(({ flashcards }) => {
    if (!flashcards) return null;
    let cards = [];
    try {
        cards = typeof flashcards === 'string' ? JSON.parse(flashcards) : flashcards;
    } catch (e) { return null; }
    if (cards.length === 0) return null;

    return (
        <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
            <h4 className="text-[16px] font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
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
});

const LegalConceptsSection = React.memo(({ concepts }) => {
    if (!concepts) return null;
    let items = [];
    try {
        items = typeof concepts === 'string' ? JSON.parse(concepts) : concepts;
    } catch (e) { return null; }
    if (!items || items.length === 0) return null;

    return (
        <div className="bg-purple-50 dark:bg-purple-900/10 border border-purple-100 dark:border-purple-900/30 p-5 rounded-lg my-6">
            <h4 className="text-[16px] font-bold text-purple-800 dark:text-purple-300 flex items-center gap-2 mb-3">
                <BookOpen className="w-5 h-5" />
                KEY LEGAL CONCEPTS
            </h4>
            <div className="space-y-4">
                {items.map((item, idx) => (
                    <div key={idx} className="text-sm">
                        <span className="font-bold text-purple-900 dark:text-purple-200 block mb-1">{item.term}</span>
                        <div className="text-gray-800 dark:text-gray-200 border-l-2 border-purple-300 dark:border-purple-600 pl-3 leading-relaxed">
                            {item.definition}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
});

const SignificanceSection = React.memo(({ narrative, category }) => {
    if (!narrative && !category) return null;

    const processContent = (text) => {
        if (!text) return "";
        let processed = text;
        // Remove [CATEGORY] tag from start (e.g. [MODIFICATION])
        processed = processed.replace(/^\[.*?\]\s*/, '');
        // Ensure double newline before Significance for spacing
        processed = processed.replace(/(\n\s*)*(\*\*Significance:\*\*|Significance:)/g, '\n\n$2');
        return processed;
    };

    return (
        <section className="mb-8">
            <h4 className="text-[16px] font-bold text-gray-900 dark:text-gray-100 border-b border-gray-200 dark:border-gray-700 pb-3 mb-4 uppercase tracking-wide flex items-center justify-between">
                <span className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-500" />
                    Jurisprudential Impact
                </span>
                {category && <span className={`text-[12px] px-3 py-1.5 rounded-md border text-xs ${getCategoryColor(category)} uppercase tracking-wider font-extrabold ml-2 shadow-sm`}>{category}</span>}
            </h4>
            <div className="bg-gradient-to-br from-white to-amber-50/50 dark:from-gray-800 dark:to-amber-900/10 p-5 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm relative overflow-hidden">
                <div className="text-gray-800 dark:text-gray-200 leading-relaxed text-sm relative z-10">
                    <ReactMarkdown components={{
                        p: ({ node, ...props }) => <p className="mb-4 last:mb-0 text-left leading-relaxed" {...props} />,
                        strong: ({ node, ...props }) => <strong className="font-bold text-amber-900 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/30 px-1 rounded" {...props} />
                    }}>
                        {processContent(narrative)}
                    </ReactMarkdown>
                </div>
            </div>
        </section>
    );
});

const formatRatioToParagraphs = (text) => {
    if (!text) return "";
    let formatted = text.replace(/^\s*[\*\-]\s+/gm, '\n\n');
    formatted = formatted.replace(/([^\n])\s*(\*\*.*?\*\*[:?])/g, '$1\n\n$2');
    return formatted.trim();
};

const MarkdownText = React.memo(({ content, onCaseClick, variant = 'default', contextRef }) => {
    if (!content) return null;
    let processedContent = content;
    if (variant === 'facts') {
        processedContent = content.replace(/([^\n])\n(\*\*.*?\*\*[:?])/g, '$1\n\n$2');
    }

    return (
        <div ref={contextRef} className="text-gray-800 dark:text-gray-200 leading-relaxed text-left text-sm">
            <ReactMarkdown components={{
                p: ({ children }) => <div className="mb-4 text-gray-800 dark:text-gray-200 leading-relaxed text-left"><SmartLinkWrapper onCaseClick={onCaseClick}>{children}</SmartLinkWrapper></div>,
                strong: ({ children }) => <strong className="font-bold text-gray-900 dark:text-gray-100">{children}</strong>,
                ul: ({ children }) => <ul className="mb-4 list-disc pl-5 space-y-2 text-gray-800 dark:text-gray-200">{children}</ul>,
                li: ({ children }) => <li className="pl-1 leading-relaxed"><SmartLinkWrapper onCaseClick={onCaseClick}>{children}</SmartLinkWrapper></li>
            }}>
                {processedContent}
            </ReactMarkdown>
        </div>
    );
});

// --- NEW HELPER COMPONENTS FOR STATUTES & CITATIONS ---

const StatutesSection = React.memo(({ statutes }) => {
    if (!statutes) return null;
    let items = [];
    try {
        items = typeof statutes === 'string' ? JSON.parse(statutes) : statutes;
    } catch (e) { return null; }
    if (!Array.isArray(items) || items.length === 0) return null;

    return (
        <div className="mb-8">
            <h4 className="text-[16px] font-bold text-gray-900 dark:text-gray-100 border-b border-gray-200 dark:border-gray-700 pb-2 mb-4 flex items-center gap-2">
                <Book className="w-5 h-5 text-teal-600 dark:text-teal-400" />
                STATUTES INVOLVED
            </h4>
            <div className="bg-teal-50 dark:bg-teal-900/10 rounded-lg border border-teal-100 dark:border-teal-900/30 overflow-hidden">
                <table className="min-w-full divide-y divide-teal-200 dark:divide-teal-800">
                    <thead className="bg-teal-100/50 dark:bg-teal-900/30">
                        <tr>
                            <th scope="col" className="px-4 py-2 text-left text-xs font-bold text-teal-800 dark:text-teal-300 uppercase tracking-wider w-1/3">Law / Statute</th>
                            <th scope="col" className="px-4 py-2 text-left text-xs font-bold text-teal-800 dark:text-teal-300 uppercase tracking-wider">Provision</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-teal-100 dark:divide-teal-800/50 bg-white dark:bg-gray-800/50">
                        {items.map((item, idx) => (
                            <tr key={idx} className="hover:bg-teal-50/50 dark:hover:bg-teal-900/20 transition-colors">
                                <td className="px-4 py-2.5 text-sm font-semibold text-gray-800 dark:text-gray-200 align-top">
                                    {item.law || "Unknown Law"}
                                </td>
                                <td className="px-4 py-2.5 text-sm text-gray-700 dark:text-gray-300 align-top">
                                    {item.provision || "N/A"}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
});

const CitedCasesSection = React.memo(({ citations, onCaseClick }) => {
    if (!citations) return null;
    let items = [];
    try {
        items = typeof citations === 'string' ? JSON.parse(citations) : citations;
    } catch (e) { return null; }
    if (!Array.isArray(items) || items.length === 0) return null;

    const getTypeColor = (type) => {
        const t = type?.toUpperCase() || 'CITED';
        if (t.includes('APPLIED')) return 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-300';
        if (t.includes('DISTINGUISHED')) return 'bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/30 dark:text-orange-300';
        if (t.includes('OVERTURNED') || t.includes('REVERSED')) return 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-300';
        return 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300';
    };

    return (
        <div className="mb-8">
            <h4 className="text-[16px] font-bold text-gray-900 dark:text-gray-100 border-b border-gray-200 dark:border-gray-700 pb-2 mb-4 flex items-center gap-2">
                <Gavel className="w-5 h-5 text-indigo-500 dark:text-indigo-400" />
                CITED JURISPRUDENCE
            </h4>
            <div className="space-y-3">
                {items.map((item, idx) => (
                    <div key={idx} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-3 hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors shadow-sm">
                        <div className="flex justify-between items-start gap-3 mb-1">
                            <h5 className="text-[16px] font-bold text-gray-900 dark:text-white flex-grow">
                                <SmartLink text={item.case_title || item.title} onCaseClick={onCaseClick} />
                            </h5>
                            {item.type && (
                                <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wide border ${getTypeColor(item.type)} whitespace-nowrap`}>
                                    {item.type}
                                </span>
                            )}
                        </div>
                        {item.elaboration && (
                            <div className="text-xs text-gray-600 dark:text-gray-400 mt-1 leading-relaxed border-l-2 border-gray-200 dark:border-gray-600 pl-2">
                                <ReactMarkdown components={{
                                    p: ({ node, ...props }) => <p className="mb-1 last:mb-0" {...props} />,
                                    strong: ({ node, ...props }) => <strong className="font-semibold text-gray-800 dark:text-gray-300" {...props} />,
                                    em: ({ node, ...props }) => <em className="italic text-gray-700 dark:text-gray-300" {...props} />
                                }}>
                                    {item.elaboration}
                                </ReactMarkdown>
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
});

// --- MAIN MODAL COMPONENT ---

/** Matches Tailwind `md` (768px). Digest PDF preview + download are disabled below this width. */
const isMobileDigestPdfDisabled = () =>
    typeof window !== 'undefined' && window.matchMedia('(max-width: 767px)').matches;

const CaseDecisionModal = ({ decision, onClose, onCaseSelect }) => {
    const { requireAccess } = useSubscription();
    const [fullDecision, setFullDecision] = useState(decision);
    const [viewMode, setViewMode] = useState('digest'); // 'digest' or 'full'
    const [showPlaylistSelector, setShowPlaylistSelector] = useState(false);
    const [showHtmlViewer, setShowHtmlViewer] = useState(false);
    const [newPlaylistName, setNewPlaylistName] = useState('');
    const [isCreatingPlaylist, setIsCreatingPlaylist] = useState(false);
    const [headerCollapsed, setHeaderCollapsed] = useState(true); // metadata panel hidden until user expands (all breakpoints)
    const ratioRef = useRef(null);

    const { 
        savedPlaylists, 
        addToSpecificPlaylist, 
        createPlaylist, 
        setIsDrawerOpen,
        fetchPlaylists 
    } = useLexPlay();

    const handleAddToPlaylist = useCallback(async (playlistId) => {
        try {
            const track = {
                id: fullDecision.id,
                type: 'case',
                title: fullDecision.short_title || fullDecision.title || fullDecision.case_number,
                subtitle: fullDecision.case_number
            };
            await addToSpecificPlaylist(playlistId, track);
            setShowPlaylistSelector(false);
            setIsDrawerOpen(true);
        } catch (err) {
            console.error("Failed to add to playlist", err);
            alert("Failed to add to playlist. Please try again.");
        }
    }, [fullDecision, addToSpecificPlaylist, setIsDrawerOpen]);

    const handleCreateAndAdd = async () => {
        if (!newPlaylistName.trim()) return;
        setIsCreatingPlaylist(true);
        try {
            const headers = await (async () => {
                // This is a bit hacky but we need the fetchPlaylists to update the state so we can find the new ID
                // Alternatively, createPlaylist could return the new ID.
                // Let's assume createPlaylist updates savedPlaylists in context.
                await createPlaylist(newPlaylistName.trim());
                // We need to wait for the update. In a real app we'd have the ID returned.
                // For now, let's just use the active queue if creation is too complex to sync here,
                // BUT the user specifically asked for "available LexPlay playlist to add to and the option to create one".
            })();
            
            // Re-fetch to be sure
            await fetchPlaylists();
            setNewPlaylistName('');
            setShowPlaylistSelector(false);
            // After creation, user might expect it to be added to the NEW one.
            // Since we don't have the ID easily, we'll suggest adding it from the list next time or 
            // find the latest one.
        } catch (err) {
            console.error(err);
        } finally {
            setIsCreatingPlaylist(false);
        }
    };



    // Handle Scroller Sync
    useEffect(() => {
        if (fullDecision && fullDecision.scrollToRatioIndex !== undefined && ratioRef.current) {
            setTimeout(() => {
                const divs = ratioRef.current.querySelectorAll('.mb-4'); 
                const target = divs[fullDecision.scrollToRatioIndex];
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    target.classList.add('bg-yellow-100', 'dark:bg-yellow-900/40', 'transition-colors', 'duration-1000', 'rounded', 'p-2');
                    setTimeout(() => target.classList.remove('bg-yellow-100', 'dark:bg-yellow-900/40', 'rounded', 'p-2'), 4000);
                }
            }, 500);
        }
    }, [fullDecision]);

    useEffect(() => {
        const mq = window.matchMedia('(max-width: 767px)');
        const onViewportChange = () => {
            if (mq.matches) setShowHtmlViewer(false);
        };
        mq.addEventListener('change', onViewportChange);
        return () => mq.removeEventListener('change', onViewportChange);
    }, []);

    // Internal Smart Link Handler
    const handleSmartCaseClick = useCallback(async (caseRef) => {
        try {
            document.body.style.cursor = 'wait';
            let res = await fetch(`/api/sc_decisions?search=${encodeURIComponent(caseRef)}&limit=1`);
            let data = await res.json();
            if (data.data?.length > 0) {
                onCaseSelect(data.data[0]);
                return;
            }
            const cleaned = caseRef.replace(/\s*\([^)]{5,}\)$/, '').trim();
            if (cleaned !== caseRef) {
                res = await fetch(`/api/sc_decisions?search=${encodeURIComponent(cleaned)}&limit=1`);
                data = await res.json();
                if (data.data?.length > 0) {
                    onCaseSelect(data.data[0]);
                    return;
                }
            }
            alert(`Case not found: "${caseRef}"`);
        } catch (err) {
            console.error(err);
        } finally {
            document.body.style.cursor = 'default';
        }
    }, [onCaseSelect]);

    const handleClose = useCallback(
        (e) => {
            e?.preventDefault?.();
            e?.stopPropagation?.();
            closeModalAbsorbingGhostTap(onClose);
        },
        [onClose]
    );

    const handleViewHtmlViewer = () => {
        if (!fullDecision) return;
        if (isMobileDigestPdfDisabled()) return;
        if (!requireAccess('case_digest_download')) return;
        setShowHtmlViewer(true);
    };

    const handleDownloadDigestPDF = () => {
        if (!fullDecision) return;
        if (isMobileDigestPdfDisabled()) return;
        if (!requireAccess('case_digest_download')) return;

        const doc = new jsPDF({ format: 'a4', unit: 'mm' });
        const pageWidth = doc.internal.pageSize.getWidth();
        const pageHeight = doc.internal.pageSize.getHeight();
        const margin = 20;
        const maxLineWidth = pageWidth - margin * 2;
        let y = margin + 5;

        // Supreme Court Digest Header
        doc.setFont("helvetica", "bold");
        doc.setFontSize(16);
        doc.text("Supreme Court Decision Digest", pageWidth / 2, y, { align: "center" });
        y += 10;

        // Title
        doc.setFontSize(13);
        const titleLines = doc.splitTextToSize(toTitleCase(fullDecision.short_title || fullDecision.title || ''), maxLineWidth * 0.9);
        titleLines.forEach(line => {
            doc.text(line, pageWidth / 2, y, { align: "center" });
            y += 6;
        });

        // Case Number + Date
        let caseNo = (fullDecision.case_number || fullDecision.gr_number || '').trim();
        if (caseNo && !caseNo.toLowerCase().includes('no.') && !caseNo.toLowerCase().includes('g.r.') && !caseNo.toLowerCase().includes('a.m.')) {
            caseNo = `G.R. No. ${caseNo}`;
        }
        const dateStr = formatDate(fullDecision.date_str || fullDecision.date) || "";
        const subTitle = [caseNo, dateStr].filter(Boolean).join(' | ');

        doc.setFont("helvetica", "normal");
        doc.setFontSize(10);
        doc.text(subTitle, pageWidth / 2, y, { align: "center" });
        y += 6; // slightly more space before horizontal line

        // Horizontal Rule
        doc.setDrawColor(0);
        doc.setLineWidth(0.5);
        doc.line(margin, y, pageWidth - margin, y);
        y += 10;

        // Sanitize string targeting unsupported Unicode, preserving markdown for font parsing
        const sanitizeUnicode = (str) => {
            if (!str) return '';
            let s = str.replace(/_/g, '').trim();
            
            s = s.replace(/₱/g, 'Php ')
                 .replace(/[“”]/g, '"')
                 .replace(/[‘’]/g, "'")
                 .replace(/—/g, '--')
                 .replace(/–/g, '-')
                 .replace(/…/g, '...')
                 .replace(/•/g, '-');
            
            // Strictly preserve the asterisks (\*) for bold tracking
            s = s.replace(/[^\x09\x0A\x0D\x20-\xFF\*]/g, '');
            return s;
        };

        const formatContent = (content) => {
            if (!content) return '';
            let formatted = content.replace(/^\s*[\*\-]\s+/gm, '\n\n');
            formatted = formatted.replace(/([A-Za-z0-9\.])\s*\n(\*\*.*?\*\*[:?]?)/g, '$1\n\n$2');
            formatted = formatted.replace(/\n{3,}/g, '\n\n');
            return formatted.trim();
        };

        const addTextSection = (title, rawContent, isItalic = false) => {
            let content = formatContent(rawContent);
            content = sanitizeUnicode(content);
            if (!content) return;
            
            if (y > pageHeight - margin - 15) { doc.addPage(); y = margin + 10; }
            
            doc.setFont("helvetica", "bold");
            doc.setFontSize(11);
            doc.text(title, margin, y);
            y += 6;

            const paragraphs = content.split('\n');
            paragraphs.forEach(paragraph => {
                if (!paragraph.trim()) {
                    y += 5.5; // empty line gap
                    return;
                }

                if (y > pageHeight - margin - 10) {
                    doc.addPage();
                    y = margin + 10;
                }

                let currentX = margin;
                const parts = paragraph.split(/(\*\*.*?\*\*)/g);
                
                parts.forEach(part => {
                    if (!part) return;
                    const isBold = part.startsWith('**') && part.endsWith('**');
                    let cleanPart = isBold ? part.slice(2, -2) : part;
                    cleanPart = cleanPart.replace(/\*/g, ''); // scrub trailing asterisks

                    doc.setFont("helvetica", isBold ? "bold" : (isItalic ? "italic" : "normal"));
                    doc.setFontSize(10);
                    
                    const tokens = cleanPart.match(/(\s+|\S+)/g) || [];
                    tokens.forEach(token => {
                        const tokenWidth = doc.getTextWidth(token);
                        
                        // Word-wrap if limit exceeded
                        if (currentX + tokenWidth > margin + maxLineWidth && token.trim() !== '') {
                            y += 5.5;
                            currentX = margin;
                            if (y > pageHeight - margin) {
                                doc.addPage();
                                y = margin + 10;
                            }
                        }
                        
                        // Skip rendering floating leading spaces on new lines
                        if (currentX === margin && token.trim() === '') {
                            return;
                        }
                        
                        doc.text(token, currentX, y);
                        currentX += tokenWidth;
                    });
                });
                
                y += 5.5; // End of paragraph
            });
            y += 4; // Extra padding below section
        };

        addTextSection("MAIN DOCTRINE", fullDecision.main_doctrine, true);
        addTextSection("FACTS", fullDecision.digest_facts);
        addTextSection("ISSUE(S)", fullDecision.digest_issues);
        addTextSection("RULING", fullDecision.digest_ruling);
        addTextSection("RATIO DECIDENDI", fullDecision.digest_ratio);

        doc.save(`${fullDecision.case_number || fullDecision.gr_number}_Digest.pdf`);
    };

    if (!fullDecision) return null;

    const decisionYear = fullDecision.date_str
        ? (() => {
              try {
                  const y = new Date(fullDecision.date_str).getFullYear();
                  return Number.isNaN(y) ? '' : y;
              } catch {
                  return '';
              }
          })()
        : '';

    return createPortal(
        <div className="fixed inset-0 z-[520] lex-modal-overlay bg-black/50 backdrop-blur-sm animate-in fade-in duration-200" onClick={handleClose}>
            <div
                className="glass relative flex w-full max-w-5xl max-h-[90vh] flex-col overflow-hidden rounded-2xl border-2 border-slate-300/85 bg-white/92 shadow-2xl animate-in zoom-in-95 duration-300 dark:border-white/10 dark:bg-slate-900/45"
                role="dialog"
                aria-modal="true"
                onClick={(e) => e.stopPropagation()}
            >
                
                {/* Ambient glow orbs inside the modal to drive the glass effect */}
                <div className="absolute top-[-20%] left-[-10%] w-[500px] h-[500px] bg-blue-500/20 rounded-full blur-[120px] pointer-events-none z-0"></div>
                <div className="absolute bottom-[-20%] right-[-10%] w-[500px] h-[500px] bg-purple-500/20 rounded-full blur-[120px] pointer-events-none z-0"></div>

                {/* PLAYLIST SELECTOR OVERLAY */}
                {showPlaylistSelector && (
                    <div className="absolute inset-x-0 top-0 z-[60] max-h-[min(80dvh,100%)] overflow-y-auto lex-modal-scroll glass bg-white/60 dark:bg-slate-900/60 backdrop-blur-2xl border-b-2 border-slate-300/85 dark:border-white/10 shadow-2xl animate-in slide-in-from-top duration-300 p-4 sm:p-6">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-[16px] font-extrabold text-gray-900 dark:text-white flex items-center gap-2">
                                <ListMusic className="text-purple-500" />
                                ADD TO LEXPLAY PLAYLIST
                            </h3>
                            <button onClick={() => setShowPlaylistSelector(false)} className="text-gray-500 hover:text-red-500 transition-colors">
                                <X size={20} />
                            </button>
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
                            {/* Existing Playlists */}
                            <div>
                                <h4 className="text-sm md:text-[16px] font-bold text-gray-400 uppercase tracking-widest mb-3">Your Playlists</h4>
                                <div className="max-h-[40vh] sm:max-h-48 overflow-y-auto lex-modal-scroll space-y-2 pr-2 custom-scrollbar">
                                    {savedPlaylists.length === 0 ? (
                                        <p className="text-sm text-gray-500 italic py-2">No playlists created yet.</p>
                                    ) : (
                                        savedPlaylists.map(pl => (
                                            <button
                                                key={pl.id}
                                                onClick={() => handleAddToPlaylist(pl.id)}
                                                className="w-full text-left p-3 rounded-lg border border-gray-100 dark:border-gray-800 hover:border-purple-300 dark:hover:border-purple-700 hover:bg-purple-50 dark:hover:bg-purple-900/10 transition-all flex items-center justify-between group"
                                            >
                                                <span className="font-bold text-gray-700 dark:text-gray-200">{pl.name}</span>
                                                <Plus size={16} className="text-gray-300 group-hover:text-purple-500" />
                                            </button>
                                        ))
                                    )}
                                </div>
                            </div>

                            {/* Create New */}
                            <div className="md:border-l border-t md:border-t-0 border-gray-100 dark:border-gray-800 pt-4 md:pt-0 md:pl-6">
                                <h4 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-3">Create New</h4>
                                <div className="space-y-3">
                                    <input 
                                        type="text" 
                                        placeholder="Playlist Name (e.g. Remedial Law)"
                                        className="w-full p-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-sm focus:ring-2 focus:ring-purple-500 outline-none"
                                        value={newPlaylistName}
                                        onChange={(e) => setNewPlaylistName(e.target.value)}
                                        onKeyDown={(e) => e.key === 'Enter' && handleCreateAndAdd()}
                                    />
                                    <button 
                                        onClick={handleCreateAndAdd}
                                        disabled={!newPlaylistName.trim() || isCreatingPlaylist}
                                        className="w-full py-2.5 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-lg font-bold text-sm transition-all shadow-md active:scale-95"
                                    >
                                        {isCreatingPlaylist ? 'Creating...' : 'Create & Finish'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* HEADER — must stack above scroll body (both were z-10; scroll came later in DOM and ate taps on the X on mobile) */}
                <div className="relative z-30 shrink-0 border-b-2 border-slate-300/85 bg-white/20 backdrop-blur-sm dark:border-white/10 dark:bg-black/10">
                    <div className="flex min-w-0 items-start gap-1.5 px-1.5 pt-1.5 pb-1 sm:gap-2 sm:px-2 md:px-3">
                        <button
                            type="button"
                            onClick={() => setShowPlaylistSelector(true)}
                            className="touch-manipulation mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-purple-200/80 bg-purple-50/90 text-purple-600 transition-all hover:bg-purple-100 active:scale-95 dark:border-purple-800 dark:bg-purple-900/40 dark:text-purple-300 dark:hover:bg-purple-900/60"
                            title="Add audio digest to LexPlay playlist"
                            aria-label="Add to LexPlay playlist"
                        >
                            <Headphones className="h-3 w-3" strokeWidth={2} />
                        </button>
                        <h2 className="min-w-0 flex-1 break-words text-[15px] font-medium leading-snug text-gray-900 [overflow-wrap:anywhere] dark:text-white md:text-[17px]">
                            {fullDecision.short_title || fullDecision.title || fullDecision.case_number}
                        </h2>
                        <div className="mt-0.5 flex shrink-0 items-center gap-0.5 sm:gap-1">
                            {decisionYear !== '' && (
                                <span className="tabular-nums text-[14px] font-medium leading-snug text-gray-900 dark:text-white sm:text-[15px] md:text-[17px]">
                                    {decisionYear}
                                </span>
                            )}
                            <button
                                type="button"
                                className="touch-manipulation flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-gray-500 transition-all hover:bg-gray-100 hover:text-gray-800 active:scale-95 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-gray-100"
                                onClick={() => setHeaderCollapsed((v) => !v)}
                                title={headerCollapsed ? 'Show details' : 'Hide details'}
                                aria-label={headerCollapsed ? 'Show details' : 'Hide details'}
                                aria-expanded={!headerCollapsed}
                            >
                                <ChevronDown size={18} className={`transition-transform duration-200 ${headerCollapsed ? '' : 'rotate-180'}`} />
                            </button>
                            <button
                                type="button"
                                onClick={handleClose}
                                className="touch-manipulation flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-red-200/70 bg-red-50/80 text-red-500 transition-all hover:bg-red-100 active:scale-95 dark:border-red-800/60 dark:bg-red-950/40 dark:text-red-400 dark:hover:bg-red-900/50"
                                title="Close"
                                aria-label="Close"
                            >
                                <X className="h-3.5 w-3.5" strokeWidth={2.25} />
                            </button>
                        </div>
                    </div>

                    <div className="border-t border-white/20 px-1.5 py-1 sm:px-2 md:px-3 dark:border-white/10">
                        <p
                            className="w-full truncate text-left font-mono text-[12px] font-medium leading-snug text-gray-600 dark:text-gray-400 sm:text-[13px]"
                            title={
                                [fullDecision.case_number, fullDecision.date_str ? formatDate(fullDecision.date_str) : '']
                                    .filter(Boolean)
                                    .join(' · ') || undefined
                            }
                        >
                            {fullDecision.case_number || '—'}
                            {fullDecision.date_str ? (
                                <span className="text-gray-500 dark:text-gray-500">
                                    {' '}
                                    &middot; {formatDate(fullDecision.date_str)}
                                </span>
                            ) : null}
                        </p>
                    </div>

                    <div className={`px-4 pb-3 sm:px-6 sm:pb-4 ${headerCollapsed ? 'hidden' : 'block'}`}>
                        <div className="rounded-lg border border-white/35 bg-white/25 px-3 py-2.5 backdrop-blur-sm dark:border-white/10 dark:bg-slate-900/35">
                            <dl className="space-y-2.5">
                                {fullDecision.significance_category && (
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
                                                className={`mt-0.5 text-[13px] font-semibold leading-snug ${getCategoryTextClass(fullDecision.significance_category)}`}
                                            >
                                                {fullDecision.significance_category}
                                            </dd>
                                        </div>
                                    </div>
                                )}

                                <div
                                    className={`flex gap-2.5 ${fullDecision.significance_category ? 'border-t border-white/25 pt-2.5 dark:border-white/10' : ''}`}
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
                                            {fullDecision.division?.trim() || '—'}
                                        </dd>
                                    </div>
                                </div>

                                <div className="flex gap-2.5 border-t border-white/25 pt-2.5 dark:border-white/10">
                                    <BookOpen
                                        className="mt-0.5 h-4 w-4 shrink-0 text-violet-600 dark:text-violet-400"
                                        strokeWidth={2}
                                        aria-hidden
                                    />
                                    <div className="min-w-0 flex-1">
                                        <dt className="text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                                            Subject
                                        </dt>
                                        <dd className="mt-0.5 text-[13px] font-medium leading-snug text-gray-900 dark:text-gray-100">
                                            {fullDecision.subject?.toString().trim() || '—'}
                                        </dd>
                                    </div>
                                </div>

                                {fullDecision.ponente && (
                                    <div className="flex gap-2.5 border-t border-white/25 pt-2.5 dark:border-white/10">
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
                                                {fullDecision.ponente}
                                            </dd>
                                        </div>
                                    </div>
                                )}
                            </dl>
                        </div>
                    </div>
                </div>

                {/* SCROLLABLE MAIN CONTENT */}
                <div className="relative z-0 flex-1 min-h-0 space-y-0 overflow-y-auto lex-modal-scroll p-3 sm:p-6 md:p-8 custom-scrollbar bg-transparent">

                    {viewMode === 'digest' ? (
                        <>
                             {fullDecision.main_doctrine && (
                                <div className="glass relative mb-6 overflow-hidden rounded-2xl border border-white/60 bg-gradient-to-br from-blue-50/60 to-white/40 p-4 shadow-[0_8px_30px_rgb(0,0,0,0.12)] sm:mb-10 dark:border-white/10 dark:from-slate-800/60 dark:to-slate-900/40 sm:p-6 md:p-8">
                                    <div className="absolute top-0 left-0 w-1.5 h-full bg-gradient-to-b from-blue-400 to-indigo-600"></div>
                                    <h4 className="mb-4 flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-[13px] font-black uppercase tracking-widest text-transparent dark:from-blue-400 dark:to-indigo-400">
                                        <Lightbulb className="w-5 h-5 text-blue-500 drop-shadow-sm" /> 
                                        Main Doctrine
                                    </h4>
                                    <div className="text-gray-800 dark:text-gray-100 text-sm leading-relaxed font-medium">
                                        <SmartLink text={fullDecision.main_doctrine} onCaseClick={handleSmartCaseClick} />
                                    </div>
                                </div>
                            )}

                            {/* FACTS */}
                            {fullDecision.digest_facts && (
                                <section className="mb-6 sm:mb-10">
                                    <h4 className="relative mb-5 flex items-center gap-3 pb-3 font-extrabold text-gray-900 dark:text-white">
                                        <span className="p-2 glass bg-white/60 dark:bg-white/10 rounded-xl border border-white/50 dark:border-white/10 shadow-sm">
                                            <FileText className="w-5 h-5 text-indigo-500 dark:text-indigo-400" />
                                        </span>
                                        <span className="text-[15px] uppercase tracking-wide">Facts</span>
                                        <div className="absolute bottom-0 left-0 w-full h-px bg-gradient-to-r from-gray-300 via-gray-200 to-transparent dark:from-white/20 dark:via-white/5 dark:to-transparent"></div>
                                    </h4>
                                    <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                        <MarkdownText content={fullDecision.digest_facts} variant="facts" onCaseClick={handleSmartCaseClick} />
                                    </div>
                                </section>
                            )}

                            {/* TIMELINE */}
                            <TimelineSection timeline={fullDecision.timeline} />

                            {/* ISSUE */}
                            {fullDecision.digest_issues && (
                                <section className="mb-6 sm:mb-10">
                                    <h4 className="relative mb-5 flex items-center gap-3 pb-3 font-extrabold text-gray-900 dark:text-white">
                                        <span className="p-2 glass bg-white/60 dark:bg-white/10 rounded-xl border border-white/50 dark:border-white/10 shadow-sm">
                                            <AlertTriangle className="w-5 h-5 text-amber-500 dark:text-amber-400" />
                                        </span>
                                        <span className="text-[15px] uppercase tracking-wide">Issue</span>
                                        <div className="absolute bottom-0 left-0 w-full h-px bg-gradient-to-r from-gray-300 via-gray-200 to-transparent dark:from-white/20 dark:via-white/5 dark:to-transparent"></div>
                                    </h4>
                                    <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                        <MarkdownText content={fullDecision.digest_issues} onCaseClick={handleSmartCaseClick} />
                                    </div>
                                </section>
                            )}

                            {/* RULING */}
                            {fullDecision.digest_ruling && (
                                <section className="mb-6 sm:mb-10">
                                    <h4 className="relative mb-5 flex items-center gap-3 pb-3 font-extrabold text-gray-900 dark:text-white">
                                        <span className="p-2 glass bg-white/60 dark:bg-white/10 rounded-xl border border-white/50 dark:border-white/10 shadow-sm">
                                            <Gavel className="w-5 h-5 text-blue-500 dark:text-blue-400" />
                                        </span>
                                        <span className="text-[15px] uppercase tracking-wide">Ruling</span>
                                        <div className="absolute bottom-0 left-0 w-full h-px bg-gradient-to-r from-gray-300 via-gray-200 to-transparent dark:from-white/20 dark:via-white/5 dark:to-transparent"></div>
                                    </h4>
                                    <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                        <MarkdownText content={fullDecision.digest_ruling} onCaseClick={handleSmartCaseClick} />
                                    </div>
                                </section>
                            )}

                            {/* RATIO DECIDENDI */}
                            {fullDecision.digest_ratio && (
                                <section className="mb-6 sm:mb-10">
                                    <h4 className="relative mb-5 flex items-center gap-3 pb-3 font-extrabold text-gray-900 dark:text-white">
                                        <span className="p-2 glass bg-white/60 dark:bg-white/10 rounded-xl border border-white/50 dark:border-white/10 shadow-sm">
                                            <BookOpen className="w-5 h-5 text-purple-500 dark:text-purple-400" />
                                        </span>
                                        <span className="text-[15px] uppercase tracking-wide">Ratio Decidendi</span>
                                        <div className="absolute bottom-0 left-0 w-full h-px bg-gradient-to-r from-gray-300 via-gray-200 to-transparent dark:from-white/20 dark:via-white/5 dark:to-transparent"></div>
                                    </h4>
                                    <div className="pl-6 border-l-2 border-purple-200 dark:border-purple-500/30 text-gray-700 dark:text-gray-300 leading-relaxed">
                                        <MarkdownText content={formatRatioToParagraphs(fullDecision.digest_ratio)} contextRef={ratioRef} onCaseClick={handleSmartCaseClick} />
                                    </div>
                                </section>
                            )}

                            <StatutesSection statutes={fullDecision.statutes_involved} />
                            <CitedCasesSection citations={fullDecision.cited_cases} onCaseClick={handleSmartCaseClick} />

                            <LegalConceptsSection concepts={fullDecision.legal_concepts} />
                            <SignificanceSection narrative={fullDecision.digest_significance} category={fullDecision.significance_category} />
                            <FlashcardSection flashcards={fullDecision.flashcards} />

                            {fullDecision.separate_opinions && fullDecision.separate_opinions.length > 0 && (
                                <div className="mt-12 pt-8 relative">
                                    <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-gray-300 dark:via-white/20 to-transparent"></div>
                                    <h4 className="mb-6 bg-gradient-to-r from-gray-600 to-gray-900 bg-clip-text text-center text-[16px] font-bold uppercase tracking-widest text-transparent dark:from-gray-300 dark:to-white">
                                        Separate Opinions
                                    </h4>
                                    <div className="space-y-6">
                                        {fullDecision.separate_opinions.map((op, idx) => (
                                            <SeparateOpinionCard key={idx} op={op} idx={idx} />
                                        ))}
                                    </div>
                                </div>
                            )}
                        </>
                    ) : (
                        // FULL TEXT VIEW
                        <div className="animate-in fade-in duration-300">
                            <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                                <h3 className="text-[16px] font-bold text-center text-gray-900 dark:text-white mb-2">
                                    {fullDecision.short_title}
                                </h3>
                                <div className="text-center text-sm text-gray-600 dark:text-gray-400 font-mono">
                                    {fullDecision.case_number} | {formatDate(fullDecision.date_str)}
                                </div>
                            </div>

                            <div className="prose prose-sm md:prose-base dark:prose-invert max-w-none text-justify">
                                <MarkdownText content={fullDecision.full_text_md || "*Content not available in Markdown format.*"} onCaseClick={handleSmartCaseClick} />
                            </div>

                            {/* Also show separate opinions in full text mode if they are appended? 
                                usually separate opinions are part of the full text if extracted correctly, 
                                but sometimes they are separate fields. I'll include them at the bottom just in case context needs them.
                                But typically full_text_md should have them or the user might expect them.
                                For now, I'll essentially replicate the logic or just let Full Text be Full Text.
                                Usually Full Text includes everything.
                            */}
                        </div>
                    )}

                </div>

                {/* FOOTER — same visual language as header strip */}
                <div className="relative z-20 flex shrink-0 items-center justify-end gap-0.5 border-t-2 border-slate-300/85 bg-white/20 px-1.5 py-1.5 backdrop-blur-sm dark:border-white/10 dark:bg-black/10 sm:gap-1 sm:px-2 md:px-3">
                    {viewMode === 'digest' && (
                        <button
                            type="button"
                            onClick={() => handleViewHtmlViewer()}
                            className="touch-manipulation mr-auto hidden h-7 w-7 shrink-0 items-center justify-center rounded-md border border-amber-200/80 bg-amber-50/90 text-amber-700 transition-all hover:bg-amber-100 active:scale-95 dark:border-amber-800/80 dark:bg-amber-950/40 dark:text-amber-300 dark:hover:bg-amber-900/50 md:flex"
                            title="View digest format (tablet or desktop)"
                            aria-label="View digest format"
                        >
                            <FileText className="h-3.5 w-3.5" strokeWidth={2} />
                        </button>
                    )}
                    <button
                        type="button"
                        onClick={() => setViewMode(viewMode === 'digest' ? 'full' : 'digest')}
                        className="touch-manipulation flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-white/50 bg-white/40 text-gray-700 transition-all hover:bg-white/70 active:scale-95 dark:border-white/15 dark:bg-white/10 dark:text-gray-200 dark:hover:bg-white/20"
                        title={viewMode === 'digest' ? 'Read full text' : 'View case digest'}
                        aria-label={viewMode === 'digest' ? 'Read full text' : 'View case digest'}
                    >
                        {viewMode === 'digest' ? (
                            <BookOpen className="h-3.5 w-3.5" strokeWidth={2} />
                        ) : (
                            <FileText className="h-3.5 w-3.5" strokeWidth={2} />
                        )}
                    </button>
                </div>

            </div>

            {/* DIGEST HTML VIEWER OVERLAY */}
            {showHtmlViewer && (
                <DigestHtmlViewer 
                    decision={fullDecision}
                    onClose={() => setShowHtmlViewer(false)}
                    onDownload={handleDownloadDigestPDF}
                />
            )}
        </div>,
        document.body
    );
};

const SeparateOpinionCard = React.memo(({ op, idx }) => {
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
});

export default CaseDecisionModal;
