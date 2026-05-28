import React, { useState } from 'react';
import {
  Pencil, Highlighter, Eraser, RotateCcw, RotateCw, Trash2,
  X, Cloud, Check, Fingerprint,
} from 'lucide-react';

const PEN_COLORS = [
  { hex: '#5b21b6', label: 'Violet'  },
  { hex: '#dc2626', label: 'Red'     },
  { hex: '#2563eb', label: 'Blue'    },
  { hex: '#16a34a', label: 'Green'   },
  { hex: '#d97706', label: 'Amber'   },
  { hex: '#000000', label: 'Black'   },
  { hex: '#6b7280', label: 'Gray'    },
  { hex: '#ffffff', label: 'White'   },
];

const HIGHLIGHTER_COLORS = [
  { hex: '#facc15', label: 'Yellow'      },
  { hex: '#86efac', label: 'Mint'        },
  { hex: '#4ade80', label: 'Green'       },
  { hex: '#fed7aa', label: 'Peach'       },
  { hex: '#a5f3fc', label: 'Sky blue'    },
  { hex: '#60a5fa', label: 'Blue'        },
  { hex: '#ddd6fe', label: 'Lavender'    },
  { hex: '#fda4af', label: 'Rose'        },
  { hex: '#f472b6', label: 'Pink'        },
];

const WIDTH_STEPS = [1, 2, 4, 6, 8];
const ERASER_WIDTHS = [4, 8, 16, 24, 32];

/**
 * AnnotationToolbar — floating palette shown when annotation mode is active.
 *
 * Pen and highlighter each have their own color palette.
 * Clicking a tool button selects it AND opens its color picker inline.
 */
