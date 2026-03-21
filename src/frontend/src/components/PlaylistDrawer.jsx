import React, { useState } from 'react';
import { useLexPlay } from '../features/lexplay';
import { X, Play, Pause, SkipForward, SkipBack, Settings, Trash2, ListMusic, Volume2, Plus, Edit2, Save } from 'lucide-react';

const PlaylistDrawer = () => {
    const {
        playlist,
        currentTrack,
        currentIndex,
        isPlaying,
        playbackRate,
        isDrawerOpen,
        setIsDrawerOpen,
        removeFromPlaylist,
        playTrack,
        handlePlayPause,
        handleNext,
        handlePrevious,
        setPlaybackRate,
        
        savedPlaylists,
        activePlaylistId,
        createPlaylist,
        renamePlaylist,
        deletePlaylist,
        removeFromSpecificPlaylist,
        loadSavedPlaylist
    } = useLexPlay();

    const [isCreating, setIsCreating] = useState(false);
    const [newPlaylistName, setNewPlaylistName] = useState('');
    const [isEditing, setIsEditing] = useState(false);
    const [editPlaylistName, setEditPlaylistName] = useState('');

    if (!isDrawerOpen) {
        // Render a minimized floating button if there are items in the playlist but drawer is closed
        if (playlist.length === 0) return null;
        return (
            <button
                onClick={() => setIsDrawerOpen(true)}
                className="fixed bottom-6 right-6 z-50 bg-blue-600 hover:bg-blue-700 text-white rounded-full p-4 shadow-xl transition-transform hover:scale-105 animate-in slide-in-from-bottom"
                title="Open LexPlay Playlist"
            >
                <div className="relative">
                    <ListMusic className="w-6 h-6" />
                    <span className="absolute -top-2 -right-2 bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full border-2 border-white dark:border-gray-900">
                        {playlist.length}
                    </span>
                </div>
            </button>
        );
    }

    return (
        <div className="fixed inset-y-0 right-0 z-50 w-full sm:w-[420px] bg-white/[0.08] backdrop-blur-3xl shadow-2xl border-l border-white/10 flex flex-col animate-in slide-in-from-right duration-500 ease-out">
            {/* Drawer Header */}
            <div className="p-6 lg:p-8 border-b border-white/10 flex justify-between items-center bg-gradient-to-r from-purple-600/20 to-blue-600/10">
                <div className="flex items-center gap-4 text-white">
                    <div className="p-2.5 bg-white/10 rounded-xl">
                        <ListMusic className="w-6 h-6 text-purple-300" />
                    </div>
                    <div>
                        <h2 className="font-bold text-xl tracking-tight">LexPlay Queue</h2>
                        <p className="text-[10px] font-bold text-white/30 uppercase tracking-widest">{playlist.length} tracks today</p>
                    </div>
                </div>
                <button
                    onClick={() => setIsDrawerOpen(false)}
                    className="p-3 rounded-2xl hover:bg-white/10 text-white/40 hover:text-white transition-all active:scale-90"
                >
                    <X className="w-6 h-6" />
                </button>
            </div>

            {/* Playlist Manager */}
            <div className="p-6 border-b border-white/10 bg-white/[0.02]">
                {!isCreating ? (
                    <div className="flex items-center gap-3">
                        <select
                            value={activePlaylistId || ''}
                            onChange={(e) => {
                                if (e.target.value) loadSavedPlaylist(e.target.value);
                            }}
                            className="flex-1 bg-white/5 border border-white/10 text-white text-sm rounded-2xl focus:ring-purple-500 focus:border-purple-500 block w-full p-3 transition-all outline-none"
                        >
                            <option value="" disabled className="bg-[#0f172a]">Select a Playlist...</option>
                            {savedPlaylists.map(p => (
                                <option key={p.id} value={p.id} className="bg-[#0f172a]">{p.name} ({p.item_count || 0})</option>
                            ))}
                        </select>
                        <button onClick={() => setIsCreating(true)} className="p-3 bg-white/5 text-white/60 rounded-2xl border border-white/10 hover:bg-white/10 hover:text-white transition-all shadow-lg shadow-black/20" title="Create Playlist">
                            <Plus className="w-6 h-6" />
                        </button>
                    </div>
                ) : (
                    <div className="flex items-center gap-3 animate-in slide-in-from-top duration-300">
                        <input
                            type="text"
                            placeholder="Playlist name..."
                            value={newPlaylistName}
                            onChange={(e) => setNewPlaylistName(e.target.value)}
                            className="flex-1 bg-white/5 border border-white/10 text-white text-sm rounded-2xl p-3 focus:ring-purple-500 focus:border-purple-500 outline-none transition-all placeholder:text-white/20"
                            autoFocus
                        />
                        <button onClick={async () => {
                            if (newPlaylistName.trim()) {
                                await createPlaylist(newPlaylistName.trim());
                                setNewPlaylistName('');
                                setIsCreating(false);
                            }
                        }} className="p-3 bg-green-500/20 text-green-400 rounded-2xl border border-green-500/30 hover:bg-green-500/30 transition-all">
                            <Save className="w-6 h-6" />
                        </button>
                        <button onClick={() => setIsCreating(false)} className="p-3 bg-white/5 text-white/40 rounded-2xl border border-white/10 hover:bg-white/10 transition-all">
                            <X className="w-6 h-6" />
                        </button>
                    </div>
                )}
                
                {activePlaylistId && !isCreating && (
                    <div className="mt-4 flex items-center justify-end gap-4 px-2">
                        {!isEditing ? (
                            <>
                                <button onClick={() => {
                                    setIsEditing(true);
                                    setEditPlaylistName(savedPlaylists.find(p => p.id === activePlaylistId)?.name || '');
                                }} className="text-xs font-bold text-white/40 hover:text-purple-400 flex items-center gap-1.5 transition-all uppercase tracking-widest">
                                    <Edit2 className="w-3.5 h-3.5" /> Rename
                                </button>
                                <button onClick={() => {
                                    if(window.confirm("Are you sure you want to delete this playlist?")) {
                                        deletePlaylist(activePlaylistId);
                                    }
                                }} className="text-xs font-bold text-white/40 hover:text-red-400 flex items-center gap-1.5 transition-all uppercase tracking-widest">
                                    <Trash2 className="w-3.5 h-3.5" /> Delete
                                </button>
                            </>
                        ) : (
                            <div className="flex items-center gap-2 w-full animate-in slide-in-from-right duration-300">
                                <input 
                                    type="text" 
                                    value={editPlaylistName} 
                                    onChange={(e) => setEditPlaylistName(e.target.value)} 
                                    className="flex-1 bg-white/5 border border-white/10 text-white text-xs rounded-xl p-2 focus:ring-purple-500 focus:border-purple-500 outline-none" 
                                    autoFocus
                                />
                                <button onClick={() => {
                                    if(editPlaylistName.trim()) {
                                        renamePlaylist(activePlaylistId, editPlaylistName.trim());
                                        setIsEditing(false);
                                    }
                                }} className="p-2 text-green-400 hover:bg-green-500/10 rounded-xl transition-all"><Save className="w-4 h-4" /></button>
                                <button onClick={() => setIsEditing(false)} className="p-2 text-white/40 hover:bg-white/10 rounded-xl transition-all"><X className="w-4 h-4" /></button>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Current Track Player Area */}
            {currentTrack && (
                <div className="p-8 bg-white/5 border-b border-white/10">
                    <div className="flex items-center gap-2 mb-4">
                        <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded-lg uppercase tracking-widest ${currentTrack.type === 'codal' ? 'bg-amber-500/20 text-amber-400' : 'bg-blue-500/20 text-blue-400'}`}>
                            {currentTrack.type}
                        </span>
                        <div className="flex items-center gap-1 h-3">
                            <div className="w-0.5 bg-purple-400 h-full animate-[bounce_0.8s_infinite]"></div>
                            <div className="w-0.5 bg-purple-400 h-2/3 animate-[bounce_0.8s_infinite_0.2s]"></div>
                            <div className="w-0.5 bg-purple-400 h-full animate-[bounce_0.8s_infinite_0.4s]"></div>
                        </div>
                    </div>
                    
                    <h3 className="font-bold text-white text-xl leading-tight tracking-tight line-clamp-2 mb-2">
                        {currentTrack.title}
                    </h3>
                    <p className="text-xs font-bold text-white/30 uppercase tracking-widest mb-8">
                        {currentTrack.subtitle}
                    </p>

                    {/* Controls */}
                    <div className="flex flex-col items-center gap-8">
                        <div className="flex items-center gap-8">
                            <button
                                onClick={handlePrevious}
                                className="p-3 text-white/40 hover:text-white hover:bg-white/10 rounded-full transition-all active:scale-90"
                            >
                                <SkipBack size={28} />
                            </button>
                            <button
                                onClick={handlePlayPause}
                                className="w-20 h-20 bg-white text-[#0f172a] rounded-full flex items-center justify-center shadow-[0_0_50px_rgba(255,255,255,0.2)] hover:shadow-[0_0_60px_rgba(255,255,255,0.4)] transition-all hover:scale-105 active:scale-90"
                            >
                                {isPlaying ? <Pause size={36} fill="currentColor" strokeWidth={0} /> : <Play size={36} fill="currentColor" strokeWidth={0} className="ml-1" />}
                            </button>
                            <button
                                onClick={handleNext}
                                className="p-3 text-white/40 hover:text-white hover:bg-white/10 rounded-full transition-all active:scale-90"
                            >
                                <SkipForward size={28} />
                            </button>
                        </div>

                        {/* Speed Selector */}
                        <div className="flex items-center bg-white/5 border border-white/10 rounded-2xl p-1 shadow-lg">
                            {[1.0, 1.25, 1.5, 2.0].map(speed => (
                                <button
                                    key={speed}
                                    onClick={() => setPlaybackRate(speed)}
                                    className={`px-4 py-1.5 text-[10px] font-extrabold rounded-xl uppercase tracking-tighter transition-all ${playbackRate === speed
                                        ? 'bg-white text-[#0f172a] shadow-md'
                                        : 'text-white/40 hover:text-white hover:bg-white/5'
                                        }`}
                                >
                                    {speed}x
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* Playlist Queue */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-4">
                {playlist.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-center space-y-6">
                        <div className="p-6 bg-white/5 rounded-[40px] border border-white/10">
                            <ListMusic size={64} className="text-white/10" />
                        </div>
                        <div className="space-y-2">
                            <p className="font-bold text-xl text-white">Queue is empty</p>
                            <p className="text-sm text-white/40 leading-relaxed max-w-[200px] mx-auto">Add cases or codals to start your audio journey.</p>
                        </div>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {playlist.map((item, idx) => {
                            const isCurrent = idx === currentIndex;
                            return (
                                <div
                                    key={`${item.id}-${idx}`}
                                    className={`relative group flex items-start gap-4 p-4 rounded-3xl border transition-all duration-300 cursor-pointer ${isCurrent
                                        ? 'bg-white/10 border-white/20 shadow-xl scale-[1.02]'
                                        : 'bg-white/[0.03] border-white/5 hover:border-white/10 hover:bg-white/[0.06]'
                                        }`}
                                    onClick={() => playTrack(idx)}
                                >
                                    <div className="relative w-12 h-12 rounded-2xl bg-white/5 flex-shrink-0 overflow-hidden flex items-center justify-center border border-white/10">
                                        <div className={`absolute inset-0 bg-purple-600/80 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity z-10 ${isCurrent ? 'opacity-100' : ''}`}>
                                            {isCurrent && isPlaying ? <Pause size={20} fill="currentColor" /> : <Play size={20} fill="currentColor" />}
                                        </div>
                                        <span className={`text-[14px] font-bold ${isCurrent ? 'text-white' : 'text-white/20'}`}>
                                            {idx + 1}
                                        </span>
                                    </div>

                                    <div className="flex-1 min-w-0 pr-8">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className={`text-[9px] font-extrabold px-2 py-0.5 rounded-lg uppercase tracking-widest ${item.type === 'codal' ? 'bg-amber-500/20 text-amber-400'
                                                : 'bg-blue-500/20 text-blue-400'
                                                }`}>
                                                {item.type}
                                            </span>
                                            {isCurrent && (
                                                <span className="text-[9px] font-bold text-purple-400 uppercase tracking-widest flex items-center gap-1.5">
                                                    <Volume2 size={10} /> Now
                                                </span>
                                            )}
                                        </div>
                                        <h4 className={`text-sm font-bold truncate ${isCurrent ? 'text-white' : 'text-white/80'}`}>
                                            {item.title}
                                        </h4>
                                        <p className="text-[10px] text-white/40 font-bold uppercase tracking-widest truncate mt-0.5">
                                            {item.subtitle}
                                        </p>
                                    </div>

                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            if (activePlaylistId && item.playlist_item_id) {
                                                removeFromSpecificPlaylist(activePlaylistId, item.playlist_item_id);
                                            } else {
                                                removeFromPlaylist(idx);
                                            }
                                        }}
                                        className="absolute right-4 top-1/2 -translate-y-1/2 p-2.5 text-white/20 hover:text-red-400 hover:bg-red-400/10 rounded-xl opacity-0 group-hover:opacity-100 transition-all duration-200"
                                        title="Remove from playlist"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
};

export default PlaylistDrawer;
