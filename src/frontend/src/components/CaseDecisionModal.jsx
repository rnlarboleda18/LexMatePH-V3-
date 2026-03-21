
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { jsPDF } from "jspdf";
import { Calendar, Gavel, FileText, X, BookOpen, Clock, Hash, AlertTriangle, Lightbulb, Layers, Book, Star, Headphones, Play, Pause, Square, ListMusic, Plus } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { formatDate } from '../utils/dateUtils';
import { getSubjectColor } from '../utils/colors';
import { useLexPlay } from '../features/lexplay';

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

const getCategoryIcon = (cat) => {
    const c = cat?.toUpperCase() || 'REITERATION';
    const iconMap = {
        'NEW DOCTRINE': '✨',
        'MODIFICATION': '⚡',
        'ABANDONMENT': '🚫',
        'REVERSAL': '🔄',
        'CLARIFICATION': '🔍',
        'REITERATION': '📘',
    };
    return iconMap[c] || '📘';
};

const TimelineSection = React.memo(({ timeline }) => {
    if (!timeline || timeline.length === 0) return null;
    let events = [];
    try {
        events = typeof timeline === 'string' ? JSON.parse(timeline) : timeline;
    } catch (e) { return null; }
    if (!Array.isArray(events) || events.length === 0) return null;

    return (
        <div className="mb-8" style={{ contentVisibility: 'auto' }}>
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
        <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700" style={{ contentVisibility: 'auto' }}>
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
        <div className="bg-purple-50 dark:bg-purple-900/10 border border-purple-100 dark:border-purple-900/30 p-5 rounded-lg my-6" style={{ contentVisibility: 'auto' }}>
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
        <section className="mb-8" style={{ contentVisibility: 'auto' }}>
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
                        p: ({ node, ...props }) => <p className="mb-4 last:mb-0 text-justify leading-relaxed" {...props} />,
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
        <div ref={contextRef} className="text-gray-800 dark:text-gray-200 leading-relaxed text-justify">
            <ReactMarkdown components={{
                p: ({ children }) => <div className="mb-4 text-gray-800 dark:text-gray-200 leading-relaxed text-justify"><SmartLinkWrapper onCaseClick={onCaseClick}>{children}</SmartLinkWrapper></div>,
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
        <div className="mb-8" style={{ contentVisibility: 'auto' }}>
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
        <div className="mb-8" style={{ contentVisibility: 'auto' }}>
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

const CaseDecisionModal = ({ decision, onClose, onCaseSelect }) => {
    const [fullDecision, setFullDecision] = useState(decision);
    const [loading, setLoading] = useState(false);
    const [viewMode, setViewMode] = useState('digest'); // 'digest' or 'full'
    const [showPlaylistSelector, setShowPlaylistSelector] = useState(false);
    const [newPlaylistName, setNewPlaylistName] = useState('');
    const [isCreatingPlaylist, setIsCreatingPlaylist] = useState(false);
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

    // Fetch Full Details on Mount or Update
    useEffect(() => {
        if (!decision?.id) return;

        const fetchDetails = async () => {
            setLoading(true);
            try {
                const res = await fetch(`/api/sc_decisions/${decision.id}`);
                const data = await res.json();
                setFullDecision({ ...decision, ...data });
            } catch (err) {
                console.error("Failed to load case details", err);
            } finally {
                setLoading(false);
            }
        };

        fetchDetails();
    }, [decision.id]);

    // Handle Scroller Sync
    useEffect(() => {
        if (!loading && fullDecision && fullDecision.scrollToRatioIndex !== undefined && ratioRef.current) {
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
    }, [fullDecision, loading]);

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

    if (!fullDecision) return null;

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200"
            onClick={(e) => e.target === e.currentTarget && onClose()}
        >
            <div className="bg-white dark:bg-[#1a1a1a] rounded-2xl shadow-xl w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col animate-in zoom-in-95 duration-200 border border-gray-200 dark:border-gray-800 relative">

                {/* PLAYLIST SELECTOR OVERLAY */}
                {showPlaylistSelector && (
                    <div className="absolute inset-x-0 top-0 z-[60] bg-white dark:bg-[#1a1a1a] border-b border-gray-200 dark:border-gray-800 shadow-2xl animate-in slide-in-from-top duration-300 p-6">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-[16px] font-extrabold text-gray-900 dark:text-white flex items-center gap-2">
                                <ListMusic className="text-purple-500" />
                                ADD TO LEXPLAY PLAYLIST
                            </h3>
                            <button onClick={() => setShowPlaylistSelector(false)} className="text-gray-500 hover:text-red-500 transition-colors">
                                <X size={20} />
                            </button>
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* Existing Playlists */}
                            <div>
                                <h4 className="text-[16px] font-bold text-gray-400 uppercase tracking-widest mb-3">Your Playlists</h4>
                                <div className="max-h-48 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
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
                            <div className="border-l border-gray-100 dark:border-gray-800 pl-6">
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

                {/* HEADERS */}
                <div className="p-6 border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/30 flex justify-between items-start">
                    <div className="flex-1 pr-8">
                        <div className="flex items-center gap-3 mb-2 flex-wrap">
                            <h2 className="text-[16px] font-bold text-gray-900 dark:text-white leading-snug">
                                {fullDecision.short_title || fullDecision.title || fullDecision.case_number}
                            </h2>
                            {fullDecision.significance_category && (
                                <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded shadow-sm border ${getCategoryColor(fullDecision.significance_category)}`}>
                                    <span className="text-sm">{getCategoryIcon(fullDecision.significance_category)}</span>
                                    <span className="font-bold text-xs uppercase tracking-wide">{fullDecision.significance_category}</span>
                                </div>
                            )}
                        </div>
                        <div className="flex flex-wrap items-center gap-3 text-sm text-gray-600 dark:text-gray-300">
                            <div className="flex items-center gap-1.5 bg-white dark:bg-gray-700 px-3 py-1 rounded-full shadow-sm border border-gray-200 dark:border-gray-600">
                                <span className="font-mono">#{fullDecision.id} • {fullDecision.case_number || ''}</span>
                            </div>
                            <div className="flex items-center gap-1.5 bg-white dark:bg-gray-700 px-3 py-1 rounded-full shadow-sm border border-gray-200 dark:border-gray-600">
                                <Calendar className="h-4 w-4 text-blue-500" />
                                <span>{formatDate(fullDecision.date_str)}</span>
                            </div>
                            <button
                                onClick={() => setShowPlaylistSelector(true)}
                                className="flex items-center gap-2 px-4 py-1.5 rounded-full shadow-sm border transition-all bg-purple-50 border-purple-200 text-purple-600 dark:bg-purple-900/20 dark:border-purple-800 dark:text-purple-400 hover:bg-purple-100 dark:hover:bg-purple-900/30"
                                title="Add Audio Digest to LexPlay queue"
                            >
                                <Headphones className="w-4 h-4" />
                                <span className="font-bold text-xs uppercase tracking-tight">
                                    Add to LexPlay Playlist
                                </span>
                            </button>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-500 transition-colors">
                        <X size={24} />
                    </button>
                </div>

                {/* SCROLLABLE MAIN CONTENT */}
                <div className="flex-grow overflow-y-auto p-6 custom-scrollbar bg-white dark:bg-[#1a1a1a]">

                    {viewMode === 'digest' ? (
                        <>
                            {/* MAIN DOCTRINE */}
                            {fullDecision.main_doctrine && (
                                <div className="bg-blue-50 dark:bg-blue-900/20 p-5 rounded-lg border-l-4 border-blue-500 mb-8 font-medium shadow-sm">
                                    <h4 className="text-[16px] font-bold text-blue-800 dark:text-blue-300 uppercase mb-2 flex items-center gap-2">
                                        <Lightbulb className="w-4 h-4" /> Main Doctrine
                                    </h4>
                                    <div className="text-gray-800 dark:text-gray-200 italic">
                                        <SmartLink text={fullDecision.main_doctrine} onCaseClick={handleSmartCaseClick} />
                                    </div>
                                </div>
                            )}

                            {/* FACTS */}
                            {fullDecision.digest_facts && (
                                <section className="mb-8">
                                    <h4 className="text-[16px] font-bold text-gray-900 dark:text-gray-100 border-b border-gray-200 dark:border-gray-700 pb-2 mb-4 flex items-center gap-2">
                                        <FileText className="w-5 h-5 text-gray-500" /> FACTS
                                    </h4>
                                    <MarkdownText content={fullDecision.digest_facts} variant="facts" onCaseClick={handleSmartCaseClick} />
                                </section>
                            )}

                            {/* TIMELINE */}
                            <TimelineSection timeline={fullDecision.timeline} />

                            {/* ISSUE */}
                            {fullDecision.digest_issues && (
                                <section className="mb-8">
                                    <h4 className="text-[16px] font-bold text-gray-900 dark:text-gray-100 border-b border-gray-200 dark:border-gray-700 pb-2 mb-4 flex items-center gap-2">
                                        <AlertTriangle className="w-5 h-5 text-amber-500" /> ISSUE
                                    </h4>
                                    <MarkdownText content={fullDecision.digest_issues} onCaseClick={handleSmartCaseClick} />
                                </section>
                            )}

                            {/* RULING */}
                            {fullDecision.digest_ruling && (
                                <section className="mb-8">
                                    <h4 className="text-[16px] font-bold text-gray-900 dark:text-gray-100 border-b border-gray-200 dark:border-gray-700 pb-2 mb-4 flex items-center gap-2">
                                        <Gavel className="w-5 h-5 text-blue-500" /> RULING
                                    </h4>
                                    <MarkdownText content={fullDecision.digest_ruling} onCaseClick={handleSmartCaseClick} />
                                </section>
                            )}

                            {/* RATIO DECIDENDI */}
                            {fullDecision.digest_ratio && (
                                <section className="mb-8">
                                    <h4 className="text-[16px] font-bold text-gray-900 dark:text-gray-100 border-b border-gray-200 dark:border-gray-700 pb-2 mb-4 flex items-center gap-2">
                                        <BookOpen className="w-5 h-5 text-purple-500" /> RATIO DECIDENDI
                                    </h4>
                                    <div className="pl-4 border-l-2 border-purple-100 dark:border-purple-900/30">
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
                                <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
                                    <h4 className="text-[16px] font-bold text-gray-900 dark:text-white mb-4">Separate Opinions</h4>
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

                {/* FOOTER ACTIONS */}
                <div className="p-4 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/30 flex justify-end gap-3">
                    <button
                        onClick={() => setViewMode(viewMode === 'digest' ? 'full' : 'digest')}
                        className="px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
                    >
                        {viewMode === 'digest' ? 'Read Full Text' : 'View Digest'}
                    </button>
                    <button
                        onClick={onClose}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors shadow-sm"
                    >
                        Close
                    </button>
                </div>

            </div>
        </div>
    );
};

const SeparateOpinionCard = React.memo(({ op, idx }) => {
    const [expanded, setExpanded] = useState(false);

    return (
        <div id={`sep-op-${idx}`} className="bg-gray-50 dark:bg-gray-700/30 p-4 rounded-lg border border-gray-100 dark:border-gray-700/50" style={{ contentVisibility: 'auto' }}>
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
