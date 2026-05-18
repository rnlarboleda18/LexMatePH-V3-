# Sidebar Redesign & LexCode Search Bar Removal

**Date:** 2026-05-19
**Scope:** Layout.jsx, Sidebar.jsx, LexCodeViewer.jsx

---

## Goals

1. Sidebar is **closed by default on desktop** — burger button visible on all screen sizes, toggles open/close.
2. Sidebar nav items have **consistent size and spacing** — no breakpoint size jumps.
3. **Remove the LexCode search bar** from LexCodeViewer — it is unused.

---

## 1. Sidebar Toggle Behavior (`Layout.jsx`)

### Current

- Burger button has `xl:hidden` — hidden on desktop.
- `<aside>` has `xl:translate-x-0 xl:block` — forces sidebar open on `xl` screens regardless of state.
- Main content wrapper has `xl:pl-52` — reserves space for always-open sidebar.
- Scrim overlay has `xl:hidden` — never shown on desktop.

### Changes

| Element | Remove | Result |
|---|---|---|
| Burger `<button>` | `xl:hidden` | Burger visible on all screen sizes |
| `<aside>` | `xl:translate-x-0 xl:block` | Sidebar always controlled by `isSidebarOpen` state |
| Main content `<div>` | `xl:pl-52` | No reserved sidebar space; content fills full width |
| Scrim `<div>` | `xl:hidden` | Scrim shows whenever sidebar is open on any screen |

Sidebar always overlays content (drawer pattern). `isSidebarOpen` defaults to `false`, so sidebar is closed on load on all screen widths.

---

## 2. Sidebar Style Tightening (`Sidebar.jsx`)

Remove the `md:` breakpoint size jumps on top-level nav items so sizing is uniform at all screen widths.

| Element | Before | After |
|---|---|---|
| Nav button font | `text-[15px] md:text-base` | `text-sm` (14px, uniform) |
| Nav button padding | `py-2.5 md:py-3` | `py-2.5` (uniform) |
| Nav icons | `size={20}` | `size={18}` |

Subject headers (`text-[12px]`) and law items (`text-[11px]`) are unchanged — their relative scale to the parent is already appropriate.

This applies to **all** top-level nav buttons: About, Updates, Lexify, Flashcards, LexMate AI, LexPlay, Case Digest, LexCode, Bar Questions, BAR 2026, Admin Tools.

---

## 3. Remove LexCode Search Bar (`LexCodeViewer.jsx`)

Remove the search `<form>` element and its wrapper `<div>` (approximately lines 1092–1133). This includes:
- The `<form onSubmit={handleSearchSubmit}>` with the search `<input>` and clear `<button>`
- The outer `<div className="w-full min-w-0 max-w-7xl px-3 py-2 ...">` container

The surrounding chrome surface `<div>` that wraps other filter controls (codal selector, etc.) stays if it contains other elements; if the search form is the only child, that container is removed too.

State variables and handlers related exclusively to the search bar (`searchTerm`, `searchSuggestions`, `showSuggestions`, `searchBoxRect`, `searchBoxRef`, `closeSuggestionsTimerRef`, `handleSearchSubmit`, `handleClearSearch`, `handleKeyDown` for search, Fuse.js search logic) should be removed to avoid dead code.

---

## Files Changed

| File | Change |
|---|---|
| `src/frontend/src/components/Layout.jsx` | Remove `xl:hidden` from burger; remove `xl:translate-x-0 xl:block` from aside; remove `xl:pl-52` from main content |
| `src/frontend/src/components/Sidebar.jsx` | Nav buttons: `text-sm`, `py-2.5` (no md: variant), `size={18}` icons |
| `src/frontend/src/components/LexCodeViewer.jsx` | Remove search form, wrapper div, and dead search state/handlers |
