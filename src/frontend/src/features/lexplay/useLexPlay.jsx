import React, { createContext, useContext, useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from '@clerk/clerk-react';

const LexPlayContext = createContext();
const LexPlayApiContext = createContext();

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
    const [activePlaylistId, setActivePlaylistId] = useState(null);
    const [currentIndex, setCurrentIndex] = useState(-1);
    const [isPlaying, setIsPlaying] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [playbackRate, setPlaybackRate] = useState(1.0);
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
    
    // MediaSession Stable Handler Refs
    const playPauseRef = useRef(null);
    const nextTrackRef = useRef(null);
    const prevTrackRef = useRef(null);
    const seekForwardRef = useRef(null);
    const seekBackwardRef = useRef(null);
    
    const MAX_RETRIES = 3;

    // Keep refs in sync with state
    useEffect(() => { playlistRef.current = playlist; }, [playlist]);
    useEffect(() => { currentIndexRef.current = currentIndex; }, [currentIndex]);

    const currentTrack = currentIndex >= 0 && currentIndex < playlist.length ? playlist[currentIndex] : null;

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
                        setPlaylist(tracks);
                        setActivePlaylistId(state.playlist_id);
                        
                        // 2. Find and set current track
                        if (state.current_track_id && tracks.length > 0) {
                            const foundIndex = tracks.findIndex(t => String(t.id) === String(state.current_track_id));
                            if (foundIndex !== -1) {
                                setCurrentIndex(foundIndex);
                                setPlaybackRate(state.playback_rate || 1.0);
                                
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
            playback_rate: playbackRate
        });
    }, [activePlaylistId, currentTrack?.id, playbackRate, isStateLoaded, isSignedIn]);

    // 2. Debounced save for time updates
    useEffect(() => {
        if (!isStateLoaded || !isSignedIn || !currentTrack || !isPlaying) return;
        
        const interval = setInterval(() => {
            if (audioRef.current && !audioRef.current.paused) {
                savePlaybackState({
                    playlist_id: activePlaylistId,
                    current_track_id: currentTrack.id,
                    current_time: audioRef.current.currentTime,
                    playback_rate: playbackRate
                });
            }
        }, 10000); // Sync time every 10 seconds while playing

        return () => clearInterval(interval);
    }, [activePlaylistId, currentTrack?.id, playbackRate, isStateLoaded, isSignedIn, isPlaying]);


    // Initialize Audio Element
    useEffect(() => {
        if (!audioRef.current) {
            audioRef.current = new Audio();
            // Critical for iOS background playback
            audioRef.current.setAttribute('playsinline', 'true');
            audioRef.current.preload = 'auto';
            
            audioRef.current.onended = handleTrackEnd;
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
            return;
        }
        try {
            const headers = await getAuthHeaders();
            const res = await fetch('/api/playlists', { headers });
            if (res.ok) {
                const data = await res.json();
                setSavedPlaylists(data);
            }
        } catch (e) { console.error("Failed to fetch playlists:", e); }
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
        handleStop();
        try {
            const headers = await getAuthHeaders();
            const res = await fetch(`/api/playlists/${playlistId}/items`, { headers });
            if (res.ok) {
                const tracks = await res.json();
                setActivePlaylistId(playlistId);
                setPlaylist(tracks);
                if (tracks.length > 0) setCurrentIndex(0);
                else setCurrentIndex(-1);
            }
        } catch (e) { console.error("Load playlist error:", e); }
    }, [handleStop, getToken]);

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
    // Handle Playback Rate changes
    // When playbackRate changes, reload the current track so the backend generates
    // audio at the new speed natively via Azure TTS SSML prosody.
    // We do NOT set audioRef.current.playbackRate because that causes robotic artifacts.
    const playbackRateRef = useRef(playbackRate);
    useEffect(() => {
        playbackRateRef.current = playbackRate;
    }, [playbackRate]);


    const playTrack = useCallback(async (index, trackOverride = null, attempt = 1) => {
        // Use ref to avoid stale closure on playlist
        const latestPlaylist = playlistRef.current;
        const track = trackOverride || latestPlaylist[index];
        if (!track) return;

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
            // Pass rate to backend so Azure TTS synthesizes at the correct speed natively.
            const currentRate = playbackRateRef.current || playbackRate;
            const rateParam = `rate=${currentRate}`;
            const codeParam = track.code_id ? `code=${track.code_id}&` : '';
            // REMOVED: timestampParam = `&t=${new Date().getTime()}`; // CACHE BUSTER REMOVED
            const fetchUrl = `/api/audio/${track.type}/${track.id}?${codeParam}${rateParam}`;
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

                audioRef.current.src = finalSource;
                audioRef.current.playbackRate = 1.0; // Always native speed — rate is baked into the audio by Azure

                // Listen for load errors before play() resolves
                const loadErrorPromise = new Promise((_, reject) => {
                    const onError = (e) => {
                        audioRef.current?.removeEventListener('error', onError);
                        const code = audioRef.current?.error?.code;
                        const msgs = {
                            1: 'Playback aborted.',
                            2: 'Network error while loading audio.',
                            3: 'Audio decoding failed.',
                            4: 'Audio format not supported or source unavailable.',
                        };
                        reject(new Error(msgs[code] || 'Audio failed to load.'));
                    };
                    audioRef.current?.addEventListener('error', onError, { once: true });
                });

                await Promise.race([
                    audioRef.current.play(),
                    loadErrorPromise
                ]);
                setIsPlaying(true);
                // MediaSession is now handled by a dedicated useEffect
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
    }, [playbackRate]);

    const handlePlayPause = useCallback(() => {
        if (!audioRef.current) return;

        if (isPlaying) {
            audioRef.current.pause();
            setIsPlaying(false);
        } else {
            if (currentTrack) {
                // Check if the current src matches what we expect for this track
                const expectedPath = `/api/audio/${currentTrack.type}/${currentTrack.id}${currentTrack.code_id ? `?code=${currentTrack.code_id}` : ''}`;
                const currentSrc = audioRef.current.src;
                const isCorrectSrc = currentSrc && (currentSrc.endsWith(expectedPath) || currentSrc === expectedPath);

                if (!isCorrectSrc) {
                    // Need to load it first if completely stopped or source mismatch
                    playTrack(currentIndex);
                } else {
                    audioRef.current.play().catch(e => {
                        if (e.name !== 'AbortError' && e.name !== 'NotAllowedError' && !e.message?.includes('interrupted')) {
                            console.error("Error resuming playback:", e);
                            setError(e.message);
                        }
                    });
                    setIsPlaying(true);
                }
            } else if (playlist.length > 0) {
                playTrack(0);
            }
        }
    }, [isPlaying, currentTrack, playlist.length, playTrack, currentIndex]);

    const handleNext = useCallback(() => {
        if (isShuffleRef.current && playlist.length > 1) {
            let nextIdx;
            do { nextIdx = Math.floor(Math.random() * playlist.length); } 
            while (nextIdx === currentIndex && playlist.length > 1);
            playTrack(nextIdx);
        } else if (currentIndex < playlist.length - 1) {
            playTrack(currentIndex + 1);
        } else if (repeatModeRef.current === 'all') {
            playTrack(0);
        }
    }, [currentIndex, playlist.length, playTrack]);

    const handlePrevious = useCallback(() => {
        if (audioRef.current && audioRef.current.currentTime > 3) {
            // If more than 3s in, restart current track
            audioRef.current.currentTime = 0;
            if (!isPlaying) handlePlayPause();
            return;
        }

        if (isShuffleRef.current && playlist.length > 1) {
            let nextIdx;
            do { nextIdx = Math.floor(Math.random() * playlist.length); } 
            while (nextIdx === currentIndex && playlist.length > 1);
            playTrack(nextIdx);
        } else if (currentIndex > 0) {
            playTrack(currentIndex - 1);
        } else if (audioRef.current) {
            audioRef.current.currentTime = 0;
            if (!isPlaying) handlePlayPause();
        }
    }, [currentIndex, isPlaying, handlePlayPause, playTrack, playlist.length]);

    const handleTrackEnd = useCallback(() => {
        const idx = currentIndexRef.current;
        const list = playlistRef.current;
        
        if (repeatModeRef.current === 'one') {
            playTrack(idx);
            return;
        }
        
        if (isShuffleRef.current && list.length > 1) {
            let nextIdx;
            do { nextIdx = Math.floor(Math.random() * list.length); } 
            while (nextIdx === idx && list.length > 1);
            playTrack(nextIdx);
            return;
        }

        if (idx < list.length - 1) {
            playTrack(idx + 1);
        } else {
            if (repeatModeRef.current === 'all') {
                playTrack(0);
            } else {
                setIsPlaying(false);
                if (list.length > 0) setCurrentIndex(0);
                else setCurrentIndex(-1);
            }
        }
    }, [playTrack]);

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
        setPlaybackRate,
        audioRef,
        retryCurrentTrack,
        
        // Playlist API Context
        savedPlaylists,
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
        currentTrack,
        currentIndex,
        isPlaying,
        isLoading,
        error,
        playbackRate,
        volume,
        repeatMode,
        isShuffle,
        cycleRepeatMode,
        toggleShuffle,
        handleScrubForward,
        handleScrubBackward,
        isDrawerOpen,
        savedPlaylists,
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
        setPlaybackRate,
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
        setPlaybackRate,
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
