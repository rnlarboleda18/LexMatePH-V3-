import React, { useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { X, Headphones, ListMusic, Plus, ChevronLeft, ChevronRight } from 'lucide-react';
import { getSubjectColor } from '../utils/colors';
import { HighlightText } from '../utils/highlight';
import { useLexPlay } from '../features/lexplay';
import { useSubscription } from '../context/SubscriptionContext';
import { closeModalAbsorbingGhostTap } from '../utils/modalClose';

const QuestionDetailModal = ({ 
    question, 
    onClose, 
    onNext, 
    onPrev, 
    hasNext, 
    hasPrev, 
    searchQuery 
}) => {
    if (!question) return null;

    const colorClass = getSubjectColor(question.subject);
    const textColor = colorClass.split(' ').find(c => c.startsWith('text-'));

    const [showPlaylistSelector, setShowPlaylistSelector] = useState(false);
    const [newPlaylistName, setNewPlaylistName] = useState('');
    const [isCreatingPlaylist, setIsCreatingPlaylist] = useState(false);

    const { 
        savedPlaylists, 
        addToSpecificPlaylist, 
        createPlaylist, 
        setIsDrawerOpen,
        fetchPlaylists 
    } = useLexPlay();

    const { canAccess, openUpgradeModal } = useSubscription();
    const canLexPlay = canAccess('lexplay_bar');

    const handleAddToPlaylist = useCallback(async (playlistId) => {
        try {
            const track = {
                id: question.id,
                type: 'question',
                title: `${question.year} Bar Question`,
                subtitle: question.subject
            };
            await addToSpecificPlaylist(playlistId, track);
            setShowPlaylistSelector(false);
            setIsDrawerOpen(true);
        } catch (err) {
            console.error("Failed to add to playlist", err);
            alert("Failed to add to playlist. Please try again.");
        }
    }, [question, addToSpecificPlaylist, setIsDrawerOpen]);

    const handleCreateAndAdd = async () => {
        if (!newPlaylistName.trim()) return;
        setIsCreatingPlaylist(true);
        try {
            const newPlaylist = await createPlaylist(newPlaylistName.trim());
            if (newPlaylist && newPlaylist.id) {
                await handleAddToPlaylist(newPlaylist.id);
            } else {
                // If for some reason we don't get the ID back immediately
                await fetchPlaylists();
                setNewPlaylistName('');
                setShowPlaylistSelector(false);
            }
        } catch (err) {
            console.error("Failed to create and add:", err);
            alert("Failed to create playlist or add question. Please try again.");
        } finally {
            setIsCreatingPlaylist(false);
        }
    };

    const handleClose = useCallback(
        (e) => {
            e?.preventDefault?.();
            e?.stopPropagation?.();
            closeModalAbsorbingGhostTap(onClose);
        },
        [onClose]
    );

    return createPortal(
        <div className="fixed inset-0 z-[540] lex-modal-overlay bg-black/60 backdrop-blur-md animate-in fade-in duration-200" onClick={handleClose}>
            <div
                className="lex-modal-card glass relative flex max-w-5xl flex-col overflow-hidden rounded-2xl border-2 border-slate-300/85 bg-white/92 shadow-2xl animate-in zoom-in-95 duration-300 dark:border-white/10 dark:bg-slate-900/45"
                role="dialog"
                aria-modal="true"
                onClick={(e) => e.stopPropagation()}
            >
                
                {/* Ambient glow orbs inside the modal to drive the glass effect */}
                <div className="absolute top-[-20%] left-[-10%] w-[400px] h-[400px] bg-blue-500/10 rounded-full blur-[100px] pointer-events-none z-0"></div>
                <div className="absolute bottom-[-20%] right-[-10%] w-[400px] h-[400px] bg-purple-500/10 rounded-full blur-[100px] pointer-events-none z-0"></div>
                
                {/* Header: headphones + subject left · prev/next centered · year + close right */}
                <div className="relative z-10 grid shrink-0 grid-cols-[1fr_auto_1fr] items-center gap-1 border-b-2 border-slate-300/85 bg-white/25 px-1.5 py-1.5 backdrop-blur-sm dark:border-white/10 dark:bg-black/15 sm:px-2 md:px-3">
                    <div className="flex min-w-0 items-center gap-1.5 sm:gap-2">
                        <button
                            type="button"
                            onClick={() => {
                                if (!canLexPlay) { openUpgradeModal('lexplay_bar'); return; }
                                setShowPlaylistSelector(true);
                            }}
                            className="touch-manipulation flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-purple-200/80 bg-purple-50/90 text-purple-600 transition-all hover:bg-purple-100 active:scale-95 dark:border-purple-800 dark:bg-purple-900/40 dark:text-purple-300 dark:hover:bg-purple-900/60"
                            title={canLexPlay ? "Add question audio to LexPlay playlist" : "Upgrade to add bar question audio to LexPlay"}
                            aria-label="Add to LexPlay playlist"
                        >
                            <Headphones className="h-3 w-3" strokeWidth={2} />
                        </button>
                        <span className={`min-w-0 truncate text-[15px] font-medium leading-snug md:text-[17px] ${textColor}`}>
                            {question.subject}
                        </span>
                    </div>
                    <div className="flex justify-center justify-self-center">
                        <div className="flex items-center gap-1.5">
                            <button
                                type="button"
                                onClick={onPrev}
                                disabled={!hasPrev}
                                className="touch-manipulation flex h-8 items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-[11px] font-bold text-slate-600 shadow-sm transition-all hover:border-slate-400 hover:bg-slate-50 hover:text-slate-900 active:scale-95 disabled:pointer-events-none disabled:opacity-30 dark:border-white/15 dark:bg-white/8 dark:text-white/70 dark:hover:border-white/25 dark:hover:bg-white/12 dark:hover:text-white"
                                title="Previous question"
                                aria-label="Previous question"
                            >
                                <ChevronLeft className="h-4 w-4 shrink-0" strokeWidth={2.5} />
                                <span className="hidden sm:inline">Prev</span>
                            </button>
                            <button
                                type="button"
                                onClick={onNext}
                                disabled={!hasNext}
                                className="touch-manipulation flex h-8 items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-[11px] font-bold text-slate-600 shadow-sm transition-all hover:border-slate-400 hover:bg-slate-50 hover:text-slate-900 active:scale-95 disabled:pointer-events-none disabled:opacity-30 dark:border-white/15 dark:bg-white/8 dark:text-white/70 dark:hover:border-white/25 dark:hover:bg-white/12 dark:hover:text-white"
                                title="Next question"
                                aria-label="Next question"
                            >
                                <span className="hidden sm:inline">Next</span>
                                <ChevronRight className="h-4 w-4 shrink-0" strokeWidth={2.5} />
                            </button>
                        </div>
                    </div>
                    <div className="flex items-center justify-end gap-1.5 sm:gap-2">
                        <span className="shrink-0 tabular-nums text-[15px] font-medium leading-snug text-gray-900 dark:text-white md:text-[17px]">
                            {question.year}
                        </span>
                        <button
                            type="button"
                            onClick={handleClose}
                            className="touch-manipulation flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-red-200/70 bg-red-50/80 text-red-500 transition-all hover:bg-red-100 active:scale-95 dark:border-red-800/60 dark:bg-red-950/40 dark:text-red-400 dark:hover:bg-red-900/50"
                            aria-label="Close"
                        >
                            <X className="h-3.5 w-3.5" strokeWidth={2.25} />
                        </button>
                    </div>
                </div>

                {/* PLAYLIST SELECTOR OVERLAY */}
                {showPlaylistSelector && (
                    <div className="absolute inset-x-0 top-0 z-[60] max-h-[min(75dvh,100%)] overflow-y-auto lex-modal-scroll bg-white dark:bg-dark-card border-b border-gray-100 dark:border-gray-800 shadow-2xl animate-in slide-in-from-top duration-300 p-4 md:p-6">
                        <div className="flex justify-between items-center mb-3 md:mb-4">
                            <h3 className="text-sm md:text-lg font-extrabold text-gray-900 dark:text-white flex items-center gap-1.5 md:gap-2">
                                <ListMusic className="text-purple-500 w-4 h-4 md:w-5 md:h-5" />
                                ADD TO LEXPLAY PLAYLIST
                            </h3>
                            <button onClick={() => setShowPlaylistSelector(false)} className="text-gray-500 hover:text-red-500 transition-colors">
                                <X size={18} className="md:w-[20px] md:h-[20px]" />
                            </button>
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
                            {/* Existing Playlists */}
                            <div>
                                <h4 className="text-[9px] md:text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-2 md:mb-3">Your Playlists</h4>
                                <div className="max-h-48 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
                                    {savedPlaylists.length === 0 ? (
                                        <p className="text-xs md:text-sm text-gray-500 italic py-2">No playlists created yet.</p>
                                    ) : (
                                        savedPlaylists.map(pl => (
                                            <button
                                                key={pl.id}
                                                onClick={() => handleAddToPlaylist(pl.id)}
                                                className="w-full text-left p-2.5 md:p-3 rounded-lg border border-gray-100 dark:border-gray-800 hover:border-purple-300 dark:hover:border-purple-700 hover:bg-purple-50 dark:hover:bg-purple-900/10 transition-all flex items-center justify-between group"
                                            >
                                                <span className="font-bold text-sm md:text-base text-gray-700 dark:text-gray-200">{pl.name}</span>
                                                <Plus size={14} className="text-gray-300 group-hover:text-purple-500 md:w-[16px] md:h-[16px]" />
                                            </button>
                                        ))
                                    )}
                                </div>
                            </div>

                            {/* Create New */}
                            <div className="md:border-l border-t md:border-t-0 pt-4 md:pt-0 border-gray-100 dark:border-gray-800 md:pl-6">
                                <h4 className="text-[9px] md:text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-2 md:mb-3">Create New</h4>
                                <div className="space-y-2.5 md:space-y-3">
                                    <input 
                                        type="text" 
                                        placeholder="Playlist Name"
                                        className="w-full p-2 md:p-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-sm focus:ring-2 focus:ring-purple-500 outline-none text-gray-900 dark:text-white"
                                        value={newPlaylistName}
                                        onChange={(e) => setNewPlaylistName(e.target.value)}
                                        onKeyDown={(e) => e.key === 'Enter' && handleCreateAndAdd()}
                                    />
                                    <button 
                                        onClick={handleCreateAndAdd}
                                        disabled={!newPlaylistName.trim() || isCreatingPlaylist}
                                        className="w-full py-2 md:py-2.5 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-lg font-bold text-xs md:text-sm transition-all shadow-md active:scale-95"
                                    >
                                        {isCreatingPlaylist ? 'Creating...' : 'Create & Finish'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Content - Scrollable */}
                <div className="relative z-10 flex min-h-0 flex-1 flex-col space-y-6 overflow-y-auto p-3 lex-modal-scroll custom-scrollbar sm:p-6 md:space-y-10 md:p-8">
                    {/* Main/Parent Question */}
                    <div>
                        <div className="mb-1.5 flex items-center gap-2 drop-shadow-sm md:mb-4">
                            <h4 className="m-0 px-1 text-[10px] font-black uppercase tracking-widest text-gray-500 dark:text-gray-400 md:text-[12px] lg:text-[13px]">
                                {question.subQuestions && question.subQuestions.length > 0 ? 'Problem Stem' : 'Question'}
                            </h4>
                            <div className="h-px flex-1 bg-gradient-to-r from-gray-200 to-transparent dark:from-white/10 dark:to-transparent" />
                        </div>
                        <div className="px-1 text-[15px] font-medium leading-relaxed text-gray-800 dark:text-gray-100 md:text-[17px] whitespace-pre-wrap">
                            <HighlightText text={question.text} query={searchQuery} />
                        </div>
                    </div>

                    {/* Main/Parent Answer (Only if it exists or if no subs) */}
                    {((!question.subQuestions || question.subQuestions.length === 0) || (question.answer && question.answer.trim())) && (
                        <div>
                            <div className="mt-2 mb-1.5 flex items-center gap-2 drop-shadow-sm md:mb-4">
                                <h4 className={`m-0 px-1 text-[10px] font-black uppercase tracking-widest md:text-[12px] lg:text-[13px] ${textColor}`}>
                                    Suggested Answer
                                </h4>
                                <div className={`h-px flex-1 bg-gradient-to-r to-transparent ${textColor.replace('text-', 'from-')}`} />
                            </div>
                            <div className="relative overflow-hidden rounded-xl border border-white/60 bg-gradient-to-br from-blue-50/60 to-white/40 p-3 glass shadow-[0_8px_30px_rgb(0,0,0,0.12)] dark:border-white/10 dark:from-slate-800/60 dark:to-slate-900/40 sm:p-5 md:rounded-2xl md:p-8">
                                <div className="absolute top-0 left-0 h-full w-[4px] bg-gradient-to-b from-blue-400 to-indigo-600 md:w-1.5" />
                                <div className="text-[15px] leading-relaxed text-gray-800 dark:text-gray-100 md:text-[17px] whitespace-pre-wrap">
                                    <HighlightText text={question.answer || 'Answer not available.'} query={searchQuery} />
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Sub-questions loop */}
                    {question.subQuestions && question.subQuestions.map((sub, sIdx) => (
                        <div key={sub.id} className="relative mt-6 space-y-3 pt-6 sm:space-y-6 md:mt-8 md:pt-10">
                            <div className="absolute top-0 left-0 h-px w-full bg-gradient-to-r from-gray-300 via-gray-200 to-transparent dark:from-white/20 dark:via-white/5 dark:to-transparent" />

                            <div>
                                <div className="mb-1.5 flex items-center gap-2 drop-shadow-sm md:mb-4">
                                    <h4 className="m-0 px-1 text-[10px] font-black uppercase tracking-widest text-gray-500 dark:text-gray-400 md:text-[12px] lg:text-[13px]">
                                        Sub-Question {sIdx + 1}
                                    </h4>
                                    <div className="h-px flex-1 bg-gradient-to-r from-gray-200 to-transparent dark:from-white/10 dark:to-transparent" />
                                </div>
                                <div className="px-1 text-[15px] font-medium leading-relaxed text-gray-800 dark:text-gray-100 md:text-[17px] whitespace-pre-wrap">
                                    <HighlightText text={sub.text} query={searchQuery} />
                                </div>
                            </div>

                            <div>
                                <div className="mt-2 mb-1.5 flex items-center gap-2 drop-shadow-sm md:mb-4">
                                    <h4 className={`m-0 px-1 text-[10px] font-black uppercase tracking-widest md:text-[12px] lg:text-[13px] ${textColor}`}>
                                        Suggested Answer
                                    </h4>
                                    <div className={`h-px flex-1 bg-gradient-to-r to-transparent ${textColor.replace('text-', 'from-')}`} />
                                </div>
                                <div className="relative overflow-hidden rounded-xl border border-white/60 bg-gradient-to-br from-blue-50/60 to-white/40 p-3 glass shadow-[0_8px_30px_rgb(0,0,0,0.12)] dark:border-white/10 dark:from-slate-800/60 dark:to-slate-900/40 sm:p-5 md:rounded-2xl md:p-8">
                                    <div className="absolute top-0 left-0 h-full w-[4px] bg-gradient-to-b from-blue-400 to-indigo-600 md:w-1.5" />
                                    <div className="text-[15px] leading-relaxed text-gray-800 dark:text-gray-100 md:text-[17px] whitespace-pre-wrap">
                                        <HighlightText text={sub.answer || 'Answer not available.'} query={searchQuery} />
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>,
        document.body
    );
};

export default QuestionDetailModal;
