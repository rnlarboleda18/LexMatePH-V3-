
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { createPortal } from 'react-dom';
import { jsPDF } from "jspdf";
import { Gavel, FileText, X, BookOpen, Clock, AlertTriangle, Lightbulb, Layers, Book, Star, Headphones, Play, Pause, Square, ListMusic, Plus, ChevronDown, User, Download, Landmark, Scale, ExternalLink, Sparkles } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { formatDate } from '../utils/dateUtils';
import { toTitleCase, normalizeDigestCitationDisplayText } from '../utils/textUtils';
import { useLexPlay } from '../features/lexplay';
import { useSubscription } from '../context/SubscriptionContext';
import DigestHtmlViewer from './DigestHtmlViewer';
import { getSubjectMainDoctrinePanelClasses } from '../utils/colors';
import { closeModalAbsorbingGhostTap } from '../utils/modalClose';
import { apiUrl } from '../utils/apiUrl';
import { consumeFreeTierUsage, notifyUsageBlocked } from '../utils/freeTierUsage';
import { CaseFullTextMarkdown, DigestMarkdownText, SmartLink } from './CaseDigestMarkdown';
import FontSizeControl from './FontSizeControl';
import { useFontSize } from '../hooks/useFontSize';
import { useFavorites } from '../hooks/useFavorites';
import CardVioletInnerWash from './CardVioletInnerWash';
import CaseDigestHistory from './CaseDigestHistory';

const formatTitleCase = (str) => {
    if (!str) return '';
    if (/[a-z]/.test(str)) {
        return str;
    }
    return str
        .toLowerCase()
        .replace(/(?:^|\s|-|\/)\S/g, (m) => m.toUpperCase());
};

