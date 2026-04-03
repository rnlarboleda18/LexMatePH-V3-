import React, { useState, useEffect, useLayoutEffect, useRef, useCallback, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { useLexPlay } from './useLexPlay';
import {
    Play, Pause, SkipBack, SkipForward, Maximize2, Minimize2,
    Volume2, ListMusic, Trash2, X, Headphones, Plus, Edit2, Save, ChevronDown,
    DownloadCloud, CheckCircle2, Loader2, Eraser, Square,
} from 'lucide-react';

/** Remove one track’s audio from the Cache Storage `audio-cache` bucket (matches buildAudioUrl @ rate 1.0). */
async function removeTrackAudioFromCache(track, buildAudioUrlFn) {
    if (!track?.id || !track?.type || !('caches' in window)) return false;
    const rel = buildAudioUrlFn(track, 1.0);
    if (!rel) return false;
    const cache = await caches.open('audio-cache');
    const abs = new URL(rel, window.location.origin).href;
    let removed = (await cache.delete(rel)) || (await cache.delete(abs));
    if (!removed) {
        const keys = await cache.keys();
        const needle = `/api/audio/${track.type}/${track.id}`;
        for (const req of keys) {
            if (req.url.includes(needle)) {
                await cache.delete(req);
                removed = true;
                break;
            }
        }
    }
    return removed;
}

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
                className="w-full flex items-center justify-between rounded-2xl border-2 border-slate-300/85 bg-white text-sm text-slate-900 shadow-sm outline-none transition-all hover:bg-slate-50 dark:border-white/10 dark:bg-white/[0.03] dark:text-white dark:hover:bg-white/10"
                onClick={() => setIsOpen(!isOpen)}
            >
                <span className={`truncate mr-2 ${!selectedOption ? 'text-slate-400 dark:text-white/40' : 'font-semibold'}`}>
                    {selectedOption ? selectedOption.label : placeholder}
                </span>
                <ChevronDown size={18} className={`text-slate-400 transition-transform dark:text-white/40 ${isOpen ? 'rotate-180' : ''}`} />
            </button>
            {isOpen && (
                <div className="absolute z-50 mt-2 max-h-60 w-full overflow-y-auto rounded-2xl border-2 border-slate-300/85 bg-white py-2 shadow-2xl backdrop-blur-3xl dark:border-white/10 dark:bg-[#0f172a]/95">
                    {options?.length === 0 && (
                        <div className="px-4 py-3 text-center text-sm italic text-slate-500 dark:text-white/40">No playlists found</div>
                    )}
                    {options?.map((option) => (
                        <button
                            key={option.value}
                            type="button"
                            className={`w-full px-4 py-3 text-left text-sm transition-colors hover:bg-purple-500/15 hover:text-slate-900 dark:hover:bg-purple-500/30 dark:hover:text-white ${value === option.value ? 'bg-purple-100 font-bold text-purple-900 dark:bg-purple-500/20 dark:text-purple-200' : 'text-slate-700 dark:text-white/70'}`}
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

    /** Mini vs full LexPlayer are separate component instances; state must match the shared <audio> element immediately. */
    const readAudioClock = useCallback(() => {
        const audio = audioRef?.current;
        if (!audio) return;
        setCurrentTime(audio.currentTime);
        const d = audio.duration;
        if (d && !Number.isNaN(d) && Number.isFinite(d)) {
            setDuration(d);
        }
    }, [audioRef]);

    useLayoutEffect(() => {
        readAudioClock();
    }, [readAudioClock, isMinimized]);

    // Provider creates `audio` in its own useEffect (runs after child effects); defer once so we attach listeners + clock after <audio> exists.
    useEffect(() => {
        const id = window.setTimeout(() => readAudioClock(), 0);
        return () => window.clearTimeout(id);
    }, [readAudioClock, isMinimized]);

    useEffect(() => {
        const audio = audioRef?.current;
        if (!audio) return;

        const updateTime = () => {
            if (!isScrubbing) setCurrentTime(audio.currentTime);
        };
        const updateDuration = () => {
            const d = audio.duration;
            if (d && !Number.isNaN(d) && Number.isFinite(d)) setDuration(d);
        };

        audio.addEventListener('timeupdate', updateTime);
        audio.addEventListener('loadedmetadata', updateDuration);
        audio.addEventListener('durationchange', updateDuration);
        audio.addEventListener('seeked', updateTime);

        return () => {
            audio.removeEventListener('timeupdate', updateTime);
            audio.removeEventListener('loadedmetadata', updateDuration);
            audio.removeEventListener('durationchange', updateDuration);
            audio.removeEventListener('seeked', updateTime);
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
        /* Thin scrub — a bit slimmer on mobile minimized bar */
        return (
            <div
                ref={progressBarRef}
                className="relative w-full h-[3px] md:h-[4px] cursor-pointer group touch-manipulation select-none"
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
                    className={`absolute top-1/2 -translate-y-1/2 -ml-1 w-2 h-2 md:-ml-1.5 md:w-2.5 md:h-2.5 bg-white rounded-full transition-transform duration-200 shadow-md border-2 border-purple-500 ${isScrubbing ? 'scale-125' : 'scale-0 group-hover:scale-100'}`}
                    style={{ left: `${progressPercent}%` }}
                />
            </div>
        );
    }

    /* max-lg: stream-style thin scrub (touch-friendly thumb); lg+: original desktop bar */
    return (
        <div className="z-10 w-full max-w-2xl px-0 sm:px-2 md:max-w-xl md:px-0 max-lg:max-w-none max-lg:px-0">
            <div
                className="group relative h-1 w-full cursor-pointer touch-manipulation select-none rounded-full bg-slate-200/90 ring-0 sm:h-[5px] dark:bg-white/[0.12] lg:h-2.5 lg:bg-slate-200/90 lg:ring-1 lg:ring-slate-300/60 lg:dark:bg-white/[0.06] lg:dark:ring-white/[0.04] lg:md:h-2"
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
                    className="absolute left-0 top-0 h-full rounded-full bg-gradient-to-r from-fuchsia-500 via-purple-500 to-violet-400 shadow-[0_0_12px_rgba(168,85,247,0.35)] transition-[width] duration-150 ease-out max-lg:shadow-[0_0_10px_rgba(168,85,247,0.4)]"
                    style={{ width: `${progressPercent}%` }}
                />
                <div
                    className={`absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border border-slate-300 bg-white shadow-md ring-2 ring-purple-500/40 transition-transform duration-200 max-lg:h-3.5 max-lg:w-3.5 max-lg:scale-100 max-lg:border lg:h-4 lg:w-4 lg:border-2 lg:ring-purple-500/40 dark:border-white/95 dark:ring-purple-500/35 lg:dark:border-white/90 ${isScrubbing ? 'scale-110' : 'max-lg:scale-100 lg:scale-0 lg:group-hover:scale-100'}`}
                    style={{ left: `${progressPercent}%` }}
                />
            </div>
            <div className="mt-2 flex justify-between px-0.5 tabular-nums text-slate-500 max-lg:mt-2.5 max-lg:text-[11px] max-lg:font-medium max-lg:sm:text-xs lg:mt-2 lg:font-mono lg:text-[11px] lg:font-bold lg:tracking-wider sm:px-1 lg:md:mt-1.5 lg:md:text-[10px] dark:text-white/50 max-lg:dark:text-white/40">
                <span>{formatTime(currentTime)}</span>
                <span>{formatTime(duration)}</span>
            </div>
        </div>
    );
};

/**
 * PlaylistItem: Memoized track item to prevent re-rendering when other items are interacting.
 */
const PlaylistItem = React.memo(({ item, index, isActive, isPlaying, isLoading, onPlay, onRemove, onClearDownload }) => {
    const { cachedTrackIds, downloadingTrackIds, startTrackCacheDownload, stopTrackCacheDownload } = useLexPlay();
    const id = String(item?.id ?? '');
    const isDownloaded = id ? cachedTrackIds.has(id) : false;
    const isDownloading = id ? downloadingTrackIds.has(id) : false;

    const handleDownloadOrStop = (e) => {
        e.stopPropagation();
        if (isDownloaded || !item?.id) return;
        if (isDownloading) {
            stopTrackCacheDownload(id);
            return;
        }
        void startTrackCacheDownload(item);
    };

    if (!item) return null;

    return (
        <div
            className={`relative group flex items-center gap-3 rounded-2xl border transition-all duration-300 pl-1 pr-3 py-2.5 md:py-3 ${
                isActive
                    ? 'border-purple-300/80 bg-gradient-to-r from-purple-100/90 via-purple-50/50 to-white shadow-[0_8px_32px_-12px_rgba(88,28,135,0.2)] ring-1 ring-purple-200/50 dark:from-purple-500/15 dark:via-white/[0.07] dark:to-white/[0.04] dark:border-purple-400/35 dark:shadow-[0_8px_32px_-12px_rgba(88,28,135,0.45)] dark:ring-white/10'
                    : 'border-slate-200/90 bg-white/90 hover:border-slate-300 hover:bg-slate-50/90 dark:border-white/[0.06] dark:bg-white/[0.02] dark:hover:border-white/15 dark:hover:bg-white/[0.04]'
            }`}
        >
            <div
                className={`absolute left-0 top-2 bottom-2 w-1 rounded-full transition-colors ${isActive ? 'bg-gradient-to-b from-fuchsia-400 to-purple-600 opacity-100' : 'bg-transparent opacity-0'}`}
                aria-hidden
            />
            <div className={`relative ml-1 flex h-11 w-11 flex-shrink-0 items-center justify-center overflow-hidden rounded-2xl border ${isActive ? 'border-purple-300/80 bg-purple-600/90 shadow-[0_0_20px_rgba(168,85,247,0.25)] dark:border-white/20 dark:shadow-[0_0_20px_rgba(168,85,247,0.35)]' : 'border-slate-200/90 bg-slate-100/90 dark:border-white/[0.08] dark:bg-white/[0.06]'}`}>
                
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
                {!isActive && <span className="relative z-10 text-sm font-black tracking-tighter text-slate-300 transition-opacity group-hover:opacity-0 dark:text-white/20">{index + 1}</span>}
                
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
                <h4 className={`truncate text-[13px] font-bold leading-snug tracking-tight ${isActive ? 'text-slate-900 dark:text-white' : 'text-slate-800 dark:text-white/85'}`}>{item?.title}</h4>
                <p className="mt-0.5 truncate text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500 dark:text-white/35">{item?.subtitle}</p>
            </div>
            <div className="flex items-center gap-1 shrink-0">
                {isDownloaded ? (
                    <>
                        <div
                            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-emerald-500/35 bg-emerald-500/12 text-emerald-400 shadow-[0_0_0_1px_rgba(16,185,129,0.12)]"
                            title="Saved offline — plays without network"
                            aria-label="Saved offline"
                        >
                            <CheckCircle2 size={17} strokeWidth={2.35} className="drop-shadow-[0_0_6px_rgba(52,211,153,0.35)]" />
                        </div>
                        <button
                            type="button"
                            onClick={(e) => {
                                e.stopPropagation();
                                onClearDownload?.(item);
                            }}
                            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border-2 border-slate-300/85 bg-white text-slate-500 transition-colors hover:border-rose-400/50 hover:bg-rose-50 hover:text-rose-700 dark:border-white/10 dark:bg-white/[0.04] dark:text-white/50 dark:hover:border-rose-500/35 dark:hover:bg-rose-500/15 dark:hover:text-rose-200"
                            title="Remove offline copy from device"
                        >
                            <Eraser size={16} strokeWidth={2.25} />
                        </button>
                    </>
                ) : (
                    <button
                        type="button"
                        onClick={handleDownloadOrStop}
                        className={`rounded-xl border border-transparent p-2 transition-all ${isDownloading ? 'bg-rose-100 text-rose-700 ring-1 ring-rose-300/50 hover:bg-rose-200/80 dark:bg-rose-500/20 dark:text-rose-200 dark:ring-rose-500/30 dark:hover:bg-rose-500/30' : 'text-slate-400 opacity-70 hover:border-slate-200 hover:bg-slate-100 hover:text-slate-800 group-hover:opacity-100 dark:text-white/45 dark:hover:border-white/10 dark:hover:bg-white/10 dark:hover:text-white'}`}
                        title={isDownloading ? 'Stop download' : 'Download for offline'}
                        aria-label={isDownloading ? 'Stop download' : 'Download for offline'}
                    >
                        {isDownloading ? (
                            <div className="relative flex items-center justify-center">
                                <div className="absolute -inset-1.5 animate-spin rounded-full border-2 border-rose-500/20 border-t-rose-600 dark:border-rose-400/20 dark:border-t-rose-400" />
                                <Square size={13} strokeWidth={2.5} className="fill-current relative z-10" />
                            </div>
                        ) : (
                            <DownloadCloud size={18} strokeWidth={2} />
                        )}
                    </button>
                )}
                <button
                    type="button"
                    onClick={onRemove}
                    className="rounded-xl border border-transparent p-2 text-slate-300 opacity-0 transition-all hover:border-rose-200 hover:bg-rose-50 hover:text-rose-600 group-hover:opacity-100 dark:text-white/25 dark:hover:border-rose-500/20 dark:hover:bg-rose-500/10 dark:hover:text-rose-400"
                    title="Remove item"
                >
                    <Trash2 size={17} strokeWidth={2} />
                </button>
            </div>
        </div>
    );
});

const VirtualizedPlaylist = ({ items, currentIndex, isPlaying, isLoading, onPlay, onRemove, onClearDownload }) => {
    const containerRef = useRef(null);

    useEffect(() => {
        if (!containerRef.current) return;
        const activeItem = containerRef.current.querySelector('[data-active="true"]');
        if (activeItem) {
            activeItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }, [currentIndex, items.length]);

    if (items.length === 0) {
        return (
            <div className="flex h-full min-h-[12rem] flex-col items-center justify-center rounded-3xl border-2 border-dashed border-slate-400/70 bg-slate-50/80 px-6 py-12 text-center dark:border-white/[0.08] dark:bg-white/[0.02]">
                <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl border border-slate-200/80 bg-gradient-to-br from-purple-100/80 to-indigo-50/80 dark:from-purple-500/20 dark:to-indigo-600/10 dark:border-white/10">
                    <ListMusic size={32} className="text-slate-400 dark:text-white/35" strokeWidth={1.5} />
                </div>
                <p className="text-sm font-bold tracking-tight text-slate-600 dark:text-white/50">Nothing in queue</p>
                <p className="mt-1 max-w-[14rem] text-[11px] leading-relaxed text-slate-400 dark:text-white/25">Add tracks with + or load a saved playlist below.</p>
            </div>
        );
    }

    return (
        <div className="space-y-3">
            {items.length > 0 && (
                <div className="space-y-3" ref={containerRef}>
                    <div className="flex items-center justify-between gap-3 px-1 pt-0.5">
                        <span className="inline-flex items-center gap-2 text-[10px] font-extrabold uppercase tracking-[0.2em] text-slate-400 dark:text-white/40">
                            <span className="h-px w-6 rounded-full bg-gradient-to-r from-purple-400/60 to-transparent" aria-hidden />
                            Queue
                        </span>
                        <button
                            type="button"
                            onClick={() => {
                                const activeItem = containerRef.current?.querySelector('[data-active="true"]');
                                activeItem?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            }}
                            className="rounded-lg px-2 py-1 text-[10px] font-bold uppercase tracking-widest text-purple-700 transition-colors hover:bg-slate-100 hover:text-purple-900 dark:text-purple-300/80 dark:hover:bg-white/5 dark:hover:text-white"
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
                                    onPlay={() => onPlay?.(index)} 
                                    onRemove={() => onRemove?.(item, index)}
                                    onClearDownload={onClearDownload}
                                />
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
};

const LexPlayer = ({ isMinimized, onExpand, onMinimize, isDarkMode = true }) => {
    const {
        playlist,
        displayPlaylist,
        listUiCurrentIndex,
        activatePlaylistRow,
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
        playlistFetchError,
        activePlaylistId,
        addBulkToSpecificPlaylist,
        removeFromSpecificPlaylist,
        createPlaylist,
        renamePlaylist,
        deletePlaylist,
        loadSavedPlaylist,
        fetchPlaylists,
        cachedCount,
        isBulkDownloading,
        bulkDownloadProgress,
        bulkDownloadStatusText,
        handleBulkCacheDownloadClick,
        refreshCacheForDisplayPlaylist,
    } = useLexPlay();

    const progressBarRef = useRef(null);
    const miniBarRef = useRef(null);

    const [showBulkModal, setShowBulkModal] = useState(false);
    const [bulkForm, setBulkForm] = useState({ codal: 'RPC', range: '', targetPlaylist: '' });
    const [isBulking, setIsBulking] = useState(false);
    const [bulkError, setBulkError] = useState('');
    const [activeTab, setActiveTab] = useState('player'); // 'player' | 'playlist'

    // Same URL shape as useLexPlay `buildAudioFetchPath` for cache helpers in this file
    const buildAudioUrl = useCallback((track, rate = 1.0) => {
        if (!track?.id || !track?.type) return null;
        const codeParam = track.code_id ? `code=${track.code_id}&` : '';
        return `/api/audio/${track.type}/${track.id}?${codeParam}rate=${rate}`;
    }, []);

    const clearTrackFromCache = useCallback(
        async (track) => {
            try {
                await removeTrackAudioFromCache(track, buildAudioUrl);
                await refreshCacheForDisplayPlaylist();
            } catch (e) {
                console.warn('Clear track cache failed:', e);
            }
        },
        [buildAudioUrl, refreshCacheForDisplayPlaylist]
    );

    const clearQueueCachedTracks = useCallback(async () => {
        if (!displayPlaylist?.length || !('caches' in window)) return;
        try {
            for (const track of displayPlaylist) {
                await removeTrackAudioFromCache(track, buildAudioUrl);
            }
            await refreshCacheForDisplayPlaylist();
        } catch (e) {
            console.warn('Clear queue cache failed:', e);
        }
    }, [displayPlaylist, buildAudioUrl, refreshCacheForDisplayPlaylist]);

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

    // Keep `html.dark` aligned with app theme while fullscreen LexPlayer is open (portaled nodes still match Tailwind `dark:`).
    useLayoutEffect(() => {
        if (isMinimized) return;
        document.documentElement.classList.toggle('dark', isDarkMode);
    }, [isMinimized, isDarkMode]);

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
                    className="w-full shrink-0 border-b-2 border-slate-300/85 dark:border-gray-800"
                    onClick={(e) => e.stopPropagation()}
                >
                    <PlaybackProgress audioRef={audioRef} isPlaying={isPlaying} isMinimized />
                </div>

                {/* Mobile: label row above transport. Desktop/tablet: label left, transport centered. */}
                <div
                    className="flex w-full flex-col cursor-pointer hover:bg-white/95 dark:hover:bg-gray-900/95
                        pl-[max(0.5rem,calc(env(safe-area-inset-left,0px)+0.35rem))] pr-[max(0.35rem,env(safe-area-inset-right,0px))] py-0 pb-0.5 md:py-1 md:pb-1"
                    onClick={onExpand}
                >
                    <div className="md:hidden w-full px-1.5 pt-1 pb-0">
                        <p
                            className={`truncate text-center text-[10px] font-semibold leading-tight tracking-tight sm:text-[11px] ${miniMarqueeClass}`}
                            title={miniMarqueeText}
                        >
                            {miniMarqueeText}
                        </p>
                    </div>

                    {/* Mobile: compact transport (md+ uses grid below) */}
                    <div className="w-full md:hidden flex items-center justify-center pb-0 pt-0">
                        <div
                            className="relative z-10 flex shrink-0 items-center"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="flex items-center justify-center gap-2.5 sm:gap-3">
                                <button
                                    type="button"
                                    onClick={(e) => { e.stopPropagation(); handlePrevious(); }}
                                    className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-gray-200/90 bg-gray-100/70 text-gray-600 shadow-sm transition-all hover:border-purple-200/90 hover:bg-purple-50/90 hover:text-purple-700 active:scale-95 disabled:pointer-events-none disabled:opacity-25 dark:border-white/10 dark:bg-white/[0.04] dark:text-white/70 dark:hover:border-white/18 dark:hover:bg-white/[0.08] dark:hover:text-white"
                                    disabled={playlist.length === 0}
                                    aria-label="Previous track"
                                >
                                    <SkipBack className="h-4 w-4" fill="currentColor" />
                                </button>
                                <button
                                    type="button"
                                    onClick={(e) => { e.stopPropagation(); handlePlayPause(); }}
                                    disabled={playlist.length === 0}
                                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-violet-600 text-white shadow-[0_4px_14px_-4px_rgba(124,58,237,0.45)] ring-1 ring-white/15 transition-all hover:scale-[1.03] hover:shadow-[0_8px_24px_-6px_rgba(168,85,247,0.45)] active:scale-95 disabled:pointer-events-none disabled:opacity-45 disabled:hover:scale-100"
                                    aria-label={isPlaying ? 'Pause' : 'Play'}
                                >
                                    {isLoading ? (
                                        <div className="h-5 w-5 animate-spin rounded-full border-[3px] border-white/25 border-t-white" />
                                    ) : isPlaying ? (
                                        /* Same EQ treatment as playlist rows — no Pause icon while playing (tap still pauses) */
                                        <div className="flex h-3 items-end justify-center gap-0.5" aria-hidden>
                                            {[0.4, 1.0, 0.7, 0.5].map((h, i) => (
                                                <div
                                                    key={i}
                                                    className="w-0.5 rounded-full bg-white animate-[bounce_0.8s_infinite] shadow-[0_0_8px_rgba(255,255,255,0.95)]"
                                                    style={{ height: `${h * 100}%`, animationDelay: `${i * 0.15}s` }}
                                                />
                                            ))}
                                        </div>
                                    ) : (
                                        <Play className="ml-0.5 h-5 w-5 fill-current" />
                                    )}
                                </button>
                                <button
                                    type="button"
                                    onClick={(e) => { e.stopPropagation(); handleNext(); }}
                                    className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-gray-200/90 bg-gray-100/70 text-gray-600 shadow-sm transition-all hover:border-purple-200/90 hover:bg-purple-50/90 hover:text-purple-700 active:scale-95 disabled:pointer-events-none disabled:opacity-25 dark:border-white/10 dark:bg-white/[0.04] dark:text-white/70 dark:hover:border-white/18 dark:hover:bg-white/[0.08] dark:hover:text-white"
                                    disabled={playlist.length === 0}
                                    aria-label="Next track"
                                >
                                    <SkipForward className="h-4 w-4" fill="currentColor" />
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Desktop/tablet: label left, transport centered via grid */}
                    <div
                        className="hidden w-full md:grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-x-2"
                    >
                        {/* Desktop/tablet left label */}
                        <div className="min-w-0 justify-self-start self-center py-0.5 pr-2">
                            <p
                                className={`truncate text-left text-[11px] font-semibold leading-snug tracking-tight sm:text-xs md:text-sm ${miniMarqueeClass}`}
                                title={miniMarqueeText}
                            >
                                {miniMarqueeText}
                            </p>
                        </div>

                        {/* Transport */}
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

                        {/* Balance column */}
                        <div className="min-w-0" aria-hidden />
                    </div>
                </div>
            </div>
        );

        return typeof document !== 'undefined' ? createPortal(miniPlayer, document.body) : null;
    }

    // Full Screen Mode — portaled to body so z-index stacks above Layout header (main is z-10; header z-50)
    const fullScreenUi = (
        <div
            className={`fixed inset-0 z-[120] flex items-stretch justify-center md:items-center ${isDarkMode ? 'dark' : ''}`}
            data-lexplay-theme={isDarkMode ? 'dark' : 'light'}
        >
            {/* Backdrop Overlay — explicit light/dark so it matches Layout (not only html.dark timing) */}
            <div
                className={`absolute inset-0 backdrop-blur-md transition-opacity duration-500 animate-in fade-in ${
                    isDarkMode ? 'bg-[#0f172a]/80' : 'bg-slate-900/15'
                }`}
                onClick={onMinimize}
            />

            <div
                className={`relative h-full min-h-0 w-full max-md:max-h-[100dvh] overflow-hidden border shadow-2xl backdrop-blur-[40px] animate-in zoom-in-95 slide-in-from-bottom-10 duration-500 md:h-[calc(100vh-8rem)] md:w-[90vw] md:max-w-6xl md:rounded-[2rem] lg:w-[85vw] xl:w-[80vw] ${
                    isDarkMode
                        ? 'border-white/20 bg-gradient-to-br from-white/10 via-[#ffffff05] to-transparent shadow-[0_32px_64px_-16px_rgba(31,38,135,0.4)]'
                        : 'border-slate-200/90 bg-white/98 shadow-xl'
                }`}
            >
                {/* Inner shine layer for glass effect */}
                <div className="pointer-events-none absolute inset-0 z-0 opacity-0 bg-gradient-to-b from-white/10 to-transparent dark:opacity-30" aria-hidden />
                {/* Mobile + tablet (<lg): centered pills + minimize; lg+ uses floating minimize only */}
                <div className="pointer-events-none absolute inset-x-0 top-[max(0.75rem,env(safe-area-inset-top,0px))] z-[60] h-12 lg:hidden">
                    <div className="pointer-events-auto absolute left-1/2 top-1/2 z-[60] flex w-max max-w-[min(100%-5.5rem,12rem)] -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-slate-300/85 bg-white/95 p-1 shadow-xl backdrop-blur-xl dark:border-white/10 dark:bg-white/5">
                        <button
                            type="button"
                            onClick={() => setActiveTab('player')}
                            className={`whitespace-nowrap rounded-full px-3.5 py-1.5 text-[9px] font-extrabold uppercase tracking-wider transition-all duration-300 sm:px-4 sm:py-2 sm:text-[10px] ${activeTab === 'player' ? 'bg-slate-900 text-white shadow-md dark:bg-white dark:text-[#0f172a]' : 'text-slate-500 hover:text-slate-800 dark:text-white/40 dark:hover:text-white/60'}`}
                        >
                            Player
                        </button>
                        <button
                            type="button"
                            onClick={() => setActiveTab('playlist')}
                            className={`whitespace-nowrap rounded-full px-3.5 py-1.5 text-[9px] font-extrabold uppercase tracking-wider transition-all duration-300 sm:px-4 sm:py-2 sm:text-[10px] ${activeTab === 'playlist' ? 'bg-slate-900 text-white shadow-md dark:bg-white dark:text-[#0f172a]' : 'text-slate-500 hover:text-slate-800 dark:text-white/40 dark:hover:text-white/60'}`}
                        >
                            Playlist
                        </button>
                    </div>
                    <div className="pointer-events-auto absolute right-4 top-1/2 z-[61] flex h-11 w-11 -translate-y-1/2 items-center justify-center">
                        <button
                            type="button"
                            onClick={onMinimize}
                            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border-2 border-slate-300/85 bg-white text-slate-600 shadow-xl backdrop-blur-3xl transition-all hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900 active:scale-95 dark:border-white/10 dark:bg-white/[0.04] dark:text-white/80 dark:hover:border-white/20 dark:hover:bg-white/[0.08] dark:hover:text-white"
                            title="Minimize Player"
                        >
                            <Minimize2 className="h-5 w-5" strokeWidth={2.25} />
                        </button>
                    </div>
                </div>
                {/* Desktop (lg+): top-right minimize — tabs are inline in playlist/player headers below lg */}
                <div className="pointer-events-none absolute z-[60] hidden lg:top-[calc(1.25rem+0.0625rem)] lg:flex lg:items-center lg:right-10 xl:right-12">
                    <button
                        type="button"
                        onClick={onMinimize}
                        className="group pointer-events-auto flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border-2 border-slate-300/85 bg-white text-slate-600 shadow-xl backdrop-blur-xl transition-all hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900 active:scale-[0.98] md:h-12 md:w-12 dark:border-white/10 dark:bg-white/[0.04] dark:text-white/80 dark:hover:border-white/20 dark:hover:bg-white/[0.08] dark:hover:text-white"
                        title="Minimize Player"
                    >
                        <Minimize2 className="h-5 w-5 transition-transform group-hover:scale-105" strokeWidth={2.25} />
                    </button>
                </div>

                <div className="flex h-full w-full flex-col lg:flex-row-reverse">

                    {/* Right Area: Player Stage — lg+ = original centered column; max-lg = mobile/tablet layout */}
                    <div className={`relative flex min-h-0 flex-1 flex-col overflow-y-auto scrollbar-hide bg-gradient-to-b from-slate-50 via-white to-slate-100/95 backdrop-blur-2xl transition-all duration-500 ease-in-out dark:from-slate-950/90 dark:via-[#0c1222]/95 dark:to-slate-950/90 lg:overflow-y-auto lg:overscroll-contain lg:border-l-2 lg:border-slate-300/80 lg:shadow-none dark:lg:border-white/[0.07] dark:lg:shadow-[inset_-1px_0_0_rgba(255,255,255,0.04)] ${activeTab === 'player' ? 'translate-x-0 opacity-100' : 'hidden -translate-x-10 opacity-0 lg:flex lg:translate-x-0 lg:opacity-100'}`}>
                        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-purple-500/[0.04] via-transparent to-indigo-100/30 dark:from-purple-500/[0.06] dark:to-indigo-950/20" />
                        <div className="pointer-events-none absolute left-1/2 top-[38%] h-[min(360px,50vh)] w-[min(380px,78vw)] -translate-x-1/2 rounded-full bg-purple-400/10 blur-[90px] dark:bg-purple-500/10 md:top-[42%] md:h-[min(220px,38vh)] md:w-[min(260px,85%)] lg:top-[42%]" />

                        {/* max-lg: vertically centered block + even gaps; lg+: centered column */}
                        <div className="relative z-10 mx-auto flex w-full max-w-2xl flex-col items-center px-4 pt-[calc(env(safe-area-inset-top,0px)+3rem)] sm:px-5 md:max-lg:max-w-4xl md:max-lg:px-5 md:max-lg:pt-[calc(env(safe-area-inset-top,0px)+3rem)] lg:max-w-2xl lg:min-h-0 lg:shrink lg:flex-1 lg:justify-center lg:gap-7 lg:px-8 lg:pb-5 lg:pt-12 max-lg:flex-1 max-lg:justify-center max-lg:gap-4 max-lg:py-2 max-lg:pb-[max(1rem,env(safe-area-inset-bottom,0px))]">
                            <header className="flex w-full flex-col items-center justify-center max-lg:mb-0 lg:pt-0">
                                <p className="flex items-baseline gap-0.5 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl md:text-2xl md:max-lg:text-[1.35rem] lg:text-[1.65rem] dark:text-white" aria-label="LexPlayer">
                                    <span className="dark:text-white">Lex</span>
                                    <span className="bg-gradient-to-r from-violet-600 via-fuchsia-600 to-purple-600 bg-clip-text text-transparent dark:from-violet-300 dark:via-fuchsia-200 dark:to-purple-400">Player</span>
                                </p>
                                <div className="mt-1 h-[2px] w-10 rounded-full bg-gradient-to-r from-purple-500/0 via-purple-400/80 to-fuchsia-500/0 max-lg:mt-0.5 max-lg:w-9 lg:mt-2 lg:h-[3px] lg:w-12" aria-hidden />
                            </header>

                            {/* Mobile: vertical; Tablet (md–lg): art | meta+controls; Desktop lg+: vertical stack */}
                            <div className="flex w-full flex-col items-center gap-4 md:max-lg:flex-row md:max-lg:items-start md:max-lg:gap-4 lg:flex-col lg:items-center lg:gap-7">
                                {/* Artwork column */}
                                <div className="relative flex w-full max-w-[min(100%,18rem)] shrink-0 justify-center md:max-lg:max-w-none md:max-lg:w-[40%] md:max-lg:min-w-0 md:max-lg:self-center lg:max-w-none lg:w-full">
                                    <div className="group relative flex-shrink-0">
                                        <div className="pointer-events-none absolute -inset-3 rounded-[1.75rem] bg-gradient-to-br from-purple-500/25 via-fuchsia-500/12 to-transparent opacity-80 blur-2xl transition-opacity group-hover:opacity-100 md:-inset-2.5 md:rounded-xl lg:-inset-4 lg:rounded-[2rem]" />
                                        <div className="relative mx-auto flex h-[12rem] w-[12rem] max-h-[min(36vh,210px)] max-w-[min(36vh,210px)] items-center justify-center overflow-hidden rounded-2xl border-2 border-slate-300/85 bg-white shadow-[0_12px_48px_-16px_rgba(88,28,135,0.15)] ring-1 ring-slate-200/60 backdrop-blur-sm sm:h-56 sm:w-56 sm:max-h-[min(38vh,220px)] sm:max-w-[min(38vh,220px)] md:max-lg:h-44 md:max-lg:w-44 md:max-lg:max-h-none md:max-lg:max-w-none md:max-lg:rounded-2xl lg:mx-0 lg:h-48 lg:w-48 lg:max-h-none lg:max-w-none lg:rounded-[1.75rem] dark:border-white/[0.1] dark:bg-white/[0.04] dark:shadow-[0_12px_48px_-16px_rgba(88,28,135,0.45)] dark:ring-white/[0.08]">
                                            <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-white via-slate-50/80 to-transparent dark:from-white/[0.12] dark:via-white/[0.03]" />
                                            <Headphones className={`relative z-10 h-[4.75rem] w-[4.75rem] text-purple-600 drop-shadow-[0_8px_24px_rgba(124,58,237,0.25)] transition-transform duration-700 dark:text-white/90 dark:drop-shadow-[0_8px_24px_rgba(124,58,237,0.45)] sm:h-[5rem] sm:w-[5rem] md:max-lg:h-24 md:max-lg:w-24 lg:h-[7.25rem] lg:w-[7.25rem] ${isPlaying ? '-translate-y-3 scale-95 md:max-lg:-translate-y-2 lg:-translate-y-3' : 'group-hover:scale-105'}`} strokeWidth={1.25} />
                                            {isPlaying && (
                                                <div className="absolute bottom-4 left-1/2 z-10 flex h-8 w-full max-w-[85%] -translate-x-1/2 items-end justify-center gap-1.5 px-3 md:bottom-3 md:max-lg:h-7 lg:bottom-5 lg:h-9">
                                                    {[0.4, 0.8, 0.6, 1.0, 0.5, 0.9, 0.7, 0.3, 0.6, 0.8].map((h, i) => (
                                                        <div key={i} className="w-1.5 animate-[bounce_1s_infinite] rounded-full bg-white/95 shadow-[0_0_8px_rgba(255,255,255,0.85)] md:w-2" style={{ height: `${h * 100}%`, animationDelay: `${i * 0.1}s` }} />
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                {/* Track info + scrub + transport */}
                                <div className="flex w-full min-w-0 flex-col items-center gap-4 md:max-lg:flex-1 md:max-lg:justify-start md:max-lg:gap-4 lg:w-full lg:gap-6">
                                    <div className="z-10 w-full max-w-xl px-0 text-center md:max-lg:max-w-none md:max-lg:text-left lg:max-w-xl lg:px-2 lg:text-center">
                                        <h2 className="line-clamp-2 text-lg font-semibold leading-snug tracking-tight text-slate-900 drop-shadow-sm dark:text-white sm:text-xl md:max-lg:line-clamp-3 md:max-lg:text-[1.2rem] md:text-lg md:leading-snug lg:text-xl lg:font-bold">
                                            {currentTrack ? currentTrack.title : 'LexPlayer is idle'}
                                        </h2>
                                        <p className="mt-1 text-[10px] font-medium uppercase leading-relaxed tracking-[0.1em] text-slate-500 sm:text-[11px] md:max-lg:mt-1 md:mt-1.5 md:text-[11px] md:leading-snug lg:mt-2 lg:text-xs lg:font-semibold lg:tracking-[0.12em] dark:text-white/45">
                                            {currentTrack ? (activePlaylistName ? `${activePlaylistName} · ${currentTrack.subtitle}` : currentTrack.subtitle) : 'Add items to your LexPlaylist'}
                                        </p>
                                        <div className="mt-2 flex min-h-0 flex-col items-center justify-center md:max-lg:items-start md:mt-1.5 lg:mt-3 lg:items-center">
                                            {error && (
                                                <div className="inline-flex max-w-full items-center gap-2 rounded-2xl border border-rose-300/80 bg-rose-50 px-5 py-2.5 text-center text-xs font-bold text-rose-800 animate-in shake md:max-lg:text-left dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200/95">
                                                    {error}
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    <div className="w-full max-w-xl pt-0.5 md:max-lg:max-w-none lg:max-w-xl">
                                        <PlaybackProgress audioRef={audioRef} isPlaying={isPlaying} isMinimized={false} />
                                    </div>

                                    <div className="z-10 flex w-full max-w-2xl flex-col items-center pb-0 md:max-lg:max-w-none lg:max-w-2xl">
                                        <div className="flex w-full items-center justify-center gap-2 px-1 sm:gap-3 md:max-lg:gap-3 md:max-lg:px-2 lg:gap-10 lg:px-4">
                                            <button
                                                type="button"
                                                onClick={handlePrevious}
                                                disabled={playlist.length === 0}
                                                className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border-2 border-slate-300/85 bg-white text-slate-600 shadow-md transition-all hover:border-purple-200 hover:bg-purple-50 hover:text-purple-800 active:scale-95 disabled:pointer-events-none disabled:opacity-25 sm:h-14 sm:w-14 md:max-lg:h-[3.75rem] md:max-lg:w-[3.75rem] lg:h-11 lg:w-11 dark:border-white/10 dark:bg-white/[0.06] dark:text-white/80 dark:hover:border-white/18 dark:hover:bg-white/[0.1] dark:hover:text-white"
                                                aria-label="Previous track"
                                            >
                                                <SkipBack className="h-6 w-6 sm:h-7 sm:w-7 md:max-lg:h-8 md:max-lg:w-8 lg:h-6 lg:w-6" fill="currentColor" />
                                            </button>

                                            <button
                                                type="button"
                                                onClick={handlePlayPause}
                                                disabled={playlist.length === 0}
                                                className="flex h-[7.5rem] w-[7.5rem] shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-violet-600 text-white shadow-[0_16px_44px_-6px_rgba(124,58,237,0.55)] ring-2 ring-white/10 transition-all hover:scale-[1.03] hover:shadow-[0_20px_48px_-6px_rgba(168,85,247,0.5)] active:scale-95 disabled:opacity-45 disabled:hover:scale-100 sm:h-[8.25rem] sm:w-[8.25rem] md:max-lg:h-[9rem] md:max-lg:w-[9rem] lg:h-[6.5rem] lg:w-[6.5rem] lg:ring-1"
                                                aria-label={isPlaying ? 'Pause' : 'Play'}
                                            >
                                                {isLoading ? (
                                                    <div className="h-11 w-11 animate-spin rounded-full border-[3px] border-white/25 border-t-white sm:h-12 sm:w-12 md:max-lg:h-14 md:max-lg:w-14 lg:h-10 lg:w-10" />
                                                ) : isPlaying ? (
                                                    <div className="flex h-8 w-[4.25rem] items-end justify-center gap-0.5 sm:h-9 sm:w-20 sm:gap-1 md:max-lg:h-12 md:max-lg:w-24 lg:h-6 lg:w-12" aria-hidden>
                                                        {[0.4, 1.0, 0.7, 0.5].map((h, i) => (
                                                            <div
                                                                key={i}
                                                                className="w-2.5 rounded-full bg-white animate-[bounce_0.8s_infinite] shadow-[0_0_10px_rgba(255,255,255,0.95)] sm:w-3 md:max-lg:w-3.5 lg:w-1.5"
                                                                style={{ height: `${h * 100}%`, animationDelay: `${i * 0.15}s` }}
                                                            />
                                                        ))}
                                                    </div>
                                                ) : (
                                                    <Play className="ml-1 h-14 w-14 sm:h-16 sm:w-16 md:max-lg:h-[4.5rem] md:max-lg:w-[4.5rem] lg:h-12 lg:w-12" fill="currentColor" />
                                                )}
                                            </button>

                                            <button
                                                type="button"
                                                onClick={handleNext}
                                                disabled={playlist.length === 0}
                                                className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border-2 border-slate-300/85 bg-white text-slate-600 shadow-md transition-all hover:border-purple-200 hover:bg-purple-50 hover:text-purple-800 active:scale-95 disabled:pointer-events-none disabled:opacity-25 sm:h-14 sm:w-14 md:max-lg:h-[3.75rem] md:max-lg:w-[3.75rem] lg:h-11 lg:w-11 dark:border-white/10 dark:bg-white/[0.06] dark:text-white/80 dark:hover:border-white/18 dark:hover:bg-white/[0.1] dark:hover:text-white"
                                                aria-label="Next track"
                                            >
                                                <SkipForward className="h-6 w-6 sm:h-7 sm:w-7 md:max-lg:h-8 md:max-lg:w-8 lg:h-6 lg:w-6" fill="currentColor" />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Left Area: Playlist — side panel from lg+; full-width sheet on mobile/tablet tab */}
                    <div className={`z-20 flex h-full w-full shrink-0 flex-col border-b-2 border-slate-300/80 bg-gradient-to-b from-slate-50 via-white to-slate-100/95 shadow-sm backdrop-blur-2xl transition-all duration-500 ease-in-out dark:border-white/[0.07] dark:from-slate-950/90 dark:via-[#0c1222]/95 dark:to-slate-950/90 dark:shadow-[inset_1px_0_0_rgba(255,255,255,0.04),-12px_0_40px_-8px_rgba(0,0,0,0.4)] lg:w-80 lg:border-b-0 lg:border-r lg:border-slate-200/80 dark:lg:border-white/[0.07] xl:w-[420px] ${activeTab === 'playlist' ? 'translate-x-0 opacity-100' : 'hidden -translate-x-10 opacity-0 lg:flex lg:translate-x-0 lg:opacity-100'}`}>
                        <div className="flex items-center justify-between gap-3 border-b-2 border-slate-300/80 bg-slate-50/90 p-4 max-lg:pt-[calc(env(safe-area-inset-top,0px)+3.75rem)] md:gap-4 dark:border-white/[0.06] dark:bg-white/[0.02] lg:p-5 lg:pt-5">
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
                                    <h3 className="truncate text-base font-bold tracking-tight text-slate-900 max-md:leading-tight md:text-lg dark:text-white">
                                        {activePlaylistName || 'LexPlaylist'}
                                    </h3>
                                    <div className="mt-1 flex items-center gap-2">
                                        <span className="inline-flex items-center rounded-full border-2 border-slate-300/85 bg-white px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-slate-500 dark:border-white/10 dark:bg-white/[0.04] dark:text-white/45">
                                            {displayPlaylist.length} {displayPlaylist.length === 1 ? 'track' : 'tracks'}
                                        </span>
                                    </div>
                                </div>
                            </div>
                            <div className="flex items-center gap-2 shrink-0">
                                {displayPlaylist.length > 0 && (
                                    <>
                                        <button
                                            type="button"
                                            onClick={handleBulkCacheDownloadClick}
                                            className={`flex h-11 w-11 md:h-12 md:w-12 items-center justify-center rounded-2xl border transition-all ${isBulkDownloading ? 'border-rose-300 bg-rose-50 text-rose-800 hover:bg-rose-100 dark:border-rose-500/35 dark:bg-rose-500/15 dark:text-rose-100 dark:hover:bg-rose-500/25' : cachedCount === displayPlaylist.length ? 'border-emerald-300/80 bg-emerald-50 text-emerald-700 dark:border-emerald-500/25 dark:bg-emerald-500/10 dark:text-emerald-400' : 'border-slate-200/90 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900 dark:border-white/10 dark:bg-white/[0.04] dark:text-white/55 dark:hover:border-white/20 dark:hover:bg-white/[0.08] dark:hover:text-white'}`}
                                            title={
                                                isBulkDownloading
                                                    ? 'Stop download'
                                                    : cachedCount === displayPlaylist.length
                                                      ? 'All tracks cached for offline'
                                                      : cachedCount > 0
                                                        ? `${cachedCount}/${displayPlaylist.length} items cached — download all for offline`
                                                        : 'Download all for offline'
                                            }
                                            aria-label={isBulkDownloading ? 'Stop bulk download' : 'Download all for offline'}
                                        >
                                            {isBulkDownloading ? (
                                                <div className="relative flex items-center justify-center">
                                                    <div className="absolute -inset-2.5 animate-spin rounded-full border-[3px] border-rose-500/20 border-t-rose-600 dark:border-rose-400/20 dark:border-t-rose-400" />
                                                    <Square className="h-4 w-4 fill-current relative z-10" strokeWidth={2.5} />
                                                </div>
                                            ) : cachedCount === displayPlaylist.length ? (
                                                <CheckCircle2 className="w-5 h-5" strokeWidth={2.25} />
                                            ) : (
                                                <div className="relative flex items-center justify-center">
                                                    <DownloadCloud className="w-5 h-5" strokeWidth={2} />
                                                    {cachedCount > 0 && (
                                                        <span className="absolute -right-1 -top-1 flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-emerald-500 px-0.5 text-[8px] font-black text-white ring-2 ring-white dark:ring-slate-950">
                                                            {cachedCount}
                                                        </span>
                                                    )}
                                                </div>
                                            )}
                                        </button>
                                        {cachedCount > 0 && !isBulkDownloading && (
                                            <button
                                                type="button"
                                                onClick={() => {
                                                    if (window.confirm(`Remove offline copies for all ${cachedCount} cached track(s) in this queue?`)) {
                                                        clearQueueCachedTracks();
                                                    }
                                                }}
                                                className="flex h-11 w-11 md:h-12 md:w-12 items-center justify-center rounded-2xl border border-rose-300/80 bg-rose-50 text-rose-800 transition-all hover:border-rose-400/60 hover:bg-rose-100 dark:border-rose-500/25 dark:bg-rose-500/10 dark:text-rose-200/95 dark:hover:border-rose-400/40 dark:hover:bg-rose-500/20"
                                                title="Clear offline copies for this queue"
                                            >
                                                <Eraser className="h-5 w-5" strokeWidth={2.25} />
                                            </button>
                                        )}
                                    </>
                                )}
                            </div>
                        </div>

                        {/* Bulk Download Progress Bar Overlay */}
                        {isBulkDownloading && (
                            <div className="border-b-2 border-slate-300/80 bg-gradient-to-r from-purple-100/90 via-violet-50/80 to-transparent px-5 py-3.5 animate-in slide-in-from-top-4 duration-300 dark:border-white/[0.06] dark:from-purple-500/12 dark:via-violet-500/8 dark:to-transparent">
                                <div className="mb-2 flex items-center justify-between">
                                    <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-purple-900 dark:text-purple-100/90">{bulkDownloadStatusText}</span>
                                    <span className="tabular-nums text-[10px] font-bold text-purple-800 dark:text-purple-200">{bulkDownloadProgress}%</span>
                                </div>
                                <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200/90 ring-1 ring-slate-300/50 dark:bg-white/[0.06] dark:ring-white/[0.04]">
                                    <div
                                        className="h-full rounded-full bg-gradient-to-r from-fuchsia-500 via-purple-500 to-violet-400 transition-all duration-500 shadow-[0_0_12px_rgba(168,85,247,0.4)]"
                                        style={{ width: `${bulkDownloadProgress}%` }}
                                    />
                                </div>
                            </div>
                        )}

                        <div className="border-b-2 border-slate-300/80 bg-gradient-to-b from-slate-50/95 to-transparent px-4 py-5 dark:border-white/[0.05] dark:from-white/[0.03] md:px-5">
                            {!isCreating ? (
                                <>
                                    <div className="flex flex-col gap-3 sm:flex-row sm:items-stretch">
                                        <button
                                            type="button"
                                            onClick={() => setIsCreating(true)}
                                            className="shrink-0 rounded-2xl border border-purple-300/80 bg-purple-100/90 px-4 py-3 text-center text-[11px] font-extrabold uppercase tracking-[0.15em] text-purple-900 transition-all hover:border-purple-400/70 hover:bg-purple-100 active:scale-[0.98] sm:w-auto dark:border-purple-400/35 dark:bg-purple-500/15 dark:text-purple-100 dark:hover:border-purple-300/50 dark:hover:bg-purple-500/25"
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
                                    {playlistFetchError && (
                                        <p className="mt-3 text-[11px] leading-relaxed text-amber-800 dark:text-amber-200/90">
                                            {playlistFetchError === 'unauthorized'
                                                ? 'Playlists could not be loaded (server rejected the session). Try refreshing the page.'
                                                : playlistFetchError === 'network'
                                                  ? 'Could not reach the server to load playlists. Check your connection.'
                                                  : 'Playlists could not be loaded.'}
                                        </p>
                                    )}
                                </>
                            ) : (
                                <div className="flex flex-wrap items-center gap-2">
                                    <input type="text" placeholder="Playlist name…" value={newPlaylistName} onChange={(e) => setNewPlaylistName(e.target.value)} className="min-w-[10rem] flex-1 rounded-2xl border-2 border-slate-300/85 bg-white px-4 py-3 text-sm text-slate-900 placeholder:text-slate-400 outline-none ring-0 focus:border-purple-400/50 focus:bg-white dark:border-white/10 dark:bg-white/[0.05] dark:text-white dark:placeholder:text-white/25 dark:focus:border-purple-400/40 dark:focus:bg-white/[0.07]" autoFocus />
                                    <button type="button" onClick={async () => { if(newPlaylistName.trim()){ await createPlaylist(newPlaylistName.trim()); setNewPlaylistName(''); setIsCreating(false); }}} className="flex h-11 w-11 items-center justify-center rounded-2xl border border-purple-400/50 bg-purple-100 text-purple-900 transition-all hover:bg-purple-200 dark:border-purple-400/40 dark:bg-purple-500/20 dark:text-purple-100 dark:hover:bg-purple-500/35" aria-label="Save playlist">
                                        <Save size={20} strokeWidth={2.25} />
                                    </button>
                                    <button type="button" onClick={() => setIsCreating(false)} className="flex h-11 w-11 items-center justify-center rounded-2xl border-2 border-slate-300/85 bg-white text-slate-500 transition-all hover:bg-slate-50 hover:text-slate-800 dark:border-white/10 dark:bg-white/[0.04] dark:text-white/45 dark:hover:bg-white/[0.08] dark:hover:text-white" aria-label="Cancel">
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
                                                className="inline-flex items-center gap-1.5 rounded-xl border-2 border-slate-300/85 bg-white px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-slate-700 transition-all hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900 dark:border-white/12 dark:bg-white/[0.04] dark:text-white/70 dark:hover:border-white/20 dark:hover:bg-white/[0.08] dark:hover:text-white"
                                            >
                                                <Edit2 size={12} strokeWidth={2.5} /> Rename
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => window.confirm("Delete playlist?") && deletePlaylist(activePlaylistId)}
                                                className="inline-flex shrink-0 items-center gap-1.5 rounded-xl border border-rose-300/80 bg-rose-50 px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-rose-800 transition-all hover:border-rose-400/60 hover:bg-rose-100 dark:border-rose-500/20 dark:bg-rose-500/[0.08] dark:text-rose-200/90 dark:hover:border-rose-400/35 dark:hover:bg-rose-500/15"
                                            >
                                                <Trash2 size={12} strokeWidth={2.5} /> Delete
                                            </button>
                                        </div>
                                    ) : (
                                        <div className="flex w-full flex-wrap items-center gap-2">
                                            <input type="text" value={editPlaylistName} onChange={(e) => setEditPlaylistName(e.target.value)} className="min-w-0 flex-1 rounded-xl border-2 border-slate-300/85 bg-white px-3 py-2 text-xs text-slate-900 outline-none focus:border-purple-400/50 dark:border-white/12 dark:bg-white/[0.05] dark:text-white dark:focus:border-purple-400/40" autoFocus />
                                            <button type="button" onClick={() => { if(editPlaylistName.trim()){ renamePlaylist(activePlaylistId, editPlaylistName.trim()); setIsEditing(false); }}} className="flex h-9 w-9 items-center justify-center rounded-xl border border-purple-400/50 bg-purple-100 text-purple-900 hover:bg-purple-200 dark:border-purple-400/35 dark:bg-purple-500/20 dark:text-purple-200 dark:hover:bg-purple-500/30" aria-label="Save name">
                                                <Save size={16} strokeWidth={2.5} />
                                            </button>
                                            <button type="button" onClick={() => setIsEditing(false)} className="flex h-9 w-9 items-center justify-center rounded-xl border-2 border-slate-300/85 bg-white text-slate-500 hover:text-slate-800 dark:border-white/10 dark:bg-white/[0.04] dark:text-white/45 dark:hover:text-white" aria-label="Cancel rename">
                                                <X size={16} strokeWidth={2.5} />
                                            </button>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>

                        <div className="flex-1 overflow-y-auto scroll-smooth overscroll-contain px-4 py-5 md:px-5 md:pb-6">
                            <VirtualizedPlaylist 
                                items={displayPlaylist}
                                currentIndex={listUiCurrentIndex}
                                isPlaying={isPlaying}
                                isLoading={isLoading}
                                onPlay={activatePlaylistRow}
                                onRemove={handlePlaylistRemove}
                                onClearDownload={clearTrackFromCache}
                            />
                        </div>
                    </div>
                </div>
                
                {/* Bulk Add Modal */}
                {showBulkModal && (
                    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-3xl dark:bg-black/70">
                        <div className="w-full max-w-md overflow-hidden rounded-[32px] border-2 border-slate-300/85 bg-white shadow-2xl backdrop-blur-3xl dark:border-white/10 dark:bg-[#1e293b]/40">
                            <div className="flex items-center justify-between border-b-2 border-slate-300/80 bg-slate-50/95 px-8 py-6 dark:border-white/5 dark:bg-white/[0.02]">
                                <div>
                                    <h3 className="flex items-center gap-2 text-xl font-black tracking-tight text-slate-900 dark:text-white">Add Tracks</h3>
                                    <p className="mt-1 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 dark:text-white/30">Bulk create audio queue</p>
                                </div>
                                <button type="button" onClick={() => setShowBulkModal(false)} className="text-slate-400 hover:text-slate-700 dark:text-white/40 dark:hover:text-white"><X size={24} /></button>
                            </div>
                            <div className="space-y-6 p-8">
                                {bulkError && <div className="rounded-2xl border border-red-300/80 bg-red-50 p-4 text-xs font-black uppercase text-red-800 dark:border-red-500/40 dark:bg-red-500/20 dark:text-red-400">{bulkError}</div>}
                                <div className="space-y-2">
                                    <label className="ml-1 block text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 dark:text-white/30">Destination Playlist</label>
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
                                    <label className="ml-1 block text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 dark:text-white/30">Select Codal</label>
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
                                    <label className="ml-1 block text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 dark:text-white/30">
                                        {bulkForm.codal === 'ROC' ? 'Rule Range (Optional)' : 
                                         bulkForm.codal === 'CONST' ? 'Article / Section Range (Optional)' : 
                                         'Article Range (Optional)'}
                                    </label>
                                    <input type="text" placeholder="e.g. 1-20" value={bulkForm.range} onChange={e => setBulkForm({...bulkForm, range: e.target.value})} className="w-full rounded-2xl border-2 border-slate-300/85 bg-white p-4 text-sm font-bold text-slate-900 outline-none placeholder:text-slate-400 dark:border-white/10 dark:bg-white/5 dark:text-white" />
                                </div>
                            </div>
                            <div className="flex justify-end gap-4 border-t-2 border-slate-300/80 bg-slate-50/90 px-8 py-6 dark:border-white/5 dark:bg-white/[0.02]">
                                <button type="button" onClick={() => setShowBulkModal(false)} className="text-xs font-black uppercase tracking-widest text-slate-500 transition-all hover:text-slate-800 dark:text-white/30 dark:hover:text-white">Cancel</button>
                                <button type="button" onClick={handleAddBulkItems} disabled={isBulking} className="rounded-[20px] bg-purple-600 px-10 py-4 text-xs font-black uppercase tracking-widest text-white shadow-xl shadow-purple-500/20 transition-all hover:bg-purple-500 disabled:opacity-50 active:scale-95 dark:bg-purple-500 dark:hover:bg-purple-400">
                                    {isBulking ? "Adding..." : "Add to Tracks"}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );

    return typeof document !== 'undefined' ? createPortal(fullScreenUi, document.body) : null;
};

export default LexPlayer;
