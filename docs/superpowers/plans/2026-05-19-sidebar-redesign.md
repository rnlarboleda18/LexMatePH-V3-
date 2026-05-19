# Sidebar Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the sidebar closed by default on all screen sizes (burger-toggled), tighten nav item sizing, and remove the unused LexCode search bar.

**Architecture:** Three independent changes to three files — Layout.jsx (toggle behavior), Sidebar.jsx (style tightening), LexCodeViewer.jsx (search bar removal). No new components needed. No state shape changes.

**Tech Stack:** React 19, Tailwind CSS 4, Lucide React icons

---

## Files Modified

| File | Change |
|---|---|
| `src/frontend/src/components/Layout.jsx` | Remove `xl:hidden` from burger; remove `xl:translate-x-0 xl:block` from aside; remove `xl:pl-52` from main content wrapper |
| `src/frontend/src/components/Sidebar.jsx` | Nav buttons: `text-sm` uniform, `py-2.5` uniform (no `md:` jump), icons `size={18}` |
| `src/frontend/src/components/LexCodeViewer.jsx` | Remove search form UI, portaled dropdown, all search state/handlers, and now-unused imports |

---

## Task 1: Sidebar always-closed by default

**Files:**
- Modify: `src/frontend/src/components/Layout.jsx`

### Changes

There are three class changes in Layout.jsx.

**Change A — Burger button (line ~80):** Remove `xl:hidden` so the burger is visible on all screen sizes.

- [ ] **Step 1: Edit burger button className**

Find the burger `<button>` element — it currently has `xl:hidden` at the start of its className. Remove `xl:hidden`:

```jsx
// BEFORE
className={`xl:hidden flex h-9 w-9 max-sm:h-8 max-sm:w-8 shrink-0 items-center justify-center rounded-lg border transition-colors backdrop-blur-md ${
    isDarkMode
        ? 'border-zinc-600 bg-zinc-900/80 text-zinc-200 shadow-sm ring-1 ring-inset ring-white/[0.06] hover:bg-zinc-800 hover:text-white'
        : 'border-lex-strong bg-white text-black shadow-sm ring-1 ring-inset ring-neutral-200/80 hover:bg-neutral-50'
}`}

// AFTER
className={`flex h-9 w-9 max-sm:h-8 max-sm:w-8 shrink-0 items-center justify-center rounded-lg border transition-colors backdrop-blur-md ${
    isDarkMode
        ? 'border-zinc-600 bg-zinc-900/80 text-zinc-200 shadow-sm ring-1 ring-inset ring-white/[0.06] hover:bg-zinc-800 hover:text-white'
        : 'border-lex-strong bg-white text-black shadow-sm ring-1 ring-inset ring-neutral-200/80 hover:bg-neutral-50'
}`}
```

**Change B — `<aside>` element (line ~185):** Remove `xl:block xl:translate-x-0` so the aside never force-shows itself on desktop; it is always controlled by `isSidebarOpen`.

- [ ] **Step 2: Edit aside className**

```jsx
// BEFORE
className={`fixed left-0 top-[var(--app-header-offset)] z-40 w-52 transform overflow-y-auto transition-transform duration-300 ease-in-out xl:block xl:translate-x-0 ${SIDEBAR_ASIDE_SURFACE} ${
    isSidebarOpen ? 'translate-x-0' : '-translate-x-full'
}`}

// AFTER
className={`fixed left-0 top-[var(--app-header-offset)] z-40 w-52 transform overflow-y-auto transition-transform duration-300 ease-in-out ${SIDEBAR_ASIDE_SURFACE} ${
    isSidebarOpen ? 'translate-x-0' : '-translate-x-full'
}`}
```

**Change C — Main content wrapper (line ~211):** Remove `xl:pl-52` since there is no longer a permanently-open sidebar reserving space.

- [ ] **Step 3: Edit main content padding**

```jsx
// BEFORE
<div className={hideAppChrome ? '' : `xl:pl-52 ${['supreme_decisions', 'codex', 'browse_bar', 'flashcard', 'about', 'updates', 'quiz', 'landing'].includes(mode) ? 'px-0' : 'px-4 lg:px-8'}`}>

// AFTER
<div className={hideAppChrome ? '' : `${['supreme_decisions', 'codex', 'browse_bar', 'flashcard', 'about', 'updates', 'quiz', 'landing'].includes(mode) ? 'px-0' : 'px-4 lg:px-8'}`}>
```

- [ ] **Step 4: Verify manually**

