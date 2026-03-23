# LexPlay — Audio Playback Feature

**LexPlay** is an in-app audio player that generates and plays spoken audio of Philippine legal texts (codal provisions and case digests). It is modeled after a professional music player with a full-screen mode, a persistent minimized bar, and a personalized queue called "My LexPlaylist."

---

## Table of Contents

1. [Feature Overview](#1-feature-overview)
2. [Architecture](#2-architecture)
3. [File Map](#3-file-map)
4. [Backend — AudioProvider API](#4-backend--audioprovider-api)
5. [Frontend — Components & Hooks](#5-frontend--components--hooks)
6. [Adding Items to the Playlist](#6-adding-items-to-the-playlist)
7. [Local Development Setup](#7-local-development-setup)
8. [Known Issues & Future Work](#8-known-issues--future-work)
9. [Environment Variables](#9-environment-variables)

---

## 1. Feature Overview

| Capability | Status |
|---|---|
| Add Codal Provisions to playlist | ✅ Implemented |
| Add Case Digests to playlist | ✅ Implemented |
| Full-screen LexPlayer UI | ✅ Implemented |
| Minimized persistent bottom bar | ✅ Implemented |
| Playback speed control (1x/1.25x/1.5x/2x) | ✅ Implemented |
| Progress bar scrubbing | ✅ Implemented |
| OS Media Session integration (system keys) | ✅ Implemented |
| Azure TTS (en-PH-RosaNeural voice) | ✅ Implemented (needs key) |
| gTTS fallback (Google TTS, free) | ✅ Implemented |
| Azure Blob Storage audio caching | ✅ Implemented (needs Azurite) |
| Audio plays successfully end-to-end | ⚠️ Partially working — see Known Issues |

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND                                                   │
│                                                             │
│  LexPlayer.jsx          ← Full-screen or minimized UI       │
│  useLexPlay.jsx (hook)  ← Global audio state & API calls   │
│  ArticleNode.jsx        ← 🎧 button per Codal article       │
│  CaseDecisionModal.jsx  ← 🎧 button per Case Digest         │
│  LexPlayProvider       ← Context wrapping entire App       │
└──────────────────────────┬──────────────────────────────────┘
                           │  GET /api/audio/{type}/{id}
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  BACKEND  (Azure Functions — audio_provider.py)             │
│                                                             │
│  1. Check Azurite Blob Cache ──── HIT → return SAS URL JSON │
│                    │                                        │
│                  MISS                                       │
│                    ▼                                        │
│  2. Fetch text from PostgreSQL                              │
│     ├── codal: codex_data table (article_num, content_md)  │
│     └── case:  sc_decided_cases (spoken_script or digest)  │
│                    │                                        │
│                    ▼                                        │
│  3. Generate audio                                          │
│     ├── Try Azure TTS (en-PH-RosaNeural) — needs SPEECH_KEY│
│     └── Fallback: gTTS (Google, free, needs internet)      │
│                    │                                        │
│                    ▼                                        │
│  4. Cache to Azurite (best-effort, silent on failure)      │
│                    │                                        │
│                    ▼                                        │
│  5. Stream audio bytes directly (audio/mpeg)               │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
                  PostgreSQL (local or Azure)
                  Azurite (local Blob emulator)
```

---

## 3. File Map

### Backend
| File | Purpose |
|---|---|
| `api/blueprints/audio_provider.py` | Main Azure Function. Handles text fetch, TTS, caching, streaming. |

### Frontend
| File | Purpose |
|---|---|
| `src/frontend/src/hooks/useLexPlay.jsx` | React Context + hook. Manages `playlist`, `currentIndex`, `isPlaying`, `isLoading`, `error`. Exposes `addToPlaylist`, `playTrack`, `handlePlayPause`, etc. |
| `src/frontend/src/components/LexPlayer.jsx` | Full-screen and minimized player UI. Consumes `useLexPlay`. |
| `src/frontend/src/components/ArticleNode.jsx` | Renders each Codal article. Has a `🎧` button that calls `addToPlaylist({ id, type:'codal', title, subtitle })`. |
| `src/frontend/src/components/CaseDecisionModal.jsx` | Case Digest modal. Has an "Add to LexPlay Playlist" button. Calls `addToPlaylist({ id, type:'case', title, subtitle })`. |
| `src/frontend/src/App.jsx` | Routes `mode='lexplay'` to show `<LexPlayer />` full-screen. Shows minimized `<LexPlayer isMinimized>` globally. |

---

## 4. Backend — AudioProvider API

### Endpoint
```
GET /api/audio/{content_type}/{content_id}
```

**`content_type`**: `codal` or `case`

**`content_id`**: 
- For `codal`: the `id` (primary key) column from the `codex_data` table
- For `case`: the `id` (primary key) from `sc_decided_cases`

### Response
- **Cache hit**: `200 application/json` → `{ "url": "<SAS URL>", "cached": true }`
- **Cache miss**: `200 audio/mpeg` → raw MP3 bytes streamed directly
- **Error**: `4xx/5xx application/json` → `{ "error": "..." }`

### Text Sourcing

**Case Digests:**
1. Prefers `spoken_script` field if populated (pre-authored for TTS).
2. Falls back to combining `short_title` + `digest_facts` + `digest_issues` + `digest_ruling`.

**Codal Articles:**
1. Fetches `article_num`, `article_title`, `content_md` from `codex_data`.
2. Strips markdown (`#`, `*`, `_`, `[`, `]`) before TTS.
3. Prepends "Article N. Title." prefix.

### TTS Priority
1. **Azure TTS** — uses `SPEECH_KEY` + `SPEECH_REGION`. Voice: `en-PH-RosaNeural`.
2. **gTTS fallback** — calls Google Translate's TTS API. Free, requires internet. Returns MP3. Uses `tld='com.ph'` for Filipino accent.

> ⚠️ gTTS is rate-limited by Google. For production, always use Azure TTS.

### Caching
- Audio is uploaded to an Azure Blob Storage container named `lexplay-audio-cache`.
- Blob names: `{type}_{id}.mp3` (gTTS) or `{type}_{id}.wav` (Azure TTS).
- On cache miss, audio is still served after being generated (not blocked by cache failure).
- Locally: Azurite must be running (`npx azurite` or via `start_all.ps1`).

---

## 5. Frontend — Components & Hooks

### `useLexPlay` Hook / `LexPlayProvider`

The `LexPlayProvider` must wrap the entire app (done in `App.jsx`). It creates a single shared `Audio` element via `useRef`.

**Exposed state:**
| Name | Type | Description |
|---|---|---|
| `playlist` | `Array` | Ordered list of track items |
| `currentTrack` | `Object\|null` | Currently loaded track |
| `currentIndex` | `number` | Index of current track (-1 = none) |
| `isPlaying` | `boolean` | Whether audio is currently playing |
| `isLoading` | `boolean` | Whether audio is being fetched/generated |
| `error` | `string\|null` | Last error message (cleared on next play) |
| `playbackRate` | `number` | Current speed: 1, 1.25, 1.5, 2 |
| `audioRef` | `React.Ref` | Ref to the `HTMLAudioElement` |

**Exposed functions:**
| Name | Description |
|---|---|
| `addToPlaylist(item)` | Add `{ id, type, title, subtitle }` to the queue |
| `removeFromPlaylist(index)` | Remove by index |
| `playTrack(index)` | Load and play a track by index |
| `handlePlayPause()` | Toggle play/pause |
| `handleNext()` | Skip to next track |
| `handlePrevious()` | Go to previous track (or restart current) |
| `setPlaybackRate(speed)` | Set 1x, 1.25x, etc. |
| `setIsDrawerOpen(bool)` | Control the full-screen player visibility |

**Important implementation notes:**
- `playTrack` uses `playlistRef` (a ref mirror of `playlist` state) to avoid stale closures in async callbacks.
- `handleTrackEnd` also uses refs to avoid reading stale `currentIndex`.
- The hook checks `response.headers.get('content-type')` to decide if the API returned JSON (cached URL) or raw bytes (live stream), and creates a `blob://` URL accordingly.

### `LexPlayer` Component

Accepts two props:
- `isMinimized: boolean` — whether to show the mini bar or the full-screen player
- `onExpand: () => void` — callback to enter full-screen mode
- `onMinimize: () => void` — callback to minimize

**Mini-player shows:**
- Track title & subtitle (or error/loading status)
- Prev / Play-Pause (spinner when loading) / Next buttons
- A mini progress scrub bar
- "Expand Player" button

**Full-screen shows:**
- Cover art area (with animated equalizer bars when playing)
- Track title, subtitle, error/loading banner
- Full progress bar with scrub handle
- Speed controls (1x / 1.25x / 1.5x / 2x)
- Prev / Play-Pause / Next buttons
- "My LexPlaylist" queue panel on the right

---

## 6. Adding Items to the Playlist

### From a Codal Article
See `ArticleNode.jsx`. Every article with a database `id` renders a `🎧` Headphones button in the article header. On click:

```js
addToPlaylist({
    id: article.id,       // the DB primary key from codex_data
    type: 'codal',
    title: `Article ${article.article_num}`,
    subtitle: article.article_title || 'Codal Provision'
});
setIsDrawerOpen(true); // opens the full-screen player
```

> ⚠️ The button only appears if `article.id` is present. Make sure the API returns `id` in the article response.

### From a Case Digest
See `CaseDecisionModal.jsx`. The "Add to LexPlay Playlist" button is always visible when a case modal is open. On click:

```js
addToPlaylist({
    id: fullDecision.id,
    type: 'case',
    title: fullDecision.short_title || fullDecision.title || 'Case Digest',
    subtitle: fullDecision.case_number || ''
});
setIsDrawerOpen(true);
```

---

## 7. Local Development Setup

### Prerequisites
- Python venv with: `gtts`, `azure-functions`, `psycopg2`, `azure-storage-blob`, `azure-cognitiveservices-speech`
- Node.js for the Vite frontend
- PostgreSQL running locally
- Azurite (optional, for blob caching)

### Install gTTS (if missing)
```powershell
# from the api directory
.\.venv\Scripts\pip.exe install gTTS
```

### Start all services
Use the `start_all.ps1` script at project root:
```powershell
.\start_all.ps1
```

This should start:
- Azurite (local Azure Blob emulator) on port 10000
- Azure Functions (`func start`) on port 7071
- Vite frontend on port 5173

### Testing the API directly
```
GET http://localhost:7071/api/audio/codal/1
GET http://localhost:7071/api/audio/case/42
```
The first call per article will take **5–20 seconds** while gTTS generates audio. Subsequent calls return cached audio instantly (if Azurite is running).

---

## 8. Known Issues & Future Work

### 🔴 Current Blocker: Audio not playing end-to-end
The audio pipeline generates audio on the backend (gTTS confirmed working in isolation), but audio playback in the browser is failing. Likely causes to investigate:

1. **CORS on the Azure Functions local host** — The Function might not be sending CORS headers for `localhost:5173`. Check `host.json` for CORS configuration.
   ```json
   // api/host.json — add this:
   "cors": {
     "allowedOrigins": ["http://localhost:5173"],
     "supportCredentials": false
   }
   ```

2. **Content-Type header mismatch** — Ensure the backend returns `Content-Type: audio/mpeg` (not `audio/wav`) when using gTTS. The browser's Audio API is strict about this.

3. **gTTS network timeout** — gTTS calls Google's servers. If there's a proxy or firewall in the dev environment, it may time out silently. Try running:
   ```python
   from gtts import gTTS
   import io
   tts = gTTS("Hello world", lang='en')
   fp = io.BytesIO()
   tts.write_to_fp(fp)
   print(f"Success: {len(fp.getvalue())} bytes")
   ```

4. **Azure Functions streaming** — Verify the Function is correctly setting the `body=audio_data` bytes (not a string). `func.HttpResponse(body=<bytes>)` should work.

5. **Azurite not running** — If Azurite isn't running, the cache check+write both fail and the code falls through. Confirm `start_all.ps1` starts Azurite successfully.

### 🟡 Future Enhancements

| Enhancement | Notes |
|---|---|
| Persistent playlist (saved to DB per user) | Schema: `playlists` + `playlist_items` tables already defined |
| Pre-fetch audio for common articles | `scripts/prefetch_audio.py` skeleton exists |
| Article-level audio (only selected provisions, not full code) | Already supported — each article has its own `id` |
| Shuffle & repeat modes | Add to `useLexPlay` |
| Sleep timer | Common podcast feature |
| Replace gTTS with Azure TTS | Insert real `SPEECH_KEY` in `local.settings.json` |
| Waveform visualization | Use Web Audio API AnalyserNode |
| Playlist sharing | Generate shareable link |

---

## 9. Environment Variables

Set in `api/local.settings.json` for local development:

```json
{
  "Values": {
    "DB_CONNECTION_STRING": "postgresql://user:pass@localhost:5432/lexmateph-ea-db",
    "AZURE_STORAGE_CONNECTION_STRING": "UseDevelopmentStorage=true",
    "SPEECH_KEY": "<your-azure-speech-key-here>",
    "SPEECH_REGION": "japaneast"
  }
}
```

| Variable | Required | Description |
|---|---|---|
| `DB_CONNECTION_STRING` | ✅ Yes | PostgreSQL connection string |
| `AZURE_STORAGE_CONNECTION_STRING` | Optional | `UseDevelopmentStorage=true` for Azurite, or real Azure connection string for prod |
| `SPEECH_KEY` | Optional | Azure Cognitive Services Speech key. If missing, falls back to gTTS. |
| `SPEECH_REGION` | Optional | Azure region for Speech. Defaults to `japaneast`. |

---

*Last updated: March 2026*
