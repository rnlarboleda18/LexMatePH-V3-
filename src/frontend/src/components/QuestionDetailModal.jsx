import React, { useState, useCallback } from 'react';
import { X, Headphones, ListMusic, Plus, ChevronLeft, ChevronRight, Zap, ChevronDown } from 'lucide-react';
import { getSubjectColor, getSubjectAnswerColor } from '../utils/colors';
import { HighlightText } from '../utils/highlight';
import { useLexPlay } from '../features/lexplay';

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
    const answerBgClass = getSubjectAnswerColor(question.subject);

    const [showPlaylistSelector, setShowPlaylistSelector] = useState(false);
    const [newPlaylistName, setNewPlaylistName] = useState('');
    const [isCreatingPlaylist, setIsCreatingPlaylist] = useState(false);
    const [isHeaderCollapsed, setIsHeaderCollapsed] = useState(true);
    const [isCompactView, setIsCompactView] = useState(false);

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

    return (
        <div
            className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-[5vh] pb-[var(--player-height,0px)] bg-black/50 backdrop-blur-sm animate-in fade-in duration-200"
            onClick={(e) => e.target === e.currentTarget && onClose()}
        >
            <div className="glass bg-white/50 dark:bg-slate-900/50 backdrop-blur-3xl rounded-3xl shadow-[0_10px_50px_rgba(0,0,0,0.4)] w-full max-w-3xl max-h-[85vh] overflow-hidden flex flex-col animate-in zoom-in-95 duration-300 border border-white/50 dark:border-white/20 relative">
                
                {/* Ambient glow orbs inside the modal to drive the glass effect */}
                <div className="absolute top-[-20%] left-[-10%] w-[400px] h-[400px] bg-blue-500/10 rounded-full blur-[100px] pointer-events-none z-0"></div>
                <div className="absolute bottom-[-20%] right-[-10%] w-[400px] h-[400px] bg-purple-500/10 rounded-full blur-[100px] pointer-events-none z-0"></div>
                
                {/* Header */}
                <div className="p-4 sm:p-6 md:p-8 border-b border-white/30 dark:border-white/10 flex justify-between items-start shrink-0 relative z-10 bg-white/20 dark:bg-black/10 backdrop-blur-sm">
                    <div className="flex-1 min-w-0">
                        <div className={`transition-all duration-300 ${isHeaderCollapsed ? 'hidden sm:block' : 'block'}`}>
                            <span className={`inline-block mb-2 sm:mb-3 px-3 py-1 rounded-md text-[10px] sm:text-[11px] md:text-xs font-black uppercase tracking-widest glass bg-white/40 dark:bg-white/10 border border-white/40 dark:border-white/10 shadow-sm ${textColor}`}>
                                {question.subject}
                            </span>
                            <h3 className="text-base sm:text-lg md:text-xl font-extrabold text-gray-900 dark:text-white mt-1 leading-tight sm:leading-snug">
                                {question.year} Bar Exam Question {question.source_label && question.source_label !== `${question.year} Bar Exams` && <span className="text-gray-500 font-medium text-xs sm:text-sm ml-2">({question.source_label})</span>}
                            </h3>
                        </div>
                        
                        {/* Compact Title for Mobile when collapsed */}
                        {isHeaderCollapsed && (
                            <h3 className="sm:hidden text-[14px] font-bold text-gray-900 dark:text-white line-clamp-1 mb-1">
                                {question.year} {question.subject}
                            </h3>
                        )}

                        <button
                            onClick={() => setShowPlaylistSelector(true)}
                            className="flex items-center gap-1.5 px-3 py-1.5 mt-2 sm:mt-3 rounded-lg shadow-sm border border-purple-200 dark:border-purple-800 transition-all bg-purple-50 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 hover:bg-purple-100 dark:hover:bg-purple-900/50 hover:scale-[1.02]"
                            title="Add Question Audio to LexPlay queue"
                        >
                            <Headphones className="w-3.5 h-3.5" />
                            <span className="font-extrabold text-[10px] uppercase tracking-wide">
                                {isHeaderCollapsed ? "Add" : "Add to LexPlay Playlist"}
                            </span>
                        </button>
                    </div>

                    {/* Navigation and Close Buttons */}
                    <div className="flex items-center gap-1 sm:gap-2 ml-2 sm:ml-4 shrink-0">
                        {/* Compact View Toggle */}
                        <button
                            className="p-1.5 rounded-full text-gray-400 hover:text-amber-600 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-all border border-transparent shadow-sm"
                            onClick={() => setIsCompactView(v => !v)}
                            title={isCompactView ? 'Show Full Labels' : 'Compact View (Hide Labels)'}
                        >
                            <Zap size={18} className={isCompactView ? 'text-amber-500 fill-amber-500' : ''} />
                        </button>
                        
                        <div className="flex items-center glass bg-white/50 dark:bg-white/10 border border-white/50 dark:border-white/10 shadow-sm rounded-lg p-0.5 sm:p-1">
                            <button
                                onClick={onPrev}
                                disabled={!hasPrev}
                                className="p-1.5 sm:p-2 rounded-md hover:bg-white/80 dark:hover:bg-white/20 text-gray-600 dark:text-gray-300 transition-all disabled:opacity-30 disabled:hover:bg-transparent"
                                title="Previous Question"
                            >
                                <ChevronLeft size={16} sm={18} />
                            </button>
                            <button
                                onClick={onNext}
                                disabled={!hasNext}
                                className="p-1.5 sm:p-2 rounded-md hover:bg-white/80 dark:hover:bg-white/20 text-gray-600 dark:text-gray-300 transition-all disabled:opacity-30 disabled:hover:bg-transparent"
                                title="Next Question"
                            >
                                <ChevronRight size={16} sm={18} />
                            </button>
                        </div>
                        
                        {/* Collapse toggle — mobile only */}
                        <button
                            className="sm:hidden p-1.5 rounded-full text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-all border border-transparent shadow-sm"
                            onClick={() => setIsHeaderCollapsed(v => !v)}
                        >
                            <ChevronDown size={18} className={`transition-transform duration-200 ${isHeaderCollapsed ? '' : 'rotate-180'}`} />
                        </button>

                        <button
                            onClick={onClose}
                            className="p-1.5 sm:p-2 ml-1 rounded-full glass bg-red-50/50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/50 hover:bg-red-100 dark:hover:bg-red-900/40 text-red-500 transition-all shadow-sm hover:scale-110"
                        >
                            <X size={20} />
                        </button>
                    </div>
                </div>

                {/* PLAYLIST SELECTOR OVERLAY */}
                {showPlaylistSelector && (
                    <div className="absolute inset-x-0 top-0 z-[60] bg-white dark:bg-dark-card border-b border-gray-100 dark:border-gray-800 shadow-2xl animate-in slide-in-from-top duration-300 p-6">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-lg font-extrabold text-gray-900 dark:text-white flex items-center gap-2">
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
                                <h4 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-3">Your Playlists</h4>
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
                                        placeholder="Playlist Name"
                                        className="w-full p-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-sm focus:ring-2 focus:ring-purple-500 outline-none text-gray-900 dark:text-white"
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

                {/* Content - Scrollable */}
                <div className={`flex-1 overflow-y-auto p-4 sm:p-6 md:p-8 relative z-10 custom-scrollbar ${isCompactView ? 'space-y-6' : 'space-y-10'}`}>
                    {/* Main/Parent Question */}
                    <div>
                        <h4 className={`text-[13px] font-black text-gray-500 dark:text-gray-400 uppercase tracking-widest px-1 drop-shadow-sm ${isCompactView ? 'mb-2' : 'mb-4'}`}>
                            {isCompactView ? "" : (question.subQuestions && question.subQuestions.length > 0 ? "Problem Stem" : "Question")}
                        </h4>
                        <div className={`${isCompactView ? 'text-[16px]' : 'text-[17px]'} leading-relaxed text-gray-800 dark:text-gray-100 whitespace-pre-wrap font-medium`}>
                            <HighlightText text={question.text} query={searchQuery} />
                        </div>
                    </div>

                    {/* Main/Parent Answer (Only if it exists or if no subs) */}
                    {((!question.subQuestions || question.subQuestions.length === 0) || (question.answer && question.answer.trim())) && (
                        <div>
                            <h4 className={`text-[13px] font-black uppercase tracking-widest px-1 drop-shadow-sm ${isCompactView ? 'mb-2' : 'mb-4'} ${textColor}`}>
                                {isCompactView ? "" : "Suggested Answer"}
                            </h4>
                            <div className={`relative overflow-hidden glass bg-gradient-to-br from-blue-50/60 to-white/40 dark:from-slate-800/60 dark:to-slate-900/40 p-5 sm:p-6 md:p-8 rounded-2xl border border-white/60 dark:border-white/10 shadow-[0_8px_30px_rgb(0,0,0,0.12)]`}>
                                <div className="absolute top-0 left-0 w-1.5 h-full bg-gradient-to-b from-blue-400 to-indigo-600"></div>
                                <div className={`${isCompactView ? 'text-[16px]' : 'text-[17px]'} leading-relaxed text-gray-800 dark:text-gray-100 whitespace-pre-wrap`}>
                                    <HighlightText text={question.answer || "Answer not available."} query={searchQuery} />
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Sub-questions loop */}
                    {question.subQuestions && question.subQuestions.map((sub, sIdx) => (
                        <div key={sub.id} className={`${isCompactView ? 'pt-6 mt-4' : 'pt-10 mt-8'} relative space-y-4 sm:space-y-6`}>
                            <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-gray-300 via-gray-200 to-transparent dark:from-white/20 dark:via-white/5 dark:to-transparent"></div>
                            
                            <div>
                                <h4 className={`text-[12px] font-black text-gray-500 dark:text-gray-400 uppercase tracking-widest px-1 drop-shadow-sm ${isCompactView ? 'mb-1' : 'mb-4'}`}>Sub-Question {sIdx + 1}</h4>
                                <div className={`${isCompactView ? 'text-[16px]' : 'text-[17px]'} leading-relaxed text-gray-800 dark:text-gray-100 whitespace-pre-wrap font-medium`}>
                                    <HighlightText text={sub.text} query={searchQuery} />
                                </div>
                            </div>
                            
                            <div>
                                <h4 className={`text-[12px] font-black uppercase tracking-widest px-1 drop-shadow-sm ${isCompactView ? 'mb-1' : 'mb-4'} ${textColor}`}>
                                    {isCompactView ? "" : "Suggested Answer"}
                                </h4>
                                <div className={`relative overflow-hidden glass bg-gradient-to-br from-blue-50/60 to-white/40 dark:from-slate-800/60 dark:to-slate-900/40 p-5 sm:p-6 md:p-8 rounded-2xl border border-white/60 dark:border-white/10 shadow-[0_8px_30px_rgb(0,0,0,0.12)]`}>
                                    <div className="absolute top-0 left-0 w-1.5 h-full bg-gradient-to-b from-blue-400 to-indigo-600"></div>
                                    <div className={`${isCompactView ? 'text-[16px]' : 'text-[17px]'} leading-relaxed text-gray-800 dark:text-gray-100 whitespace-pre-wrap`}>
                                        <HighlightText text={sub.answer || "Answer not available."} query={searchQuery} />
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Footer */}
                <div className="p-5 md:p-6 border-t border-white/30 dark:border-white/10 bg-white/40 dark:bg-slate-900/60 flex justify-end shrink-0 backdrop-blur-2xl relative z-20 shadow-[0_-10px_40px_rgba(0,0,0,0.05)]">
                    <button
                        onClick={onClose}
                        className="px-8 py-2.5 bg-gradient-to-r from-gray-700 to-gray-900 dark:from-gray-600 dark:to-gray-800 hover:from-gray-600 hover:to-gray-800 dark:hover:from-gray-500 dark:hover:to-gray-700 text-white rounded-xl text-sm font-extrabold transition-all shadow-lg hover:scale-[1.02] active:scale-95 border border-gray-600/50"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
};

export default QuestionDetailModal;
