import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useLexPlay } from './useLexPlay';
import {
    Play, Pause, SkipBack, SkipForward, Maximize2, Minimize2,
    Volume2, ListMusic, Trash2, X, Headphones, Plus, Edit2, Save, ChevronDown, RotateCcw
} from 'lucide-react';

// Custom modern dropdown for playlists
const CustomPlaylistSelect = ({ value, onChange, options, placeholder="Select a Playlist..." }) => {
    const [isOpen, setIsOpen] = useState(false);
    const selectRef = useRef(null);
    const selectedOption = options.find(o => o.value === value);

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (selectRef.current && !selectRef.current.contains(event.target)) setIsOpen(false);
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    return (
        <div className="relative flex-1" ref={selectRef}>
            <button
                type="button"
                className="w-full flex items-center justify-between bg-white/[0.03] hover:bg-white/10 border border-white/10 text-white text-sm rounded-2xl p-3 outline-none transition-all shadow-sm"
                onClick={() => setIsOpen(!isOpen)}
            >
                <span className={`truncate mr-2 ${!selectedOption ? 'text-white/40' : 'font-semibold'}`}>
                    {selectedOption ? selectedOption.label : placeholder}
                </span>
                <ChevronDown size={18} className={`text-white/40 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>
            {isOpen && (
                <div className="absolute z-50 w-full mt-2 bg-[#0f172a]/95 backdrop-blur-3xl border border-white/10 rounded-2xl shadow-2xl py-2 max-h-60 overflow-y-auto">
                    {options.length === 0 && (
                        <div className="px-4 py-3 text-sm text-white/40 italic text-center">No playlists found</div>
                    )}
                    {options.map((option) => (
                        <button
                            key={option.value}
                            type="button"
                            className={`w-full text-left px-4 py-3 text-sm transition-colors hover:bg-purple-600/30 hover:text-white ${value === option.value ? 'bg-purple-600/20 text-purple-300 font-bold' : 'text-white/70'}`}
                            onClick={() => {
                                onChange(option.value);
                                setIsOpen(false);
                            }}
                        >
                            {option.label}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
};

// Helper to format seconds into mm:ss
const formatTime = (timeInSeconds) => {
    if (isNaN(timeInSeconds)) return "00:00";
    const m = Math.floor(timeInSeconds / 60).toString().padStart(2, '0');
    const s = Math.floor(timeInSeconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
};

// --- Sub-components for Optimization ---

/**
 * PlaybackProgress: Decouples high-frequency time updates from the main LexPlayer.
 */
const PlaybackProgress = ({ audioRef, isPlaying, isMinimized }) => {
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [isScrubbing, setIsScrubbing] = useState(false);
    const progressBarRef = useRef(null);

    useEffect(() => {
        const audio = audioRef?.current;
        if (!audio) return;

        const updateTime = () => {
            if (!isScrubbing) setCurrentTime(audio.currentTime);
        };
        const updateDuration = () => setDuration(audio.duration);

        audio.addEventListener('timeupdate', updateTime);
        audio.addEventListener('loadedmetadata', updateDuration);

        return () => {
            audio.removeEventListener('timeupdate', updateTime);
            audio.removeEventListener('loadedmetadata', updateDuration);
        };
    }, [audioRef, isScrubbing]);

    const handleScrub = useCallback((e) => {
        if (!progressBarRef.current || !duration) return;
        const clientX = e.type.includes('touch') 
            ? (e.touches ? (e.touches[0] || e.changedTouches[0]).clientX : e.clientX)
            : e.clientX;
        const rect = progressBarRef.current.getBoundingClientRect();
        const percent = Math.min(Math.max((clientX - rect.left) / rect.width, 0), 1);
        const newTime = percent * duration;
        setCurrentTime(newTime);
        return newTime;
    }, [duration]);

    useEffect(() => {
        if (!isScrubbing) return;

        const onMove = (e) => handleScrub(e);
        const onUp = (e) => {
            const finalTime = handleScrub(e);
            if (audioRef.current) audioRef.current.currentTime = finalTime;
            setIsScrubbing(false);
        };

        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup', onUp);
        window.addEventListener('touchmove', onMove);
        window.addEventListener('touchend', onUp);

        return () => {
            window.removeEventListener('mousemove', onMove);
            window.removeEventListener('mouseup', onUp);
            window.removeEventListener('touchmove', onMove);
            window.removeEventListener('touchend', onUp);
        };
    }, [isScrubbing, handleScrub, audioRef]);

    const onMouseDown = (e) => {
        setIsScrubbing(true);
        handleScrub(e);
    };

    const progressPercent = duration ? (currentTime / duration) * 100 : 0;

    if (isMinimized) {
        return (
            <div className="flex w-full items-center gap-2 px-0 mt-[-4px]">
                <span className="text-[10px] text-gray-500 font-mono min-w-[32px] text-right">{formatTime(currentTime)}</span>
                <div 
                    className="h-4 flex-1 flex items-center cursor-pointer relative group"
                    ref={progressBarRef}
                    onMouseDown={onMouseDown}
                    onTouchStart={onMouseDown}
                >
                    <div className="h-1 w-full bg-gray-200 dark:bg-gray-700 rounded-full relative overflow-hidden">
                        <div className="absolute top-0 left-0 h-full bg-purple-600" style={{ width: `${progressPercent}%` }} />
                    </div>
                    {/* Visual Thumb for Minimized Mode */}
                    <div 
                        className={`absolute top-1/2 -translate-y-1/2 -ml-1.5 w-3 h-3 bg-white rounded-full transition-transform duration-200 shadow-md border-2 border-purple-600 ${isScrubbing ? 'scale-125' : 'scale-0 group-hover:scale-100'}`} 
                        style={{ left: `${progressPercent}%` }} 
                    />
                </div>
                <span className="text-[10px] text-gray-500 font-mono min-w-[32px]">{formatTime(duration)}</span>
            </div>
        );
    }

    return (
        <div className="w-full max-w-2xl mb-4 z-10">
            <div className="flex justify-between text-xs font-bold text-white/40 mb-2 px-2 tracking-widest font-mono">
                <span>{formatTime(currentTime)}</span>
                <span>{formatTime(duration)}</span>
            </div>
            <div
                className="h-3 bg-white/10 rounded-full cursor-pointer relative group"
                ref={progressBarRef}
                onMouseDown={onMouseDown}
                onTouchStart={onMouseDown}
            >
                <div className="absolute top-0 left-0 h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full" style={{ width: `${progressPercent}%` }} />
                <div className={`absolute top-1/2 -translate-y-1/2 -ml-2.5 w-5 h-5 bg-white rounded-full scale-0 group-hover:scale-100 ${isScrubbing ? 'scale-125' : ''} transition-all duration-200 border-4 border-purple-600`} style={{ left: `${progressPercent}%` }} />
            </div>
        </div>
    );
};

/**
 * PlaylistItem: Memoized track item to prevent re-rendering when other items are interacting.
 */
const PlaylistItem = React.memo(({ item, index, isActive, isPlaying, onPlay, onRemove }) => {
    if (!item) return null;

    return (
        <div className={`relative group flex items-start gap-4 p-4 rounded-3xl border transition-all ${isActive ? 'bg-white/10 border-white/20 shadow-xl' : 'bg-white/[0.03] border-white/5 hover:border-white/10'}`}>
            <div className={`relative w-14 h-14 rounded-2xl overflow-hidden flex-shrink-0 flex items-center justify-center border ${isActive ? 'bg-purple-600 border-none' : 'bg-white/5 border-white/10'}`}>
                
                {/* Action Overlay: Hover state, or Active+Paused state */}
                <div className={`absolute inset-0 z-20 bg-purple-600/80 flex items-center justify-center transition-opacity ${(isActive && !isPlaying) ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}>
                    <button onClick={onPlay} className="text-white w-full h-full flex items-center justify-center">
                        {isActive && isPlaying ? <Pause size={24} fill="currentColor" /> : <Play size={24} fill="currentColor" />}
                    </button>
                </div>

                {/* Track Number: Default state when completely inactive */}
                {!isActive && <span className="text-lg font-bold text-white/20 z-10 relative group-hover:opacity-0 transition-opacity">{index + 1}</span>}
                
                {/* Playing Animation: Default state when playing */}
                {isActive && isPlaying && (
                    <div className="flex items-end gap-1 h-4 z-10 relative group-hover:opacity-0 transition-opacity">
                        {[0.4, 1.0, 0.6].map((h, i) => (
                            <div key={i} className="w-1 bg-white rounded-full animate-[bounce_1s_infinite]" style={{ height: `${h * 100}%`, animationDelay: `${i * 0.1}s` }}></div>
                        ))}
                    </div>
                )}
            </div>
            <div className="flex-1 min-w-0 pr-8">
                <h4 className={`text-sm font-bold truncate ${isActive ? 'text-white' : 'text-white/80'}`}>{item?.title}</h4>
                <p className="text-xs text-white/40 truncate">{item?.subtitle}</p>
            </div>
            <button 
                onClick={onRemove}
                className="absolute right-4 top-1/2 -translate-y-1/2 p-2 text-white/20 hover:text-red-400 transition-opacity opacity-0 group-hover:opacity-100"
            >
                <Trash2 size={18} />
            </button>
        </div>
    );
});

