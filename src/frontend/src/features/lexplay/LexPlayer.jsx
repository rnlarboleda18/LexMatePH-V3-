import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { createPortal } from 'react-dom';
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
    const selectedOption = options?.find(o => o.value === value);

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
                    {options?.length === 0 && (
                        <div className="px-4 py-3 text-sm text-white/40 italic text-center">No playlists found</div>
                    )}
                    {options?.map((option) => (
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
        /* Thin scrub — keep bar short on desktop */
        return (
            <div
                ref={progressBarRef}
                className="relative w-full h-[4px] cursor-pointer group touch-manipulation select-none"
                onMouseDown={onMouseDown}
                onTouchStart={onMouseDown}
                role="slider"
                aria-valuenow={Math.round(currentTime)}
                aria-valuemin={0}
                aria-valuemax={duration && !Number.isNaN(duration) ? Math.round(duration) : 100}
                aria-label="Playback position"
            >
                <div className="absolute left-0 right-0 top-1/2 -translate-y-1/2 h-0.5 bg-gray-200 dark:bg-gray-700 rounded-none overflow-hidden">
                    <div className="h-full bg-primary" style={{ width: `${progressPercent}%` }} />
                </div>
                <div
                    className={`absolute top-1/2 -translate-y-1/2 -ml-1.5 w-2.5 h-2.5 bg-white rounded-full transition-transform duration-200 shadow-md border-2 border-purple-500 ${isScrubbing ? 'scale-125' : 'scale-0 group-hover:scale-100'}`}
                    style={{ left: `${progressPercent}%` }}
                />
            </div>
        );
    }

    return (
        <div className="z-10 w-full max-w-2xl px-0 sm:px-2 md:max-w-xl md:px-0">
            <div className="mb-4 flex items-center justify-center gap-2.5 px-1 md:mb-2">
                <span className="h-px w-8 rounded-full bg-gradient-to-r from-purple-400/50 to-transparent md:w-8" aria-hidden />
                <span className="text-[10px] font-extrabold uppercase tracking-[0.2em] text-white/45">Playback</span>
                <span className="h-px w-8 rounded-full bg-gradient-to-l from-purple-400/50 to-transparent md:w-8" aria-hidden />
            </div>
            <div
                className="group relative h-2.5 w-full cursor-pointer touch-manipulation select-none rounded-full bg-white/[0.06] ring-1 ring-white/[0.04] md:h-2"
                ref={progressBarRef}
                onMouseDown={onMouseDown}
                onTouchStart={onMouseDown}
                role="slider"
                aria-valuenow={Math.round(currentTime)}
                aria-valuemin={0}
                aria-valuemax={duration && !Number.isNaN(duration) ? Math.round(duration) : 100}
                aria-label="Playback position"
            >
                <div
                    className="absolute left-0 top-0 h-full rounded-full bg-gradient-to-r from-fuchsia-500 via-purple-500 to-violet-400 shadow-[0_0_12px_rgba(168,85,247,0.35)] transition-[width] duration-150 ease-out"
                    style={{ width: `${progressPercent}%` }}
                />
                <div
                    className={`absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white/90 bg-white shadow-md ring-2 ring-purple-500/40 transition-transform duration-200 ${isScrubbing ? 'scale-110' : 'scale-0 group-hover:scale-100'}`}
                    style={{ left: `${progressPercent}%` }}
                />
            </div>
            <div className="mt-2.5 flex justify-between px-0.5 font-mono text-[11px] font-bold tabular-nums tracking-wider text-white/50 sm:px-1 md:mt-1.5 md:text-[10px]">
                <span>{formatTime(currentTime)}</span>
                <span>{formatTime(duration)}</span>
            </div>
        </div>
    );
};

/**
 * PlaylistItem: Memoized track item to prevent re-rendering when other items are interacting.
 */
const PlaylistItem = React.memo(({ item, index, isActive, isPlaying, isLoading, isDownloaded: isDownloadedProp, onPlay, onRemove, onDownloadSuccess }) => {
    const [isDownloading, setIsDownloading] = useState(false);
    const isDownloaded = isDownloadedProp;

    // Build the audio URL from track fields (same formula as playTrack in useLexPlay)
    const getAudioUrl = (track, rate = 1.0) => {
        if (!track?.id || !track?.type) return null;
        const codeParam = track.code_id ? `code=${track.code_id}&` : '';
        return `/api/audio/${track.type}/${track.id}?${codeParam}rate=${rate}`;
    };

    // The child no longer manages its own cache state; it relies on the parent's downloadedTrackIds set.
    // This provides a single source of truth and enables real-time updates for bulk downloads.

    const handleDownload = async (e) => {
        e.stopPropagation();
        if (isDownloaded || isDownloading || !item?.id) return;

        const audioUrl = getAudioUrl(item, 1.0);
        if (!audioUrl) return;

        setIsDownloading(true);
        try {
            const response = await fetch(audioUrl);
            if (response.ok) {
                if ('caches' in window) {
                    const cache = await caches.open('audio-cache');
                    await cache.put(audioUrl, response);
                }
                onDownloadSuccess?.(item.id);
            } else {
                console.error('Download failed: server returned', response.status);
            }
        } catch (err) {
            console.error('Cache save failed:', err);
        } finally {
            setIsDownloading(false);
        }
    };

    if (!item) return null;

    return (
        <div
            className={`relative group flex items-center gap-3 rounded-2xl border transition-all duration-300 pl-1 pr-3 py-2.5 md:py-3 ${
                isActive
                    ? 'bg-gradient-to-r from-purple-500/15 via-white/[0.07] to-white/[0.04] border-purple-400/35 shadow-[0_8px_32px_-12px_rgba(88,28,135,0.45)] ring-1 ring-white/10'
                    : 'bg-white/[0.02] border-white/[0.06] hover:border-white/15 hover:bg-white/[0.04]'
            }`}
        >
            <div
                className={`absolute left-0 top-2 bottom-2 w-1 rounded-full transition-colors ${isActive ? 'bg-gradient-to-b from-fuchsia-400 to-purple-600 opacity-100' : 'bg-transparent opacity-0'}`}
                aria-hidden
            />
            <div className={`relative ml-1 w-11 h-11 rounded-2xl overflow-hidden flex-shrink-0 flex items-center justify-center border ${isActive ? 'bg-purple-600/90 border-white/20 shadow-[0_0_20px_rgba(168,85,247,0.35)]' : 'bg-white/[0.06] border-white/[0.08]'}`}>
                
                {/* Action Overlay: Hover state, or Active+Paused state, or Loading state */}
                <div className={`absolute inset-0 z-20 bg-gradient-to-br from-purple-600/90 to-indigo-900/90 flex items-center justify-center transition-opacity backdrop-blur-[2px] ${((isActive && !isPlaying) || (isActive && isLoading)) ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}>
                    <button type="button" onClick={onPlay} className="text-white w-full h-full flex items-center justify-center">
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
            <div className="flex-1 min-w-0 pr-1">
                <h4 className={`text-[13px] font-bold leading-snug truncate tracking-tight ${isActive ? 'text-white' : 'text-white/85'}`}>{item?.title}</h4>
                <p className="text-[10px] font-semibold text-white/35 truncate uppercase tracking-[0.12em] mt-0.5">{item?.subtitle}</p>
            </div>
            <div className="flex items-center gap-0.5 shrink-0">
                {isDownloaded ? (
                    <div className="p-2 rounded-xl text-emerald-400/90 bg-emerald-500/10 border border-emerald-500/20" title="Cached offline">
                        <CheckCircle2 size={18} strokeWidth={2.25} />
                    </div>
                ) : (
                    <button
                        type="button"
                        onClick={handleDownload}
                        disabled={isDownloading}
                        className={`p-2 rounded-xl border border-transparent transition-all ${isDownloading ? 'text-purple-300 bg-purple-500/15' : 'text-white/45 hover:text-white hover:bg-white/10 hover:border-white/10 opacity-70 group-hover:opacity-100'}`}
                        title="Download for offline"
                    >
                        {isDownloading ? <Loader2 size={18} className="animate-spin" /> : <DownloadCloud size={18} strokeWidth={2} />}
                    </button>
                )}
                <button
                    type="button"
                    onClick={onRemove}
                    className="p-2 rounded-xl text-white/25 hover:text-rose-400 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/20 transition-all opacity-0 group-hover:opacity-100"
                    title="Remove item"
                >
                    <Trash2 size={17} strokeWidth={2} />
                </button>
            </div>
        </div>
    );
});

// Note: NOT using React.memo here so downloadedTrackIds changes always propagate
const VirtualizedPlaylist = ({ items, currentIndex, isPlaying, isLoading, downloadedIds, onPlay, onRemove, onDownloadSuccess }) => {
    const containerRef = useRef(null);
    // Convert array back to Set for O(1) lookup
    const downloadedSet = useMemo(() => new Set(downloadedIds), [downloadedIds]);

    useEffect(() => {
        if (!containerRef.current) return;
        const activeItem = containerRef.current.querySelector('[data-active="true"]');
        if (activeItem) {
            activeItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }, [currentIndex, items.length]);

    if (items.length === 0) {
        return (
            <div className="h-full min-h-[12rem] flex flex-col items-center justify-center text-center px-6 py-12 rounded-3xl border border-dashed border-white/[0.08] bg-white/[0.02]">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500/20 to-indigo-600/10 border border-white/10 flex items-center justify-center mb-4">
                    <ListMusic size={32} className="text-white/35" strokeWidth={1.5} />
                </div>
                <p className="text-sm font-bold text-white/50 tracking-tight">Nothing in queue</p>
                <p className="text-[11px] text-white/25 mt-1 max-w-[14rem] leading-relaxed">Add tracks with + or load a saved playlist below.</p>
            </div>
        );
    }

    return (
        <div className="space-y-3">
            {items.length > 0 && (
                <div className="space-y-3" ref={containerRef}>
                    <div className="flex items-center justify-between gap-3 px-1 pt-0.5">
                        <span className="inline-flex items-center gap-2 text-[10px] font-extrabold uppercase tracking-[0.2em] text-white/40">
                            <span className="h-px w-6 bg-gradient-to-r from-purple-400/60 to-transparent rounded-full" aria-hidden />
                            Queue
                        </span>
                        <button
                            type="button"
                            onClick={() => {
                                const activeItem = containerRef.current?.querySelector('[data-active="true"]');
                                activeItem?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            }}
                            className="text-[10px] font-bold text-purple-300/80 hover:text-white uppercase tracking-widest transition-colors px-2 py-1 rounded-lg hover:bg-white/5"
                        >
                            Jump to now
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
                                    isDownloaded={downloadedSet.has(String(item.id))}
                                    onPlay={() => onPlay?.(index)} 
                                    onRemove={() => onRemove?.(item, index)}
                                    onDownloadSuccess={onDownloadSuccess}
                                />
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
};

// Note: NOT using React.memo here - downloadedTrackIds must always propagate
const PlaylistList = ({ playlist, currentIndex, isPlaying, downloadedTrackIds, onPlay, onRemove, onDownloadSuccess }) => {
    // Convert Set to sorted array so React can do equality checks between renders
    const downloadedIds = useMemo(() => Array.from(downloadedTrackIds || []).sort(), [downloadedTrackIds]);
    return (
        <VirtualizedPlaylist
            items={playlist}
            currentIndex={currentIndex}
            isPlaying={isPlaying}
            downloadedIds={downloadedIds}
            onPlay={onPlay}
            onRemove={onRemove}
            onDownloadSuccess={onDownloadSuccess}
        />
    );
};

const LexPlayer = ({ isMinimized, onExpand, onMinimize }) => {
    const {
        playlist,
        currentTrack,
        currentIndex,
        isPlaying,
        isLoading,
        error,
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
    const miniBarRef = useRef(null);

    const [showBulkModal, setShowBulkModal] = useState(false);
    const [bulkForm, setBulkForm] = useState({ codal: 'RPC', range: '', targetPlaylist: '' });
    const [isBulking, setIsBulking] = useState(false);
    const [bulkError, setBulkError] = useState('');
    const [activeTab, setActiveTab] = useState('player'); // 'player' | 'playlist'

    // Bulk Download Progress State
    const [downloadProgress, setDownloadProgress] = useState(0);
    const [isDownloadingAll, setIsDownloadingAll] = useState(false);
    const [downloadStatusText, setDownloadStatusText] = useState('');
    const [cachedCount, setCachedCount] = useState(0);
    const [downloadedTrackIds, setDownloadedTrackIds] = useState(new Set());

    // Build the audio URL from track fields — same formula as playTrack in useLexPlay
    // useCallback ensures stable reference so updateCachedCount closure always works
    const buildAudioUrl = useCallback((track, rate = 1.0) => {
        if (!track?.id || !track?.type) return null;
        const codeParam = track.code_id ? `code=${track.code_id}&` : '';
        return `/api/audio/${track.type}/${track.id}?${codeParam}rate=${rate}`;
    }, []);

    const updateCachedCount = useCallback(async () => {
        if (!playlist || playlist.length === 0 || !('caches' in window)) {
            setCachedCount(0);
            setDownloadedTrackIds(new Set());
            return;
        }
        try {
            const cache = await caches.open('audio-cache');

            // Get all stored keys once (absolute URLs)
            const allKeys = await cache.keys();
            const storedUrls = new Set(allKeys.map(r => r.url));
            console.log(`[LexPlay] audio-cache has ${storedUrls.size} entries`);

            let count = 0;
            const ids = new Set();
            for (const track of (playlist || [])) {
                if (!track?.id || !track?.type) continue;
                const relUrl = buildAudioUrl(track, 1.0);
                if (!relUrl) continue;
                // Convert to absolute URL (same as what Cache API stores)
                const absUrl = new URL(relUrl, window.location.origin).href;
                if (storedUrls.has(absUrl)) {
                    count++;
                    ids.add(String(track.id));
                    console.log(`[LexPlay] MATCH: ${absUrl} → id=${track.id}`);
                }
            }
            console.log(`[LexPlay] Cache check: ${count}/${playlist.length} cached, IDs:`, [...ids]);
            setCachedCount(count);
            setDownloadedTrackIds(ids);
        } catch (e) { console.warn("Cache check failed:", e); }
    }, [playlist, buildAudioUrl]);

    useEffect(() => {
        updateCachedCount();
    }, [playlist, updateCachedCount]);

    const handleDownloadAll = async () => {
        if (isDownloadingAll || !playlist || playlist.length === 0) return;

        setIsDownloadingAll(true);
        setDownloadProgress(0);
        setDownloadStatusText('Starting...');

        let completed = 0;
        const total = playlist.length;
        let successCount = 0;

        try {
            const cache = 'caches' in window ? await caches.open('audio-cache') : null;

            for (const track of playlist) {
                const audioUrl = buildAudioUrl(track, 1.0);
                if (audioUrl) {
                    setDownloadStatusText(`Downloading: ${track.title}`);
                    try {
                        // Check if already cached — still mark as downloaded
                        const existing = cache ? await cache.match(audioUrl) : null;
                        if (existing) {
                            successCount++;
                            setDownloadedTrackIds(prev => new Set(prev).add(String(track.id)));
                        } else {
                            const resp = await fetch(audioUrl);
                            if (resp.ok) {
                                if (cache) await cache.put(audioUrl, resp);
                                successCount++;
                                // Update status in real-time
                                setDownloadedTrackIds(prev => new Set(prev).add(String(track.id)));
                            } else {
                                console.warn(`Server error ${resp.status} for ${track.title}`);
                            }
                        }
                    } catch (e) {
                        console.warn(`Failed to download ${track.title}:`, e);
                    }
                }
                completed++;
                setDownloadProgress(Math.round((completed / total) * 100));
            }

            setDownloadStatusText(`✓ ${successCount}/${total} tracks cached for offline`);
            updateCachedCount(); // Refresh the bulk indicator
            setTimeout(() => {
                setIsDownloadingAll(false);
                setDownloadProgress(0);
                setDownloadStatusText('');
            }, 3000);
        } catch (err) {
            console.error('Bulk download failed:', err);
            setDownloadStatusText('Download failed. Try again.');
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

    const activePlaylistName = savedPlaylists?.find(p => p.id === activePlaylistId)?.name;

    const miniMarqueeText = useMemo(() => {
        if (error) return `⚠ ${error}`;
        if (isLoading) return 'Generating audio…';
        if (currentTrack) {
            return activePlaylistName
                ? `${currentTrack.title} · ${activePlaylistName} · ${currentTrack.subtitle}`
                : `${currentTrack.title} · ${currentTrack.subtitle}`;
        }
        return 'Nothing queued — add from Codal or Case Digest';
    }, [error, isLoading, currentTrack, activePlaylistName]);

    const miniMarqueeClass = useMemo(() => {
        if (error) return 'text-red-500 dark:text-red-400';
        if (isLoading) return 'text-purple-600 dark:text-purple-300 animate-pulse';
        if (currentTrack) return 'text-gray-900 dark:text-white';
        return 'text-gray-500 dark:text-gray-400';
    }, [error, isLoading, currentTrack]);

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

    // Expose mini player height so Layout/main content can pad above the fixed bar (--player-height in index.css)
    useEffect(() => {
        if (!isMinimized) {
            document.documentElement.style.setProperty('--player-height', '0px');
            return;
        }
        const el = miniBarRef.current;
        if (!el) return;
        const sync = () => {
            const h = Math.ceil(el.getBoundingClientRect().height);
            document.documentElement.style.setProperty('--player-height', `${h}px`);
        };
        sync();
        const ro = new ResizeObserver(sync);
        ro.observe(el);
        window.addEventListener('orientationchange', sync);
        return () => {
            ro.disconnect();
            window.removeEventListener('orientationchange', sync);
            document.documentElement.style.setProperty('--player-height', '0px');
        };
    }, [isMinimized]);

    if (isMinimized) {
        /** Portaled to body + z above modals (z-[520]): avoids blur/cover from modal overlay when mini bar lived under Layout's stacking context. */
        const miniPlayer = (
            <div
                ref={miniBarRef}
                role="region"
                aria-label="LexPlay mini player"
                className="pointer-events-auto fixed bottom-0 left-0 right-0 z-[530] flex flex-col overflow-hidden bg-white/90 dark:bg-gray-900/90 shadow-[0_-4px_20px_-8px_rgba(0,0,0,0.1)] dark:shadow-[0_-4px_20px_-8px_rgba(0,0,0,0.3)] transition-all duration-300 touch-manipulation pb-[env(safe-area-inset-bottom,0px)]"
            >
                {/* Top edge: scrub line, full viewport width */}
                <div
                    className="w-full shrink-0 border-b border-gray-200/90 dark:border-gray-800"
                    onClick={(e) => e.stopPropagation()}
                >
                    <PlaybackProgress audioRef={audioRef} isPlaying={isPlaying} isMinimized />
                </div>

                {/* Mobile: label row above transport. Desktop/tablet: label left, transport centered. */}
                <div
                    className="flex w-full flex-col cursor-pointer hover:bg-white/95 dark:hover:bg-gray-900/95
                        pl-[max(0.5rem,calc(env(safe-area-inset-left,0px)+0.35rem))] pr-[max(0.35rem,env(safe-area-inset-right,0px))] py-1"
                    onClick={onExpand}
                >
                    <div className="md:hidden w-full px-2 pt-1.5 pb-0.5">
                        <p
                            className={`truncate text-center text-[11px] font-semibold leading-snug tracking-tight sm:text-xs ${miniMarqueeClass}`}
                            title={miniMarqueeText}
                        >
                            {miniMarqueeText}
                        </p>
                    </div>

                    <div
                        className="grid w-full grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-x-2"
                    >
                        {/* Desktop/tablet left label */}
                        <div className="hidden min-w-0 justify-self-start self-center py-0.5 pr-2 md:block">
                            <p
                                className={`truncate text-left text-[11px] font-semibold leading-snug tracking-tight sm:text-xs md:text-sm ${miniMarqueeClass}`}
                                title={miniMarqueeText}
                            >
                                {miniMarqueeText}
                            </p>
                        </div>

                        {/* Transport — geometrically centered; stops click from expanding player */}
                        <div
                            className="relative z-10 flex shrink-0 justify-self-center"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="flex items-center justify-center gap-4 sm:gap-5">
                                <button
                                    type="button"
                                    onClick={(e) => { e.stopPropagation(); handlePrevious(); }}
                                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-gray-200/90 bg-gray-100/70 text-gray-600 shadow-sm transition-all hover:border-purple-200/90 hover:bg-purple-50/90 hover:text-purple-700 active:scale-95 disabled:pointer-events-none disabled:opacity-25 dark:border-white/10 dark:bg-white/[0.04] dark:text-white/70 dark:hover:border-white/18 dark:hover:bg-white/[0.08] dark:hover:text-white"
                                    disabled={playlist.length === 0}
                                    aria-label="Previous track"
                                >
                                    <SkipBack className="h-5 w-5" fill="currentColor" />
                                </button>
                                <button
                                    type="button"
                                    onClick={(e) => { e.stopPropagation(); handlePlayPause(); }}
                                    disabled={playlist.length === 0}
                                    className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-violet-600 text-white shadow-[0_6px_20px_-6px_rgba(124,58,237,0.5)] ring-1 ring-white/15 transition-all hover:scale-[1.03] hover:shadow-[0_8px_24px_-6px_rgba(168,85,247,0.45)] active:scale-95 disabled:pointer-events-none disabled:opacity-45 disabled:hover:scale-100"
                                    aria-label={isPlaying ? 'Pause' : 'Play'}
                                >
                                    {isLoading ? (
                                        <div className="h-6 w-6 animate-spin rounded-full border-[3px] border-white/25 border-t-white" />
                                    ) : isPlaying ? (
                                        /* Same EQ treatment as playlist rows — no Pause icon while playing (tap still pauses) */
                                        <div className="flex h-3.5 items-end justify-center gap-0.5" aria-hidden>
                                            {[0.4, 1.0, 0.7, 0.5].map((h, i) => (
                                                <div
                                                    key={i}
                                                    className="w-1 rounded-full bg-white animate-[bounce_0.8s_infinite] shadow-[0_0_8px_rgba(255,255,255,0.95)]"
                                                    style={{ height: `${h * 100}%`, animationDelay: `${i * 0.15}s` }}
                                                />
                                            ))}
                                        </div>
                                    ) : (
                                        <Play className="ml-0.5 h-6 w-6 fill-current" />
                                    )}
                                </button>
                                <button
                                    type="button"
                                    onClick={(e) => { e.stopPropagation(); handleNext(); }}
                                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-gray-200/90 bg-gray-100/70 text-gray-600 shadow-sm transition-all hover:border-purple-200/90 hover:bg-purple-50/90 hover:text-purple-700 active:scale-95 disabled:pointer-events-none disabled:opacity-25 dark:border-white/10 dark:bg-white/[0.04] dark:text-white/70 dark:hover:border-white/18 dark:hover:bg-white/[0.08] dark:hover:text-white"
                                    disabled={playlist.length === 0}
                                    aria-label="Next track"
                                >
                                    <SkipForward className="h-5 w-5" fill="currentColor" />
                                </button>
                            </div>
                        </div>

                        {/* Balance column so middle transport stays true center */}
                        <div className="min-w-0 md:block" aria-hidden />
                    </div>
                </div>
            </div>
        );

        return typeof document !== 'undefined' ? createPortal(miniPlayer, document.body) : null;
    }

    // Full Screen Mode — max-md respects iOS safe areas (notch / home indicator)
    return (
        <div className="fixed inset-0 z-[100] flex items-stretch justify-center md:items-center">
            {/* Backdrop Overlay */}
            <div 
                className="absolute inset-0 bg-[#0f172a]/80 backdrop-blur-md transition-opacity duration-500 animate-in fade-in"
                onClick={onMinimize}
            />
            
            <div className="relative w-full h-full min-h-0 max-md:max-h-[100dvh] md:h-[calc(100vh-8rem)] md:w-[90vw] lg:w-[85vw] xl:w-[80vw] md:max-w-6xl md:rounded-[2rem] bg-gradient-to-br from-white/10 via-[#ffffff05] to-transparent backdrop-blur-[40px] border border-white/20 shadow-[0_32px_64px_-16px_rgba(31,38,135,0.4)] overflow-hidden animate-in zoom-in-95 slide-in-from-bottom-10 duration-500">
                {/* Inner shine layer for glass effect */}
                <div className="absolute inset-0 bg-gradient-to-b from-white/10 to-transparent opacity-30 pointer-events-none z-0"></div>
                {/* Mobile: viewport-centered compact pills; window controls top-right */}
                <div className="md:hidden absolute inset-x-0 z-[60] top-[max(0.75rem,env(safe-area-inset-top,0px))] h-12 pointer-events-none">
                    <div className="absolute left-1/2 top-1/2 z-[60] flex w-max max-w-[min(100%-5.5rem,12rem)] -translate-x-1/2 -translate-y-1/2 bg-white/5 backdrop-blur-xl border border-white/10 rounded-full p-1 shadow-xl pointer-events-auto">
                        <button
                            type="button"
                            onClick={() => setActiveTab('player')}
                            className={`rounded-full px-3.5 py-1.5 text-[9px] font-extrabold uppercase tracking-wider transition-all duration-300 whitespace-nowrap sm:px-4 sm:py-2 sm:text-[10px] ${activeTab === 'player' ? 'bg-white text-[#0f172a] shadow-md' : 'text-white/40 hover:text-white/60'}`}
                        >
                            Player
                        </button>
                        <button
                            type="button"
                            onClick={() => setActiveTab('playlist')}
                            className={`rounded-full px-3.5 py-1.5 text-[9px] font-extrabold uppercase tracking-wider transition-all duration-300 whitespace-nowrap sm:px-4 sm:py-2 sm:text-[10px] ${activeTab === 'playlist' ? 'bg-white text-[#0f172a] shadow-md' : 'text-white/40 hover:text-white/60'}`}
                        >
                            Playlist
                        </button>
                    </div>
                    <div className="absolute right-4 top-1/2 z-[61] flex h-11 w-11 -translate-y-1/2 items-center justify-center pointer-events-auto">
                        <button
                            type="button"
                            onClick={onMinimize}
                            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] text-white/80 shadow-xl backdrop-blur-3xl transition-all hover:border-white/20 hover:bg-white/[0.08] hover:text-white active:scale-95"
                            title="Minimize Player"
                        >
                            <Minimize2 className="h-5 w-5" strokeWidth={2.25} />
                        </button>
                    </div>
                </div>
                {/* Desktop: top nudged to match playlist header items-center row (title + badge taller than h-12); right inset matches player area padding */}
                <div className="pointer-events-none absolute z-[60] hidden md:top-[calc(1.25rem+0.0625rem)] md:flex md:items-center md:right-8 lg:right-10 xl:right-12">
                    <button
                        type="button"
                        onClick={onMinimize}
                        className="group pointer-events-auto flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] text-white/80 shadow-xl backdrop-blur-xl transition-all hover:border-white/20 hover:bg-white/[0.08] hover:text-white active:scale-[0.98] md:h-12 md:w-12"
                        title="Minimize Player"
                    >
                        <Minimize2 className="h-5 w-5 transition-transform group-hover:scale-105" strokeWidth={2.25} />
                    </button>
                </div>

                <div className="flex flex-col md:flex-row-reverse h-full w-full relative">

                    {/* Right Area: Player Stage — visual language matches playlist column */}
                    <div className={`relative flex min-h-0 flex-1 flex-col overflow-y-auto scrollbar-hide bg-gradient-to-b from-slate-950/90 via-[#0c1222]/95 to-slate-950/90 backdrop-blur-2xl transition-all duration-500 ease-in-out md:overflow-y-auto md:overscroll-contain md:border-l md:border-white/[0.07] md:shadow-[inset_-1px_0_0_rgba(255,255,255,0.04)] ${activeTab === 'player' ? 'translate-x-0 opacity-100' : 'hidden -translate-x-10 opacity-0 md:flex md:translate-x-0 md:opacity-100'}`}>
                        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-purple-500/[0.06] via-transparent to-indigo-950/20" />
                        <div className="pointer-events-none absolute left-1/2 top-[38%] h-[min(360px,50vh)] w-[min(380px,78vw)] -translate-x-1/2 rounded-full bg-purple-500/10 blur-[90px] md:top-[42%] md:h-[min(220px,38vh)] md:w-[min(260px,85%)]" />

                        <div className="relative z-10 mx-auto flex w-full max-w-2xl shrink-0 flex-col items-center gap-7 px-0 pb-6 pt-[calc(env(safe-area-inset-top,0px)+3.25rem)] sm:gap-8 sm:px-4 md:min-h-0 md:shrink md:flex-1 md:justify-center md:gap-5 md:px-6 md:pb-5 md:pt-12 lg:gap-6 lg:px-8 max-md:pb-[max(1.25rem,env(safe-area-inset-bottom,0px))]">
                        <header className="flex w-full flex-col items-center justify-center px-4 pt-1 md:pt-0">
                            <p className="flex items-baseline gap-0.5 text-3xl font-bold tracking-tight sm:text-4xl md:text-2xl lg:text-[1.65rem]" aria-label="LexPlayer">
                                <span className="text-white">Lex</span>
                                <span className="bg-gradient-to-r from-violet-300 via-fuchsia-200 to-purple-400 bg-clip-text text-transparent">Player</span>
                            </p>
                            <div className="mt-2 h-[3px] w-12 rounded-full bg-gradient-to-r from-purple-500/0 via-purple-400/80 to-fuchsia-500/0 md:mt-1.5 md:w-10" aria-hidden />
                        </header>

                        <div className="relative flex-shrink-0 group">
                            <div className="pointer-events-none absolute -inset-4 rounded-[2rem] bg-gradient-to-br from-purple-500/25 via-fuchsia-500/12 to-transparent opacity-80 blur-2xl transition-opacity group-hover:opacity-100 md:-inset-3 md:rounded-xl" />
                            <div className="relative flex h-52 w-52 max-h-[42vh] max-w-[42vh] items-center justify-center overflow-hidden rounded-2xl border border-white/[0.1] bg-white/[0.04] shadow-[0_12px_48px_-16px_rgba(88,28,135,0.45)] ring-1 ring-white/[0.08] backdrop-blur-sm sm:h-60 sm:w-60 md:h-44 md:w-44 md:max-h-none md:max-w-none md:rounded-2xl lg:h-48 lg:w-48 lg:rounded-[1.75rem]">
                                <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/[0.12] via-white/[0.03] to-transparent" />
                                <Headphones className={`relative z-10 h-[5rem] w-[5rem] text-white/90 drop-shadow-[0_8px_24px_rgba(124,58,237,0.45)] transition-transform duration-700 sm:h-32 sm:w-32 md:h-28 md:w-28 lg:h-[7.25rem] lg:w-[7.25rem] ${isPlaying ? '-translate-y-3 scale-95 md:-translate-y-2 md:scale-95' : 'group-hover:scale-105'}`} strokeWidth={1.25} />
                                {isPlaying && (
                                    <div className="absolute bottom-5 left-1/2 z-10 flex h-9 w-full max-w-[85%] -translate-x-1/2 items-end justify-center gap-1.5 px-3 md:bottom-4 md:h-8 md:gap-1.5">
                                        {[0.4, 0.8, 0.6, 1.0, 0.5, 0.9, 0.7, 0.3, 0.6, 0.8].map((h, i) => (
                                            <div key={i} className="w-1.5 animate-[bounce_1s_infinite] rounded-full bg-white/95 shadow-[0_0_8px_rgba(255,255,255,0.85)] md:w-2" style={{ height: `${h * 100}%`, animationDelay: `${i * 0.1}s` }} />
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="z-10 w-full max-w-xl px-3 text-center md:max-w-lg md:px-2">
                            <h2 className="line-clamp-2 text-2xl font-bold tracking-tight text-white drop-shadow-sm sm:text-3xl md:text-lg md:leading-snug lg:text-xl">
                                {currentTrack ? currentTrack.title : "LexPlayer is idle"}
                            </h2>
                            <p className="mt-2 text-xs font-semibold uppercase leading-relaxed tracking-[0.12em] text-white/45 sm:text-sm md:mt-1.5 md:text-[11px] md:leading-snug lg:text-xs">
                                {currentTrack ? (activePlaylistName ? `${activePlaylistName} · ${currentTrack.subtitle}` : currentTrack.subtitle) : "Add items to your LexPlaylist"}
                            </p>
                            <div className="mt-3 flex min-h-0 flex-col items-center justify-center md:mt-2">
                                {error && (
                                    <div className="inline-flex max-w-full items-center gap-2 rounded-2xl border border-rose-500/30 bg-rose-500/10 px-5 py-2.5 text-center text-xs font-bold text-rose-200/95 animate-in shake">
                                        {error}
                                    </div>
                                )}
                            </div>
                        </div>

                        <PlaybackProgress audioRef={audioRef} isPlaying={isPlaying} isMinimized={false} />

                        <div className="z-10 flex w-full max-w-2xl flex-col items-center space-y-6 sm:space-y-8 md:space-y-0">
                            <div className="flex w-full items-center justify-center gap-8 px-4 md:gap-10 lg:gap-12">
                                <button
                                    type="button"
                                    onClick={handlePrevious}
                                    disabled={playlist.length === 0}
                                    className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/[0.04] text-white/70 shadow-sm transition-all hover:border-white/18 hover:bg-white/[0.08] hover:text-white active:scale-95 disabled:pointer-events-none disabled:opacity-25 md:h-10 md:w-10 lg:h-11 lg:w-11"
                                    aria-label="Previous track"
                                >
                                    <SkipBack className="h-6 w-6 md:h-5 md:w-5 lg:h-6 lg:w-6" fill="currentColor" />
                                </button>

                                <button
                                    type="button"
                                    onClick={handlePlayPause}
                                    disabled={playlist.length === 0}
                                    className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-violet-600 text-white shadow-[0_8px_28px_-6px_rgba(124,58,237,0.55)] ring-1 ring-white/15 transition-all hover:scale-[1.04] hover:shadow-[0_12px_32px_-6px_rgba(168,85,247,0.5)] active:scale-95 disabled:opacity-45 disabled:hover:scale-100 md:h-14 md:w-14 lg:h-[3.75rem] lg:w-[3.75rem]"
                                    aria-label={isPlaying ? 'Pause' : 'Play'}
                                >
                                    {isLoading ? (
                                        <div className="h-8 w-8 animate-spin rounded-full border-[3px] border-white/25 border-t-white md:h-6 md:w-6" />
                                    ) : isPlaying ? (
                                        <div
                                            className="flex h-4 w-9 items-end justify-center gap-0.5 md:h-5 md:w-11 md:gap-1 lg:h-6 lg:w-12"
                                            aria-hidden
                                        >
                                            {[0.4, 1.0, 0.7, 0.5].map((h, i) => (
                                                <div
                                                    key={i}
                                                    className="w-1 rounded-full bg-white animate-[bounce_0.8s_infinite] shadow-[0_0_10px_rgba(255,255,255,0.95)] md:w-1.5"
                                                    style={{ height: `${h * 100}%`, animationDelay: `${i * 0.15}s` }}
                                                />
                                            ))}
                                        </div>
                                    ) : (
                                        <Play className="ml-1 h-8 w-8 md:h-7 md:w-7 lg:h-8 lg:w-8" fill="currentColor" />
                                    )}
                                </button>

                                <button
                                    type="button"
                                    onClick={handleNext}
                                    disabled={playlist.length === 0}
                                    className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/[0.04] text-white/70 shadow-sm transition-all hover:border-white/18 hover:bg-white/[0.08] hover:text-white active:scale-95 disabled:pointer-events-none disabled:opacity-25 md:h-10 md:w-10 lg:h-11 lg:w-11"
                                    aria-label="Next track"
                                >
                                    <SkipForward className="h-6 w-6 md:h-5 md:w-5 lg:h-6 lg:w-6" fill="currentColor" />
                                </button>
                            </div>
                        </div>
                        </div>
                    </div>

                    {/* Left Area: Playlist (Desktop) */}
                    <div className={`w-full md:w-72 lg:w-80 xl:w-[420px] flex flex-col h-full shrink-0 z-20 transition-all duration-500 ease-in-out bg-gradient-to-b from-slate-950/90 via-[#0c1222]/95 to-slate-950/90 backdrop-blur-2xl border-b md:border-b-0 md:border-r border-white/[0.07] shadow-[inset_1px_0_0_rgba(255,255,255,0.04),-12px_0_40px_-8px_rgba(0,0,0,0.4)] ${activeTab === 'playlist' ? 'opacity-100 translate-x-0' : 'hidden md:flex md:opacity-100 md:translate-x-0 opacity-0 -translate-x-10'}`}>
                        <div className="p-4 md:p-5 max-md:pt-[calc(env(safe-area-inset-top,0px)+3.75rem)] md:pt-5 border-b border-white/[0.06] bg-white/[0.02] flex items-center justify-between gap-3 md:gap-4">
                            <div className="min-w-0 flex-1 flex items-center justify-start gap-3 md:gap-3.5 text-left">
                                <button
                                    type="button"
                                    onClick={() => setShowBulkModal(true)}
                                    className="group relative flex h-11 w-11 md:h-12 md:w-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-purple-500 to-violet-600 text-white shadow-[0_6px_24px_-4px_rgba(124,58,237,0.55)] ring-1 ring-white/15 transition-all hover:scale-[1.04] hover:shadow-[0_10px_28px_-4px_rgba(168,85,247,0.5)] active:scale-95"
                                    title="Add Tracks to Playlist"
                                >
                                    <Plus className="transition-transform group-hover:rotate-90 duration-300" size={22} strokeWidth={2.5} />
                                </button>
                                <div className="min-w-0">
                                    <h3 className="text-base max-md:leading-tight md:text-lg font-bold text-white truncate tracking-tight">
                                        {activePlaylistName || 'LexPlaylist'}
                                    </h3>
                                    <div className="mt-1 flex items-center gap-2">
                                        <span className="inline-flex items-center rounded-full border border-white/10 bg-white/[0.04] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-white/45">
                                            {playlist.length} {playlist.length === 1 ? 'track' : 'tracks'}
                                        </span>
                                    </div>
                                </div>
                            </div>
                            <div className="flex items-center gap-2 shrink-0">
                                {playlist.length > 0 && (
                                    <button
                                        type="button"
                                        onClick={handleDownloadAll}
                                        disabled={isDownloadingAll}
                                        className={`flex h-11 w-11 md:h-12 md:w-12 items-center justify-center rounded-2xl border transition-all ${isDownloadingAll ? 'border-purple-400/30 bg-purple-500/15 text-purple-200' : cachedCount === playlist.length ? 'border-emerald-500/25 bg-emerald-500/10 text-emerald-400' : 'border-white/10 bg-white/[0.04] text-white/55 hover:border-white/20 hover:bg-white/[0.08] hover:text-white'}`}
                                        title={cachedCount === playlist.length ? "All tracks cached for offline" : (cachedCount > 0 ? `${cachedCount}/${playlist.length} items cached` : "Download all for offline")}
                                    >
                                        {isDownloadingAll ? (
                                            <Loader2 className="w-5 h-5 animate-spin" strokeWidth={2.5} />
                                        ) : cachedCount === playlist.length ? (
                                            <CheckCircle2 className="w-5 h-5" strokeWidth={2.25} />
                                        ) : (
                                            <div className="relative flex items-center justify-center">
                                                <DownloadCloud className="w-5 h-5" strokeWidth={2} />
                                                {cachedCount > 0 && (
                                                    <span className="absolute -right-1 -top-1 flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-emerald-500 px-0.5 text-[8px] font-black text-white ring-2 ring-slate-950">
                                                        {cachedCount}
                                                    </span>
                                                )}
                                            </div>
                                        )}
                                    </button>
                                )}
                            </div>
                        </div>

                        {/* Bulk Download Progress Bar Overlay */}
                        {isDownloadingAll && (
                            <div className="px-5 py-3.5 bg-gradient-to-r from-purple-500/12 via-violet-500/8 to-transparent border-b border-white/[0.06] animate-in slide-in-from-top-4 duration-300">
                                <div className="flex justify-between items-center mb-2">
                                    <span className="text-[10px] font-bold text-purple-100/90 uppercase tracking-[0.15em]">{downloadStatusText}</span>
                                    <span className="tabular-nums text-[10px] font-bold text-purple-200">{downloadProgress}%</span>
                                </div>
                                <div className="h-2 w-full rounded-full bg-white/[0.06] overflow-hidden ring-1 ring-white/[0.04]">
                                    <div
                                        className="h-full rounded-full bg-gradient-to-r from-fuchsia-500 via-purple-500 to-violet-400 transition-all duration-500 shadow-[0_0_12px_rgba(168,85,247,0.4)]"
                                        style={{ width: `${downloadProgress}%` }}
                                    />
                                </div>
                            </div>
                        )}

                        <div className="border-b border-white/[0.05] bg-gradient-to-b from-white/[0.03] to-transparent px-4 py-5 md:px-5">
                            {!isCreating ? (
                                <div className="flex flex-col gap-3 sm:flex-row sm:items-stretch">
                                    <button
                                        type="button"
                                        onClick={() => setIsCreating(true)}
                                        className="sm:w-auto shrink-0 rounded-2xl border border-purple-400/35 bg-purple-500/15 px-4 py-3 text-center text-[11px] font-extrabold uppercase tracking-[0.15em] text-purple-100 transition-all hover:border-purple-300/50 hover:bg-purple-500/25 active:scale-[0.98]"
                                    >
                                        New playlist
                                    </button>
                                    <div className="min-w-0 flex-1">
                                        <CustomPlaylistSelect
                                            value={activePlaylistId || ''}
                                            onChange={(val) => val && loadSavedPlaylist(val)}
                                            options={savedPlaylists.map(p => ({
                                                value: p.id,
                                                label: `${p.name} (${p.item_count || 0})`
                                            }))}
                                        />
                                    </div>
                                </div>
                            ) : (
                                <div className="flex flex-wrap items-center gap-2">
                                    <input type="text" placeholder="Playlist name…" value={newPlaylistName} onChange={(e) => setNewPlaylistName(e.target.value)} className="min-w-[10rem] flex-1 rounded-2xl border border-white/10 bg-white/[0.05] px-4 py-3 text-sm text-white placeholder:text-white/25 outline-none ring-0 focus:border-purple-400/40 focus:bg-white/[0.07]" autoFocus />
                                    <button type="button" onClick={async () => { if(newPlaylistName.trim()){ await createPlaylist(newPlaylistName.trim()); setNewPlaylistName(''); setIsCreating(false); }}} className="flex h-11 w-11 items-center justify-center rounded-2xl border border-purple-400/40 bg-purple-500/20 text-purple-100 transition-all hover:bg-purple-500/35" aria-label="Save playlist">
                                        <Save size={20} strokeWidth={2.25} />
                                    </button>
                                    <button type="button" onClick={() => setIsCreating(false)} className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] text-white/45 transition-all hover:bg-white/[0.08] hover:text-white" aria-label="Cancel">
                                        <X size={20} strokeWidth={2.25} />
                                    </button>
                                </div>
                            )}
                            {activePlaylistId && !isCreating && (
                                <div className="mt-4 w-full">
                                    {!isEditing ? (
                                        <div className="flex w-full items-center justify-between gap-3">
                                            <button
                                                type="button"
                                                onClick={() => { setIsEditing(true); setEditPlaylistName(savedPlaylists.find(p => p.id === activePlaylistId)?.name || ''); }}
                                                className="inline-flex items-center gap-1.5 rounded-xl border border-white/12 bg-white/[0.04] px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-white/70 transition-all hover:border-white/20 hover:bg-white/[0.08] hover:text-white"
                                            >
                                                <Edit2 size={12} strokeWidth={2.5} /> Rename
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => window.confirm("Delete playlist?") && deletePlaylist(activePlaylistId)}
                                                className="inline-flex shrink-0 items-center gap-1.5 rounded-xl border border-rose-500/20 bg-rose-500/[0.08] px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-rose-200/90 transition-all hover:border-rose-400/35 hover:bg-rose-500/15"
                                            >
                                                <Trash2 size={12} strokeWidth={2.5} /> Delete
                                            </button>
                                        </div>
                                    ) : (
                                        <div className="flex w-full flex-wrap items-center gap-2">
                                            <input type="text" value={editPlaylistName} onChange={(e) => setEditPlaylistName(e.target.value)} className="min-w-0 flex-1 rounded-xl border border-white/12 bg-white/[0.05] px-3 py-2 text-xs text-white outline-none focus:border-purple-400/40" autoFocus />
                                            <button type="button" onClick={() => { if(editPlaylistName.trim()){ renamePlaylist(activePlaylistId, editPlaylistName.trim()); setIsEditing(false); }}} className="flex h-9 w-9 items-center justify-center rounded-xl border border-purple-400/35 bg-purple-500/20 text-purple-200 hover:bg-purple-500/30" aria-label="Save name">
                                                <Save size={16} strokeWidth={2.5} />
                                            </button>
                                            <button type="button" onClick={() => setIsEditing(false)} className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04] text-white/45 hover:text-white" aria-label="Cancel rename">
                                                <X size={16} strokeWidth={2.5} />
                                            </button>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>

                        <div className="flex-1 overflow-y-auto scroll-smooth overscroll-contain px-4 py-5 md:px-5 md:pb-6">
                            <VirtualizedPlaylist 
                                items={playlist}
                                currentIndex={currentIndex}
                                isPlaying={isPlaying}
                                isLoading={isLoading}
                                downloadedIds={Array.from(downloadedTrackIds || []).sort()}
                                onPlay={handlePlaylistPlay}
                                onRemove={handlePlaylistRemove}
                                onDownloadSuccess={(id) => setDownloadedTrackIds(prev => new Set(prev).add(String(id)))}
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