// --- HELPER COMPONENTS ---

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
                        <div className="text-gray-700 dark:text-gray-300">{t.event}</div>
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
        <div className="mt-8 pt-6 border-t border-lex">
            <h4 className="text-[16px] font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <Lightbulb className="w-5 h-5 text-yellow-500 dark:text-amber-500" />
                Study Flashcards
            </h4>
            <div className="grid grid-cols-1 gap-tile md:grid-cols-3">
                {cards.map((card, idx) => (
                    <div key={idx} className="bg-yellow-50 dark:bg-yellow-900/10 border border-yellow-200 dark:border-yellow-700 p-4 rounded-lg shadow-sm hover:shadow-md transition-shadow">
                        <div className="text-xs font-bold text-yellow-700 dark:text-yellow-400 uppercase tracking-wide mb-2">{card.type}</div>
                        <div className="font-sans font-bold text-gray-800 dark:text-gray-100 mb-3">{card.q}</div>
                        <div className="text-gray-700 dark:text-gray-300 border-t border-yellow-200 dark:border-yellow-700 pt-2">{card.a}</div>
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
        <div className="mb-6 pt-6 md:pt-8 border-t border-lex dark:border-lex mt-6">
            <div className="rounded-lg border border-purple-100 bg-purple-50 p-5 dark:border-purple-900/30 dark:bg-purple-900/10">
                <h4 className="text-[16px] font-bold text-purple-800 dark:text-purple-300 flex items-center gap-2 mb-3">
                    <BookOpen className="w-5 h-5" />
                    KEY LEGAL CONCEPTS
                </h4>
                <div className="space-y-4">
                    {items.map((item, idx) => (
                        <div key={idx}>
                            <span className="font-bold text-purple-900 dark:text-purple-200 block mb-1">{item.term}</span>
                            <div className="text-gray-800 dark:text-gray-200 border-l-2 border-purple-300 dark:border-purple-600 pl-3 leading-relaxed">
                                {item.definition}
                            </div>
                        </div>
                    ))}
                </div>
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
        <section className="mb-8 pt-4 md:pt-6">
            <h4 className="text-[16px] font-bold text-gray-900 dark:text-gray-100 border-b border-lex pb-3 mb-4 uppercase tracking-wide flex items-center justify-between">
                <span className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-500" />
                    Jurisprudential Impact
                </span>
                {category && <span className={`text-[12px] px-3 py-1.5 rounded-md border text-xs ${getCategoryColor(category)} uppercase tracking-wider font-extrabold ml-2 shadow-sm`}>{category}</span>}
            </h4>
            <div className="bg-gradient-to-br from-white to-amber-50/50 dark:from-gray-800 dark:to-amber-900/10 p-5 rounded-xl border border-lex shadow-sm relative overflow-hidden">
                <div className="text-gray-800 dark:text-gray-200 leading-relaxed relative z-10">
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

// --- NEW HELPER COMPONENTS FOR STATUTES & CITATIONS ---

const StatutesSection = React.memo(({ statutes }) => {
    if (!statutes) return null;
    let items = [];
    try {
        items = typeof statutes === 'string' ? JSON.parse(statutes) : statutes;
    } catch (e) { return null; }
    if (!Array.isArray(items) || items.length === 0) return null;

    return (
        <div className="mb-8 pt-6 md:pt-8 border-t border-lex dark:border-lex mt-6">
            <h4 className="text-[16px] font-bold text-gray-900 dark:text-gray-100 border-b border-lex pb-2 mb-4 flex items-center gap-2">
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
                                <td className="px-4 py-2.5 font-semibold text-gray-800 dark:text-gray-200 align-top">
                                    {item.law || "Unknown Law"}
                                </td>
                                <td className="px-4 py-2.5 text-gray-700 dark:text-gray-300 align-top">
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

const CitedCasesSection = React.memo(({ citations }) => {
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
        <div className="mb-8 pt-6 md:pt-8 border-t border-lex dark:border-lex mt-6">
            <h4 className="text-[16px] font-bold text-gray-900 dark:text-gray-100 border-b border-lex pb-2 mb-4 flex items-center gap-2">
                <Gavel className="w-5 h-5 text-indigo-500 dark:text-indigo-400" />
                CITED JURISPRUDENCE
            </h4>
            <div className="space-y-3">
                {items.map((item, idx) => {
                    const rawTitle = item.case_title || item.title;
                    const citeTitle =
                        normalizeDigestCitationDisplayText(rawTitle || '') || rawTitle || '';
                    const citeElab = normalizeDigestCitationDisplayText(item.elaboration || '');
                    return (
                    <div key={idx} className="bg-white dark:bg-gray-800 border border-lex rounded-lg p-3 hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors shadow-sm">
                        <div className="flex justify-between items-start gap-3 mb-1">
                            <h5 className="text-[16px] font-bold text-gray-900 dark:text-white flex-grow">
                                <SmartLink text={citeTitle || '—'} plain />
                            </h5>
                            {item.type && (
                                <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wide border ${getTypeColor(item.type)} whitespace-nowrap`}>
                                    {item.type}
                                </span>
                            )}
                        </div>
                        {citeElab && (
                            <div className="text-xs text-gray-600 dark:text-gray-400 mt-1 leading-relaxed border-l-2 border-lex-strong pl-2">
                                <ReactMarkdown components={{
                                    p: ({ node, ...props }) => <p className="mb-1 last:mb-0" {...props} />,
                                    strong: ({ node, ...props }) => <strong className="font-semibold text-gray-800 dark:text-gray-300" {...props} />,
                                    em: ({ node, ...props }) => <em className="italic text-gray-700 dark:text-gray-300" {...props} />,
                                    a: ({ children, className, node: _n, href: _h, ref, ..._r }) => (
                                        <span ref={ref} className={className}>
                                            {children}
                                        </span>
                                    )
                                }}>
                                    {citeElab}
                                </ReactMarkdown>
                            </div>
                        )}
                    </div>
                );
                })}
            </div>
        </div>
    );
});

// --- MAIN MODAL COMPONENT ---

/** Matches Tailwind `md` (768px). Digest PDF preview + download are disabled below this width. */
const isMobileDigestPdfDisabled = () =>
    typeof window !== 'undefined' && window.matchMedia('(max-width: 767px)').matches;

const DIGEST_PDF_BRAND_TITLE = 'LexMatePH Case Digest';
const DIGEST_PDF_BRAND_URL = 'www.lexmateph.com';
const DIGEST_PDF_WATERMARK_PRIMARY = 'LexMatePH - Your Legal Companion';

/** Diagonal text-only watermark (draw before page body). */
function drawDigestPdfWatermark(doc) {
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const angleDeg = -32;
    const angleRad = (angleDeg * Math.PI) / 180;
    const lineGap = 3.5;
    const urlOffset = {
        x: -Math.sin(angleRad) * lineGap,
        y: Math.cos(angleRad) * lineGap,
    };

    doc.setTextColor(236, 236, 236);
    const stepX = 92;
    const stepY = 42;

    for (let row = -2; row < pageHeight / stepY + 6; row++) {
        for (let col = -1; col < pageWidth / stepX + 5; col++) {
            const stagger = (row & 1) * (stepX * 0.45);
            const x = col * stepX + stagger;
            const y = row * stepY;

            doc.setFont('helvetica', 'normal');
            doc.setFontSize(7.4);
            doc.text(DIGEST_PDF_WATERMARK_PRIMARY, x, y, { angle: angleDeg, baseline: 'middle' });

            doc.setFontSize(6.2);
            doc.text(DIGEST_PDF_BRAND_URL, x + urlOffset.x, y + urlOffset.y, {
                angle: angleDeg,
                baseline: 'middle',
            });
        }
    }
    doc.setTextColor(0, 0, 0);
}

const CaseDecisionModal = ({ decision, onClose, onCaseSelect }) => {
    const { getToken, isSignedIn, isLoaded: authLoaded } = useAuth();
    const { canAccess, openUpgradeModal, loading: subscriptionLoading, isAdmin } = useSubscription();
    const canLexPlay = canAccess('lexplay_case_digest');
    const [fullDecision, setFullDecision] = useState(decision);
    const lastSyncedCaseIdRef = useRef(decision?.id ?? null);
    const [viewMode, setViewMode] = useState('digest'); // 'digest' or 'full'
    /** Deferred flag: true only after two rAF ticks so the spinner renders before heavy MD parse. */
    const [fullTextReady, setFullTextReady] = useState(false);
    const [showPlaylistSelector, setShowPlaylistSelector] = useState(false);
    const [showHtmlViewer, setShowHtmlViewer] = useState(false);
    const [newPlaylistName, setNewPlaylistName] = useState('');
    const [isCreatingPlaylist, setIsCreatingPlaylist] = useState(false);
    const [headerCollapsed, setHeaderCollapsed] = useState(true); // metadata panel hidden until user expands (all breakpoints)
    const [headerVisible, setHeaderVisible] = useState(true);
    const lastScrollYRef = useRef(0);
    const { fontSize, increase: increaseFontSize, decrease: decreaseFontSize } = useFontSize(14);
    const canFavorite = canAccess('favorites');
    const { isFavorited, toggleFavorite } = useFavorites(
        'case',
        fullDecision?.id
    );
    const handleToggleFavorite = useCallback(() => {
        toggleFavorite(
            fullDecision?.short_title || fullDecision?.title || fullDecision?.case_number,
            fullDecision?.case_number
        );
    }, [toggleFavorite, fullDecision]);
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
            const newPlaylist = await createPlaylist(newPlaylistName.trim());
            if (newPlaylist && newPlaylist.id) {
                await handleAddToPlaylist(newPlaylist.id);
            } else {
                // Fallback: re-fetch playlists and close selector
                await fetchPlaylists();
                setNewPlaylistName('');
                setShowPlaylistSelector(false);
            }
        } catch (err) {
            console.error("Failed to create and add:", err);
            alert("Failed to create playlist or add case. Please try again.");
        } finally {
            setIsCreatingPlaylist(false);
        }
    };

    // Opened with digest-only first, then parent merges full text (same id) — keep modal in sync.
    useEffect(() => {
        if (!decision) {
            lastSyncedCaseIdRef.current = null;
            setFullDecision(null);
            return;
        }
        const id = decision.id;
        if (lastSyncedCaseIdRef.current !== id) {
            lastSyncedCaseIdRef.current = id;
            setFullDecision(decision);
            setViewMode('digest');
            setFullTextReady(false);
            return;
        }
        setFullDecision((prev) => (prev ? { ...prev, ...decision } : decision));
    }, [decision]);

    // Reveal header when switching view modes so new buttons are visible
    useEffect(() => { setHeaderVisible(true); }, [viewMode]);

    const handleContentScroll = useCallback((e) => {
        const scrollY = e.currentTarget.scrollTop;
        const delta = scrollY - lastScrollYRef.current;
        lastScrollYRef.current = scrollY;
        if (delta > 8) setHeaderVisible(false);
        else if (delta < -3) setHeaderVisible(true);
    }, []);

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
        if (showPlaylistSelector) fetchPlaylists();
    }, [showPlaylistSelector, fetchPlaylists]);

    useEffect(() => {
        const mq = window.matchMedia('(max-width: 767px)');
        const onViewportChange = () => {
            if (mq.matches) setShowHtmlViewer(false);
        };
        mq.addEventListener('change', onViewportChange);
        return () => mq.removeEventListener('change', onViewportChange);
    }, []);

    const handleClose = useCallback(
        (e) => {
            e?.preventDefault?.();
            e?.stopPropagation?.();
            closeModalAbsorbingGhostTap(onClose);
        },
        [onClose]
    );

    const handleViewHtmlViewer = async () => {
        if (!fullDecision) return;
        if (isMobileDigestPdfDisabled()) return;
        const usage = await consumeFreeTierUsage({
            feature: 'case_digest_download',
            getToken,
            isSignedIn,
            canAccess,
            subscriptionLoading,
            authLoaded,
        });
        if (!usage.allowed) {
            notifyUsageBlocked(usage, openUpgradeModal, 'case_digest_download_unlimited');
            return;
        }
        // Defer mount so the overlay paint completes before the heavy ReactMarkdown render.
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                setShowHtmlViewer(true);
            });
        });
    };

    const handleDownloadDigestPDF = async () => {
        if (!fullDecision) return;
        if (isMobileDigestPdfDisabled()) return;
        const usage = await consumeFreeTierUsage({
            feature: 'case_digest_download',
            getToken,
            isSignedIn,
            canAccess,
            subscriptionLoading,
            authLoaded,
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
        let y = margin + 5;

        drawDigestPdfWatermark(doc);

        const startPdfDigestPage = () => {
            doc.addPage();
            drawDigestPdfWatermark(doc);
            y = margin + 10;
        };

        // Branded digest header
        doc.setFont("helvetica", "bold");
        doc.setFontSize(16);
        doc.text(DIGEST_PDF_BRAND_TITLE, pageWidth / 2, y, { align: "center" });
        y += 8;
        doc.setFont("helvetica", "normal");
        doc.setFontSize(10);
        doc.text(DIGEST_PDF_BRAND_URL, pageWidth / 2, y, { align: "center" });
        y += 10;
        doc.setFont("helvetica", "bold");

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
            
            if (y > pageHeight - margin - 15) { startPdfDigestPage(); }
            
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
                    startPdfDigestPage();
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
                                startPdfDigestPage();
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

        if (secondaryRulings && secondaryRulings.length > 0) {
            const secondaryText = secondaryRulings
                .map(r => `**${r.topic || r.issue || 'Ruling'}**\n${r.ruling || r.content || ''}`)
                .filter(Boolean)
                .join("\n\n");
            if (secondaryText) {
                addTextSection("SECONDARY RULINGS", secondaryText);
            }
        }

        doc.save(`${fullDecision.case_number || fullDecision.gr_number}_Digest.pdf`);
    };

    if (!fullDecision) return null;

    let secondaryRulings = [];
    if (fullDecision && fullDecision.secondary_rulings) {
        try {
            secondaryRulings = typeof fullDecision.secondary_rulings === 'string'
                ? JSON.parse(fullDecision.secondary_rulings)
                : fullDecision.secondary_rulings;
        } catch (e) {
            console.error("Error parsing secondary_rulings:", e);
        }
    }
    if (!Array.isArray(secondaryRulings)) {
        secondaryRulings = [];
    }

    const doctrinePanel = getSubjectMainDoctrinePanelClasses(fullDecision.subject);

    const _decisionDateRaw = fullDecision.date_str || fullDecision.date;
    const decisionYear = _decisionDateRaw
        ? (() => {
              try {
                  const y = new Date(_decisionDateRaw).getFullYear();
                  return Number.isNaN(y) ? '' : y;
              } catch {
                  return '';
              }
          })()
        : '';

    let _statutesParsed = null;
    let _citationsParsed = null;
    try {
        if (fullDecision.statutes_involved) {
            const st = typeof fullDecision.statutes_involved === 'string' ? JSON.parse(fullDecision.statutes_involved) : fullDecision.statutes_involved;
            if (Array.isArray(st) && st.length > 0) _statutesParsed = st;
        }
    } catch (e) { /* ignore */ }
    try {
        if (fullDecision.cited_cases) {
            const c = typeof fullDecision.cited_cases === 'string' ? JSON.parse(fullDecision.cited_cases) : fullDecision.cited_cases;
            if (Array.isArray(c) && c.length > 0) _citationsParsed = c;
        }
    } catch (e) { /* ignore */ }

    return createPortal(
        <div
            className="lex-modal-overlay lex-modal-overlay--full-bleed fixed inset-0 z-[540] bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
            onClick={handleClose}
        >
            <div
                className="lex-modal-card relative flex w-full min-w-0 max-w-5xl flex-col overflow-hidden rounded-2xl border border-lex bg-white shadow-2xl animate-in zoom-in-95 duration-300 dark:border-lex dark:bg-zinc-900"
                role="dialog"
                aria-modal="true"
                onClick={(e) => e.stopPropagation()}
            >
                
                {/* Lightweight ambient orbs — kept small so modal opens without GPU stall */}
                <div className="pointer-events-none absolute -left-10 -top-10 h-40 w-40 rounded-full bg-blue-400/12 blur-2xl dark:bg-blue-500/10 z-0" aria-hidden />
                <div className="pointer-events-none absolute -bottom-10 -right-10 h-40 w-40 rounded-full bg-purple-400/12 blur-2xl dark:bg-purple-500/10 z-0" aria-hidden />

                {/* PLAYLIST SELECTOR OVERLAY */}
                {showPlaylistSelector && (
                    <div className="absolute inset-x-0 top-0 z-[60] max-h-[min(80dvh,100%)] overflow-y-auto lex-modal-scroll border-b border-lex bg-neutral-50 shadow-2xl animate-in slide-in-from-top duration-300 p-4 dark:border-lex dark:bg-zinc-950 sm:p-6">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-[16px] font-extrabold text-gray-900 dark:text-white flex items-center gap-2">
                                <ListMusic className="text-purple-500" />
                                ADD TO LEXPLAY PLAYLIST
                            </h3>
                            <button onClick={() => setShowPlaylistSelector(false)} className="text-gray-500 hover:text-red-500 transition-colors">
                                <X size={20} />
                            </button>
                        </div>
                        
                        <div className="grid grid-cols-1 gap-tile md:grid-cols-2">
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
                                                className="w-full text-left p-3 rounded-lg border border-lex hover:border-purple-300 dark:hover:border-purple-700 hover:bg-purple-50 dark:hover:bg-purple-900/10 transition-all flex items-center justify-between group"
                                            >
                                                <span className="font-bold text-gray-700 dark:text-gray-200">{pl.name}</span>
                                                <Plus size={16} className="text-gray-300 group-hover:text-purple-500" />
                                            </button>
                                        ))
                                    )}
                                </div>
                            </div>

                            {/* Create New */}
                            <div className="md:border-l border-t md:border-t-0 border-lex pt-4 md:pt-0 md:pl-6">
                                <h4 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-3">Create New</h4>
                                <div className="space-y-3">
                                    <input 
                                        type="text" 
                                        placeholder="Playlist Name (e.g. Remedial Law)"
                                        className="w-full p-2.5 rounded-lg border border-lex bg-gray-50 dark:bg-gray-800 text-sm focus:ring-2 focus:ring-purple-500 outline-none"
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

                {/* HEADER — auto-hides on scroll down, reveals on scroll up */}
                <div className={`overflow-hidden transition-[max-height] duration-200 ease-in-out shrink-0 ${headerVisible ? 'max-h-[500px]' : 'max-h-0'}`}>
                <div className="relative z-30 border-b border-lex bg-white dark:border-lex dark:bg-zinc-900">
                    <div className="flex h-[28px] min-w-0 items-center gap-1 px-1.5 sm:h-auto sm:gap-1.5 sm:px-2 sm:py-1 md:px-3">
                        {/* Left cluster: collapse · headphones · view toggle · SC link */}
                        <button
                            type="button"
                            className="touch-manipulation flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-gray-500 transition-all hover:bg-gray-100 hover:text-gray-800 active:scale-95 sm:h-7 sm:w-7 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-gray-100"
                            onClick={() => setHeaderCollapsed((v) => !v)}
                            title={headerCollapsed ? 'Show details' : 'Hide details'}
                            aria-label={headerCollapsed ? 'Show details' : 'Hide details'}
                            aria-expanded={!headerCollapsed}
                        >
                            <ChevronDown size={16} className={`transition-transform duration-200 ${headerCollapsed ? '' : 'rotate-180'}`} />
                        </button>
                        <button
                            type="button"
                            onClick={() => {
                                if (!canLexPlay) { openUpgradeModal('lexplay_case_digest'); return; }
                                setShowPlaylistSelector(true);
                            }}
                            className="touch-manipulation flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-purple-200/80 bg-purple-50/90 text-purple-600 transition-all hover:bg-purple-100 active:scale-95 sm:h-7 sm:w-7 dark:border-purple-800 dark:bg-purple-900/40 dark:text-purple-300 dark:hover:bg-purple-900/60"
                            title={canLexPlay ? "Add audio digest to LexPlay playlist" : "Upgrade to add case digest audio to LexPlay"}
                            aria-label="Add to LexPlay playlist"
                        >
                            <Headphones className="h-3 w-3" strokeWidth={2} />
                        </button>
                        <button
                            type="button"
                            onClick={() => {
                                if (viewMode === 'digest') {
                                    setViewMode('full');
                                    setFullTextReady(false);
                                    requestAnimationFrame(() =>
                                        requestAnimationFrame(() => setFullTextReady(true))
                                    );
                                } else {
                                    setViewMode('digest');
                                    setFullTextReady(false);
                                }
                            }}
                            className="touch-manipulation flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-lex bg-white text-gray-700 transition-all hover:bg-neutral-100 active:scale-95 sm:h-7 sm:w-7 dark:border-lex dark:bg-zinc-800 dark:text-gray-200 dark:hover:bg-zinc-700"
                            title={viewMode === 'digest' ? 'Read full text' : 'View case digest'}
                            aria-label={viewMode === 'digest' ? 'Read full text' : 'View case digest'}
                        >
                            {viewMode === 'digest' ? (
                                <BookOpen className="h-3.5 w-3.5" strokeWidth={2} />
                            ) : (
                                <FileText className="h-3.5 w-3.5" strokeWidth={2} />
                            )}
                        </button>
                        {viewMode === 'digest' && (
                            <button
                                type="button"
                                onClick={handleViewHtmlViewer}
                                className="touch-manipulation hidden md:flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-lex bg-white text-gray-600 transition-all hover:bg-neutral-100 hover:text-gray-900 active:scale-95 sm:h-7 sm:w-7 dark:border-lex dark:bg-zinc-800 dark:text-gray-300 dark:hover:bg-zinc-700"
                                title="View / download case digest PDF"
                                aria-label="View / download case digest PDF"
                            >
                                <Download className="h-3.5 w-3.5" strokeWidth={2} />
                            </button>
                        )}
                        {fullDecision?.sc_url && (
                            <a
                                href={fullDecision.sc_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="touch-manipulation flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-lex bg-white text-gray-500 transition-all hover:bg-neutral-100 hover:text-gray-800 active:scale-95 sm:h-7 sm:w-7 dark:border-lex dark:bg-zinc-800 dark:text-gray-400 dark:hover:bg-zinc-700 dark:hover:text-gray-100"
                                title="View on SC e-Library"
                                aria-label="View on SC e-Library"
                            >
                                <ExternalLink className="h-3.5 w-3.5" strokeWidth={2} />
                            </a>
                        )}

                        {/* Spacer */}
                        <div className="flex-1" />

                        {isAdmin && fullDecision.ai_model && (
                            <div className="mr-1 sm:mr-1.5 shrink-0 flex items-center">
                                <CaseDigestHistory caseId={fullDecision.id} currentModel={fullDecision.ai_model} mode="header" />
                            </div>
                        )}

                        {/* Right cluster: A-/A+ · close */}
                        {canFavorite && (
                            <button
                                type="button"
                                onClick={handleToggleFavorite}
                                className={`touch-manipulation flex h-6 w-6 shrink-0 items-center justify-center rounded-full border transition-all hover:scale-110 active:scale-95 sm:h-7 sm:w-7 ${
                                    isFavorited
                                        ? 'border-yellow-300/80 bg-yellow-50/90 text-yellow-500 dark:border-yellow-600/60 dark:bg-yellow-900/40 dark:text-yellow-400'
                                        : 'border-gray-200/80 bg-white/80 text-gray-400 hover:text-yellow-400 dark:border-zinc-700 dark:bg-zinc-800/60 dark:text-zinc-500'
                                }`}
                                title={isFavorited ? 'Remove from favorites' : 'Add to favorites'}
                                aria-label={isFavorited ? 'Remove from favorites' : 'Add to favorites'}
                            >
                                <Star
                                    className="h-3 w-3"
                                    strokeWidth={2}
                                    fill={isFavorited ? 'currentColor' : 'none'}
                                />
                            </button>
                        )}
                        <FontSizeControl fontSize={fontSize} onIncrease={increaseFontSize} onDecrease={decreaseFontSize} />
                        <button
                            type="button"
                            onClick={handleClose}
                            className="touch-manipulation flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-red-200/70 bg-red-50/80 text-red-500 transition-all hover:bg-red-100 active:scale-95 sm:h-7 sm:w-7 dark:border-red-800/60 dark:bg-red-950/40 dark:text-red-400 dark:hover:bg-red-900/50"
                            title="Close"
                            aria-label="Close"
                        >
                            <X className="h-3.5 w-3.5" strokeWidth={2.25} />
                        </button>
                    </div>

                    <div className={`border-t border-lex px-4 pt-3 pb-3 sm:px-6 sm:pt-4 sm:pb-4 ${headerCollapsed ? 'hidden' : 'block'}`}>
                        <div className="rounded-lg border border-lex bg-neutral-50 px-3 py-2.5 dark:border-lex dark:bg-zinc-800/90">
                            <dl className="grid grid-cols-2 gap-x-4 gap-y-0">
                                {/* Row 1 */}
                                <div className="col-span-2 grid grid-cols-2 gap-x-4 pb-2.5 border-b border-lex dark:border-lex">
                                    {/* Left upper: Court Body */}
                                    <div className="flex items-start gap-2">
                                        <Scale className="h-4 w-4 shrink-0 mt-0.5 text-indigo-600 dark:text-indigo-400" strokeWidth={2} aria-hidden />
                                        <div className="min-w-0">
                                            <dt className="text-[11px] font-semibold text-neutral-500 dark:text-zinc-400 uppercase tracking-wide">Court Body</dt>
                                            <dd className="text-[13px] font-semibold leading-snug text-gray-900 dark:text-gray-100 mt-0.5">
                                                {formatTitleCase(fullDecision.division?.trim()) || '—'}
                                            </dd>
                                        </div>
                                    </div>

                                    {/* Right upper: Decision / Resolution type */}
                                    <div className="flex items-start gap-2 border-l border-lex pl-4 dark:border-lex">
                                        <FileText className="h-4 w-4 shrink-0 mt-0.5 text-emerald-600 dark:text-emerald-400" strokeWidth={2} aria-hidden />
                                        <div className="min-w-0">
                                            <dt className="text-[11px] font-semibold text-neutral-500 dark:text-zinc-400 uppercase tracking-wide">Issuance</dt>
                                            <dd className="text-[13px] font-semibold leading-snug text-gray-900 dark:text-gray-100 mt-0.5">
                                                {fullDecision.document_type ? formatTitleCase(fullDecision.document_type.toString().trim()) : '—'}
                                            </dd>
                                        </div>
                                    </div>
                                </div>

                                {/* Row 2 */}
                                <div className="col-span-2 grid grid-cols-2 gap-x-4 pt-2.5 pb-2.5 border-b border-lex dark:border-lex">
                                    {/* Left lower: Ponente */}
                                    <div className="flex items-start gap-2">
                                        <User className="h-4 w-4 shrink-0 mt-0.5 text-sky-600 dark:text-sky-400" strokeWidth={2} aria-hidden />
                                        <div className="min-w-0">
                                            <dt className="text-[11px] font-semibold text-neutral-500 dark:text-zinc-400 uppercase tracking-wide">Ponente</dt>
                                            <dd className="text-[13px] font-semibold leading-snug text-gray-800 dark:text-gray-200 mt-0.5">
                                                {fullDecision.ponente ? formatTitleCase(fullDecision.ponente) : '—'}
                                            </dd>
                                        </div>
                                    </div>

                                    {/* Right lower: Significance Category */}
                                    <div className="flex items-start gap-2 border-l border-lex pl-4 dark:border-lex">
                                        <Lightbulb className="h-4 w-4 shrink-0 mt-0.5 text-amber-500 dark:text-amber-400" strokeWidth={2} aria-hidden />
                                        <div className="min-w-0">
                                            <dt className="text-[11px] font-semibold text-neutral-500 dark:text-zinc-400 uppercase tracking-wide">Significance Category</dt>
                                            <dd className={`text-[13px] font-bold leading-snug mt-0.5 ${getCategoryTextClass(fullDecision.significance_category)}`}>
                                                {formatTitleCase(fullDecision.significance_category?.toString().trim()) || 'Reiteration'}
                                            </dd>
                                        </div>
                                    </div>
                                </div>

                                {/* Row 3 */}
                                <div className="col-span-2 pt-2.5">
                                    {/* Subject */}
                                    <div className="flex items-start gap-2">
                                        <BookOpen className="h-4 w-4 shrink-0 mt-0.5 text-violet-600 dark:text-violet-400" strokeWidth={2} aria-hidden />
                                        <div className="min-w-0">
                                            <dt className="text-[11px] font-semibold text-neutral-500 dark:text-zinc-400 uppercase tracking-wide">Subject</dt>
                                            <dd className="text-[13px] font-semibold leading-snug text-gray-900 dark:text-gray-100 mt-0.5">
                                                {formatTitleCase(fullDecision.subject?.toString().trim()) || '—'}
                                            </dd>
                                        </div>
                                    </div>
                                </div>
                            </dl>
                        </div>
                    </div>
                </div>
                </div>{/* end auto-hide header wrapper */}

                {/* SCROLLABLE MAIN CONTENT */}
                <div onScroll={handleContentScroll} className="relative z-0 flex-1 min-h-0 overflow-y-auto lex-modal-scroll p-3 sm:p-6 md:p-8 custom-scrollbar bg-transparent" style={{ fontSize: `${fontSize}px` }}>

                    {viewMode === 'digest' && (
                        <div className="w-full max-w-3xl mx-auto mb-6 text-center">
                            <h2 className="text-lg sm:text-xl font-black leading-tight tracking-tight text-gray-900 dark:text-white text-balance mb-1">
                                {(fullDecision.short_title && fullDecision.short_title.trim()) || (fullDecision.title && fullDecision.title.trim()) || fullDecision.case_number}
                            </h2>
                            <p className="text-sm font-medium text-gray-500 dark:text-gray-400 leading-relaxed">
                                {fullDecision.case_number}
                                {_decisionDateRaw ? (
                                    <span> · {formatDate(_decisionDateRaw)}</span>
                                ) : null}
                            </p>
                        </div>
                    )}

                    {viewMode === 'digest' ? (
                        <>
                             {fullDecision.main_doctrine && (
                                <div className={`relative mb-6 overflow-hidden rounded-2xl border border-lex bg-gradient-to-br ${doctrinePanel.card} p-4 shadow-md sm:mb-10 dark:border-lex sm:p-6 md:p-8`}>
                                    <div className={`absolute top-0 left-0 h-full w-1.5 bg-gradient-to-b ${doctrinePanel.stripe}`}></div>
                                    <h4 className={`mb-4 flex items-center gap-2 bg-gradient-to-r ${doctrinePanel.title} bg-clip-text text-[13px] font-black uppercase tracking-widest text-transparent`}>
                                        <Lightbulb className={`h-5 w-5 drop-shadow-sm ${doctrinePanel.icon}`} />
                                        Main Doctrine
                                    </h4>
                                    <div className="text-gray-800 dark:text-gray-100 leading-relaxed font-medium">
                                        <SmartLink text={fullDecision.main_doctrine} plain />
                                    </div>
                                </div>
                            )}

                            {/* FACTS */}
                            {fullDecision.digest_facts && (
                                <section className="mb-6 sm:mb-10">
                                    <h4 className="relative mb-5 flex items-center gap-3 pb-3 font-extrabold text-gray-900 dark:text-white">
                                        <span className="rounded-xl border border-lex bg-white p-2 shadow-sm dark:border-lex dark:bg-zinc-800/90">
                                            <FileText className="w-5 h-5 text-indigo-500 dark:text-indigo-400" />
                                        </span>
                                        <span className="text-[15px] uppercase tracking-wide">Facts</span>
                                        <div className="absolute bottom-0 left-0 w-full h-px bg-gradient-to-r from-gray-300 via-gray-200 to-transparent dark:from-white/20 dark:via-white/5 dark:to-transparent"></div>
                                    </h4>
                                    <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                        <DigestMarkdownText content={fullDecision.digest_facts} variant="facts" fontSize={fontSize} />
                                    </div>
                                </section>
                            )}

                            {/* TIMELINE */}
                            <TimelineSection timeline={fullDecision.timeline} />

                            {/* ISSUE */}
                            {fullDecision.digest_issues && (
                                <section className="mb-6 sm:mb-10 pt-4 md:pt-6">
                                    <h4 className="relative mb-5 flex items-center gap-3 pb-3 font-extrabold text-gray-900 dark:text-white">
                                        <span className="rounded-xl border border-lex bg-white p-2 shadow-sm dark:border-lex dark:bg-zinc-800/90">
                                            <AlertTriangle className="w-5 h-5 text-amber-500 dark:text-amber-400" />
                                        </span>
                                        <span className="text-[15px] uppercase tracking-wide">Issue</span>
                                        <div className="absolute bottom-0 left-0 w-full h-px bg-gradient-to-r from-gray-300 via-gray-200 to-transparent dark:from-white/20 dark:via-white/5 dark:to-transparent"></div>
                                    </h4>
                                    <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                        <DigestMarkdownText content={fullDecision.digest_issues} fontSize={fontSize} />
                                    </div>
                                </section>
                            )}

                            {/* RULING */}
                            {fullDecision.digest_ruling && (
                                <section className="mb-6 sm:mb-10">
                                    <h4 className="relative mb-5 flex items-center gap-3 pb-3 font-extrabold text-gray-900 dark:text-white">
                                        <span className="rounded-xl border border-lex bg-white p-2 shadow-sm dark:border-lex dark:bg-zinc-800/90">
                                            <Gavel className="w-5 h-5 text-blue-500 dark:text-blue-400" />
                                        </span>
                                        <span className="text-[15px] uppercase tracking-wide">Ruling</span>
                                        <div className="absolute bottom-0 left-0 w-full h-px bg-gradient-to-r from-gray-300 via-gray-200 to-transparent dark:from-white/20 dark:via-white/5 dark:to-transparent"></div>
                                    </h4>
                                    <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                        <DigestMarkdownText content={fullDecision.digest_ruling} fontSize={fontSize} />
                                    </div>
                                </section>
                            )}

                            {/* RATIO DECIDENDI */}
                            {fullDecision.digest_ratio && (
                                <section className="mb-6 sm:mb-10">
                                    <h4 className="relative mb-5 flex items-center gap-3 pb-3 font-extrabold text-gray-900 dark:text-white">
                                        <span className="rounded-xl border border-lex bg-white p-2 shadow-sm dark:border-lex dark:bg-zinc-800/90">
                                            <BookOpen className="w-5 h-5 text-purple-500 dark:text-purple-400" />
                                        </span>
                                        <span className="text-[15px] uppercase tracking-wide">Ratio Decidendi</span>
                                        <div className="absolute bottom-0 left-0 w-full h-px bg-gradient-to-r from-gray-300 via-gray-200 to-transparent dark:from-white/20 dark:via-white/5 dark:to-transparent"></div>
                                    </h4>
                                    <div className="pl-6 border-l-2 border-purple-200 dark:border-purple-500/30 text-gray-700 dark:text-gray-300 leading-relaxed">
                                        <DigestMarkdownText content={formatRatioToParagraphs(fullDecision.digest_ratio)} contextRef={ratioRef} fontSize={fontSize} />
                                    </div>
                                </section>
                            )}

                            {/* SECONDARY RULINGS */}
                            {secondaryRulings && secondaryRulings.length > 0 && (
                                <section className="mb-2">
                                    <h4 className="relative mb-5 flex items-center gap-3 pb-3 font-extrabold text-gray-900 dark:text-white">
                                        <span className="rounded-xl border border-lex bg-white p-2 shadow-sm dark:border-lex dark:bg-zinc-800/90">
                                            <Layers className="w-5 h-5 text-teal-500 dark:text-teal-400" />
                                        </span>
                                        <span className="text-[15px] uppercase tracking-wide">Secondary Rulings</span>
                                        <div className="absolute bottom-0 left-0 w-full h-px bg-gradient-to-r from-gray-300 via-gray-200 to-transparent dark:from-white/20 dark:via-white/5 dark:to-transparent"></div>
                                    </h4>
                                    <div className="relative overflow-hidden rounded-xl border border-gray-100 bg-gray-50/50 px-4 pt-4 dark:border-zinc-800 dark:bg-zinc-900/30">
                                        {secondaryRulings.map((r, idx) => {
                                            if (!r || typeof r !== 'object') return null;
                                            const topic = r.topic || r.issue || 'Ruling';
                                            const rulingContent = r.ruling || r.content || '';
                                            if (!rulingContent) return null;
                                            return (
                                                <div key={idx} className={idx > 0 ? 'pt-4 mt-4' : ''}>
                                                    <h5 className="mb-2 font-bold text-gray-800 dark:text-zinc-200">
                                                        {topic}
                                                    </h5>
                                                    <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                                        <DigestMarkdownText content={rulingContent} fontSize={fontSize} />
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </section>
                            )}

                            <SignificanceSection 
                                narrative={fullDecision.digest_significance} 
                                category={fullDecision.significance_category} 
                            />

                            <StatutesSection statutes={fullDecision.statutes_involved} />
                            <CitedCasesSection citations={fullDecision.cited_cases} />

                            <LegalConceptsSection concepts={fullDecision.legal_concepts} />
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
                        // FULL TEXT VIEW — content deferred until fullTextReady to keep UI responsive
                        <div className="animate-in fade-in duration-300">
                            {!fullTextReady ? (
                                <div className="flex flex-col items-center gap-4 py-16 text-gray-500 dark:text-gray-400">
                                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-purple-300 border-t-purple-600 dark:border-purple-700 dark:border-t-purple-300" />
                                    <span className="text-sm">Loading full text…</span>
                                </div>
                            ) : (
                                <div className="prose prose-sm md:prose-base dark:prose-invert max-w-none text-justify" style={{ fontSize: `${fontSize}px` }}>
                                    <CaseFullTextMarkdown
                                        content={fullDecision.full_text_md || '*Content not available in Markdown format.*'}
                                        fontSize={fontSize}
                                    />
                                </div>
                            )}
                        </div>
                    )}

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
        <div id={`sep-op-${idx}`} className="bg-gray-50 dark:bg-gray-700/30 p-4 rounded-lg border border-lex">
            <div className="flex items-center justify-between mb-2">
                <span className="font-bold text-gray-800 dark:text-gray-200 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                    {op.type ? op.type.toUpperCase() : "OPINION"}
                </span>
                <span className="text-sm font-medium text-gray-500 dark:text-gray-400">{op.justice}</span>
            </div>

            <p className="text-gray-700 dark:text-gray-300 italic border-l-2 border-gray-300 dark:border-gray-600 pl-3 mb-3">
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
                            <div className="bg-white dark:bg-gray-800 p-4 rounded-md border border-lex-strong text-gray-800 dark:text-gray-200 whitespace-pre-wrap leading-relaxed max-h-[400px] overflow-y-auto">
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
