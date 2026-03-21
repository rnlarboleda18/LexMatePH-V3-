import React, { useState, useCallback } from 'react';
import { X, Headphones, ListMusic, Plus } from 'lucide-react';
import { getSubjectColor, getSubjectAnswerColor } from '../utils/colors';
import { HighlightText } from '../utils/highlight';
import { useLexPlay } from '../features/lexplay';

const QuestionDetailModal = ({ question, onClose, searchQuery }) => {
    if (!question) return null;

    const colorClass = getSubjectColor(question.subject);
    const textColor = colorClass.split(' ').find(c => c.startsWith('text-'));
    const answerBgClass = getSubjectAnswerColor(question.subject);

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
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200"
            onClick={(e) => e.target === e.currentTarget && onClose()}
        >
            <div className="bg-white dark:bg-dark-card rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col animate-in zoom-in-95 duration-200 relative">
                
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
                {/* Header */}
                <div className="p-6 border-b border-gray-100 dark:border-gray-800 flex justify-between items-start">
                    <div>
                        <span className={`inline-block mb-2 text-sm font-bold uppercase tracking-wider ${textColor}`}>
                            {question.subject}
                        </span>
                        <h3 className="text-xl font-bold text-gray-900 dark:text-white mt-1">
                            {question.year} Bar Exam Question {question.source_label && question.source_label !== `${question.year} Bar Exams` && `(${question.source_label})`}
                        </h3>
                        <button
                            onClick={() => setShowPlaylistSelector(true)}
                            className="flex items-center gap-2 px-3 py-1 mt-2 rounded-full shadow-sm border transition-all bg-purple-50 border-purple-200 text-purple-600 dark:bg-purple-900/20 dark:border-purple-800 dark:text-purple-400 hover:bg-purple-100 dark:hover:bg-purple-900/30"
                            title="Add Question Audio to LexPlay queue"
                        >
                            <Headphones className="w-3.5 h-3.5" />
                            <span className="font-bold text-[10px] uppercase tracking-tight">
                                Add to LexPlay Playlist
                            </span>
                        </button>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 transition-colors"
                    >
                        <X size={24} />
                    </button>
                </div>

                {/* Content - Scrollable */}
                <div className="flex-1 overflow-y-auto p-6 space-y-8">
                    {/* Question */}
                    <div>
                        <h4 className="text-sm font-semibold text-gray-500 uppercase mb-3">Question</h4>
                        <p className="text-lg leading-relaxed text-gray-800 dark:text-gray-100 whitespace-pre-wrap">
                            <HighlightText text={question.text} query={searchQuery} />
                        </p>
                    </div>

                    {/* Answer */}
                    <div>
                        <h4 className={`text-sm font-semibold uppercase mb-3 ${textColor}`}>Suggested Answer</h4>
                        <div className={`p-6 rounded-xl ${answerBgClass} border border-transparent dark:border-white/5`}>
                            <p className="text-base leading-relaxed text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
                                <HighlightText text={question.answer} query={searchQuery} />
                            </p>
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="p-6 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50 flex justify-end">
                    <button
                        onClick={onClose}
                        className="px-6 py-2.5 rounded-lg bg-gray-900 dark:bg-white text-white dark:text-gray-900 font-medium hover:opacity-90 transition-opacity"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
};

export default QuestionDetailModal;
