import React, { useLayoutEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, Info, Gavel, Library, Book, Brain, SquareStack, Headphones, Newspaper, MessageSquare, Terminal, Scale } from 'lucide-react';
import { APP_HEADER_SURFACE } from '../utils/filterChromeClasses';

const TAB_CONFIG = {
  about:             { label: 'About',         Icon: Info },
  supreme_decisions: { label: 'Case Digest',   Icon: Gavel },
  codex:             { label: 'LexCode',       Icon: Library },
  browse_bar:        { label: 'Bar Questions', Icon: Book },
  bar_2026:          { label: 'BAR 2026',      Icon: Scale },
  quiz:              { label: 'Lexify',        Icon: Brain },
  flashcard:         { label: 'Flashcards',    Icon: SquareStack },
  lexplay:           { label: 'LexPlay',       Icon: Headphones },
  updates:           { label: 'Updates',       Icon: Newspaper },
  lexmate:           { label: 'LexMate AI',    Icon: MessageSquare },
  admin_tools:       { label: 'Admin',         Icon: Terminal },
};

const TAB_BAR_HEIGHT_PX = 36;

export default function TabBar({ tabs, activeMode, onSwitch, onClose, isDarkMode }) {
  useLayoutEffect(() => {
    const h = tabs.length >= 2 ? `${TAB_BAR_HEIGHT_PX}px` : '0px';
    document.documentElement.style.setProperty('--tab-bar-height', h);
    return () => document.documentElement.style.setProperty('--tab-bar-height', '0px');
  }, [tabs.length]);

  if (tabs.length < 2 || typeof document === 'undefined') return null;

  return createPortal(
    <div className={isDarkMode ? 'dark' : ''}>
      <div
        className={`fixed left-0 right-0 z-[45] flex items-stretch overflow-x-auto ${APP_HEADER_SURFACE}`}
        style={{ top: 'var(--app-header-offset)', height: `${TAB_BAR_HEIGHT_PX}px` }}
        data-lex-tab-bar
      >
        {tabs.map((tabMode) => {
          const cfg = TAB_CONFIG[tabMode] ?? { label: tabMode, Icon: Scale };
          const { Icon, label } = cfg;
          const isActive = tabMode === activeMode;
          return (
            <button
              key={tabMode}
              type="button"
              onClick={() => onSwitch(tabMode)}
              className={`group flex shrink-0 items-center gap-1.5 border-r border-lex px-3 text-xs font-medium transition-colors ${
                isActive
                  ? 'bg-violet-600 text-white'
                  : 'text-neutral-600 hover:bg-neutral-100 dark:text-zinc-400 dark:hover:bg-zinc-900'
              }`}
            >
              <Icon size={12} strokeWidth={2} className="shrink-0" />
              <span className="max-w-[6rem] truncate">{label}</span>
              <span
                role="button"
                aria-label={`Close ${label} tab`}
                onClick={(e) => { e.stopPropagation(); onClose(tabMode); }}
                className={`ml-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded transition-colors ${
                  isActive ? 'hover:bg-white/20' : 'hover:bg-neutral-200 dark:hover:bg-zinc-700'
                }`}
              >
                <X size={9} strokeWidth={2.5} />
              </span>
            </button>
          );
        })}
      </div>
    </div>,
    document.body
  );
}
