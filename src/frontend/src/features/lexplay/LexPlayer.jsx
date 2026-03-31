import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useLexPlay } from './useLexPlay';
import {
    Play, Pause, SkipBack, SkipForward, Maximize2, Minimize2,
    Volume2, ListMusic, Trash2, X, Headphones, Plus, Edit2, Save, ChevronDown,
    DownloadCloud, CheckCircle2, Loader2
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
                            className={`w-full text-left px-4 py-3 text-sm transition-colors hover:bg-purple-500/30 hover:text-white ${value === option.value ? 'bg-purple-500/20 text-purple-200 font-bold' : 'text-white/70'}`}
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
                        <div className="absolute top-0 left-0 h-full bg-primary" style={{ width: `${progressPercent}%` }} />
                    </div>
                    {/* Visual Thumb for Minimized Mode */}
                    <div 
                        className={`absolute top-1/2 -translate-y-1/2 -ml-1.5 w-3 h-3 bg-white rounded-full transition-transform duration-200 shadow-md border-2 border-purple-500 ${isScrubbing ? 'scale-125' : 'scale-0 group-hover:scale-100'}`} 
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
                <div className="absolute top-0 left-0 h-full bg-purple-500/80 rounded-full" style={{ width: `${progressPercent}%` }} />
                <div className={`absolute top-1/2 -translate-y-1/2 -ml-2.5 w-5 h-5 bg-white rounded-full scale-0 group-hover:scale-100 ${isScrubbing ? 'scale-125' : ''} transition-all duration-200 border-4 border-purple-500`} style={{ left: `${progressPercent}%` }} />
            </div>
        </div>
    );
};

/**
 * PlaylistItem: Memoized track item to prevent re-rendering when other items are interacting.
 */