export default function AnnotationToolbar({
  isAnnotating,
  currentTool,
  onToolChange,
  penColor,
  onPenColorChange,
  highlighterColor,
  onHighlighterColorChange,
  currentWidth,
  onWidthChange,
  eraserWidth,
  onEraserWidthChange,
  allowTouchDraw,
  onToggleTouchDraw,
  onUndo,
  onRedo,
  canUndo,
  canRedo,
  isSaving,
  canSave,
  onClear,
  onExit,
}) {
  const [openPicker,   setOpenPicker]   = useState(null); // null | 'pen' | 'highlighter'
  const [confirmClear, setConfirmClear] = useState(false);

  if (!isAnnotating) return null;

  const isEraser      = currentTool === 'eraser';
  const activeSteps   = isEraser ? ERASER_WIDTHS : WIDTH_STEPS;
  const activeWidth   = isEraser ? eraserWidth   : currentWidth;
  const activeSetWidth = isEraser ? onEraserWidthChange : onWidthChange;
  const widthIdx      = activeSteps.indexOf(activeWidth);
  const nextWidth     = () => activeSetWidth(activeSteps[(widthIdx < 0 ? 0 : (widthIdx + 1)) % activeSteps.length]);

  const handleToolClick = (tool) => {
    onToolChange(tool);
    if (tool === 'pen' || tool === 'highlighter') {
      setOpenPicker(prev => (prev === tool ? null : tool));
    } else {
      setOpenPicker(null);
    }
  };

  const handleClear = () => {
    if (confirmClear) {
      onClear?.();
      setConfirmClear(false);
    } else {
      setConfirmClear(true);
      setTimeout(() => setConfirmClear(false), 3000);
    }
  };

  const currentColor    = currentTool === 'highlighter' ? highlighterColor : penColor;
  const pickerColors    = openPicker === 'highlighter' ? HIGHLIGHTER_COLORS : PEN_COLORS;
  const pickerOnChange  = openPicker === 'highlighter' ? onHighlighterColorChange : onPenColorChange;

  return (
    <div
      className="fixed bottom-6 right-6 z-30 flex flex-col items-end gap-2"
      style={{ touchAction: 'none' }}
    >
      {/* Color picker popup — opens above toolbar */}
      {openPicker && (
        <div className="flex flex-wrap justify-end gap-2 rounded-2xl border border-gray-200 bg-white/95 p-3 shadow-xl backdrop-blur-sm dark:border-zinc-600 dark:bg-zinc-800/95"
          style={{ maxWidth: 220 }}
        >
          <p className="w-full text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-1">
            {openPicker === 'highlighter' ? 'Highlighter color' : 'Pen color'}
          </p>
          {pickerColors.map(({ hex, label }) => (
            <button
              key={hex}
              title={label}
              onClick={() => { pickerOnChange(hex); }}
              className="relative h-8 w-8 rounded-full border-2 border-white shadow-md transition-transform hover:scale-110 dark:border-zinc-700"
              style={{ backgroundColor: hex }}
            >
              {currentColor === hex && (
                <span className="absolute inset-0 flex items-center justify-center">
                  <Check
                    size={14}
                    className={
                      // Light colors need a dark check; dark colors need a white check
                      ['#ffffff','#facc15','#86efac','#fed7aa','#a5f3fc','#ddd6fe','#fda4af'].includes(hex)
                        ? 'text-gray-600'
                        : 'text-white'
                    }
                  />
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Main toolbar pill */}
      <div className="flex items-center gap-1 rounded-2xl border border-gray-200 bg-white/95 px-2 py-1.5 shadow-xl backdrop-blur-sm dark:border-zinc-600 dark:bg-zinc-800/95">

        {/* Pen tool — shows its color dot */}
        <button
          onClick={() => handleToolClick('pen')}
          title="Pen"
          className={`relative flex h-8 w-8 items-center justify-center rounded-lg transition-colors ${
            currentTool === 'pen'
              ? 'bg-violet-100 dark:bg-violet-900/40'
              : 'text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-zinc-700'
          }`}
          style={currentTool === 'pen' ? { color: penColor } : undefined}
        >
          <Pencil size={15} />
          {/* Color dot indicator */}
          <span
            className="absolute bottom-0.5 right-0.5 h-2.5 w-2.5 rounded-full border border-white dark:border-zinc-800 shadow-sm"
            style={{ backgroundColor: penColor }}
          />
        </button>

        {/* Highlighter tool — shows its color dot */}
        <button
          onClick={() => handleToolClick('highlighter')}
          title="Highlighter"
          className={`relative flex h-8 w-8 items-center justify-center rounded-lg transition-colors ${
            currentTool === 'highlighter'
              ? 'bg-amber-50 dark:bg-amber-900/20'
              : 'text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-zinc-700'
          }`}
          style={currentTool === 'highlighter' ? { color: highlighterColor } : undefined}
        >
          <Highlighter size={15} />
          {/* Color dot indicator */}
          <span
            className="absolute bottom-0.5 right-0.5 h-2.5 w-2.5 rounded-full border border-white dark:border-zinc-800 shadow-sm"
            style={{ backgroundColor: highlighterColor }}
          />
        </button>

        {/* Eraser */}
        <button
          onClick={() => handleToolClick('eraser')}
          title="Eraser"
          className={`flex h-8 w-8 items-center justify-center rounded-lg transition-colors ${
            currentTool === 'eraser'
              ? 'bg-gray-100 text-gray-700 dark:bg-zinc-700 dark:text-gray-200'
              : 'text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-zinc-700'
          }`}
        >
          <Eraser size={15} />
        </button>

        <Divider />

        {/* Stroke / eraser width */}
        <button
          onClick={nextWidth}
          title={isEraser
            ? `Eraser size: ${eraserWidth}px (tap to cycle)`
            : `Stroke width: ${currentWidth}px (tap to cycle)`}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-zinc-700"
        >
          {isEraser ? (
            // Square eraser indicator
            <span
              className="rounded-sm border border-gray-400 bg-gray-200 dark:border-gray-500 dark:bg-gray-500"
              style={{
                width:  `${Math.min(Math.max(eraserWidth / 2.5, 4), 16)}px`,
                height: `${Math.min(Math.max(eraserWidth / 2.5, 4), 16)}px`,
              }}
            />
          ) : (
            // Circular pen/highlighter dot indicator
            <span
              className="rounded-full"
              style={{
                backgroundColor: currentTool === 'highlighter' ? highlighterColor : penColor,
                width:  `${Math.min(Math.max(currentWidth + 2, 4), 12)}px`,
                height: `${Math.min(Math.max(currentWidth + 2, 4), 12)}px`,
              }}
            />
          )}
        </button>

        <Divider />

        {/* Undo / Redo */}
        <ToolBtn onClick={onUndo} disabled={!canUndo} title="Undo">
          <RotateCcw size={14} />
        </ToolBtn>
        <ToolBtn onClick={onRedo} disabled={!canRedo} title="Redo">
          <RotateCw size={14} />
        </ToolBtn>

        <Divider />

        {/* Touch drawing toggle */}
        <button
          onClick={onToggleTouchDraw}
          title={allowTouchDraw ? 'Finger drawing ON (tap to disable)' : 'Enable finger drawing'}
          className={`flex h-8 w-8 items-center justify-center rounded-lg transition-colors ${
            allowTouchDraw
              ? 'bg-violet-100 text-violet-600 dark:bg-violet-900/40 dark:text-violet-300'
              : 'text-gray-400 hover:bg-gray-100 dark:text-gray-500 dark:hover:bg-zinc-700'
          }`}
        >
          <Fingerprint size={14} />
        </button>

        <Divider />

        {/* Clear all */}
        <button
          onClick={handleClear}
          title={confirmClear ? 'Tap again to confirm clear' : 'Clear all annotations'}
          className={`flex h-8 w-8 items-center justify-center rounded-lg transition-colors ${
            confirmClear
              ? 'bg-rose-100 text-rose-600 dark:bg-rose-900/40 dark:text-rose-400'
              : 'text-gray-400 hover:bg-gray-100 dark:text-gray-500 dark:hover:bg-zinc-700'
          }`}
        >
          <Trash2 size={14} />
        </button>

        <Divider />

        {/* Save status */}
        <div
          className="flex h-8 w-8 items-center justify-center"
          title={!canSave ? 'Login to save annotations' : isSaving ? 'Saving…' : 'Saved'}
        >
          {!canSave
            ? <Cloud    size={13} className="text-gray-300 dark:text-gray-600" />
            : isSaving
              ? <Cloud  size={13} className="animate-pulse text-violet-400" />
              : <Check  size={13} className="text-emerald-500" />
          }
        </div>

        {/* Exit */}
        <button
          onClick={onExit}
          title="Exit annotation mode"
          className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-700 dark:text-gray-500 dark:hover:bg-zinc-700 dark:hover:text-gray-300"
        >
          <X size={14} />
        </button>
      </div>

      {/* Auth hint */}
      {!canSave && (
        <p className="rounded-lg bg-amber-50 px-2 py-1 text-[10px] text-amber-700 shadow dark:bg-amber-900/30 dark:text-amber-300">
          Log in to save annotations
        </p>
      )}
    </div>
  );
}

function ToolBtn({ onClick, disabled, title, children }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`flex h-8 w-8 items-center justify-center rounded-lg transition-colors ${
        disabled
          ? 'cursor-not-allowed text-gray-200 dark:text-gray-700'
          : 'text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-zinc-700'
      }`}
    >
      {children}
    </button>
  );
}

function Divider() {
  return <div className="mx-0.5 h-4 w-px bg-gray-200 dark:bg-zinc-600" />;
}
