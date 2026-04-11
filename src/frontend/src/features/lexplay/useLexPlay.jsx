import React, { createContext, useContext, useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from '@clerk/clerk-react';

const LexPlayContext = createContext();
const LexPlayApiContext = createContext();

/** Bust Service Worker `audio-cache` after server TTS text changes (bump with api `CACHE_VERSION` for codal). */
export const LEXPLAY_CODAL_AUDIO_CV = 'v22';

/** Relative URL for LexPlay TTS/audio (same formula as playTrack). */
function buildAudioFetchPath(track, rate = 1.0) {
    const codeParam = track.code_id ? `code=${track.code_id}&` : '';
    const cvParam =
        track.type === 'codal' ? `cv=${LEXPLAY_CODAL_AUDIO_CV}&` : '';
    return `/api/audio/${track.type}/${track.id}?${codeParam}${cvParam}rate=${rate}`;
}

/** Compare loaded audio URL to the track (pathname + query). Fixes resume after lock screen: old check omitted `rate=` so src never matched and we always reloaded. */
function audioSrcMatchesCurrentTrack(audioSrc, track, rate = 1.0) {
    if (!audioSrc || !track) return false;
    if (typeof window === 'undefined') return false;
    if (!audioSrc || audioSrc === window.location.href) return false;
    if (audioSrc.startsWith('blob:')) {
        return true;
    }
    try {
        const cur = new URL(audioSrc, window.location.origin);
        const exp = new URL(buildAudioFetchPath(track, rate), window.location.origin);
        return cur.pathname === exp.pathname && cur.search === exp.search;
    } catch {
        return false;
    }
}

export const useLexPlay = () => {
    return useContext(LexPlayContext);
};

export const useLexPlayApi = () => {
    return useContext(LexPlayApiContext);
};

export const LexPlayProvider = ({ children }) => {
    const { getToken, isLoaded, isSignedIn } = useAuth();
    const [playlist, setPlaylist] = useState([]); // This is the "Active Queue"
    const [savedPlaylists, setSavedPlaylists] = useState([]);
    /** Set when GET /api/playlists fails (e.g. 401) so UI can explain empty dropdown while signed in */
    const [playlistFetchError, setPlaylistFetchError] = useState(null);
    const [activePlaylistId, setActivePlaylistId] = useState(null);
    /** When set, LexPlay list UI shows this saved playlist while playback queue (`playlist`) stays unchanged — used when switching saved playlists during playback. */
    const [browsePlaylistItems, setBrowsePlaylistItems] = useState(null);
    const [currentIndex, setCurrentIndex] = useState(-1);
    const [isPlaying, setIsPlaying] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [volume, setVolume] = useState(1.0);
    const [repeatMode, setRepeatMode] = useState('none'); // 'none', 'all', 'one'
    const [isShuffle, setIsShuffle] = useState(false);
    
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const audioRef = useRef(null);
    const playlistRef = useRef([]);
    const currentIndexRef = useRef(-1);
    const retryCountRef = useRef(0);
    const repeatModeRef = useRef('none');
    const isShuffleRef = useRef(false);
    const isMounted = useRef(true);
    /** Prefetched blob URL for the upcoming track index (lock-screen / iOS gapless advance). */
    const prefetchedNextRef = useRef(null);
    const handleTrackEndRef = useRef(() => {});

    useEffect(() => {
        isMounted.current = true;
        return () => { isMounted.current = false; };
    }, []);
    
    // MediaSession Stable Handler Refs
    const playPauseRef = useRef(null);
    const nextTrackRef = useRef(null);
    const prevTrackRef = useRef(null);
    const seekForwardRef = useRef(null);
    const seekBackwardRef = useRef(null);
    
    const MAX_RETRIES = 3;
    /** LexPlay audio is always synthesized at 1× (UI speed picker removed). */
    const PLAYBACK_RATE = 1.0;

    const clearNextPrefetch = useCallback(() => {
        const p = prefetchedNextRef.current;
        if (p?.objectUrl) {
            try {
                URL.revokeObjectURL(p.objectUrl);
            } catch {
                /* ignore */
            }
        }
        prefetchedNextRef.current = null;
    }, []);

    /** Must be declared before any useCallback that lists it in deps (TDZ-safe). */
    const safeSetState = useCallback((setter, value) => {
        if (isMounted.current) setter(value);
    }, []);

    // Keep refs in sync with state
    useEffect(() => { playlistRef.current = playlist; }, [playlist]);
    useEffect(() => { currentIndexRef.current = currentIndex; }, [currentIndex]);

    const currentTrack = currentIndex >= 0 && currentIndex < playlist.length ? playlist[currentIndex] : null;

    const displayPlaylist = useMemo(
        () => (browsePlaylistItems !== null ? browsePlaylistItems : playlist),
        [browsePlaylistItems, playlist]
    );

    const listUiCurrentIndex = useMemo(() => {
        if (browsePlaylistItems === null) {
            return currentIndex;
        }
        if (!currentTrack) return -1;
        return browsePlaylistItems.findIndex(
            (t) => String(t.id) === String(currentTrack.id) && t.type === currentTrack.type
        );
    }, [browsePlaylistItems, currentTrack, currentIndex]);

    // --- Offline cache: downloads run in provider so they continue when browsing playlists or when LexPlayer unmounts ---
    const bulkDownloadCancelRef = useRef(false);
    const bulkFetchAbortRef = useRef(null);
    const trackDownloadAbortRef = useRef(new Map());

    const [isBulkDownloading, setIsBulkDownloading] = useState(false);
    const [bulkDownloadProgress, setBulkDownloadProgress] = useState(0);
    const [bulkDownloadStatusText, setBulkDownloadStatusText] = useState('');
    const [downloadingTrackIds, setDownloadingTrackIds] = useState(() => new Set());
    const [cachedCount, setCachedCount] = useState(0);
    const [cachedTrackIds, setCachedTrackIds] = useState(() => new Set());
    const cachedTrackIdsRef = useRef(cachedTrackIds);
    useEffect(() => {
        cachedTrackIdsRef.current = cachedTrackIds;
    }, [cachedTrackIds]);

    const refreshCacheForDisplayPlaylist = useCallback(async () => {
        if (!displayPlaylist || displayPlaylist.length === 0 || !('caches' in window)) {
            setCachedCount(0);
            setCachedTrackIds(new Set());
            return;
        }
        try {
            const cache = await caches.open('audio-cache');
            const allKeys = await cache.keys();
            const storedUrls = new Set(allKeys.map((r) => r.url));
            let count = 0;
            const ids = new Set();
            for (const track of displayPlaylist) {
                if (!track?.id || !track?.type) continue;
                const relUrl = buildAudioFetchPath(track, 1.0);
                if (!relUrl) continue;
                const absUrl = new URL(relUrl, window.location.origin).href;
                if (storedUrls.has(absUrl)) {
                    count++;
                    ids.add(String(track.id));
                }
            }
            setCachedCount(count);
            setCachedTrackIds(ids);
        } catch (e) {
            console.warn('[LexPlay] Cache check failed:', e);
        }
    }, [displayPlaylist]);

    useEffect(() => {
        refreshCacheForDisplayPlaylist();
    }, [refreshCacheForDisplayPlaylist]);

    const stopTrackCacheDownload = useCallback((trackId) => {
        const id = String(trackId);
        trackDownloadAbortRef.current.get(id)?.abort();
    }, []);

    const startTrackCacheDownload = useCallback(
        async (track) => {
            if (!track?.id || !track?.type) return;
            const id = String(track.id);
            if (trackDownloadAbortRef.current.has(id)) return;
            if (cachedTrackIdsRef.current.has(id)) return;

            const audioUrl = buildAudioFetchPath(track, 1.0);
            if (!audioUrl) return;

            const ac = new AbortController();
            trackDownloadAbortRef.current.set(id, ac);
            setDownloadingTrackIds((prev) => new Set(prev).add(id));

            try {
                const response = await fetch(audioUrl, { signal: ac.signal });
                if (response.ok && 'caches' in window) {
                    const cache = await caches.open('audio-cache');
                    await cache.put(audioUrl, response);
                } else if (!response.ok) {
                    console.error('[LexPlay] Download failed:', response.status);
                }
            } catch (err) {
                if (err?.name !== 'AbortError') console.error('[LexPlay] Cache save failed:', err);
            } finally {
                trackDownloadAbortRef.current.delete(id);
                setDownloadingTrackIds((prev) => {
                    const next = new Set(prev);
                    next.delete(id);
                    return next;
                });
                await refreshCacheForDisplayPlaylist();
            }
        },
        [refreshCacheForDisplayPlaylist]
    );

    const handleBulkCacheDownloadClick = useCallback(() => {
        if (isBulkDownloading) {
            bulkDownloadCancelRef.current = true;
            bulkFetchAbortRef.current?.abort();
            return;
        }
        const snapshot = displayPlaylist ? [...displayPlaylist] : [];
        if (snapshot.length === 0) return;

        void (async () => {
            bulkDownloadCancelRef.current = false;
            bulkFetchAbortRef.current = null;
            setIsBulkDownloading(true);
            setBulkDownloadProgress(0);
            setBulkDownloadStatusText('Starting...');

            let completed = 0;
            const total = snapshot.length;
            let successCount = 0;

            try {
                const cache = 'caches' in window ? await caches.open('audio-cache') : null;

                for (const track of snapshot) {
                    if (bulkDownloadCancelRef.current) break;

                    const audioUrl = buildAudioFetchPath(track, 1.0);
                    if (audioUrl) {
                        safeSetState(setBulkDownloadStatusText, `Downloading: ${track.title}`);
                        try {
                            const existing = cache ? await cache.match(audioUrl) : null;
                            if (existing) {
                                successCount++;
                                await refreshCacheForDisplayPlaylist();
                            } else {
                                const ac = new AbortController();
                                bulkFetchAbortRef.current = ac;
                                let resp;
                                try {
                                    resp = await fetch(audioUrl, { signal: ac.signal });
                                } catch (fetchErr) {
                                    bulkFetchAbortRef.current = null;
                                    if (fetchErr?.name === 'AbortError') {
                                        bulkDownloadCancelRef.current = true;
                                        break;
                                    }
                                    throw fetchErr;
                                }
                                bulkFetchAbortRef.current = null;
                                if (bulkDownloadCancelRef.current) break;
                                if (resp.ok) {
                                    if (cache) await cache.put(audioUrl, resp);
                                    successCount++;
                                    await refreshCacheForDisplayPlaylist();
                                } else {
                                    console.warn(`[LexPlay] Server error ${resp.status} for ${track.title}`);
                                }
                            }
                        } catch (e) {
                            bulkFetchAbortRef.current = null;
                            if (e?.name === 'AbortError') {
                                bulkDownloadCancelRef.current = true;
                                break;
                            }
                            console.warn(`[LexPlay] Failed to download ${track.title}:`, e);
                        }
                    }
                    completed++;
                    safeSetState(setBulkDownloadProgress, Math.round((completed / total) * 100));
                }

                const cancelled = bulkDownloadCancelRef.current;
                safeSetState(
                    setBulkDownloadStatusText,
                    cancelled ? 'Download cancelled' : `✓ ${successCount}/${total} tracks cached for offline`
                );
                await refreshCacheForDisplayPlaylist();
                const delay = cancelled ? 1500 : 3000;
                setTimeout(() => {
                    safeSetState(setIsBulkDownloading, false);
                    safeSetState(setBulkDownloadProgress, 0);
                    safeSetState(setBulkDownloadStatusText, '');
                }, delay);
            } catch (err) {
                console.error('[LexPlay] Bulk download failed:', err);
                safeSetState(setBulkDownloadStatusText, 'Download failed. Try again.');
                safeSetState(setIsBulkDownloading, false);
            }
        })();
    }, [isBulkDownloading, displayPlaylist, refreshCacheForDisplayPlaylist, safeSetState]);

    const getAuthHeaders = async () => {
        const token = await getToken();
        if (!token) return { 'Content-Type': 'application/json' };
        
        return { 
            'Authorization': `Bearer ${token}`,
            'X-Clerk-Authorization': `Bearer ${token}`, // Bypass Azure header hijacking
            'Content-Type': 'application/json' 
        };
    };

    // Handle initial state load and sync
    const [isStateLoaded, setIsStateLoaded] = useState(false);

    const savePlaybackState = useCallback(async (state) => {
        if (!isSignedIn) return;
        try {
            const headers = await getAuthHeaders();
            await fetch('/api/lexplay/state', {
                method: 'POST',
                headers,
                body: JSON.stringify(state)
            });
        } catch (e) { console.error("Failed to save playback state:", e); }
    }, [isSignedIn, getToken]);

    const loadPlaybackState = useCallback(async () => {
        if (!isLoaded || !isSignedIn || isStateLoaded) return;
        try {
            const headers = await getAuthHeaders();
            const res = await fetch('/api/lexplay/state', { headers });
            if (res.ok) {
                const state = await res.json();
                console.log("Loaded playback state:", state);
                
                if (state.playlist_id) {
                    // 1. Load the playlist
                    const itemsRes = await fetch(`/api/playlists/${state.playlist_id}/items`, { headers });
                    if (itemsRes.ok) {
                        const tracks = await itemsRes.json();
                        setBrowsePlaylistItems(null);
                        setPlaylist(tracks);
                        setActivePlaylistId(state.playlist_id);
                        
                        // 2. Find and set current track
                        if (state.current_track_id && tracks.length > 0) {
                            const foundIndex = tracks.findIndex(t => String(t.id) === String(state.current_track_id));
                            if (foundIndex !== -1) {
                                setCurrentIndex(foundIndex);
                                // 3. Seek to time (if possible)
                                if (audioRef.current && state.current_time > 0) {
                                    audioRef.current.__targetTime = state.current_time;
                                }
                            }
                        }
                    }
                } else if (state.current_track_id) {
                    // Anonymous track persistence (limited)
                    // If we have a track but no playlist, we can't easily restore context yet
                    // so we just mark as loaded.
                }
                setIsStateLoaded(true);
            } else {
                // If 404 or other error, still mark as loaded to allow new saves
                setIsStateLoaded(true);
            }
        } catch (e) { console.error("Failed to load playback state:", e); }
    }, [isLoaded, isSignedIn, isStateLoaded, getToken]);

    // 1. Immediate save on track/playlist change
    useEffect(() => {
        if (!isStateLoaded || !isSignedIn || !currentTrack) return;
        
        savePlaybackState({
            playlist_id: activePlaylistId,
            current_track_id: currentTrack.id,
            current_time: audioRef.current?.currentTime || 0,
            playback_rate: PLAYBACK_RATE
        });
    }, [activePlaylistId, currentTrack?.id, isStateLoaded, isSignedIn]);

    // 2. Save position on seek (progress bar / skip ±10s) — avoids polling the API every N seconds
    useEffect(() => {
        if (!isStateLoaded || !isSignedIn || !currentTrack) return;
        const a = audioRef.current;
        if (!a) return;
        const onSeeked = () => {
            savePlaybackState({
                playlist_id: activePlaylistId,
                current_track_id: currentTrack.id,
                current_time: a.currentTime,
                playback_rate: PLAYBACK_RATE,
            });
        };
        a.addEventListener('seeked', onSeeked);
        return () => a.removeEventListener('seeked', onSeeked);
    }, [isStateLoaded, isSignedIn, currentTrack, activePlaylistId, savePlaybackState]);

    // 3. Flush last known position when user switches tab / minimizes (mobile)
    useEffect(() => {
        if (!isStateLoaded || !isSignedIn || !currentTrack) return;
        const onVis = () => {
            if (document.visibilityState !== 'hidden' || !audioRef.current) return;
            savePlaybackState({
                playlist_id: activePlaylistId,
                current_track_id: currentTrack.id,
                current_time: audioRef.current.currentTime,
                playback_rate: PLAYBACK_RATE,
            });
        };
        document.addEventListener('visibilitychange', onVis);
        return () => document.removeEventListener('visibilitychange', onVis);
    }, [isStateLoaded, isSignedIn, currentTrack, activePlaylistId, savePlaybackState]);

    // Initialize Audio Element
    useEffect(() => {
        if (!audioRef.current) {
            audioRef.current = new Audio();
            // Critical for iOS background / lock-screen playback
            audioRef.current.setAttribute('playsinline', 'true');
            audioRef.current.setAttribute('webkit-playsinline', 'true');
            audioRef.current.preload = 'auto';
            // Ref indirection so onended always runs latest handler (avoids stale closure from mount-only effect).
            audioRef.current.onended = () => handleTrackEndRef.current();
            audioRef.current.onerror = (e) => {
                // Ignore "empty src" errors which happen during cleanup or initialization
                if (!audioRef.current || !audioRef.current.src || audioRef.current.src === window.location.href) {
                     return;
                }
                console.error("Audio playback error:", e);
                setError('Audio failed to play. The file may be unavailable.');
                setIsPlaying(false);
                setIsLoading(false);
            };
            audioRef.current.onplaying = () => {
                setIsLoading(false);
                setIsPlaying(true);
                setError(null);
                
                // Ensure volume is applied on load
                audioRef.current.volume = volume;

                // Handle initial seek from loaded state
                if (audioRef.current.__targetTime) {
                    audioRef.current.currentTime = audioRef.current.__targetTime;
                    delete audioRef.current.__targetTime;
                }
            };
            audioRef.current.onpause = () => {
                const el = audioRef.current;
                if (!el || el.ended) return;
                setIsPlaying(false);
            };
            audioRef.current.onwaiting = () => setIsLoading(true);
        }

        return () => {
            if (audioRef.current) {
                audioRef.current.pause();
                audioRef.current.removeAttribute('src'); // Do not use src = '' as it throws an error
            }
        };
    }, []);

    // Sync volume when state changes
    useEffect(() => {
        if (audioRef.current) {
            audioRef.current.volume = volume;
        }
    }, [volume]);

    // --- Saved Playlists API Logic ---

    const fetchPlaylists = useCallback(async () => {
        if (!isLoaded || !isSignedIn) {
            setSavedPlaylists([]);
            setPlaylistFetchError(null);
            return;
        }
        try {
            // Single getToken via getAuthHeaders. Do not bail if getToken() is briefly null while
            // isSignedIn is true — Clerk can resolve the token on the next effect run; retry still runs.
            const headers = await getAuthHeaders();
            const res = await fetch('/api/playlists', { headers });
            if (res.ok) {
                const data = await res.json();
                setSavedPlaylists(Array.isArray(data) ? data : []);
                setPlaylistFetchError(null);
                return;
            }
            let detail = '';
            try {
                const j = await res.json();
                detail = j.details || j.error || '';
            } catch {
                detail = await res.text();
            }
            console.warn('[LexPlay] GET /api/playlists failed', res.status, detail);
            setSavedPlaylists([]);
            setPlaylistFetchError(res.status === 401 ? 'unauthorized' : `http_${res.status}`);
        } catch (e) {
            console.error('Failed to fetch playlists:', e);
            setSavedPlaylists([]);
            setPlaylistFetchError('network');
        }
    }, [isLoaded, isSignedIn, getToken]);

    useEffect(() => {
        // Fetch saved playlists on mount
        fetchPlaylists();
        loadPlaybackState();
    }, [fetchPlaylists, loadPlaybackState]);

    const handleStop = useCallback(() => {
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current.currentTime = 0;
            setIsPlaying(false);
        }
    }, [audioRef]);

    const loadSavedPlaylist = useCallback(async (playlistId) => {
        try {
            const headers = await getAuthHeaders();
            const res = await fetch(`/api/playlists/${playlistId}/items`, { headers });
            if (!res.ok) return;
            const tracks = await res.json();
            setActivePlaylistId(playlistId);

            const audioActive =
                audioRef.current?.src &&
                (isPlaying || (audioRef.current && !audioRef.current.paused));

            if (audioActive) {
                setBrowsePlaylistItems(tracks);
            } else {
                handleStop();
                setBrowsePlaylistItems(null);
                setPlaylist(tracks);
                if (tracks.length > 0) setCurrentIndex(0);
                else setCurrentIndex(-1);
            }
        } catch (e) {
            console.error("Load playlist error:", e);
        }
    }, [handleStop, getToken, isPlaying]);

    const createPlaylist = useCallback(async (name) => {
        try {
            const headers = await getAuthHeaders();
            const res = await fetch('/api/playlists', {
                method: 'POST',
                headers,
                body: JSON.stringify({ name })
            });
            if (res.ok) {
                const newPlaylist = await res.json();
                // Optimistically update savedPlaylists so UI updates immediately
                setSavedPlaylists(prev => [...prev, newPlaylist]);
                fetchPlaylists(); // Background sync
                // Auto-select the newly created playlist
                setActivePlaylistId(newPlaylist.id);
                setBrowsePlaylistItems(null);
                setPlaylist([]); // New playlist starts empty
                setCurrentIndex(-1);
                return newPlaylist;
            } else {
                const err = await res.json();
                throw new Error(err.error || "Failed to create playlist");
            }
        } catch (e) {
            console.error("Create playlist error:", e);
            throw e;
        }
    }, [fetchPlaylists, getToken]);

    const renamePlaylist = useCallback(async (id, name) => {
        try {
            const headers = await getAuthHeaders();
            const res = await fetch(`/api/playlists/${id}`, {
                method: 'PUT', headers, body: JSON.stringify({ name })
            });
            if (res.ok) {
                fetchPlaylists();
            } else {
                const errorData = await res.json().catch(() => ({}));
                throw new Error(errorData.error || `Failed to rename playlist (${res.status})`);
            }
        } catch (e) {
            console.error("Rename playlist error:", e);
            throw e;
        }
    }, [fetchPlaylists, getToken]);

    const deletePlaylist = useCallback(async (id) => {
        try {
            const headers = await getAuthHeaders();
            const res = await fetch(`/api/playlists/${id}`, { method: 'DELETE', headers });
            if (res.ok) {
                if (activePlaylistId === id) {
                    setActivePlaylistId(null);
                    setBrowsePlaylistItems(null);
                    setPlaylist([]);
                    setCurrentIndex(-1);
                    handleStop();
                }
                fetchPlaylists();
            } else {
                const errorData = await res.json().catch(() => ({}));
                throw new Error(errorData.error || `Failed to delete playlist (${res.status})`);
            }
        } catch (e) {
            console.error("Delete playlist error:", e);
            throw e;
        }
    }, [activePlaylistId, fetchPlaylists, getToken]);

    const addToSpecificPlaylist = useCallback(async (playlistId, track) => {
        try {
            const headers = await getAuthHeaders();
            const res = await fetch(`/api/playlists/${playlistId}/items`, {
                method: 'POST', headers,
                body: JSON.stringify({
                    content_id: track.id,
                    content_type: track.type,
                    code_id: track.code_id,
                    title: track.title,
                    subtitle: track.subtitle
                })
            });
            if (res.ok) {
                fetchPlaylists(); // update counts
                // If it's the currently active playlist, reload it OR auto-select if none active
                if (activePlaylistId === playlistId || !activePlaylistId) {
                    loadSavedPlaylist(playlistId);
                }
            } else {
                const err = await res.json();
                throw new Error(err.error || "Failed to add item to playlist");
            }
        } catch (e) { 
            console.error("Add item error:", e);
            throw e;
        }
    }, [activePlaylistId, fetchPlaylists, loadSavedPlaylist, getToken]);

    const addBulkToSpecificPlaylist = useCallback(async (playlistId, items) => {
        try {
            const headers = await getAuthHeaders();
            const res = await fetch(`/api/playlists/${playlistId}/bulk_items`, {
                method: 'POST', headers,
                body: JSON.stringify({ items })
            });
            if (res.ok) {
                fetchPlaylists();
                // Critical: reload if active, OR if we have no active playlist (auto-select first add)
                if (activePlaylistId === playlistId || !activePlaylistId) {
                    loadSavedPlaylist(playlistId);
                }
            }
        } catch (e) { console.error("Bulk add error:", e); }
    }, [activePlaylistId, fetchPlaylists, loadSavedPlaylist, getToken]);

    const removeFromSpecificPlaylist = useCallback(async (playlistId, itemId) => {
        try {
            const headers = await getAuthHeaders();
            const res = await fetch(`/api/playlists/${playlistId}/items/${itemId}`, { method: 'DELETE', headers });
            if (res.ok) {
                fetchPlaylists();
                if (activePlaylistId === playlistId) loadSavedPlaylist(playlistId);
            }
        } catch (e) { console.error("Remove item error:", e); }
    }, [activePlaylistId, fetchPlaylists, loadSavedPlaylist, getToken]);

    // --- Active Queue Logic ---
    // Playback is always at PLAYBACK_RATE (1×). Server receives rate= in audio URL.

    const playTrack = useCallback(async (index, trackOverride = null, attempt = 1) => {
        // Use ref to avoid stale closure on playlist
        const latestPlaylist = playlistRef.current;
        const track = trackOverride || latestPlaylist[index];
        if (!track) return;

        clearNextPrefetch();

        setCurrentIndex(index);
        setIsLoading(true);
        setIsPlaying(false);
        setError(null);
        retryCountRef.current = attempt;

        // Revoke previous object URL to free memory
        if (audioRef.current?.src?.startsWith('blob:')) {
            URL.revokeObjectURL(audioRef.current.src);
        }

        try {
            const fetchUrl = buildAudioFetchPath(track, PLAYBACK_RATE);
            console.log(`LEXPLAY AUDIO: Load attempt ${attempt}/${MAX_RETRIES}:`, fetchUrl);

            // --- Cache-First Retrieval ---
            if (audioRef.current) {
                audioRef.current.pause();
                audioRef.current.removeAttribute('src');
                audioRef.current.load(); // Reset previous errors

                let finalSource = fetchUrl;
                try {
                    if ('caches' in window) {
                        const cache = await caches.open('audio-cache');
                        const matchedResponse = await cache.match(fetchUrl);
                        if (matchedResponse) {
                            console.log("LEXPLAY CACHE: 🚀 Instant Play (Cache Hit)");
                            const blob = await matchedResponse.blob();
                            finalSource = URL.createObjectURL(blob);
                        }
                    }
                } catch (cacheErr) {
                    console.warn("Cache retrieval failed, falling back to network:", cacheErr);
                }

                if (!isMounted.current) return;
                audioRef.current.src = finalSource;

                // Restoring the playback engine
                try {
                    const playPromise = audioRef.current.play();
                    if (playPromise !== undefined) {
                        await playPromise;
                        safeSetState(setIsPlaying, true);
                        safeSetState(setIsLoading, false);
                    }
                } catch (playErr) {
                    if (playErr.name !== 'AbortError') {
                        console.error("Playback failed:", playErr);
                        safeSetState(setError, "Playback failed. Check your browser permissions.");
                        safeSetState(setIsPlaying, false);
                        safeSetState(setIsLoading, false);
                    }
                }
            }
        } catch (error) {
            // Browsers throw AbortError or NotAllowedError if play() is rapidly interrupted.
            if (error.name === 'AbortError' || error.name === 'NotAllowedError' || error.message?.includes('interrupted')) {
                console.warn(`LexPlay playback interrupted (attempt ${attempt}):`, error.message);
                setIsLoading(false);
                return;
            }

            console.error(`Error playing track (attempt ${attempt}/${MAX_RETRIES}):`, error);

            // Auto-retry with exponential backoff
            if (attempt < MAX_RETRIES) {
                const delay = Math.pow(2, attempt) * 800; // 1.6s, 3.2s
                console.log(`Retrying in ${delay}ms...`);
                setError(`Audio load failed. Retrying... (${attempt}/${MAX_RETRIES})`);
                await new Promise(r => setTimeout(r, delay));
                return playTrack(index, trackOverride, attempt + 1);
            }

            setError(`Failed to load audio after ${MAX_RETRIES} attempts. Tap retry to try again.`);
            setIsPlaying(false);
            setIsLoading(false);
        }
    }, [safeSetState, clearNextPrefetch]);

    /**
     * Auto-advance / lock-screen path: set src and call play() without await before play().
     * iOS Safari often blocks the next track if playTrack() awaits cache I/O first — the "ended"
     * activation context is lost. Falls back to async playTrack on failure.
     */
    const playTrackImmediate = useCallback(
        (index, trackOverride = null) => {
            const list = playlistRef.current;
            const track = trackOverride || list[index];
            if (!track || !audioRef.current) return;

            if (audioRef.current.src?.startsWith('blob:')) {
                try {
                    URL.revokeObjectURL(audioRef.current.src);
                } catch {
                    /* ignore */
                }
            }

            setCurrentIndex(index);
            setIsLoading(true);
            setIsPlaying(false);
            setError(null);

            const fetchPath = buildAudioFetchPath(track, PLAYBACK_RATE);
            const absoluteUrl = new URL(fetchPath, window.location.origin).href;

            let src = absoluteUrl;
            const pref = prefetchedNextRef.current;
            if (pref && pref.index === index && pref.objectUrl) {
                src = pref.objectUrl;
                prefetchedNextRef.current = null;
            } else if (pref?.objectUrl) {
                clearNextPrefetch();
            }

            const a = audioRef.current;
            a.volume = volume;
            a.src = src;
            a.load();

            try {
                const playP = a.play();
                if (playP !== undefined) {
                    playP
                        .then(() => {
                            safeSetState(setIsLoading, false);
                            safeSetState(setIsPlaying, true);
                        })
                        .catch((err) => {
                            console.warn('[LexPlay] playTrackImmediate failed, using async load', err?.name);
                            clearNextPrefetch();
                            playTrack(index, trackOverride, 1);
                        });
                }
            } catch (e) {
                console.warn('[LexPlay] playTrackImmediate threw', e);
                clearNextPrefetch();
                playTrack(index, trackOverride, 1);
            }
        },
        [volume, safeSetState, playTrack, clearNextPrefetch]
    );

    const handlePlayPause = useCallback(() => {
        if (!audioRef.current) return;
        const a = audioRef.current;

        // Use element state, not React isPlaying — OS / lock-screen media controls can pause
        // without matching React state, so a second tap would wrongly take the "pause" branch.
        if (!a.paused) {
            a.pause();
            setIsPlaying(false);
            if (isStateLoaded && isSignedIn && currentTrack) {
                void savePlaybackState({
                    playlist_id: activePlaylistId,
                    current_track_id: currentTrack.id,
                    current_time: a.currentTime,
                    playback_rate: PLAYBACK_RATE,
                });
            }
        } else if (currentTrack) {
            const matches = audioSrcMatchesCurrentTrack(a.src, currentTrack, PLAYBACK_RATE);
            if (!matches) {
                playTrack(currentIndex);
                return;
            }
            setIsLoading(true);
            const playP = a.play();
            if (playP !== undefined) {
                playP
                    .then(() => {
                        setIsLoading(false);
                        setIsPlaying(true);
                    })
                    .catch((e) => {
                        setIsLoading(false);
                        setIsPlaying(false);
                        if (e.name === 'AbortError' || e.name === 'NotAllowedError' || e.message?.includes('interrupted')) {
                            return;
                        }
                        console.error('Error resuming playback:', e);
                        setError(e.message || 'Could not resume playback.');
                    });
            } else {
                setIsPlaying(true);
            }
        } else if (playlist.length > 0) {
            playTrack(0);
        }
    }, [
        currentTrack,
        playlist.length,
        playTrack,
        currentIndex,
        isStateLoaded,
        isSignedIn,
        activePlaylistId,
        savePlaybackState,
    ]);

    const playTrackFromList = useCallback(
        (index) => {
            if (browsePlaylistItems !== null) {
                const track = browsePlaylistItems[index];
                if (!track) return;
                setPlaylist(browsePlaylistItems);
                setBrowsePlaylistItems(null);
                playTrack(index, track);
            } else {
                playTrack(index);
            }
        },
        [browsePlaylistItems, playTrack]
    );

    const activatePlaylistRow = useCallback(
        (index) => {
            if (browsePlaylistItems !== null) {
                if (index === listUiCurrentIndex && listUiCurrentIndex >= 0) {
                    handlePlayPause();
                } else {
                    playTrackFromList(index);
                }
            } else if (index === currentIndex) {
                handlePlayPause();
            } else {
                playTrack(index);
            }
        },
        [browsePlaylistItems, listUiCurrentIndex, currentIndex, handlePlayPause, playTrackFromList, playTrack]
    );

    const handleNext = useCallback(() => {
        if (isShuffleRef.current && playlist.length > 1) {
            let nextIdx;
            do {
                nextIdx = Math.floor(Math.random() * playlist.length);
            } while (nextIdx === currentIndex && playlist.length > 1);
            playTrackImmediate(nextIdx);
        } else if (currentIndex < playlist.length - 1) {
            playTrackImmediate(currentIndex + 1);
        } else if (repeatModeRef.current === 'all') {
            playTrackImmediate(0);
        }
    }, [currentIndex, playlist.length, playTrackImmediate]);

    const handlePrevious = useCallback(() => {
        if (audioRef.current && audioRef.current.currentTime > 3) {
            // If more than 3s in, restart current track
            audioRef.current.currentTime = 0;
            if (audioRef.current.paused) handlePlayPause();
            return;
        }

        if (isShuffleRef.current && playlist.length > 1) {
            let nextIdx;
            do {
                nextIdx = Math.floor(Math.random() * playlist.length);
            } while (nextIdx === currentIndex && playlist.length > 1);
            playTrackImmediate(nextIdx);
        } else if (currentIndex > 0) {
            playTrackImmediate(currentIndex - 1);
        } else if (audioRef.current) {
            audioRef.current.currentTime = 0;
            if (audioRef.current.paused) handlePlayPause();
        }
    }, [currentIndex, handlePlayPause, playTrackImmediate, playlist.length]);

    const handleTrackEnd = useCallback(() => {
        const idx = currentIndexRef.current;
        const list = playlistRef.current;

        if (repeatModeRef.current === 'one') {
            playTrackImmediate(idx);
            return;
        }

        if (isShuffleRef.current && list.length > 1) {
            let nextIdx;
            do {
                nextIdx = Math.floor(Math.random() * list.length);
            } while (nextIdx === idx && list.length > 1);
            playTrackImmediate(nextIdx);
            return;
        }

        if (idx < list.length - 1) {
            playTrackImmediate(idx + 1);
        } else if (repeatModeRef.current === 'all') {
            playTrackImmediate(0);
        } else {
            setIsPlaying(false);
            if (list.length > 0) setCurrentIndex(0);
            else setCurrentIndex(-1);
        }
    }, [playTrackImmediate]);

    useEffect(() => {
        handleTrackEndRef.current = handleTrackEnd;
    }, [handleTrackEnd]);

    useEffect(() => () => clearNextPrefetch(), [clearNextPrefetch]);

    // Warm next track into a blob URL while the current one plays so auto-advance can call play() synchronously (iOS lock screen).
    useEffect(() => {
        if (!isPlaying || currentIndex < 0) return;
        const list = playlistRef.current;
        const nextIdx = currentIndex + 1;
        if (nextIdx >= list.length) {
            clearNextPrefetch();
            return;
        }

        let cancelled = false;
        const track = list[nextIdx];
        const fetchPath = buildAudioFetchPath(track, PLAYBACK_RATE);

        (async () => {
            try {
                let blob = null;
                if ('caches' in window) {
                    const cache = await caches.open('audio-cache');
                    const matched = await cache.match(fetchPath);
                    if (matched) blob = await matched.blob();
                }
                if (!blob) {
                    const res = await fetch(fetchPath, { credentials: 'include' });
                    if (res.ok) blob = await res.blob();
                }
                if (cancelled || !blob) return;
                const old = prefetchedNextRef.current;
                if (old?.objectUrl) {
                    try {
                        URL.revokeObjectURL(old.objectUrl);
                    } catch {
                        /* ignore */
                    }
                }
                prefetchedNextRef.current = { index: nextIdx, objectUrl: URL.createObjectURL(blob) };
            } catch (e) {
                console.warn('[LexPlay] prefetch next track failed', e);
            }
        })();

        return () => {
            cancelled = true;
        };
    }, [isPlaying, currentIndex, playlist, clearNextPrefetch]);

    const handleScrubForward = useCallback(() => {
        if (audioRef.current) {
            audioRef.current.currentTime = Math.min(audioRef.current.currentTime + 10, audioRef.current.duration || 0);
        }
    }, []);

    const handleScrubBackward = useCallback(() => {
        if (audioRef.current) {
            audioRef.current.currentTime = Math.max(audioRef.current.currentTime - 10, 0);
        }
    }, []);

    const toggleShuffle = useCallback(() => {
        const next = !isShuffleRef.current;
        isShuffleRef.current = next;
        setIsShuffle(next);
    }, []);

    const cycleRepeatMode = useCallback(() => {
        const map = { 'none': 'all', 'all': 'one', 'one': 'none' };
        const next = map[repeatModeRef.current];
        repeatModeRef.current = next;
        setRepeatMode(next);
    }, []);

    // Sync Handlers to Refs
    useEffect(() => {
        playPauseRef.current = handlePlayPause;
        nextTrackRef.current = handleNext;
        prevTrackRef.current = handlePrevious;
        seekForwardRef.current = handleScrubForward;
        seekBackwardRef.current = handleScrubBackward;
    }, [handlePlayPause, handleNext, handlePrevious, handleScrubForward, handleScrubBackward]);

    // Universal MediaSession Manager
    useEffect(() => {
        if (!('mediaSession' in navigator)) return;

        if (currentTrack) {
            navigator.mediaSession.metadata = new MediaMetadata({
                title: currentTrack.title,
                artist: 'LexMatePH - Bar Reviewer',
                album: currentTrack.type === 'codal' ? 'Codal Provisions' : 'Case Digests'
            });

            // Register handlers ONCE (using stable refs)
            // This prevents the "session drop" on iOS and "controls flicker" on Android
            navigator.mediaSession.setActionHandler('play', () => playPauseRef.current?.());
            navigator.mediaSession.setActionHandler('pause', () => playPauseRef.current?.());
            navigator.mediaSession.setActionHandler('previoustrack', () => prevTrackRef.current?.());
            navigator.mediaSession.setActionHandler('nexttrack', () => nextTrackRef.current?.());
            navigator.mediaSession.setActionHandler('seekbackward', (details) => {
                const offset = details.seekOffset || 10;
                seekBackwardRef.current?.(offset);
            });
            navigator.mediaSession.setActionHandler('seekforward', (details) => {
                const offset = details.seekOffset || 10;
                seekForwardRef.current?.(offset);
            });
        }

        // Sync playback state for iOS lock screen and Android notifications
        navigator.mediaSession.playbackState = isPlaying ? 'playing' : 'paused';

        // Update position state for high-fidelity progress bars (Android/Tablets)
        const updatePosition = () => {
            if (audioRef.current && !isNaN(audioRef.current.duration) && audioRef.current.duration > 0) {
                try {
                    navigator.mediaSession.setPositionState({
                        duration: audioRef.current.duration,
                        playbackRate: 1.0,
                        position: audioRef.current.currentTime
                    });
                } catch (e) { /* Some browsers throw if duration/position mismatch slightly */ }
            }
        };

        if (isPlaying) {
            const posInterval = setInterval(updatePosition, 2000);
            updatePosition();
            return () => clearInterval(posInterval);
        }
    }, [currentTrack, isPlaying]);

    const addToPlaylist = useCallback((item) => {
        setActivePlaylistId(null);
        setBrowsePlaylistItems(null);
        setPlaylist((prev) => {
            // Avoid immediate duplicates
            if (prev.length > 0 && prev[prev.length - 1].id === item.id) {
                return prev;
            }
            const newList = [...prev, item];
            // If it's the first item added, prepare it but don't auto-play yet
            if (currentIndex === -1) {
                setCurrentIndex(0);
            }
            return newList;
        });
    }, [currentIndex]);

    const retryCurrentTrack = useCallback(() => {
        const idx = currentIndexRef.current;
        const list = playlistRef.current;
        if (idx >= 0 && list[idx]) {
            playTrack(idx, null, 1);
        }
    }, [playTrack]);

    const playNow = useCallback((item) => {
        setActivePlaylistId(null);
        setBrowsePlaylistItems(null);
        // Clear queue and add this item
        setPlaylist([item]);
        setCurrentIndex(0);
        setIsDrawerOpen(true);
        // Trigger the internal playback logic with immediate track object to bypass async state race
        playTrack(0, item);
    }, [playTrack]);

    const removeFromPlaylist = useCallback((indexToRemove) => {
        setPlaylist((prev) => {
            const newList = [...prev];
            newList.splice(indexToRemove, 1);
            return newList;
        });

        if (indexToRemove === currentIndex) {
            // If removing current track, play next (or stop if it was the last)
            if (currentIndex >= playlist.length - 1) {
                handleStop();
                setCurrentIndex(-1);
            } else {
                playTrack(currentIndex); // Will play the new item at this index
            }
        } else if (indexToRemove < currentIndex) {
            // Adjust current index if we removed something before it
            setCurrentIndex(prev => prev - 1);
        }
    }, [currentIndex, playlist.length, handleStop, playTrack]);

    const value = useMemo(() => ({
        playlist,
        displayPlaylist,
        listUiCurrentIndex,
        browsePlaylistItems,
        activatePlaylistRow,
        playTrackFromList,
        currentTrack,
        currentIndex,
        isPlaying,
        isLoading,
        error,
        playbackRate: PLAYBACK_RATE,
        volume,
        setVolume,
        repeatMode,
        cycleRepeatMode,
        isShuffle,
        toggleShuffle,
        handleScrubForward,
        handleScrubBackward,
        isDrawerOpen,
        setIsDrawerOpen,
        addToPlaylist,
        playNow,
        removeFromPlaylist,
        playTrack,
        handlePlayPause,
        handleNext,
        handlePrevious,
        handleStop,
        audioRef,
        retryCurrentTrack,

        // Offline cache (runs in provider — survives playlist browse / LexPlayer unmount)
        cachedCount,
        cachedTrackIds,
        downloadingTrackIds,
        isBulkDownloading,
        bulkDownloadProgress,
        bulkDownloadStatusText,
        handleBulkCacheDownloadClick,
        refreshCacheForDisplayPlaylist,
        startTrackCacheDownload,
        stopTrackCacheDownload,
        
        // Playlist API Context
        savedPlaylists,
        playlistFetchError,
        activePlaylistId,
        fetchPlaylists,
        createPlaylist,
        renamePlaylist,
        deletePlaylist,
        addToSpecificPlaylist,
        addBulkToSpecificPlaylist,
        removeFromSpecificPlaylist,
        loadSavedPlaylist
    }), [
        playlist,
        displayPlaylist,
        listUiCurrentIndex,
        browsePlaylistItems,
        activatePlaylistRow,
        playTrackFromList,
        currentTrack,
        currentIndex,
        isPlaying,
        isLoading,
        error,
        volume,
        repeatMode,
        isShuffle,
        cycleRepeatMode,
        toggleShuffle,
        handleScrubForward,
        handleScrubBackward,
        isDrawerOpen,
        savedPlaylists,
        playlistFetchError,
        activePlaylistId,
        addToPlaylist,
        playNow,
        removeFromPlaylist,
        playTrack,
        handlePlayPause,
        handleNext,
        handlePrevious,
        handleStop,
        retryCurrentTrack,
        cachedCount,
        cachedTrackIds,
        downloadingTrackIds,
        isBulkDownloading,
        bulkDownloadProgress,
        bulkDownloadStatusText,
        handleBulkCacheDownloadClick,
        refreshCacheForDisplayPlaylist,
        startTrackCacheDownload,
        stopTrackCacheDownload,
        fetchPlaylists,
        createPlaylist,
        renamePlaylist,
        deletePlaylist,
        addToSpecificPlaylist,
        addBulkToSpecificPlaylist,
        removeFromSpecificPlaylist,
        loadSavedPlaylist
    ]);

    const apiValue = useMemo(() => ({
        playNow,
        addToPlaylist,
        removeFromPlaylist,
        handlePlayPause,
        handleNext,
        handlePrevious,
        handleStop,
        retryCurrentTrack,
        fetchPlaylists,
        createPlaylist,
        renamePlaylist,
        deletePlaylist,
        addToSpecificPlaylist,
        addBulkToSpecificPlaylist,
        removeFromSpecificPlaylist,
        loadSavedPlaylist,
        setIsDrawerOpen
    }), [
        playNow,
        addToPlaylist,
        removeFromPlaylist,
        handlePlayPause,
        handleNext,
        handlePrevious,
        handleStop,
        retryCurrentTrack,
        fetchPlaylists,
        createPlaylist,
        renamePlaylist,
        deletePlaylist,
        addToSpecificPlaylist,
        addBulkToSpecificPlaylist,
        removeFromSpecificPlaylist,
        loadSavedPlaylist,
        setIsDrawerOpen
    ]);

    return (
        <LexPlayApiContext.Provider value={apiValue}>
            <LexPlayContext.Provider value={value}>
                {children}
            </LexPlayContext.Provider>
        </LexPlayApiContext.Provider>
    );
};
