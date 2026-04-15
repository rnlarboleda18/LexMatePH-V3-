import React, { useState } from 'react';
import { useLexPlay } from '../features/lexplay';
import { X, Play, Pause, SkipForward, SkipBack, Settings, Trash2, ListMusic, Volume2, Plus, Edit2, Save } from 'lucide-react';

const PlaylistDrawer = () => {
    const {
        playlist,
        displayPlaylist,
        listUiCurrentIndex,
        activatePlaylistRow,
        currentTrack,
        currentIndex,
        isPlaying,
        isLoading,
        isDrawerOpen,
        setIsDrawerOpen,
        removeFromPlaylist,
        handlePlayPause,
        handleNext,
        handlePrevious,
        
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
                className="fixed bottom-6 right-6 z-50 bg-purple-600 hover:bg-purple-500 text-white rounded-full p-4 shadow-xl transition-transform hover:scale-105 animate-in slide-in-from-bottom"
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
        <div className="fixed inset-y-0 right-0 z-50 flex w-full flex-col border-l border-lex-strong bg-white shadow-2xl animate-in slide-in-from-right duration-500 ease-out dark:border-lex-strong dark:bg-zinc-900 sm:w-[420px]">
            {/* Drawer Header */}
            <div className="flex items-center justify-between border-b border-lex bg-violet-50 p-6 dark:border-lex dark:bg-zinc-800 lg:p-8">
                <div className="flex items-center gap-4 text-gray-900 dark:text-white">
                    <div className="rounded-xl border border-lex-strong bg-white p-2.5 shadow-sm dark:border-lex-strong dark:bg-zinc-700">
                        <ListMusic className="h-6 w-6 text-violet-600 dark:text-violet-300" />
                    </div>
                    <div>
                        <h2 className="text-xl font-bold tracking-tight">LexPlay Queue</h2>
                        <p className="text-[10px] font-bold uppercase tracking-widest text-gray-500 dark:text-zinc-400">{playlist.length} tracks today</p>
                    </div>
                </div>
                <button
                    onClick={() => setIsDrawerOpen(false)}
                    className="rounded-2xl p-3 text-gray-500 transition-all hover:bg-white/80 hover:text-gray-900 active:scale-90 dark:text-zinc-400 dark:hover:bg-zinc-700 dark:hover:text-white"
                >
                    <X className="h-6 w-6" />
                </button>
            </div>

            {/* Playlist Manager */}
            <div className="border-b border-lex bg-slate-50 p-6 dark:border-lex dark:bg-zinc-800/50">
                {!isCreating ? (
                    <div className="flex items-center gap-3">
                        <select
                            value={activePlaylistId || ''}
                            onChange={(e) => {
                                if (e.target.value) loadSavedPlaylist(e.target.value);
                            }}
                            className="block w-full flex-1 rounded-2xl border border-lex-strong bg-white p-3 text-sm text-gray-900 outline-none transition-all focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 dark:border-lex-strong dark:bg-zinc-800 dark:text-white dark:focus:border-violet-400"
                        >
                            <option value="" disabled className="bg-[#0f172a]">Select a Playlist...</option>
                            {savedPlaylists.map(p => (
                                <option key={p.id} value={p.id} className="bg-[#0f172a]">{p.name} ({p.item_count || 0})</option>
                            ))}
                        </select>
                        <button onClick={() => setIsCreating(true)} className="rounded-2xl border border-lex-strong bg-white p-3 text-gray-600 shadow-sm transition-all hover:bg-slate-50 hover:text-gray-900 dark:border-lex-strong dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700 dark:hover:text-white" title="Create Playlist">
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
                            className="flex-1 rounded-2xl border border-lex-strong bg-white p-3 text-sm text-gray-900 outline-none transition-all placeholder:text-gray-400 focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 dark:border-lex-strong dark:bg-zinc-800 dark:text-white dark:placeholder:text-zinc-500 dark:focus:border-violet-400"
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
                        <button onClick={() => setIsCreating(false)} className="rounded-2xl border border-lex-strong bg-white p-3 text-gray-500 transition-all hover:bg-slate-50 dark:border-lex-strong dark:bg-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-700">
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
                                }} className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest text-gray-500 transition-all hover:text-violet-600 dark:text-zinc-500 dark:hover:text-violet-400">
                                    <Edit2 className="w-3 h-3" /> Rename
                                </button>
                                <button onClick={() => {
                                    if(window.confirm("Are you sure you want to delete this playlist?")) {
                                        deletePlaylist(activePlaylistId);
                                    }
                                }} className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest text-gray-500 transition-all hover:text-red-600 dark:text-zinc-500 dark:hover:text-red-400">
                                    <Trash2 className="w-3 h-3" /> Delete
                                </button>
                            </>
                        ) : (
                            <div className="flex items-center gap-2 w-full animate-in slide-in-from-right duration-300">
                                <input 
                                    type="text" 
                                    value={editPlaylistName} 
                                    onChange={(e) => setEditPlaylistName(e.target.value)} 
                                    className="flex-1 rounded-xl border border-lex-strong bg-white p-2 text-xs text-gray-900 outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 dark:border-lex-strong dark:bg-zinc-800 dark:text-white dark:focus:border-violet-400" 
                                    autoFocus
                                />
                                <button onClick={() => {
                                    if(editPlaylistName.trim()) {
                                        renamePlaylist(activePlaylistId, editPlaylistName.trim());
                                        setIsEditing(false);
                                    }
                                }} className="p-2 text-green-400 hover:bg-green-500/10 rounded-xl transition-all"><Save className="w-4 h-4" /></button>
                                <button onClick={() => setIsEditing(false)} className="rounded-xl p-2 text-gray-500 transition-all hover:bg-slate-100 dark:text-zinc-400 dark:hover:bg-zinc-700"><X className="h-4 w-4" /></button>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Current Track Player Area */}
            {currentTrack && (
                <div className="border-b border-lex bg-slate-50 p-8 dark:border-lex dark:bg-zinc-800/40">
                    <div className="mb-4 flex items-center gap-2">
                        <span className={`rounded-lg px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-widest ${currentTrack.type === 'codal' ? 'bg-amber-100 text-amber-800 dark:bg-amber-500/20 dark:text-amber-300' : 'bg-blue-100 text-blue-800 dark:bg-blue-500/20 dark:text-blue-300'}`}>
                            {currentTrack.type}
                        </span>
                        <div className="flex items-center gap-1 h-3">
                            <div className="w-0.5 bg-purple-600 h-full animate-[bounce_0.8s_infinite]"></div>
                            <div className="w-0.5 bg-purple-600 h-2/3 animate-[bounce_0.8s_infinite_0.2s]"></div>
                            <div className="w-0.5 bg-purple-600 h-full animate-[bounce_0.8s_infinite_0.4s]"></div>
                        </div>
                    </div>
                    
                    <h3 className="mb-2 line-clamp-2 text-xl font-bold leading-tight tracking-tight text-gray-900 dark:text-white">
                        {currentTrack.title}
                    </h3>
                    <p className="mb-8 text-xs font-bold uppercase tracking-widest text-gray-500 dark:text-zinc-400">
                        {currentTrack.subtitle}
                    </p>

                    {/* Controls */}
                    <div className="flex flex-col items-center gap-8">
                        <div className="flex items-center gap-8">
                            <button
                                onClick={handlePrevious}
                                className="rounded-full p-3 text-gray-500 transition-all hover:bg-slate-200 hover:text-gray-900 active:scale-90 dark:text-zinc-400 dark:hover:bg-zinc-700 dark:hover:text-white"
                            >
                                <SkipBack size={28} />
                            </button>
                            <button
                                onClick={handlePlayPause}
                                className="w-20 h-20 rounded-full bg-purple-600 hover:bg-purple-500 text-white flex items-center justify-center shadow-[0_12px_40px_-10px_rgba(147,51,234,0.8)] transition-all hover:scale-110 active:scale-95"
                            >
                                {isLoading ? (
                                    <div className="relative w-12 h-12 flex items-center justify-center">
                                        <div className="absolute inset-0 border-[4px] border-purple-600/10 rounded-full" />
                                        <div className="absolute inset-0 border-[4px] border-purple-600 border-t-transparent rounded-full animate-spin" />
                                        <div className="w-3 h-3 bg-purple-600 rounded-full animate-pulse shadow-[0_0_15px_rgba(147,51,234,0.5)]" />
                                    </div>
                                ) : isPlaying ? (
                                    <Pause size={36} fill="currentColor" strokeWidth={0} />
                                ) : (
                                    <Play size={36} fill="currentColor" strokeWidth={0} className="ml-1" />
                                )}
                            </button>
                            <button
                                onClick={handleNext}
                                className="rounded-full p-3 text-gray-500 transition-all hover:bg-slate-200 hover:text-gray-900 active:scale-90 dark:text-zinc-400 dark:hover:bg-zinc-700 dark:hover:text-white"
                            >
                                <SkipForward size={28} />
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Playlist Queue */}
            <div className="custom-scrollbar flex-1 space-y-4 overflow-y-auto p-6">
                {displayPlaylist.length === 0 ? (
                    <div className="flex h-full flex-col items-center justify-center space-y-6 text-center">
                        <div className="rounded-lg border border-lex bg-slate-50 p-6 dark:border-lex dark:bg-zinc-800/60">
                            <ListMusic size={64} className="text-gray-300 dark:text-zinc-600" />
                        </div>
                        <div className="space-y-2">
                            <p className="text-xl font-bold text-gray-900 dark:text-white">Queue is empty</p>
                            <p className="mx-auto max-w-[200px] text-sm leading-relaxed text-gray-500 dark:text-zinc-400">Add cases or codals to start your audio journey.</p>
                        </div>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {displayPlaylist.map((item, idx) => {
                            const isCurrent = idx === listUiCurrentIndex;
                            return (
                                <div
                                    key={`${item.id}-${idx}`}
                                    className={`group relative flex cursor-pointer items-start gap-4 rounded-3xl border p-4 transition-all duration-300 ${isCurrent
                                        ? 'scale-[1.02] border-lex-strong bg-violet-50 shadow-xl dark:border-lex-strong dark:bg-violet-950/30'
                                        : 'border-lex bg-white hover:border-lex-strong hover:bg-slate-50 dark:border-lex dark:bg-zinc-800/40 dark:hover:border-lex-strong dark:hover:bg-zinc-800'
                                        }`}
                                    onClick={() => activatePlaylistRow(idx)}
                                >
                                    <div className="relative flex h-12 w-12 flex-shrink-0 items-center justify-center overflow-hidden rounded-2xl border border-lex-strong bg-slate-100 dark:border-lex-strong dark:bg-zinc-700">
                                        <div className={`absolute inset-0 bg-purple-600/80 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity z-10 ${isCurrent ? 'opacity-100' : ''}`}>
                                            {isCurrent && isLoading ? (
                                                <div className="relative w-7 h-7 flex items-center justify-center">
                                                    <div className="absolute inset-0 border-2 border-white/20 rounded-full" />
                                                    <div className="absolute inset-0 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                                    <div className="w-1.5 h-1.5 bg-white rounded-full animate-pulse shadow-[0_0_8px_rgba(255,255,255,0.8)]" />
                                                </div>
                                            ) : isCurrent && isPlaying ? (
                                                <Pause size={20} fill="currentColor" />
                                            ) : (
                                                <Play size={20} fill="currentColor" />
                                            )}
                                        </div>
                                        <span className={`text-[14px] font-bold ${isCurrent ? 'text-gray-900 dark:text-white' : 'text-gray-400 dark:text-zinc-500'}`}>
                                            {idx + 1}
                                        </span>
                                    </div>

                                    <div className="flex-1 min-w-0 pr-8">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className={`rounded-lg px-2 py-0.5 text-[9px] font-extrabold uppercase tracking-widest ${item.type === 'codal' ? 'bg-amber-100 text-amber-900 dark:bg-amber-500/20 dark:text-amber-300'
                                                : 'bg-blue-100 text-blue-900 dark:bg-blue-500/20 dark:text-blue-300'
                                                }`}>
                                                {item.type}
                                            </span>
                                            {isCurrent && (
                                                <span className="text-[9px] font-bold text-purple-400 uppercase tracking-widest flex items-center gap-1.5">
                                                    <Volume2 size={10} /> Now
                                                </span>
                                            )}
                                        </div>
                                        <h4 className={`truncate text-sm font-bold ${isCurrent ? 'text-gray-900 dark:text-white' : 'text-gray-800 dark:text-zinc-200'}`}>
                                            {item.title}
                                        </h4>
                                        <p className="mt-0.5 truncate text-[10px] font-bold uppercase tracking-widest text-gray-500 dark:text-zinc-500">
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
                                        className="absolute right-4 top-1/2 -translate-y-1/2 rounded-xl p-2.5 text-gray-400 opacity-0 transition-all duration-200 hover:bg-red-50 hover:text-red-600 group-hover:opacity-100 dark:text-zinc-500 dark:hover:bg-red-950/40 dark:hover:text-red-400"
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