Start the dev server (`npm run dev` or `swa-cli`) and open the app at desktop width (≥1280px).
- Burger button should be visible in the header at all screen sizes.
- Sidebar should be hidden on load (no sidebar on the left).
- Clicking the burger should slide the sidebar in from the left.
- Clicking the burger again (or the scrim overlay) should close it.
- Content should fill full width when the sidebar is closed.

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/components/Layout.jsx
git commit -m "feat: sidebar closed by default — burger toggles on all screen sizes"
```

---

## Task 2: Tighten sidebar nav item sizing

**Files:**
- Modify: `src/frontend/src/components/Sidebar.jsx`

All top-level nav buttons use this className pattern:
```
group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2.5 text-left text-[15px] font-medium transition-colors md:py-3 md:text-base
```

Replace `text-[15px]` → `text-sm` and remove `md:py-3 md:text-base` on every nav button. Replace icon `size={20}` → `size={18}` on every top-level icon.

There are 11 nav buttons total. Do them in order as they appear in the file.

- [ ] **Step 1: Admin Tools button** (first button after the admin guard, ~line 229)

```jsx
// className BEFORE
`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2.5 text-left text-[15px] font-medium transition-colors md:py-3 md:text-base
${mode === 'admin_tools' ? SIDEBAR_NAV_ACTIVE : SIDEBAR_NAV_IDLE}`

// className AFTER
`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2.5 text-left text-sm font-medium transition-colors
${mode === 'admin_tools' ? SIDEBAR_NAV_ACTIVE : SIDEBAR_NAV_IDLE}`

// icon BEFORE
<Terminal size={20} ... />
// icon AFTER
<Terminal size={18} ... />
```

- [ ] **Step 2: About button** (~line 244)

```jsx
// className AFTER
`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2.5 text-left text-sm font-medium transition-colors
${mode === 'about' ? SIDEBAR_NAV_ACTIVE : SIDEBAR_NAV_IDLE}`

// icon AFTER
<Info size={18} ... />
```

- [ ] **Step 3: Updates button** (~line 259)

```jsx
// className AFTER
`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2.5 text-left text-sm font-medium transition-colors
${mode === 'updates' ? SIDEBAR_NAV_ACTIVE : SIDEBAR_NAV_IDLE}`

// icon AFTER
<Newspaper size={18} ... />
```

- [ ] **Step 4: Lexify button** (~line 274)

```jsx
// className AFTER
`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2.5 text-left text-sm font-medium transition-colors
${mode === 'quiz' ? SIDEBAR_NAV_ACTIVE : SIDEBAR_NAV_IDLE}`

// icon AFTER
<Brain size={18} ... />
```

- [ ] **Step 5: Flashcards button** (~line 289)

```jsx
// className AFTER
`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2.5 text-left text-sm font-medium transition-colors
${mode === 'flashcard' ? SIDEBAR_NAV_ACTIVE : SIDEBAR_NAV_IDLE}`

// icon AFTER
<SquareStack size={18} ... />
```

- [ ] **Step 6: LexMate AI button** (admin-only, ~line 305)

```jsx
// className AFTER
`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2.5 text-left text-sm font-medium transition-colors
${mode === 'lexmate' ? SIDEBAR_NAV_ACTIVE : SIDEBAR_NAV_IDLE}`

// icon AFTER
<MessageSquare size={18} ... />
```

- [ ] **Step 7: LexPlay button** (~line 319)

```jsx
// className AFTER
`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2.5 text-left text-sm font-medium transition-colors ${SIDEBAR_NAV_IDLE}`

// icon AFTER
<Headphones size={18} ... />
```

- [ ] **Step 8: Case Digest button** (~line 331)

```jsx
// className AFTER
`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2.5 text-left text-sm font-medium transition-colors
${mode === 'supreme_decisions' ? SIDEBAR_NAV_ACTIVE : SIDEBAR_NAV_IDLE}`

// icon AFTER
<Gavel size={18} ... />
```

- [ ] **Step 9: LexCode button** (~line 346)

```jsx
// className AFTER
`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2.5 text-left text-sm font-medium transition-colors
${mode === 'codex' ? SIDEBAR_NAV_ACTIVE : SIDEBAR_NAV_IDLE}`

// icon AFTER
<Library size={18} ... />
```

- [ ] **Step 10: Bar Questions button** (~line 416)

```jsx
// className AFTER
`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2.5 text-left text-sm font-medium transition-colors
${mode === 'browse_bar' ? SIDEBAR_NAV_ACTIVE : SIDEBAR_NAV_IDLE}`

// icon AFTER
<Book size={18} ... />
```

- [ ] **Step 11: BAR 2026 button** (admin-only, ~line 431)

```jsx
// className AFTER
`group flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2 py-2.5 text-left text-sm font-medium transition-colors
${mode === 'bar_2026' ? SIDEBAR_NAV_ACTIVE : SIDEBAR_NAV_IDLE}`

