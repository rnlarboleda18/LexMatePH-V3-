import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useLexPlay } from './useLexPlay';
import {
    Play, Pause, SkipBack, SkipForward, Maximize2, Minimize2,
    Volume2, VolumeX, ListMusic, Trash2, X, Headphones, Plus, Edit2, Save, ChevronDown, RotateCcw,
    Repeat, Repeat1, Shuffle, Rewind, FastForward
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
                className="w-full flex items-center justify-between bg-slate-100/80 dark:bg-white/[0.03] hover:bg-slate-200/80 dark:hover:bg-white/10 border-2 border-slate-300 dark:border-white/10 text-slate-800 dark:text-white text-sm rounded-2xl p-3 outline-none transition-all shadow-sm"
                onClick={() => setIsOpen(!isOpen)}
            >
                <span className={`truncate mr-2 ${!selectedOption ? 'text-slate-400 dark:text-white/40' : 'font-semibold'}`}>
                    {selectedOption ? selectedOption.label : placeholder}
                </span>
                <ChevronDown size={18} className={`text-slate-400 dark:text-white/40 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>
            {isOpen && (
                <div className="absolute z-50 w-full mt-2 bg-white/95 dark:bg-[#0f172a]/95 backdrop-blur-3xl border-2 border-slate-200 dark:border-white/10 rounded-2xl shadow-2xl py-2 max-h-60 overflow-y-auto">
                    {options.length === 0 && (
                        <div className="px-4 py-3 text-sm text-slate-400 dark:text-white/40 italic text-center">No playlists found</div>
                    )}
                    {options.map((option) => (
                        <button
                            key={option.value}
                            type="button"
                            className={`w-full text-left px-4 py-3 text-sm transition-colors hover:bg-purple-600/30 hover:text-slate-900 dark:hover:text-white ${value === option.value ? 'bg-purple-600/20 text-purple-600 dark:text-purple-300 font-bold' : 'text-slate-600 dark:text-white/70'}`}
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
            <div className="flex justify-between text-xs font-bold text-slate-600 dark:text-white/60 mb-2 px-2 tracking-widest font-mono">
                <span>{formatTime(currentTime)}</span>
                <span>{formatTime(duration)}</span>
            </div>
            <div
                className="h-3 glass bg-slate-200/80 dark:bg-white/10 border-2 border-slate-300 dark:border-white/10 shadow-inner rounded-full cursor-pointer relative group overflow-hidden"
                ref={progressBarRef}
                onMouseDown={onMouseDown}
                onTouchStart={onMouseDown}
            >
                <div className="absolute top-0 left-0 h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full shadow-[0_0_10px_rgba(99,102,241,0.5)]" style={{ width: `${progressPercent}%` }} />
                <div className={`absolute top-1/2 -translate-y-1/2 -ml-2.5 w-5 h-5 bg-white rounded-full scale-0 group-hover:scale-100 ${isScrubbing ? 'scale-125' : ''} transition-all duration-200 border-4 border-purple-600 shadow-lg`} style={{ left: `${progressPercent}%` }} />
            </div>
        </div>
    );
};

/**
 * PlaylistItem: Memoized track item to prevent re-rendering when other items are interacting.
 */
const PlaylistItem = React.memo(({ item, index, isActive, isPlaying, isLoading, onPlay, onRemove }) => {
    if (!item) return null;

    return (
        <div className={`relative group flex items-center gap-3 p-3 rounded-2xl border-2 transition-all duration-300 ${isActive ? 'glass bg-white/80 dark:bg-white/10 border-indigo-200/60 dark:border-white/20 shadow-xl scale-[1.02]' : 'glass bg-slate-100/50 dark:bg-slate-800/20 border-slate-200 dark:border-transparent hover:border-slate-300 dark:hover:border-white/20 hover:bg-white/60 dark:hover:bg-white/10'}`}>
            <div className={`relative w-11 h-11 rounded-xl overflow-hidden flex-shrink-0 flex items-center justify-center border-2 transition-colors ${isActive ? 'bg-gradient-to-br from-indigo-500 to-purple-600 border-none shadow-lg' : 'bg-slate-200/50 dark:bg-white/5 border-slate-300/50 dark:border-white/10'}`}>
                
                {/* Action Overlay: Hover state, or Active+Paused state; also show when loading */}
                <div className={`absolute inset-0 z-20 bg-purple-600/80 flex items-center justify-center transition-opacity ${(isActive && (!isPlaying || isLoading)) ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}>
                    <button onClick={onPlay} className="text-white w-full h-full flex items-center justify-center">
                        {isActive && isLoading
                            ? (
                                <div className="relative w-7 h-7 flex items-center justify-center">
                                    <div className="absolute inset-0 border-2 border-white/20 rounded-full" />
                                    <div className="absolute inset-0 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                    <div className="w-1.5 h-1.5 bg-white rounded-full animate-pulse shadow-[0_0_8px_rgba(255,255,255,0.8)]" />
                                </div>
                            )
                            : isActive && isPlaying
                                ? <Pause size={24} fill="currentColor" />
                                : <Play size={24} fill="currentColor" />}
                    </button>
                </div>

                {/* Track Number: Default state when completely inactive */}
                {!isActive && <span className="text-lg font-bold text-slate-400 dark:text-white/20 z-10 relative group-hover:opacity-0 transition-opacity">{index + 1}</span>}
                
                {/* Playing Animation: Default state when playing (and not loading) */}
                {isActive && isPlaying && !isLoading && (
                    <div className="flex items-end gap-1 h-4 z-10 relative group-hover:opacity-0 transition-opacity">
                        {[0.4, 1.0, 0.6].map((h, i) => (
                            <div key={i} className="w-1 bg-white rounded-full animate-[bounce_1s_infinite]" style={{ height: `${h * 100}%`, animationDelay: `${i * 0.1}s` }}></div>
                        ))}
                    </div>
                )}
            </div>
            <div className="flex-1 min-w-0 pr-8">
                <h4 className={`text-sm font-bold truncate ${isActive ? 'text-slate-900 dark:text-white' : 'text-slate-700 dark:text-white/80'}`}>{item?.title}</h4>
                <p className="text-xs text-slate-500 dark:text-white/40 truncate">{item?.subtitle}</p>
            </div>
            <button 
                onClick={onRemove}
                className="absolute right-4 top-1/2 -translate-y-1/2 p-2 text-slate-400 dark:text-white/20 hover:text-red-500 dark:hover:text-red-400 transition-opacity opacity-0 group-hover:opacity-100"
            >
                <Trash2 size={18} />
            </button>
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
        <div className="space-y-6">
            {/* Optional: we removed the floating duplicate current track so the list flows naturally */}

            {items.length > 0 && (
                <div className="space-y-4" ref={containerRef}>
                    <div className="flex items-center justify-between px-2">
                        <h4 className="text-[10px] font-bold text-slate-500 dark:text-white/40 uppercase tracking-widest">Playlist</h4>
                        <button 
                            onClick={() => {
                                const activeItem = containerRef.current?.querySelector('[data-active="true"]');
                                activeItem?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            }}
                            className="text-[10px] font-bold text-slate-500 hover:text-slate-700 dark:text-white/40 dark:hover:text-white/60 uppercase tracking-widest transition-colors"
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
                                    isLoading={index === currentIndex ? isLoading : false}
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
    isLoading,
    onPlay, 
    onRemove 
}) => {
    return (
        <VirtualizedPlaylist
            items={playlist}
            currentIndex={currentIndex}
            isPlaying={isPlaying}
            isLoading={isLoading}
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
        volume,
        setVolume,
        repeatMode,
        cycleRepeatMode,
        isShuffle,
        toggleShuffle,
        handleScrubForward,
        handleScrubBackward,
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

    // Dynamic Layout Offset Management: Update global CSS variable when minimized
    useEffect(() => {
        const root = document.documentElement;
        if (isMinimized) {
            // Minimized height is roughly 72-80px depending on sm/md breakpoints. 
            // 76px is a good safe average that prevents modal overlap.
            root.style.setProperty('--player-height', '76px');
        } else {
            root.style.setProperty('--player-height', '0px');
        }
        
        return () => {
            root.style.setProperty('--player-height', '0px');
        };
    }, [isMinimized]);

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
                // Build display title based on codal type
                let displayTitle;
                if (/^preamble$/i.test(numStr)) {
                    displayTitle = 'Preamble';
                } else if (/^(rule|article|preamble)/i.test(numStr)) {
                    displayTitle = numStr; // Already has prefix
                } else if (/^section/i.test(numStr)) {
                    displayTitle = numStr; // "SECTION 1." etc
                } else if (bulkForm.codal === 'ROC') {
                    displayTitle = `Rule ${numStr}`;
                } else if (bulkForm.codal === 'CONST') {
                    // CONST article_nums: 'I', 'II', 'II-1', 'IX-A-1', 'PREAMBLE'
                    // Build a readable label
                    const parts = numStr.split('-');
                    if (parts.length === 1) {
                        displayTitle = `Article ${numStr}`; // 'I', 'II', etc.
                    } else if (parts.length === 2) {
                        displayTitle = `Article ${parts[0]}, Section ${parts[1]}`; // 'II-1' → 'Article II, Section 1'
                    } else {
                        // 'IX-A-1' → 'Article IX-A, Section 1'
                        displayTitle = `Article ${parts.slice(0, -1).join('-')}, Section ${parts[parts.length - 1]}`;
                    }
                } else {
                    displayTitle = `Article ${numStr}`;
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
            <>
                <style dangerouslySetInnerHTML={{__html: `
                    @keyframes marquee {
                        0% { transform: translateX(0); }
                        100% { transform: translateX(-50%); }
                    }
                    .animate-marquee { animation: marquee 18s linear infinite; }
                    .marquee-container {
                        overflow: hidden;
                        mask-image: linear-gradient(to right, transparent, black 8%, black 92%, transparent);
                    }
                    @keyframes miniplayer-pulse {
                        0%, 100% { box-shadow: 0 8px 32px rgba(139,92,246,0.25), 0 2px 8px rgba(0,0,0,0.3); }
                        50% { box-shadow: 0 8px 40px rgba(139,92,246,0.45), 0 2px 12px rgba(0,0,0,0.4); }
                    }
                    .miniplayer-glow { animation: miniplayer-pulse 3s ease-in-out infinite; }
                `}} />

                {/* Mini Player Bar */}
                <div className="fixed bottom-0 left-0 right-0 z-50 miniplayer-glow border-t border-white/20 dark:border-white/10">
                    <div className="relative overflow-hidden glass bg-white/80 dark:bg-slate-900/80 backdrop-blur-2xl shadow-[0_-10px_40px_rgba(0,0,0,0.2)]">

                        {/* Ambient color blob when playing */}
                        {isPlaying && (
                            <div className="absolute inset-0 pointer-events-none">
                                <div className="absolute top-0 left-1/4 w-48 h-12 bg-purple-500/20 blur-2xl rounded-full" />
                                <div className="absolute top-0 right-1/4 w-32 h-8 bg-indigo-500/10 blur-2xl rounded-full" />
                            </div>
                        )}

                        {/* Progress bar — always at top */}
                        <div onClick={(e) => e.stopPropagation()}>
                            <PlaybackProgress audioRef={audioRef} isPlaying={isPlaying} isMinimized={true} />
                        </div>

                        {/* Main row */}
                        <div 
                            className="flex items-center justify-between px-3 py-2.5 sm:px-6 sm:py-3 w-full cursor-pointer group"
                            onClick={onExpand}
                        >

                            {/* Left Area: Album Art & Track Info (1/3 Width) */}
                            <div className="flex items-center gap-3 flex-1 min-w-0">
                                {/* Album Art / Icon */}
                                <div className="relative shrink-0 w-10 h-10 sm:w-11 sm:h-11 rounded-xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center shadow-lg overflow-hidden">
                                    <Headphones size={20} className={`text-white z-10 transition-transform duration-300 ${isPlaying ? 'scale-90' : 'group-hover:scale-110'}`} />
                                    {isPlaying && (
                                        <div className="absolute bottom-1 left-1/2 -translate-x-1/2 flex items-end gap-[2px] h-3 z-10">
                                            {[0.5, 1, 0.7, 0.9, 0.6].map((h, i) => (
                                                <div key={i} className="w-[3px] bg-white/80 rounded-t-sm animate-[bounce_0.8s_infinite]" style={{ height: `${h * 100}%`, animationDelay: `${i * 0.12}s` }} />
                                            ))}
                                        </div>
                                    )}
                                </div>

                                {/* Track Info */}
                                <div className="flex-col min-w-0 pr-4 hidden sm:flex">
                                    <div className="w-full max-w-[200px] xl:max-w-[250px] overflow-hidden">
                                        <span className="text-sm font-bold text-slate-900 dark:text-white leading-tight truncate block">
                                            {currentTrack ? currentTrack.title : 'LexPlay — Nothing queued'}
                                        </span>
                                    </div>
                                    {error ? (
                                        <div className="flex items-center gap-1.5 mt-0.5">
                                            <span className="text-[10px] text-red-500 truncate font-semibold">⚠ {error}</span>
                                            <button onClick={(e) => { e.stopPropagation(); retryCurrentTrack(); }} className="text-[9px] px-1.5 py-0.5 bg-red-500/10 border border-red-500/20 text-red-500 rounded font-extrabold uppercase tracking-widest hover:bg-red-500/20 transition-all">Retry</button>
                                        </div>
                                    ) : isLoading ? (
                                        <span className="text-[10px] text-purple-500 dark:text-purple-400 animate-pulse font-semibold">Generating audio…</span>
                                    ) : (
                                        <span className="text-[10px] text-slate-500 dark:text-white/50 truncate block font-medium">
                                            {currentTrack ? (activePlaylistName ? `${activePlaylistName} · ${currentTrack.subtitle}` : currentTrack.subtitle) : 'Add a Codal or Case Digest'}
                                        </span>
                                    )}
                                </div>
                            </div>

                            {/* Center Area: Transport Controls (1/3 Width) */}
                            <div className="flex items-center justify-center gap-2 sm:gap-4 flex-1 shrink-0">
                                <button onClick={(e) => { e.stopPropagation(); handlePrevious(); }} disabled={playlist.length === 0} className="p-2 text-slate-500 dark:text-white/50 hover:text-purple-600 dark:hover:text-white transition-all active:scale-90 disabled:opacity-30 rounded-full hover:bg-black/5 dark:hover:bg-white/10">
                                    <SkipBack size={18} />
                                </button>
                                <button onClick={(e) => { e.stopPropagation(); handlePlayPause(); }} disabled={playlist.length === 0} className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-purple-600 hover:bg-purple-500 dark:bg-white dark:hover:bg-white/90 text-white dark:text-slate-900 flex items-center justify-center shadow-[0_8px_30px_rgba(139,92,246,0.3)] hover:scale-105 active:scale-95 transition-all disabled:opacity-40">
                                    {isLoading ? (
                                        <div className="relative w-6 h-6 flex items-center justify-center">
                                            <div className="absolute inset-0 border-2 border-current/20 rounded-full" />
                                            <div className="absolute inset-0 border-2 border-current border-t-transparent rounded-full animate-spin" />
                                            <div className="w-1 h-1 bg-current rounded-full animate-pulse" />
                                        </div>
                                    ) : isPlaying ? (
                                        <Pause size={20} fill="currentColor" />
                                    ) : (
                                        <Play size={20} fill="currentColor" className="ml-0.5" />
                                    )}
                                </button>
                                <button onClick={(e) => { e.stopPropagation(); handleNext(); }} disabled={playlist.length === 0} className="p-2 text-slate-500 dark:text-white/50 hover:text-purple-600 dark:hover:text-white transition-all active:scale-90 disabled:opacity-30 rounded-full hover:bg-black/5 dark:hover:bg-white/10">
                                    <SkipForward size={18} />
                                </button>
                            </div>

                            {/* Right Area: Expand + Close (1/3 Width) */}
                            <div className="flex items-center justify-end gap-1 flex-1 min-w-0">
                                <div className="hidden md:flex p-2 text-slate-400 dark:text-white/30 hover:text-purple-600 dark:hover:text-white transition-all active:scale-90 rounded-full hover:bg-black/5 dark:hover:bg-white/10" title="Expand Player">
                                    <Maximize2 size={16} />
                                </div>
                                <button onClick={(e) => { e.stopPropagation(); handleCloseInternal(); }} className="p-2 text-slate-400 dark:text-white/30 hover:text-red-500 transition-all active:scale-90 rounded-full hover:bg-red-500/10 ml-1" title="Close Player">
                                    <X size={18} />
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </>
        );
    }


    // Full Screen Mode
    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
            {/* Backdrop Overlay */}
            <div 
                className="absolute inset-0 bg-slate-100/40 dark:bg-black/60 backdrop-blur-md transition-opacity duration-500 animate-in fade-in"
                onClick={onMinimize}
            />
            
            <div className="relative flex flex-col w-full h-full md:h-[calc(100vh-14rem)] md:w-[90vw] lg:w-[85vw] xl:w-[80vw] md:max-w-6xl md:rounded-[3rem] glass bg-white/80 dark:bg-slate-900/40 backdrop-blur-3xl border-2 border-slate-200/60 dark:border-white/20 shadow-[0_30px_70px_-15px_rgba(0,0,0,0.3)] dark:shadow-2xl overflow-hidden animate-in zoom-in-95 slide-in-from-bottom-10 duration-500">
                {/* Ambient Glow Orbs */}
                <div className="absolute top-[-10%] left-[-10%] w-[40vw] h-[40vw] max-w-[500px] max-h-[500px] bg-blue-500/20 rounded-full blur-[100px] pointer-events-none mix-blend-screen animate-pulse"></div>
                <div className="absolute bottom-[-10%] right-[-10%] w-[40vw] h-[40vw] max-w-[500px] max-h-[500px] bg-purple-500/20 rounded-full blur-[100px] pointer-events-none mix-blend-screen animate-pulse" style={{ animationDelay: '1s' }}></div>

                {/* Global Header Actions - absolute right to not interfere with flex heights */}
                <div className="absolute top-6 right-6 z-[60] flex items-center justify-end p-2 md:p-3 gap-2 md:gap-3 bg-transparent pointer-events-none">
                    <div className="pointer-events-auto flex gap-2 md:gap-3">
                    <button
                        onClick={onMinimize}
                        className="p-2 bg-white/20 hover:bg-white/30 dark:bg-white/5 dark:hover:bg-white/10 backdrop-blur-md rounded-full border border-white/30 dark:border-white/10 text-slate-800 dark:text-white transition-all hover:scale-110 active:scale-95"
                        title="Minimize Player"
                    >
                        <Minimize2 size={18} />
                    </button>
                    <button
                        onClick={handleCloseInternal}
                        className="p-2 bg-red-500/20 hover:bg-red-500/40 backdrop-blur-md rounded-full border border-red-500/30 text-red-500 dark:text-red-400 transition-all hover:scale-110 active:scale-95"
                        title="Close Player"
                    >
                        <X size={18} />
                    </button>
                    </div>
                </div>

                <div className="flex flex-col md:flex-row flex-1 min-h-0 h-full w-full relative items-stretch pt-16 md:pt-4">
                    {/* Mobile View Switcher - Pill Style */}
                    <div className="md:hidden absolute top-4 left-1/2 -translate-x-1/2 z-[55] flex bg-white/5 backdrop-blur-xl border border-white/10 rounded-full p-0.5 shadow-2xl">
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
                    <div className={`flex-1 md:flex-none w-full md:w-72 lg:w-80 xl:w-[400px] h-full !rounded-none bg-slate-50/70 dark:bg-black/40 backdrop-blur-2xl border-b-2 border-slate-200/80 dark:border-white/10 md:border-b-0 md:border-r-2 flex flex-col min-h-0 shrink-0 z-20 transition-all duration-500 ease-in-out ${activeTab === 'playlist' ? 'opacity-100 translate-x-0' : 'hidden md:flex md:opacity-100 md:translate-x-0 opacity-0 -translate-x-10'}`}>
                        {/* Empty space at top so the header buttons don't overlap on mobile if needed, though they are on right */}
                        <div className="p-4 md:p-6 pt-16 md:pt-14 border-b border-white/10 flex flex-col gap-4">
                            <div className="flex items-center gap-4">
                                <div className="p-2 bg-gradient-to-br from-indigo-500/20 to-purple-500/20 rounded-xl border border-white/20 shadow-inner"><ListMusic className="text-purple-600 dark:text-purple-400" size={24} /></div>
                                <div>
                                    <h3 className="text-lg lg:text-xl font-bold text-slate-900 dark:text-white drop-shadow-sm">
                                        {activePlaylistName || 'LexPlaylist'}
                                    </h3>
                                    <p className="text-[10px] font-bold text-slate-500 dark:text-white/50 uppercase tracking-widest">{playlist.length} items</p>
                                </div>
                                <button onClick={() => setShowBulkModal(true)} className="ml-auto flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white px-4 py-2.5 rounded-2xl shadow-lg transition-all text-sm font-bold"><Plus size={18} /> Add Items</button>
                            </div>
                            
                            {/* Rename / Delete Actions moved up here */}
                            {activePlaylistId && !isCreating && (
                                <div className="flex items-center justify-start gap-4 px-1">
                                    {!isEditing ? (
                                        <>
                                            <button onClick={() => { setIsEditing(true); setEditPlaylistName(savedPlaylists.find(p => p.id === activePlaylistId)?.name || ''); }} className="text-xs font-bold text-slate-400 dark:text-white/40 hover:text-purple-600 dark:hover:text-purple-400 flex items-center gap-1.5 transition-all">
                                                <Edit2 size={14} /> Rename
                                            </button>
                                            <button onClick={() => window.confirm("Delete playlist?") && deletePlaylist(activePlaylistId)} className="text-xs font-bold text-slate-400 dark:text-white/40 hover:text-red-500 dark:hover:text-red-400 flex items-center gap-1.5 transition-all">
                                                <Trash2 size={14} /> Delete
                                            </button>
                                        </>
                                    ) : (
                                        <div className="flex items-center gap-2 w-full max-w-[200px]">
                                            <input type="text" value={editPlaylistName} onChange={(e) => setEditPlaylistName(e.target.value)} className="flex-1 bg-black/5 dark:bg-white/5 border-2 border-slate-200 dark:border-white/10 text-slate-800 dark:text-white text-xs rounded-xl p-2 outline-none" autoFocus />
                                            <button onClick={() => { if(editPlaylistName.trim()){ renamePlaylist(activePlaylistId, editPlaylistName.trim()); setIsEditing(false); }}} className="p-2 text-green-500 dark:text-green-400 hover:bg-green-500/10 rounded-xl"><Save size={16} /></button>
                                            <button onClick={() => setIsEditing(false)} className="p-2 text-slate-400 dark:text-white/40 hover:bg-black/5 dark:hover:bg-white/10 rounded-xl"><X size={16} /></button>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>

                        <div className="p-6 border-b-2 border-slate-200 dark:border-white/5 bg-slate-50/50 dark:bg-white/[0.02]">
                            {!isCreating ? (
                                <div className="flex items-center gap-3">
                                    <button onClick={() => setIsCreating(true)} className="px-3 py-3 bg-slate-200 dark:bg-white/5 text-slate-700 dark:text-white/80 rounded-2xl border-2 border-slate-300 dark:border-white/10 hover:text-slate-900 dark:hover:text-white text-xs font-bold whitespace-nowrap transition-all shadow-sm shadow-black/5 dark:shadow-none">Create</button>
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
                                    <input type="text" placeholder="Name..." value={newPlaylistName} onChange={(e) => setNewPlaylistName(e.target.value)} className="flex-1 bg-black/5 dark:bg-white/5 border-2 border-slate-200 dark:border-white/10 text-slate-800 dark:text-white text-sm rounded-2xl p-3 outline-none" autoFocus />
                                    <button onClick={async () => { if(newPlaylistName.trim()){ const created = await createPlaylist(newPlaylistName.trim()); setNewPlaylistName(''); setIsCreating(false); if(created?.id) { setShowBulkModal(true); } }}} className="p-3 bg-green-500/20 text-green-500 dark:text-green-400 rounded-2xl transition-all"><Save size={24} /></button>
                                    <button onClick={() => setIsCreating(false)} className="p-3 bg-black/5 dark:bg-white/5 text-slate-400 dark:text-white/40 rounded-2xl transition-all hover:bg-black/10 dark:hover:bg-white/10"><X size={24} /></button>
                                </div>
                            )}
                        </div>

                        <div className="flex-1 overflow-y-auto p-6 space-y-4 scroll-smooth overscroll-contain">
                            <PlaylistList 
                                playlist={playlist}
                                currentIndex={currentIndex}
                                isPlaying={isPlaying}
                                isLoading={isLoading}
                                onPlay={handlePlaylistPlay}
                                onRemove={handlePlaylistRemove}
                            />
                        </div>
                    </div>
                    {/* Right Area: Now Playing & Controls */}
                    <div className={`flex-1 flex flex-col min-h-0 relative transition-all duration-500 ease-in-out ${activeTab === 'player' ? 'opacity-100 translate-x-0' : 'hidden md:flex md:opacity-100 md:translate-x-0 opacity-0 translate-x-10'}`}>
                        {/* Background ambient glow */}
                        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] bg-purple-600/10 blur-[120px] rounded-full pointer-events-none"></div>
                        
                        {/* Scrollable inner player content */}
                        <div className="flex-1 overflow-y-auto scrollbar-hide flex flex-col items-center justify-center px-4 md:px-8 py-4 gap-3 z-10">

                        <div className="relative group animate-float flex-shrink-0">
                            <div className="absolute -inset-4 bg-gradient-to-tr from-indigo-500 via-purple-500 to-pink-500 rounded-[32px] opacity-20 blur-2xl group-hover:opacity-40 transition-opacity"></div>
                            <div className="relative w-28 h-28 sm:w-36 sm:h-36 md:w-40 md:h-40 lg:w-48 lg:h-48 glass bg-white/30 dark:bg-white/10 backdrop-blur-xl border border-white/40 shadow-2xl rounded-[24px] md:rounded-[32px] flex items-center justify-center overflow-hidden">
                                <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/40 via-purple-500/40 to-pink-500/40 opacity-80"></div>
                                <Headphones size={52} className={`text-white drop-shadow-2xl transform transition-transform duration-700 z-10 sm:w-14 sm:h-14 md:w-16 md:h-16 ${isPlaying ? '-translate-y-3 scale-90 opacity-50' : 'group-hover:scale-110 opacity-100'}`} />
                                {isPlaying && (
                                    <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex items-end justify-center gap-1 h-7 z-10 w-full px-4">
                                        {[0.4, 0.8, 0.6, 1.0, 0.5, 0.9, 0.7, 0.3, 0.6, 0.8].map((h, i) => (
                                            <div key={i} className="w-1.5 bg-white shadow-[0_0_8px_rgba(255,255,255,0.8)] rounded-t-sm animate-[bounce_1s_infinite]" style={{ height: `${h * 100}%`, animationDelay: `${i * 0.15}s` }}></div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="text-center max-w-xl z-10 px-4">
                            <h2 className="text-lg sm:text-xl md:text-2xl font-extrabold font-serif text-slate-900 dark:text-white mb-1 line-clamp-2 drop-shadow-md tracking-tight">
                                {currentTrack ? currentTrack.title : "LexPlayer is idle"}
                            </h2>
                            <p className="text-[10px] sm:text-xs text-purple-600 dark:text-purple-300 font-bold tracking-widest uppercase opacity-90">
                                {currentTrack ? (activePlaylistName ? `${activePlaylistName} • ${currentTrack.subtitle}` : currentTrack.subtitle) : "Add items to your LexPlaylist"}
                            </p>
                            <div className="min-h-[2rem] mt-1 flex items-center justify-center w-full">
                                {error && (
                                    <div className="flex flex-col items-center gap-2">
                                        <div className="inline-flex items-center gap-2 bg-red-500/10 text-red-400 border border-red-500/20 rounded-2xl px-4 py-1.5 text-xs font-semibold">⚠ {error}</div>
                                        <button onClick={retryCurrentTrack} className="px-4 py-1.5 bg-white/5 hover:bg-white/10 text-white text-[10px] font-bold rounded-full border border-white/10 transition-all flex items-center gap-1.5 active:scale-95">
                                            <RotateCcw size={12} /> Retry
                                        </button>
                                    </div>
                                )}
                                {isLoading && !error && <div className="inline-flex items-center gap-2 bg-white/5 text-white/80 border border-white/10 rounded-2xl px-4 py-1.5 text-xs font-semibold animate-pulse">Generating...</div>}
                            </div>
                        </div>

                        <PlaybackProgress audioRef={audioRef} isPlaying={isPlaying} isMinimized={false} />

                        <div className="w-full max-w-xl flex flex-col gap-2 md:gap-3 z-10 px-2">
                            {/* Transport Controls Row */}
                            <div className="flex items-center justify-center gap-4 sm:gap-6 md:gap-8">
                                <button onClick={toggleShuffle} className={`p-1.5 transition-all active:scale-90 ${isShuffle ? 'text-purple-600 dark:text-purple-400' : 'text-slate-500 dark:text-white/40 hover:text-slate-800 dark:hover:text-white/80'}`}>
                                    <Shuffle size={16} strokeWidth={2.5} />
                                </button>
                                <button onClick={handlePrevious} disabled={playlist.length === 0} className="p-2 text-slate-700 dark:text-white/80 hover:text-purple-600 dark:hover:text-white transition-all active:scale-90 disabled:opacity-30">
                                    <SkipBack size={22} fill="currentColor" />
                                </button>
                                <button onClick={handlePlayPause} disabled={playlist.length === 0} className="w-12 h-12 md:w-14 md:h-14 glass bg-white/80 dark:bg-white/20 backdrop-blur-2xl border-2 border-slate-200 dark:border-white/30 text-purple-600 dark:text-white rounded-full flex items-center justify-center shadow-xl hover:scale-105 active:scale-95 transition-all">
                                    {isLoading ? (
                                        <div className="relative w-9 h-9 flex items-center justify-center">
                                            <div className="absolute inset-0 border-[3.5px] border-purple-500/20 rounded-full" />
                                            <div className="absolute inset-0 border-[3.5px] border-purple-500 border-t-transparent rounded-full animate-spin" />
                                            <div className="w-2.5 h-2.5 bg-purple-500 rounded-full animate-pulse shadow-[0_0_12px_rgba(168,85,247,0.6)]" />
                                        </div>
                                    ) : (
                                        isPlaying ? <Pause size={28} fill="currentColor" /> : <Play size={28} fill="currentColor" className="ml-1" />
                                    )}
                                </button>
                                <button onClick={handleNext} disabled={playlist.length === 0} className="p-2 text-slate-700 dark:text-white/80 hover:text-purple-600 dark:hover:text-white transition-all active:scale-90 disabled:opacity-30">
                                    <SkipForward size={22} fill="currentColor" />
                                </button>
                                <button onClick={cycleRepeatMode} className={`p-1.5 transition-all active:scale-90 ${repeatMode !== 'none' ? 'text-purple-600 dark:text-purple-400' : 'text-slate-500 dark:text-white/40 hover:text-slate-800 dark:hover:text-white/80'}`}>
                                    {repeatMode === 'one' ? <Repeat1 size={16} strokeWidth={2.5} /> : <Repeat size={16} strokeWidth={2.5} />}
                                </button>
                            </div>

                            {/* Speed & Scrub Tools Row */}
                            <div className="flex items-center justify-between gap-3 w-full glass bg-slate-100/90 dark:bg-slate-900/50 backdrop-blur-xl border-2 border-slate-200 dark:border-white/10 rounded-2xl px-4 py-2.5 shadow-sm dark:shadow-none">
                                <button onClick={handleScrubBackward} className="flex flex-col items-center p-1 text-slate-600 dark:text-white/60 hover:text-purple-600 dark:hover:text-white transition-colors active:scale-90">
                                    <Rewind size={16} />
                                    <span className="text-[8px] font-extrabold mt-0.5 tracking-widest">-10s</span>
                                </button>
                                <div className="flex flex-wrap justify-center gap-1">
                                    {[0.8, 1.0, 1.25, 1.5, 2.0].map(speed => (
                                        <button key={speed} onClick={() => setPlaybackRate(speed)} className={`px-2 py-1 text-[10px] font-extrabold rounded-lg transition-all ${playbackRate === speed ? 'bg-purple-600 text-white shadow-md' : 'text-slate-600 dark:text-white/50 hover:bg-slate-200 dark:hover:bg-white/10'}`}>
                                            {speed === 1 ? '1x' : speed + 'x'}
                                        </button>
                                    ))}
                                </div>
                                <button onClick={handleScrubForward} className="flex flex-col items-center p-1 text-slate-500 dark:text-white/60 hover:text-purple-600 dark:hover:text-white transition-colors active:scale-90">
                                    <FastForward size={16} />
                                    <span className="text-[8px] font-extrabold mt-0.5 tracking-widest">+10s</span>
                                </button>
                            </div>

                            {/* Volume Row */}
                            <div className="flex items-center justify-center gap-3 w-full max-w-xs mx-auto opacity-60 hover:opacity-100 transition-opacity">
                                <button onClick={() => setVolume(volume === 0 ? 1 : 0)} className="text-slate-500 dark:text-white/60 hover:text-purple-600 dark:hover:text-white transition-colors">
                                    {volume === 0 ? <VolumeX size={14} /> : <Volume2 size={14} />}
                                </button>
                                <input type="range" min="0" max="1" step="0.01" value={volume}
                                    onChange={(e) => setVolume(parseFloat(e.target.value))}
                                    className="w-full h-1 bg-slate-300 dark:bg-slate-700/50 rounded-full appearance-none cursor-pointer"
                                    style={{ backgroundImage: `linear-gradient(to right, #9333ea ${volume * 100}%, transparent ${volume * 100}%)` }}
                                />
                            </div>
                        </div>

                        </div>{/* end scrollable */}
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