const VirtualizedPlaylist = React.memo(({ items, currentIndex, isPlaying, onPlay, onRemove }) => {
    const containerRef = useRef(null);

    // Automatically scroll to active item when list changes or currentIndex changes
    useEffect(() => {
        if (!containerRef.current) return;
        const activeItem = containerRef.current.querySelector('[data-active="true"]');
        if (activeItem) {
            activeItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }, [currentIndex, items.length]);

    if (items.length === 0) {
        return (
            <div className="h-full flex flex-col items-center justify-center text-center space-y-4 opacity-20">
                <ListMusic size={64} />
                <p className="text-sm font-bold uppercase tracking-widest">Queue Empty</p>
            </div>
        );
    }

    const currentItem = items[currentIndex];

    return (
        <div className="space-y-6">
            {/* Optional: we removed the floating duplicate current track so the list flows naturally */}

            {items.length > 0 && (
                <div className="space-y-4" ref={containerRef}>
                    <div className="flex items-center justify-between px-2">
                        <h4 className="text-[10px] font-bold text-white/20 uppercase tracking-widest">Playlist</h4>
                        <button 
                            onClick={() => {
                                const activeItem = containerRef.current?.querySelector('[data-active="true"]');
                                activeItem?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            }}
                            className="text-[10px] font-bold text-white/20 hover:text-white/40 uppercase tracking-widest transition-colors"
                        >
                            Jump to Playing
                        </button>
                    </div>

                    {items.map((item, index) => {
                        return (
                            <div key={`${item.id}-${index}`} data-active={index === currentIndex}>
                                <PlaylistItem 
                                    item={item} 
                                    index={index} 
                                    isActive={index === currentIndex} 
                                    isPlaying={index === currentIndex ? isPlaying : false} 
                                    onPlay={() => onPlay(index)} 
                                    onRemove={() => onRemove(item, index)}
                                />
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
});

const PlaylistList = React.memo(({ 
    playlist, 
    currentIndex, 
    isPlaying, 
    onPlay, 
    onRemove 
}) => {
    return (
        <VirtualizedPlaylist
            items={playlist}
            currentIndex={currentIndex}
            isPlaying={isPlaying}
            onPlay={onPlay}
            onRemove={onRemove}
        />
    );
});

const LexPlayer = ({ isMinimized, onExpand, onMinimize, onClose }) => {
    const {
        playlist,
        currentTrack,
        currentIndex,
        isPlaying,
        isLoading,
        error,
        playbackRate,
        setPlaybackRate,
        audioRef,
        handlePlayPause,
        handleNext,
        handlePrevious,
        handleStop,
        removeFromPlaylist,
        playTrack,
        savedPlaylists,
        activePlaylistId,
        addBulkToSpecificPlaylist,
        removeFromSpecificPlaylist,
        createPlaylist,
        renamePlaylist,
        deletePlaylist,
        loadSavedPlaylist,
        fetchPlaylists,
        retryCurrentTrack
    } = useLexPlay();

    const progressBarRef = useRef(null);

    const [showBulkModal, setShowBulkModal] = useState(false);
    const [bulkForm, setBulkForm] = useState({ codal: 'RPC', range: '', targetPlaylist: '' });
    const [isBulking, setIsBulking] = useState(false);
    const [bulkError, setBulkError] = useState('');
    const [activeTab, setActiveTab] = useState('player'); // 'player' | 'playlist'

    // Force fetch playlists when the player is opened/mounted
    useEffect(() => {
        fetchPlaylists();
    }, [fetchPlaylists]);

    // Playlist Manager State
    const [isCreating, setIsCreating] = useState(false);
    const [newPlaylistName, setNewPlaylistName] = useState('');
    const [isEditing, setIsEditing] = useState(false);
    const [editPlaylistName, setEditPlaylistName] = useState('');

    const activePlaylistName = savedPlaylists.find(p => p.id === activePlaylistId)?.name;

    // --- Optimized Callbacks ---
    const handlePlaylistPlay = useCallback((index) => {
        if (index === currentIndex) {
            handlePlayPause();
        } else {
            playTrack(index);
        }
    }, [currentIndex, handlePlayPause, playTrack]);

    const handlePlaylistRemove = useCallback((item, index) => {
        if (activePlaylistId && item.playlist_item_id) {
            removeFromSpecificPlaylist(activePlaylistId, item.playlist_item_id);
        } else {
            removeFromPlaylist(index);
        }
    }, [activePlaylistId, removeFromSpecificPlaylist, removeFromPlaylist]);
    
    // Bulk Add Logic
    const handleAddBulkItems = async () => {
        setBulkError('');
        if (!bulkForm.targetPlaylist) {
            setBulkError("Please create a playlist first.");
            return;
        }
        setIsBulking(true);
        try {
            const res = await fetch(`/api/codex/versions?short_name=${bulkForm.codal}`);
            if (!res.ok) throw new Error("Failed to fetch codal data");
            const data = await res.json();
            let articles = data.articles || [];
            
            const rangeText = bulkForm.range.trim();
            if (rangeText) {
                const parts = rangeText.split('-').map(s => s.trim());
                if(parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
                    const start = parseInt(parts[0]);
                    const end = parseInt(parts[1]);
                    articles = articles.filter(a => {
                        // For ROC, only filter by Rule number. Rule 1, Section X => Rule 1
                        const partToParse = bulkForm.codal === 'ROC' ? String(a.article_number).split(',')[0] : String(a.article_number);
                        const numStr = partToParse.replace(/^[^\d]*/, '');
                        const num = parseInt(numStr);
                        return !isNaN(num) && num >= start && num <= end;
                    });
                } else if (!isNaN(rangeText)) {
                    // Specific fix for ROC: handle single digit input for whole rule
                    if (bulkForm.codal === 'ROC') {
                        const targetRule = parseInt(rangeText);
                        articles = articles.filter(a => {
                             const numStr = String(a.article_number).split(',')[0].replace(/^[^\d]*/, '');
                             return parseInt(numStr) === targetRule;
                        });
                    } else {
                        articles = articles.filter(a => {
                            const anum = String(a.article_number).toUpperCase();
                            const rtext = rangeText.toUpperCase();
                            return anum === rtext || anum.includes(rtext); 
                        });
                    }
                } else {
                    articles = articles.filter(a => {
                        const anum = String(a.article_number).toUpperCase();
                        const rtext = rangeText.toUpperCase();
                        return anum === rtext || anum.includes(rtext); // More forgiving exact match
                    });
                }
            }
            
            if (articles.length === 0) {
                setBulkError("No articles found matching that range.");
                setIsBulking(false);
                return;
            }
            
            const payloadItems = articles.map(a => {
                const numStr = String(a.article_number);
                // Don't add "Article" prefix if it's already there, or if it's ROC (which uses Rule)
                const displayTitle = /^(rule|article|section|preamble)/i.test(numStr)
                    ? numStr
                    : (bulkForm.codal === 'ROC' ? `Rule ${numStr}` : `Article ${numStr}`);

                return {
                    content_id: String(a.key_id || a.article_num || a.id || a.article_number),
                    content_type: 'codal',
                    code_id: bulkForm.codal,
                    title: displayTitle,
                    subtitle: a.article_title || data.metadata?.full_name || bulkForm.codal
                };
            });
            
            await addBulkToSpecificPlaylist(bulkForm.targetPlaylist, payloadItems);
            setShowBulkModal(false);
        } catch (err) {
            console.error(err);
            setBulkError(err.message || "Failed to add items.");
        } finally {
            setIsBulking(false);
        }
    };

    // Sync activePlaylistId to bulkForm when opening modal
    useEffect(() => {
        if (showBulkModal) {
            setBulkForm(prev => ({ ...prev, targetPlaylist: activePlaylistId || (savedPlaylists[0]?.id || '') }));
            setBulkError('');
        }
    }, [showBulkModal, activePlaylistId, savedPlaylists]);

    const handleCloseInternal = () => {
        handleStop();
        onClose?.();
    };

    if (isMinimized) {
        return (
            <div 
                className="fixed bottom-0 left-0 right-0 z-50 bg-white/90 dark:bg-gray-900/90 backdrop-blur-md border-t border-gray-200 dark:border-gray-800 shadow-lg px-4 py-2 flex items-center justify-between transition-all duration-300 cursor-pointer hover:bg-white/95 dark:hover:bg-gray-900/95"
                onClick={onExpand}
            >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                    <div className="h-9 w-9 shrink-0 bg-purple-100 dark:bg-purple-900/50 rounded-lg flex items-center justify-center text-purple-600 dark:text-purple-400">
                        <Headphones size={18} />
                    </div>
                    <div className="flex flex-col truncate pr-4">
                        <span className="text-sm font-bold text-gray-900 dark:text-white truncate">
                            {currentTrack ? currentTrack.title : "LexPlay - Nothing queued"}
                        </span>
                        {error ? (
                            <div className="flex items-center gap-2 mt-0.5">
                                <span className="text-[10px] text-red-500 dark:text-red-400 truncate font-medium">⚠ {error}</span>
                                <button 
                                    onClick={(e) => { e.stopPropagation(); retryCurrentTrack(); }}
                                    className="px-2 py-0.5 rounded bg-red-500/10 text-red-500 hover:bg-red-500/20 text-[8px] font-extrabold uppercase tracking-widest border border-red-500/20 transition-colors"
                                >
                                    Retry
                                </button>
                            </div>
                        ) : isLoading ? (
                            <span className="text-[10px] text-purple-500 dark:text-purple-400 truncate animate-pulse">Generating audio...</span>
                        ) : (
                            <span className="text-[10px] text-gray-500 dark:text-gray-400 truncate">
                                {currentTrack ? (activePlaylistName ? `${activePlaylistName} · ${currentTrack.subtitle}` : currentTrack.subtitle) : "Add a Codal or Case Digest"}
                            </span>
                        )}
                    </div>
                </div>

                <div className="flex flex-col items-center shrink-0 px-2 sm:px-4 flex-1 justify-center max-w-md gap-0.5">
                    <div className="flex items-center gap-3 sm:gap-4">
                        <button onClick={(e) => { e.stopPropagation(); handlePrevious(); }} className="p-1.5 text-gray-600 hover:text-purple-600 dark:text-gray-400 dark:hover:text-purple-400 transition-colors" disabled={playlist.length === 0}>
                            <SkipBack size={18} />
                        </button>
                        <button
                            onClick={(e) => { e.stopPropagation(); handlePlayPause(); }}
                            disabled={playlist.length === 0}
                            className="p-1.5 text-gray-900 hover:text-purple-600 dark:text-white dark:hover:text-purple-400 transition-transform hover:scale-110 disabled:opacity-50"
                        >
                            {isLoading ? (
                                <div className="w-5 h-5 border-2 border-purple-600/30 border-t-purple-600 dark:border-white/30 dark:border-t-white rounded-full animate-spin" />
                            ) : isPlaying ? <Pause size={24} fill="currentColor" /> : <Play size={24} fill="currentColor" />}
                        </button>
                        <button onClick={(e) => { e.stopPropagation(); handleNext(); }} className="p-1.5 text-gray-600 hover:text-purple-600 dark:text-gray-400 dark:hover:text-purple-400 transition-colors" disabled={playlist.length === 0}>
                            <SkipForward size={18} />
                        </button>
                    </div>

                    <div className="w-full" onClick={(e) => e.stopPropagation()}>
                        <PlaybackProgress audioRef={audioRef} isPlaying={isPlaying} isMinimized={true} />
                    </div>
                </div>

                <div className="flex items-center gap-2 sm:gap-3 flex-1 justify-end shrink-0 pl-2">
                    <button
                        onClick={(e) => { e.stopPropagation(); handleCloseInternal(); }}
                        className="p-1.5 rounded-full bg-red-500/10 text-red-500 hover:bg-red-500 hover:text-white transition-all duration-300 active:scale-90 flex items-center justify-center shadow-sm"
                        title="Close Player"
                    >
                        <X size={16} strokeWidth={2.5} />
                    </button>
                </div>
            </div>
        );
    }

    // Full Screen Mode
    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
            {/* Backdrop Overlay */}
            <div 
                className="absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity duration-500 animate-in fade-in"
                onClick={onMinimize}
            />
            
            <div className="relative w-full h-full md:h-[calc(100vh-8rem)] md:w-[90vw] lg:w-[85vw] xl:w-[80vw] md:max-w-6xl md:rounded-[2rem] bg-[#0f172a] shadow-2xl overflow-hidden animate-in zoom-in-95 slide-in-from-bottom-10 duration-500">
                {/* Global Header Actions (Minimize/Close) */}
                <div className="absolute top-4 left-4 right-4 z-[60] flex items-center justify-end pointer-events-none md:top-6 md:left-6 md:right-6 md:gap-3 lg:top-8 lg:left-8 lg:right-8">
                    <button
                        onClick={onMinimize}
                        className="p-2.5 bg-white/5 hover:bg-white/10 backdrop-blur-md rounded-full border border-white/10 text-white transition-all hover:scale-110 active:scale-95 group pointer-events-auto"
                        title="Minimize Player"
                    >
                        <Minimize2 size={20} className="transition-transform group-hover:scale-110" />
                    </button>
                    <button
                        onClick={handleCloseInternal}
                        className="p-2.5 bg-red-500/10 hover:bg-red-500/20 backdrop-blur-md rounded-full border border-red-500/20 text-red-400 transition-all hover:scale-110 active:scale-95 group pointer-events-auto"
                        title="Close Player"
                    >
                        <X size={20} className="transition-transform group-hover:rotate-90" />
                    </button>
                </div>

                <div className="flex flex-col md:flex-row h-full w-full relative">
                    {/* Mobile View Switcher - Pill Style */}
                    <div className="md:hidden absolute top-6 left-1/2 -translate-x-1/2 z-[55] flex bg-white/5 backdrop-blur-xl border border-white/10 rounded-full p-0.5 shadow-2xl">
                        <button
                            onClick={() => setActiveTab('playlist')}
                            className={`px-4 py-1.5 rounded-full text-[9px] font-extrabold uppercase tracking-widest transition-all duration-300 ${activeTab === 'playlist' ? 'bg-white text-[#0f172a] shadow-lg' : 'text-white/40 hover:text-white/60'}`}
                        >
                            Playlist
                        </button>
                        <button
                            onClick={() => setActiveTab('player')}
                            className={`px-4 py-1.5 rounded-full text-[9px] font-extrabold uppercase tracking-widest transition-all duration-300 ${activeTab === 'player' ? 'bg-white text-[#0f172a] shadow-lg' : 'text-white/40 hover:text-white/60'}`}
                        >
                            Player
                        </button>
                    </div>

                    {/* Left Area: Playlist */}
                    <div className={`w-full md:w-72 lg:w-80 xl:w-[400px] bg-white/5 backdrop-blur-xl border-b md:border-b-0 md:border-r border-white/10 flex flex-col h-full shrink-0 z-20 transition-all duration-500 ease-in-out ${activeTab === 'playlist' ? 'opacity-100 translate-x-0' : 'hidden md:flex md:opacity-100 md:translate-x-0 opacity-0 -translate-x-10'}`}>
                        <div className="p-4 md:p-6 pt-20 md:pt-6 border-b border-white/10 flex items-center gap-4">
                            <div className="p-2 bg-purple-500/10 rounded-xl"><ListMusic className="text-purple-400" size={24} /></div>
                            <div>
                                <h3 className="text-lg lg:text-xl font-bold text-white">
                                    {activePlaylistName || 'LexPlaylist'}
                                </h3>
                                <p className="text-[10px] font-bold text-white/30 uppercase tracking-widest">{playlist.length} items</p>
                            </div>
                            <button onClick={() => setShowBulkModal(true)} className="ml-auto bg-purple-600 hover:bg-purple-500 text-white p-3 rounded-2xl shadow-lg transition-all"><Plus size={20} /></button>
                        </div>

                        <div className="p-6 border-b border-white/5 bg-white/[0.02]">
                            {!isCreating ? (
                                <div className="flex items-center gap-3">
                                    <CustomPlaylistSelect
                                        value={activePlaylistId || ''}
                                        onChange={(val) => val && loadSavedPlaylist(val)}
                                        options={savedPlaylists.map(p => ({
                                            value: p.id,
                                            label: `${p.name} (${p.item_count || 0})`
                                        }))}
                                    />
                                    <button onClick={() => setIsCreating(true)} className="px-4 py-3 bg-white/5 text-white/60 rounded-2xl border border-white/10 hover:text-white text-xs font-bold whitespace-nowrap transition-all">Create LexPlaylist</button>
                                </div>
                            ) : (
                                <div className="flex items-center gap-2">
                                    <input type="text" placeholder="Name..." value={newPlaylistName} onChange={(e) => setNewPlaylistName(e.target.value)} className="flex-1 bg-white/5 border border-white/10 text-white text-sm rounded-2xl p-3 outline-none" autoFocus />
                                    <button onClick={async () => { if(newPlaylistName.trim()){ await createPlaylist(newPlaylistName.trim()); setNewPlaylistName(''); setIsCreating(false); }}} className="p-3 bg-green-500/20 text-green-400 rounded-2xl transition-all"><Save size={24} /></button>
                                    <button onClick={() => setIsCreating(false)} className="p-3 bg-white/5 text-white/40 rounded-2xl transition-all"><X size={24} /></button>
                                </div>
                            )}
                            {activePlaylistId && !isCreating && (
                                <div className="mt-4 flex items-center justify-end gap-4 px-2">
                                    {!isEditing ? (
                                        <>
                                            <button onClick={() => { setIsEditing(true); setEditPlaylistName(savedPlaylists.find(p => p.id === activePlaylistId)?.name || ''); }} className="text-xs font-bold text-white/40 hover:text-purple-400 flex items-center gap-1.5 transition-all">
                                                <Edit2 size={14} /> Rename
                                            </button>
                                            <button onClick={() => window.confirm("Delete playlist?") && deletePlaylist(activePlaylistId)} className="text-xs font-bold text-white/40 hover:text-red-400 flex items-center gap-1.5 transition-all">
                                                <Trash2 size={14} /> Delete
                                            </button>
                                        </>
                                    ) : (
                                        <div className="flex items-center gap-2 w-full">
                                            <input type="text" value={editPlaylistName} onChange={(e) => setEditPlaylistName(e.target.value)} className="flex-1 bg-white/5 border border-white/10 text-white text-xs rounded-xl p-2 outline-none" autoFocus />
                                            <button onClick={() => { if(editPlaylistName.trim()){ renamePlaylist(activePlaylistId, editPlaylistName.trim()); setIsEditing(false); }}} className="p-2 text-green-400 hover:bg-green-500/10 rounded-xl"><Save size={16} /></button>
                                            <button onClick={() => setIsEditing(false)} className="p-2 text-white/40 hover:bg-white/10 rounded-xl"><X size={16} /></button>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>

                        <div className="flex-1 overflow-y-auto p-6 space-y-4 scroll-smooth overscroll-contain">
                            <PlaylistList 
                                playlist={playlist}
                                currentIndex={currentIndex}
                                isPlaying={isPlaying}
                                onPlay={handlePlaylistPlay}
                                onRemove={handlePlaylistRemove}
                            />
                        </div>
                    </div>

                    {/* Right Area: Now Playing & Controls */}
                    <div className={`flex-1 flex flex-col relative overflow-y-auto scrollbar-hide transition-all duration-500 ease-in-out ${activeTab === 'player' ? 'opacity-100 translate-x-0' : 'hidden md:flex md:opacity-100 md:translate-x-0 opacity-0 translate-x-10'}`}>
                        {/* Background ambient glow - absolute to scroll container so it stays fixed */}
                        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] bg-purple-600/10 blur-[120px] rounded-full pointer-events-none sticky inset-0"></div>
                        
                        {/* Bulletproof centering inner container */}
                        <div className="m-auto shrink-0 flex flex-col items-center w-full pt-16 pb-6 px-4 md:px-8 z-10">
                        
                        <div className="relative group animate-float flex-shrink-0">
                            <div className="absolute -inset-4 bg-gradient-to-tr from-indigo-500 via-purple-500 to-pink-500 rounded-[32px] md:rounded-[40px] opacity-30 blur-2xl group-hover:opacity-50 transition-opacity"></div>
                            <div className="relative w-40 h-40 sm:w-48 sm:h-48 lg:w-56 lg:h-56 max-h-[35vh] max-w-[35vh] bg-gradient-to-tr from-[#6366f1] via-[#a855f7] to-[#ec4899] animate-gradient rounded-[30px] md:rounded-[32px] shadow-2xl flex items-center justify-center overflow-hidden">
                                <div className="absolute inset-0 bg-white/5 backdrop-blur-[1px]"></div>
                                <Headphones size={72} className={`text-white drop-shadow-[0_8px_16px_rgba(0,0,0,0.3)] transform transition-transform duration-700 z-10 md:w-20 md:h-20 ${isPlaying ? '-translate-y-5 md:-translate-y-6 scale-90' : 'group-hover:scale-110'}`} />
                                {isPlaying && (
                                    <div className="absolute bottom-4 md:bottom-6 left-1/2 -translate-x-1/2 flex items-end gap-1.5 h-8 md:h-10 z-10">
                                        {[0.4, 0.8, 0.6, 1.0, 0.5, 0.9, 0.7, 0.3].map((h, i) => (
                                            <div key={i} className="w-1.5 bg-white/90 rounded-full animate-[bounce_1s_infinite]" style={{ height: `${h * 100}%`, animationDelay: `${i * 0.1}s` }}></div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="text-center mt-4 mb-3 max-w-xl z-10">
                            <h2 className="text-2xl lg:text-3xl font-bold font-serif text-white mb-2 line-clamp-2">
                                {currentTrack ? currentTrack.title : "LexPlayer is idle"}
                            </h2>
                            <p className="text-base lg:text-lg text-white/60 font-medium tracking-wide">
                                {currentTrack ? (activePlaylistName ? `${activePlaylistName} • ${currentTrack.subtitle}` : currentTrack.subtitle) : "Add items to your LexPlaylist to start listening"}
                            </p>
                            {/* Fixed height container to prevent layout shift during loading/error states */}
                            <div className="min-h-[2.5rem] mt-1 flex items-center justify-center w-full">
                                {error && (
                                    <div className="flex flex-col items-center gap-3">
                                        <div className="inline-flex items-center justify-center gap-2 bg-red-500/10 text-red-400 border border-red-500/20 rounded-2xl px-6 py-2 text-sm font-semibold">⚠ {error}</div>
                                        <button 
                                            onClick={retryCurrentTrack}
                                            className="px-6 py-2 bg-white/5 hover:bg-white/10 text-white text-xs font-bold rounded-full border border-white/10 transition-all flex items-center gap-2 active:scale-95"
                                        >
                                            <RotateCcw size={14} /> Try to Reload Audio
                                        </button>
                                    </div>
                                )}
                                {isLoading && !error && <div className="inline-flex items-center justify-center gap-2 bg-white/5 text-white/80 border border-white/10 rounded-2xl px-6 py-3 text-sm font-semibold animate-pulse">Adding...</div>}
                            </div>
                        </div>

                        <PlaybackProgress audioRef={audioRef} isPlaying={isPlaying} isMinimized={false} />

                        <div className="flex flex-col items-center gap-3 w-full max-w-2xl z-10">
                            <div className="flex items-center gap-5 lg:gap-8">
                                <button onClick={handlePrevious} disabled={playlist.length === 0} className="p-3 text-white/50 hover:text-white hover:bg-white/10 rounded-full transition-all active:scale-90 disabled:opacity-20"><SkipBack size={28} /></button>
                                <button onClick={handlePlayPause} disabled={playlist.length === 0} className="relative w-14 h-14 lg:w-16 lg:h-16 bg-white text-[#0f172a] rounded-full flex items-center justify-center shadow-2xl hover:scale-105 active:scale-95 transition-all">
                                    {isLoading ? <div className="w-8 h-8 border-[3px] border-[#0f172a]/20 border-t-[#0f172a] rounded-full animate-spin" /> : (isPlaying ? <Pause size={32} fill="currentColor" /> : <Play size={32} fill="currentColor" className="ml-1" />)}
                                </button>
                                <button onClick={handleNext} disabled={playlist.length === 0} className="p-3 text-white/50 hover:text-white hover:bg-white/10 rounded-full transition-all active:scale-90 disabled:opacity-20"><SkipForward size={28} /></button>
                            </div>
                            <div className="flex flex-wrap justify-center bg-white/5 backdrop-blur-md border border-white/10 rounded-xl p-1 shadow-lg max-w-[90%]">
                                {[0.7, 0.8, 0.9, 1.0, 1.25, 1.5, 2.0].map(speed => (
                                    <button key={speed} onClick={() => setPlaybackRate(speed)} className={`px-2 py-1.5 md:px-3 text-xs lg:text-sm font-bold rounded-lg transition-all ${playbackRate === speed ? 'bg-white text-[#0f172a]' : 'text-white/60 hover:text-white'}`}>
                                        {speed < 1 ? speed.toFixed(2).replace('0.', '.') + 'x' : speed === 1 ? '1x' : speed + 'x'}
                                    </button>
                                ))}
                            </div>
                        </div>
                        </div>
                    </div>
                </div>
                
                {/* Bulk Add Modal */}
                {showBulkModal && (
                    <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/60 backdrop-blur-md">
                        <div className="bg-[#1e293b]/90 border border-white/10 rounded-[32px] shadow-2xl w-full max-w-md overflow-hidden">
                            <div className="px-8 py-6 border-b border-white/5 flex justify-between items-center bg-white/[0.02]">
                                <div>
                                    <h3 className="text-xl font-bold text-white flex items-center gap-2"><Plus className="text-purple-400" size={24} /> Add Items</h3>
                                    <p className="text-xs font-medium text-white/30 uppercase tracking-widest mt-1">Bulk create audio queue</p>
                                </div>
                                <button onClick={() => setShowBulkModal(false)} className="text-white/40 hover:text-white"><X size={24} /></button>
                            </div>
                            <div className="p-8 space-y-6">
                                {bulkError && <div className="p-4 bg-red-500/10 text-red-400 border border-red-500/20 rounded-2xl text-sm font-medium">{bulkError}</div>}
                                <div className="space-y-2">
                                    <label className="block text-xs font-bold text-white/40 uppercase tracking-widest ml-1">Destination Playlist</label>
                                    <select className="w-full p-4 bg-white/5 border border-white/10 text-white text-sm rounded-2xl outline-none" value={bulkForm.targetPlaylist} onChange={e => setBulkForm({...bulkForm, targetPlaylist: e.target.value})}>
                                        <option value="" disabled className="bg-[#0f172a]">Select a playlist...</option>
                                        {savedPlaylists.map(p => <option key={p.id} value={p.id} className="bg-[#0f172a]">{p.name}</option>)}
                                    </select>
                                </div>
                                <div className="space-y-2">
                                    <label className="block text-xs font-bold text-white/40 uppercase tracking-widest ml-1">Select Codal</label>
                                    <select className="w-full p-4 bg-white/5 border border-white/10 text-white text-sm rounded-2xl outline-none" value={bulkForm.codal} onChange={e => setBulkForm({...bulkForm, codal: e.target.value})}>
                                        <option value="RPC" className="bg-[#0f172a]">Revised Penal Code</option>
                                        <option value="CIV" className="bg-[#0f172a]">Civil Code</option>
                                        <option value="FC" className="bg-[#0f172a]">Family Code</option>
                                        <option value="CONST" className="bg-[#0f172a]">1987 Constitution</option>
                                        <option value="LABOR" className="bg-[#0f172a]">Labor Code</option>
                                        <option value="ROC" className="bg-[#0f172a]">Rules of Court</option>
                                    </select>
                                </div>
                                <div className="space-y-2">
                                    <label className="block text-xs font-bold text-white/40 uppercase tracking-widest ml-1">
                                        {bulkForm.codal === 'ROC' ? 'Rule Range (Optional)' : 
                                         bulkForm.codal === 'CONST' ? 'Article / Section Range (Optional)' : 
                                         'Article Range (Optional)'}
                                    </label>
                                    <input type="text" placeholder="e.g. 1-20" value={bulkForm.range} onChange={e => setBulkForm({...bulkForm, range: e.target.value})} className="w-full p-4 bg-white/5 border border-white/10 text-white text-sm rounded-2xl outline-none" />
                                </div>
                            </div>
                            <div className="px-8 py-6 border-t border-white/5 bg-white/[0.02] flex justify-end gap-3">
                                <button onClick={() => setShowBulkModal(false)} className="px-6 py-3 text-sm font-bold text-white/60 hover:text-white transition-all">Cancel</button>
                                <button onClick={handleAddBulkItems} disabled={isBulking} className="px-8 py-3 text-sm font-bold text-white bg-purple-600 rounded-[20px] hover:bg-purple-500 shadow-lg disabled:opacity-50 transition-all active:scale-95">
                                    {isBulking ? "Adding..." : "Add to Playlist"}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default LexPlayer;