// icon AFTER
<Scale size={18} ... />
```

- [ ] **Step 12: Verify manually**

Open the sidebar in the browser. Nav items should look slightly more compact and uniform across breakpoints — no size jump when you resize between mobile/tablet/desktop.

- [ ] **Step 13: Commit**

```bash
git add src/frontend/src/components/Sidebar.jsx
git commit -m "fix: sidebar nav items — uniform text-sm sizing, remove md: breakpoint jump"
```

---

## Task 3: Remove LexCode search bar and dead code

**Files:**
- Modify: `src/frontend/src/components/LexCodeViewer.jsx`

Remove the search bar UI, its portaled dropdown, all related state/handlers, and the now-unused imports. Do this in sections from top to bottom.

- [ ] **Step 1: Remove search-only imports (lines ~3, ~15–17, ~23–24)**

```jsx
// BEFORE line 3
import { Book, Calendar, ListTree, X, Gavel, ChevronDown, ChevronRight, Info, Search, ChevronLeft, Lock } from 'lucide-react';
// AFTER — remove Search
import { Book, Calendar, ListTree, X, Gavel, ChevronDown, ChevronRight, Info, ChevronLeft, Lock } from 'lucide-react';
```

```jsx
// REMOVE these three import lines entirely:
import Fuse from 'fuse.js';
import { useDebounce } from '../hooks/useDebounce';
import { HighlightText } from '../utils/highlight';
```

```jsx
// BEFORE lines 20–25
import {
    FILTER_CHROME_SURFACE,
    FILTER_SELECT,
    FILTER_SEARCH_INPUT,
    FILTER_SEARCH_ICON_CLASS,
} from '../utils/filterChromeClasses';

// AFTER — remove the two search-only tokens
import {
    FILTER_CHROME_SURFACE,
    FILTER_SELECT,
} from '../utils/filterChromeClasses';
```

- [ ] **Step 2: Remove search state declarations (~lines 129–136)**

Remove these six lines:

```jsx
// REMOVE:
const [searchTerm, setSearchTerm] = useState('');
const [searchSuggestions, setSearchSuggestions] = useState([]);
const [showSuggestions, setShowSuggestions] = useState(false);
/** Measured rect of the search input — used to position the portaled dropdown
 *  outside the overflow-hidden codal shell so it isn't clipped. */
const [searchBoxRect, setSearchBoxRect] = useState(null);
const closeSuggestionsTimerRef = useRef(null);
const searchBoxRef = useRef(null);
```

- [ ] **Step 3: Remove search logic block (~lines 694–789)**

Remove the entire block from `// --- Search ---` through `handleSuggestionClick` (the function that navigates to an article on suggestion click). This spans:
- `const debouncedSearchTerm = useDebounce(searchTerm, 250);`
- `const fuseRef = useRef(null);`
- Fuse index build `useEffect`
- Search results `useEffect`
- `handleSearchSubmit`
- `handleSearchInputChange`
- `handleClearSearch`
- Scroll/resize listener `useEffect` (keyed on `showSuggestions`)
- `handleKeyDown`
- `handleSuggestionClick`

Look for the comment `// --- Search ---` as the start anchor, and end after `handleSuggestionClick`'s closing brace.

- [ ] **Step 4: Remove search form UI (~lines 1094–1133)**

In the filter chrome `<div>`, the inner wrapper currently contains only the search `<form>`. Remove the inner wrapper div AND the form:

```jsx
// REMOVE this entire block (the inner padding div + form):
<div className="w-full min-w-0 max-w-7xl px-3 py-2 sm:px-5 lg:px-6">
    <div className="flex w-full min-w-0 max-w-full flex-col gap-2 sm:flex-row sm:flex-nowrap sm:items-center sm:gap-2">
        <form
            onSubmit={handleSearchSubmit}
            className="relative min-w-0 w-full flex-1 basis-0 sm:w-auto"
        >
            ...entire form contents...
        </form>
    </div>
</div>
```

If the outer `FILTER_CHROME_SURFACE` div now has no children (check whether the codal selector dropdown is inside the same div or a separate one), remove that outer div too. If the codal selector shares the same chrome wrapper, keep the outer wrapper and only remove the search form.

- [ ] **Step 5: Remove portaled search dropdown (~lines 1206–1282)**

Remove the entire portal block:

```jsx
// REMOVE:
{/* Search dropdown — portaled to body so it escapes overflow-hidden on the codal shell */}
{showSuggestions && searchBoxRect && typeof document !== 'undefined' &&
    createPortal(
        <div ...>
            ...all dropdown content...
        </div>,
        document.body
    )
}
```

- [ ] **Step 6: Verify no remaining references**

Search the file for any remaining uses of: `searchTerm`, `searchSuggestions`, `showSuggestions`, `searchBoxRect`, `closeSuggestionsTimerRef`, `searchBoxRef`, `debouncedSearchTerm`, `fuseRef`, `handleSearchSubmit`, `handleSearchInputChange`, `handleClearSearch`, `handleSuggestionClick`, `handleKeyDown`, `HighlightText`, `FILTER_SEARCH_INPUT`, `FILTER_SEARCH_ICON_CLASS`.

If any remain, remove them.

- [ ] **Step 7: Verify manually**

Open LexCode in the browser. The search input above the codal content should be gone. The codal selector (law picker dropdown) and all article content should still render correctly.

- [ ] **Step 8: Commit**

```bash
git add src/frontend/src/components/LexCodeViewer.jsx
git commit -m "feat: remove unused LexCode article search bar and dead code"
```