const PlaylistItem = React.memo(({ item, index, isActive, isPlaying, isLoading, onPlay, onRemove }) => {
    const [isDownloaded, setIsDownloaded] = useState(false);
    const [isDownloading, setIsDownloading] = useState(false);

    // Check if the track is already in the audio-cache
    useEffect(() => {
        if (!item?.audio_url) return;
        const checkCache = async () => {
            try {
                const cache = await caches.open('audio-cache');
                const response = await cache.match(item.audio_url);
                setIsDownloaded(!!response);
            } catch (err) {
                console.warn('Cache check failed:', err);
            }
        };
        checkCache();
    }, [item?.audio_url]);

    const handleDownload = async (e) => {
        e.stopPropagation();
        if (isDownloaded || isDownloading || !item?.audio_url) return;
        
        setIsDownloading(true);
        try {
            const cache = await caches.open('audio-cache');
            const response = await fetch(item.audio_url);
            if (response.ok) {
                await cache.put(item.audio_url, response);
                setIsDownloaded(true);
            }
        } catch (err) {
            console.error('Manual download failed:', err);
        } finally {
            setIsDownloading(false);
        }
    };

    if (!item) return null;

    return (
        <div className={`relative group flex items-center gap-3 py-2 px-4 rounded-2xl border transition-all ${isActive ? 'bg-white/10 border-white/20 shadow-lg scale-[1.02] ring-1 ring-purple-600/30' : 'bg-white/[0.03] border-white/5 hover:border-white/10'}`}>
            <div className={`relative w-10 h-10 rounded-xl overflow-hidden flex-shrink-0 flex items-center justify-center border ${isActive ? 'bg-purple-500 border-none shadow-[0_0_15px_rgba(168,85,247,0.4)]' : 'bg-white/5 border-white/10'}`}>
                
                {/* Action Overlay: Hover state, or Active+Paused state, or Loading state */}
                <div className={`absolute inset-0 z-20 bg-purple-500/80 flex items-center justify-center transition-opacity ${((isActive && !isPlaying) || (isActive && isLoading)) ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}>
                    <button onClick={onPlay} className="text-white w-full h-full flex items-center justify-center">
                        {isActive && isLoading ? (
                            <div className="relative w-6 h-6 flex items-center justify-center">
                                <div className="absolute inset-0 border-2 border-white/20 rounded-full" />
                                <div className="absolute inset-0 border-2 border-white border-t-transparent rounded-full animate-[spin_0.8s_linear_infinite]" />
                                <div className="w-1.5 h-1.5 bg-white rounded-full animate-pulse shadow-[0_0_10px_rgba(255,255,255,1)]" />
                            </div>
                        ) : (
                            isActive && isPlaying ? <Pause size={20} fill="currentColor" /> : <Play size={20} fill="currentColor" />
                        )}
                    </button>
                </div>

                {/* Track Number: Default state when completely inactive */}
                {!isActive && <span className="text-sm font-black text-white/20 z-10 relative group-hover:opacity-0 transition-opacity tracking-tighter">{index + 1}</span>}
                
                {/* Enhanced Feedback: Equalizer solely for Active+Playing+NotLoading */}
                {isActive && isPlaying && !isLoading && (
                    <div className="z-10 relative group-hover:opacity-0 transition-opacity">
                        <div className="flex items-end gap-0.5 h-3.5">
                            {[0.4, 1.0, 0.7, 0.5].map((h, i) => (
                                <div key={i} className="w-1 bg-white rounded-full animate-[bounce_0.8s_infinite] shadow-[0_0_8px_white]" style={{ height: `${h * 100}%`, animationDelay: `${i * 0.15}s` }}></div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
            <div className="flex-1 min-w-0">
                <h4 className={`text-xs font-black truncate ${isActive ? 'text-white' : 'text-white/80'}`}>{item?.title}</h4>
                <div className="flex items-center gap-2">
                    <p className="text-[10px] font-bold text-white/30 truncate uppercase tracking-wider">{item?.subtitle}</p>
                    {isDownloaded && <CheckCircle2 size={10} className="text-green-400" />}
                </div>
            </div>
            <div className="flex items-center gap-1">
                {!isDownloaded && (
                    <button 
                        onClick={handleDownload}
                        disabled={isDownloading}
                        className={`p-2 transition-all ${isDownloading ? 'text-purple-400 opacity-100' : 'text-white/20 hover:text-white group-hover:opacity-100 opacity-0'}`}
                        title="Download for offline"
                    >
                        {isDownloading ? <Loader2 size={16} className="animate-spin" /> : <DownloadCloud size={16} />}
                    </button>
                )}
                <button 
                    onClick={onRemove}
                    className="p-2 text-white/20 hover:text-red-400 transition-opacity opacity-0 group-hover:opacity-100"
                    title="Remove item"
                >
                    <Trash2 size={18} />
                </button>
            </div>
        </div>
    );
});

const VirtualizedPlaylist = React.memo(({ items, currentIndex, isPlaying, isLoading, onPlay, onRemove }) => {
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
        <div className="space-y-3">
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
                                    isLoading={isLoading}
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
        fetchPlaylists
    } = useLexPlay();

    const progressBarRef = useRef(null);

    const [showBulkModal, setShowBulkModal] = useState(false);
    const [bulkForm, setBulkForm] = useState({ codal: 'RPC', range: '', targetPlaylist: '' });
    const [isBulking, setIsBulking] = useState(false);
    const [bulkError, setBulkError] = useState('');
    const [activeTab, setActiveTab] = useState('player'); // 'player' | 'playlist'

    // Bulk Download Progress State
    const [downloadProgress, setDownloadProgress] = useState(0);
    const [isDownloadingAll, setIsDownloadingAll] = useState(false);
    const [downloadStatusText, setDownloadStatusText] = useState('');

    const handleDownloadAll = async () => {
        if (isDownloadingAll || playlist.length === 0) return;
        
        setIsDownloadingAll(true);
        setDownloadProgress(0);
        
        try {
            const cache = await caches.open('audio-cache');
            let completed = 0;
            const total = playlist.length;
            
            for (const track of playlist) {
                if (track.audio_url) {
                    setDownloadStatusText(`Caching: ${track.title}`);
                    const exists = await cache.match(track.audio_url);
                    if (!exists) {
                        try {
                            const resp = await fetch(track.audio_url);
                            if (resp.ok) await cache.put(track.audio_url, resp);
                        } catch (e) { console.warn(`Failed to cache ${track.title}`, e); }
                    }
                }
                completed++;
                setDownloadProgress(Math.round((completed / total) * 100));
            }
            
            setDownloadStatusText('Playlist Offline!');
            setTimeout(() => {
                setIsDownloadingAll(false);
                setDownloadProgress(0);
            }, 3000);
        } catch (err) {
            console.error('Bulk download failed:', err);
            setIsDownloadingAll(false);
        }
    };

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
                let numStr = String(a.article_number);
                let displayTitle = numStr;

                if (bulkForm.codal === 'CONST') {
                    if (numStr.toUpperCase() === 'PREAMBLE') {
                        displayTitle = 'Preamble';
                    } else if (numStr.includes('-')) {
                        const [art, sect] = numStr.split('-');
                        displayTitle = `Article ${art}, Section ${sect}`;
                    } else {
                        displayTitle = `Article ${numStr}`;
                    }
                } else if (!/^(rule|article|section|preamble)/i.test(numStr)) {
                    displayTitle = (bulkForm.codal === 'ROC' ? `Rule ${numStr}` : `Article ${numStr}`);
                }

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
                    <div className="h-9 w-9 shrink-0 bg-purple-100 dark:bg-purple-900/50 rounded-lg flex items-center justify-center text-purple-300 dark:text-purple-300">
                        <Headphones size={18} />
                    </div>
                    <div className="flex flex-col truncate pr-4">
                        <span className="text-sm font-bold text-gray-900 dark:text-white truncate">
                            {currentTrack ? currentTrack.title : "LexPlay - Nothing queued"}
                        </span>
                        {error ? (
                            <span className="text-[10px] text-red-500 dark:text-red-400 truncate font-medium">⚠ {error}</span>
                        ) : isLoading ? (
                            <span className="text-[10px] text-purple-300 dark:text-purple-300 truncate animate-pulse">Generating audio...</span>
                        ) : (
                            <span className="text-[10px] text-gray-500 dark:text-gray-400 truncate">
                                {currentTrack ? (activePlaylistName ? `${activePlaylistName} • ${currentTrack.subtitle}` : currentTrack.subtitle) : "Add a Codal or Case Digest"}
                            </span>
                        )}
                    </div>
                </div>

                <div className="flex flex-col items-center shrink-0 px-2 sm:px-4 flex-1 justify-center max-w-md gap-0.5">
                    <div className="flex items-center gap-3 sm:gap-4">
                        <button onClick={(e) => { e.stopPropagation(); handlePrevious(); }} className="p-1.5 text-gray-600 hover:text-purple-300 dark:text-gray-400 dark:hover:text-purple-300 transition-colors" disabled={playlist.length === 0}>
                            <SkipBack size={18} />
                        </button>
                        <button
                            onClick={(e) => { e.stopPropagation(); handlePlayPause(); }}
                            disabled={playlist.length === 0}
                            className="h-9 w-9 rounded-full bg-primary hover:bg-purple-700 text-white flex items-center justify-center transition-transform hover:scale-105 disabled:opacity-50"
                        >
                            {isLoading ? (
                                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            ) : isPlaying ? <Pause size={18} fill="currentColor" /> : <Play size={18} fill="currentColor" className="ml-0.5" />}
                        </button>
                        <button onClick={(e) => { e.stopPropagation(); handleNext(); }} className="p-1.5 text-gray-600 hover:text-purple-300 dark:text-gray-400 dark:hover:text-purple-300 transition-colors" disabled={playlist.length === 0}>
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
                className="absolute inset-0 bg-[#0f172a]/80 backdrop-blur-md transition-opacity duration-500 animate-in fade-in"
                onClick={onMinimize}
            />
            
            <div className="relative w-full h-full md:h-[calc(100vh-8rem)] md:w-[90vw] lg:w-[85vw] xl:w-[80vw] md:max-w-6xl md:rounded-[2rem] bg-gradient-to-br from-white/10 via-[#ffffff05] to-transparent backdrop-blur-[40px] border border-white/20 shadow-[0_32px_64px_-16px_rgba(31,38,135,0.4)] overflow-hidden animate-in zoom-in-95 slide-in-from-bottom-10 duration-500">
                {/* Inner shine layer for glass effect */}
                <div className="absolute inset-0 bg-gradient-to-b from-white/10 to-transparent opacity-30 pointer-events-none z-0"></div>
                {/* Global Header Actions (Minimize/Close) */}
                <div className="absolute top-5 right-4 z-[60] flex items-center gap-2 pointer-events-none md:top-6 md:right-6 md:gap-4 lg:top-8 lg:right-8">
                    <button
                        onClick={onMinimize}
                        className="p-1.5 md:p-2.5 bg-white/5 hover:bg-white/10 backdrop-blur-3xl rounded-full border border-white/20 text-white transition-all hover:scale-110 active:scale-95 group pointer-events-auto shadow-xl"
                        title="Minimize Player"
                    >
                        <Minimize2 size={14} className="md:w-5 md:h-5 transition-transform group-hover:scale-110" />
                    </button>
                    <button
                        onClick={handleCloseInternal}
                        className="p-1.5 md:p-2.5 bg-red-500/10 hover:bg-red-500/20 backdrop-blur-3xl rounded-full border border-red-500/30 text-red-400 transition-all hover:scale-110 active:scale-95 group pointer-events-auto shadow-xl"
                        title="Close Player"
                    >
                        <X size={14} className="md:w-5 md:h-5 transition-transform group-hover:rotate-90" />
                    </button>
                </div>

                <div className="flex flex-col md:flex-row-reverse h-full w-full relative">
                    {/* Mobile View Switcher - Pill Style */}
                    <div className="md:hidden absolute top-6 left-1/2 -translate-x-1/2 z-[55] flex bg-white/5 backdrop-blur-xl border border-white/10 rounded-full p-0.5 shadow-2xl">
                        <button
                            onClick={() => setActiveTab('player')}
                            className={`px-4 py-1.5 rounded-full text-[9px] font-extrabold uppercase tracking-widest transition-all duration-300 ${activeTab === 'player' ? 'bg-white text-[#0f172a] shadow-lg' : 'text-white/40 hover:text-white/60'}`}
                        >
                            Player
                        </button>
                        <button
                            onClick={() => setActiveTab('playlist')}
                            className={`px-4 py-1.5 rounded-full text-[9px] font-extrabold uppercase tracking-widest transition-all duration-300 ${activeTab === 'playlist' ? 'bg-white text-[#0f172a] shadow-lg' : 'text-white/40 hover:text-white/60'}`}
                        >
                            Playlist
                        </button>
                    </div>

                    {/* Right Area: Player Stage (Desktop) - Moves to top on mobile */}
                    <div className={`flex-1 flex flex-col relative overflow-y-auto scrollbar-hide transition-all duration-500 ease-in-out ${activeTab === 'player' ? 'opacity-100 translate-x-0' : 'hidden md:flex md:opacity-100 md:translate-x-0 opacity-0 -translate-x-10'}`}>
                        {/* Background ambient glow - absolute to scroll container so it stays fixed */}
                        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] bg-primary/10 blur-[120px] rounded-full pointer-events-none sticky inset-0"></div>
                        
                        {/* Bulletproof centering inner container */}
                        <div className="m-auto shrink-0 flex flex-col items-center w-full pt-16 pb-6 px-4 md:px-8 z-10">
                        
                        <div className="relative group animate-float flex-shrink-0">
                            <div className="absolute -inset-4 bg-purple-500/30 rounded-[32px] md:rounded-[40px] opacity-40 blur-2xl group-hover:opacity-60 transition-opacity"></div>
                            <div className="relative w-40 h-40 sm:w-48 sm:h-48 lg:w-56 lg:h-56 max-h-[35vh] max-w-[35vh] bg-white/5 border border-white/20 backdrop-blur-md shadow-[0_8px_32px_0_rgba(168,85,247,0.5)] rounded-[30px] md:rounded-[32px] flex items-center justify-center overflow-hidden">
                                {/* Diagonal glassy shine overlay */}
                                <div className="absolute top-0 left-0 right-0 h-1/2 bg-gradient-to-b from-white/20 to-transparent skew-y-12 transform origin-top-left z-0 pointer-events-none"></div>
                                <Headphones size={80} className={`text-white drop-shadow-[0_10px_20px_rgba(168,85,247,0.8)] transform transition-transform duration-700 z-10 md:w-24 md:h-24 ${isPlaying ? '-translate-y-5 md:-translate-y-8 scale-90' : 'group-hover:scale-110'}`} />
                                {isPlaying && (
                                    <div className="absolute bottom-6 md:bottom-8 left-1/2 -translate-x-1/2 flex items-end justify-center gap-2 h-10 md:h-12 z-10 w-full px-4">
                                        {[0.4, 0.8, 0.6, 1.0, 0.5, 0.9, 0.7, 0.3, 0.6, 0.8].map((h, i) => (
                                            <div key={i} className="w-2 md:w-2.5 bg-white shadow-[0_0_10px_rgba(255,255,255,1)] rounded-full animate-[bounce_1s_infinite]" style={{ height: `${h * 100}%`, animationDelay: `${i * 0.1}s` }}></div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="text-center mt-6 max-w-xl z-10">
                            <h2 className="text-3xl lg:text-4xl font-black font-serif text-white mb-2 line-clamp-2 drop-shadow-md">
                                {currentTrack ? currentTrack.title : "LexPlayer is idle"}
                            </h2>
                            <p className="text-lg lg:text-xl text-purple-200 font-extrabold tracking-widest uppercase opacity-90">
                                {currentTrack ? (activePlaylistName ? `${activePlaylistName} • ${currentTrack.subtitle}` : currentTrack.subtitle) : "Add items to your LexPlaylist"}
                            </p>
                            {/* Loading/Error feedback */}
                            <div className="min-h-[2rem] mt-2 flex flex-col items-center justify-center w-full">
                                {error && <div className="inline-flex items-center justify-center gap-2 bg-red-500/20 text-red-400 border-2 border-red-500/40 rounded-2xl px-8 py-3 text-sm font-black animate-in shake">⚠ {error}</div>}
                            </div>
                        </div>

                        <PlaybackProgress audioRef={audioRef} isPlaying={isPlaying} isMinimized={false} />

                        <div className="flex flex-col items-center w-full max-w-2xl z-10 mb-8 mt-4 space-y-8">
                            {/* Floating Modern Controls */}
                            <div className="flex items-center justify-center gap-10 md:gap-14">
                                <button onClick={handlePrevious} disabled={playlist.length === 0} className="text-white/40 hover:text-white transition-all active:scale-90 disabled:opacity-20 hover:drop-shadow-[0_0_12px_rgba(255,255,255,0.5)]">
                                    <SkipBack size={32} fill="currentColor" />
                                </button>
                                
                                <button onClick={handlePlayPause} disabled={playlist.length === 0} className="w-16 h-16 md:w-20 md:h-20 rounded-full bg-purple-500 hover:bg-purple-400 text-white flex items-center justify-center shadow-[0_12px_40px_-10px_rgba(168,85,247,0.8)] transition-all hover:scale-110 active:scale-95 disabled:opacity-50 disabled:hover:scale-100">
                                    {isLoading ? <div className="w-8 h-8 border-4 border-white/20 border-t-white rounded-full animate-spin" /> : (isPlaying ? <Pause size={32} fill="currentColor" /> : <Play size={32} fill="currentColor" className="ml-1.5" />)}
                                </button>
                                
                                <button onClick={handleNext} disabled={playlist.length === 0} className="text-white/40 hover:text-white transition-all active:scale-90 disabled:opacity-20 hover:drop-shadow-[0_0_12px_rgba(255,255,255,0.5)]">
                                    <SkipForward size={32} fill="currentColor" />
                                </button>
                            </div>

                            {/* Minimalist Glowing Typography Speed Selector */}
                            <div className="flex items-center gap-6 opacity-60 hover:opacity-100 transition-opacity">
                                {[0.8, 1.0, 1.25, 1.5, 2.0].map(speed => (
                                    <button 
                                        key={speed} 
                                        onClick={() => setPlaybackRate(speed)} 
                                        className={`text-[10px] md:text-xs font-black tracking-widest uppercase transition-all duration-300 ${playbackRate === speed ? 'text-purple-300 scale-125 drop-shadow-[0_0_10px_rgba(168,85,247,0.8)]' : 'text-white/50 hover:text-white hover:scale-110'}`}
                                    >
                                        {speed === 1 ? '1.0x' : speed + 'x'}
                                    </button>
                                ))}
                            </div>
                        </div>
                        </div>
                    </div>

                    {/* Left Area: Playlist (Desktop) */}
                    <div className={`w-full md:w-72 lg:w-80 xl:w-[420px] bg-[#0f172a]/40 backdrop-blur-[20px] border-b md:border-b-0 md:border-r border-white/10 shadow-[-8px_0_32px_rgba(0,0,0,0.5)] flex flex-col h-full shrink-0 z-20 transition-all duration-500 ease-in-out ${activeTab === 'playlist' ? 'opacity-100 translate-x-0' : 'hidden md:flex md:opacity-100 md:translate-x-0 opacity-0 -translate-x-10'}`}>
                        <div className="p-4 md:p-6 pt-20 md:pt-6 border-b border-white/10 flex items-center justify-between gap-4">
                            <div className="min-w-0 flex-1 flex items-center justify-start gap-4 text-left">
                                <div className="p-2.5 bg-purple-500 rounded-xl border border-white/10 shadow-[0_4px_12px_rgba(168,85,247,0.4)]"><ListMusic className="text-white" size={24} /></div>
                                <div>
                                    <h3 className="text-lg lg:text-xl font-black text-white truncate">
                                        {activePlaylistName || 'LexPlaylist'}
                                    </h3>
                                    <p className="text-[10px] font-bold text-white/30 uppercase tracking-widest">{playlist.length} items</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <button onClick={() => setShowBulkModal(true)} className="flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white px-4 py-2.5 rounded-2xl shadow-[0_8px_20px_rgba(139,92,246,0.3)] transition-all text-xs font-black uppercase tracking-widest flex-shrink-0 animate-in fade-in slide-in-from-left-4 duration-500"><Plus size={18} /> Add Tracks</button>
                                {playlist.length > 0 && (
                                    <button 
                                        onClick={handleDownloadAll}
                                        disabled={isDownloadingAll}
                                        className={`p-2.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl transition-all flex items-center gap-2 ${isDownloadingAll ? 'text-purple-400' : 'text-white/60 hover:text-white'}`}
                                        title="Download All for Offline"
                                    >
                                        {isDownloadingAll ? (
                                            <>
                                                <Loader2 size={20} className="animate-spin" />
                                                <span className="text-[10px] font-black">{downloadProgress}%</span>
                                            </>
                                        ) : (
                                            <DownloadCloud size={20} />
                                        )}
                                    </button>
                                )}
                            </div>
                        </div>

                        {/* Bulk Download Progress Bar Overlay */}
                        {isDownloadingAll && (
                            <div className="px-6 py-3 bg-purple-500/10 border-b border-white/10 animate-in slide-in-from-top-4 duration-300">
                                <div className="flex justify-between items-center mb-1.5">
                                    <span className="text-[9px] font-black text-purple-200 uppercase tracking-widest">{downloadStatusText}</span>
                                    <span className="text-[9px] font-black text-purple-200">{downloadProgress}%</span>
                                </div>
                                <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                                    <div 
                                        className="h-full bg-gradient-to-r from-purple-600 to-purple-400 transition-all duration-500" 
                                        style={{ width: `${downloadProgress}%` }}
                                    />
                                </div>
                            </div>
                        )}

                        <div className="p-6 border-b border-white/5 bg-white/[0.02]">
                            {!isCreating ? (
                                <div className="flex items-center gap-3">
                                    <button onClick={() => setIsCreating(true)} className="px-5 py-3 bg-purple-500 hover:bg-purple-400 text-white rounded-2xl shadow-[0_4px_12px_rgba(168,85,247,0.2)] hover:shadow-[0_8px_20px_rgba(168,85,247,0.3)] text-xs font-black uppercase tracking-widest transition-all flex-shrink-0 min-w-[100px]">Create</button>
                                    <CustomPlaylistSelect
                                        value={activePlaylistId || ''}
                                        onChange={(val) => val && loadSavedPlaylist(val)}
                                        options={savedPlaylists.map(p => ({
                                            value: p.id,
                                            label: `${p.name} (${p.item_count || 0})`
                                        }))}
                                    />
                                </div>
                            ) : (
                                <div className="flex items-center gap-2">
                                    <input type="text" placeholder="Name..." value={newPlaylistName} onChange={(e) => setNewPlaylistName(e.target.value)} className="flex-1 bg-white/5 border border-white/10 text-white text-sm rounded-2xl p-3 outline-none" autoFocus />
                                    <button onClick={async () => { if(newPlaylistName.trim()){ await createPlaylist(newPlaylistName.trim()); setNewPlaylistName(''); setIsCreating(false); }}} className="p-3 bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded-2xl transition-all hover:bg-purple-500/30"><Save size={24} /></button>
                                    <button onClick={() => setIsCreating(false)} className="p-3 bg-white/5 text-white/40 rounded-2xl transition-all"><X size={24} /></button>
                                </div>
                            )}
                            {activePlaylistId && !isCreating && (
                                <div className="mt-4 flex items-center justify-start gap-4 px-2">
                                    {!isEditing ? (
                                        <>
                                            <button 
                                                onClick={() => { setIsEditing(true); setEditPlaylistName(savedPlaylists.find(p => p.id === activePlaylistId)?.name || ''); }} 
                                                className="px-2 py-1 bg-purple-500 hover:bg-purple-400 text-white rounded-lg shadow-sm hover:shadow-md text-[9px] font-black uppercase tracking-widest transition-all flex-shrink-0 flex items-center justify-center gap-1"
                                            >
                                                <Edit2 size={10} /> Rename
                                            </button>
                                            <button 
                                                onClick={() => window.confirm("Delete playlist?") && deletePlaylist(activePlaylistId)} 
                                                className="px-2 py-1 bg-purple-500 hover:bg-purple-400 text-white rounded-lg shadow-sm hover:shadow-md text-[9px] font-black uppercase tracking-widest transition-all flex-shrink-0 flex items-center justify-center gap-1"
                                            >
                                                <Trash2 size={10} /> Delete
                                            </button>
                                        </>
                                    ) : (
                                        <div className="flex items-center gap-2 w-full">
                                            <input type="text" value={editPlaylistName} onChange={(e) => setEditPlaylistName(e.target.value)} className="flex-1 bg-white/5 border border-white/10 text-white text-xs rounded-xl p-2 outline-none" autoFocus />
                                            <button onClick={() => { if(editPlaylistName.trim()){ renamePlaylist(activePlaylistId, editPlaylistName.trim()); setIsEditing(false); }}} className="p-2 text-purple-300 hover:bg-purple-500/10 rounded-xl"><Save size={16} /></button>
                                            <button onClick={() => setIsEditing(false)} className="p-2 text-white/40 hover:bg-white/10 rounded-xl"><X size={16} /></button>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>

                        <div className="flex-1 overflow-y-auto p-6 space-y-4 scroll-smooth overscroll-contain">
                            <VirtualizedPlaylist 
                                items={playlist}
                                currentIndex={currentIndex}
                                isPlaying={isPlaying}
                                isLoading={isLoading}
                                onPlay={handlePlaylistPlay}
                                onRemove={handlePlaylistRemove}
                            />
                        </div>
                    </div>
                </div>
                
                {/* Bulk Add Modal */}
                {showBulkModal && (
                    <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/70 backdrop-blur-3xl">
                        <div className="bg-[#1e293b]/40 backdrop-blur-3xl border border-white/10 rounded-[32px] shadow-2xl w-full max-w-md overflow-hidden">
                            <div className="px-8 py-6 border-b border-white/5 flex justify-between items-center bg-white/[0.02]">
                                <div>
                                    <h3 className="text-xl font-black text-white flex items-center gap-2 tracking-tight">Add Tracks</h3>
                                    <p className="text-[10px] font-black text-white/30 uppercase tracking-[0.2em] mt-1">Bulk create audio queue</p>
                                </div>
                                <button onClick={() => setShowBulkModal(false)} className="text-white/40 hover:text-white"><X size={24} /></button>
                            </div>
                            <div className="p-8 space-y-6">
                                {bulkError && <div className="p-4 bg-red-500/20 text-red-400 border border-red-500/40 rounded-2xl text-xs font-black uppercase">{bulkError}</div>}
                                <div className="space-y-2">
                                    <label className="block text-[10px] font-black text-white/30 uppercase tracking-[0.2em] ml-1">Destination Playlist</label>
                                    <div className="flex h-[46px]">
                                        <CustomPlaylistSelect 
                                            value={bulkForm.targetPlaylist} 
                                            onChange={val => setBulkForm({...bulkForm, targetPlaylist: val})}
                                            options={savedPlaylists.map(p => ({ value: p.id, label: p.name }))}
                                            placeholder="Select a playlist..."
                                        />
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <label className="block text-[10px] font-black text-white/30 uppercase tracking-[0.2em] ml-1">Select Codal</label>
                                    <div className="flex h-[46px]">
                                        <CustomPlaylistSelect 
                                            value={bulkForm.codal} 
                                            onChange={val => setBulkForm({...bulkForm, codal: val})}
                                            options={[
                                                { value: "RPC", label: "Revised Penal Code" },
                                                { value: "CIV", label: "Civil Code" },
                                                { value: "FC", label: "Family Code" },
                                                { value: "CONST", label: "1987 Constitution" },
                                                { value: "LABOR", label: "Labor Code" },
                                                { value: "ROC", label: "Rules of Court" }
                                            ]}
                                        />
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <label className="block text-[10px] font-black text-white/30 uppercase tracking-[0.2em] ml-1">
                                        {bulkForm.codal === 'ROC' ? 'Rule Range (Optional)' : 
                                         bulkForm.codal === 'CONST' ? 'Article / Section Range (Optional)' : 
                                         'Article Range (Optional)'}
                                    </label>
                                    <input type="text" placeholder="e.g. 1-20" value={bulkForm.range} onChange={e => setBulkForm({...bulkForm, range: e.target.value})} className="w-full p-4 bg-white/5 border border-white/10 text-white text-sm rounded-2xl font-bold outline-none" />
                                </div>
                            </div>
                            <div className="px-8 py-6 border-t border-white/5 bg-white/[0.02] flex justify-end gap-4">
                                <button onClick={() => setShowBulkModal(false)} className="text-xs font-black text-white/30 hover:text-white uppercase tracking-widest transition-all">Cancel</button>
                                <button onClick={handleAddBulkItems} disabled={isBulking} className="px-10 py-4 text-xs font-black text-white bg-purple-500 rounded-[20px] hover:bg-purple-400 shadow-xl shadow-purple-500/20 disabled:opacity-50 transition-all active:scale-95 uppercase tracking-widest">
                                    {isBulking ? "Adding..." : "Add to Tracks"}
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
