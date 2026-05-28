import React, { useState } from 'react';
import {
  Pencil, Highlighter, Eraser, RotateCcw, RotateCw, Trash2,
  X, Cloud, Check, Fingerprint,
} from 'lucide-react';

const COLOR_PRESETS = [
  { hex: '#5b21b6', label: 'Violet'  },
  { hex: '#dc2626', label: 'Red'     },
  { hex: '#2563eb', label: 'Blue'    },
  { hex: '#16a34a', label: 'Green'   },
  { hex: '#d97706', label: 'Amber'   },
  { hex: '#000000', label: 'Black'   },
  { hex: '#facc15', label: 'Yellow'  }, // good for highlighter
];

const WIDTH_STEPS = [1, 2, 4, 6, 8];

/**
 * AnnotationToolbar — floating palette shown when annotation mode is active.
 *
 * Positioned fixed (bottom-right), stays visible while annotating.
 */
export default function AnnotationToolbar({
  isAnnotating,
  currentTool,
  onToolChange,
  currentColor,
  onColorChange,
  currentWidth,
  onWidthChange,
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
  const [showColors,    setShowColors]    = useState(false);
  const [confirmClear,  setConfirmClear]  = useState(false);

  if (!isAnnotating) return null;

  const widthIdx   = WIDTH_STEPS.indexOf(currentWidth);
  const nextWidth  = () => onWidthChange(WIDTH_STEPS[(widthIdx + 1) % WIDTH_STEPS.length]);

  const handleClear = () => {
    if (confirmClear) {
      onClear?.();
      setConfirmClear(false);
    } else {
      setConfirmClear(true);
      setTimeout(() => setConfirmClear(false), 3000); // auto-cancel after 3s
    }
  };

  return (
    <div
      className="fixed bottom-6 right-6 z-30 flex flex-col items-end gap-2"
      style={{ touchAction: 'none' }} // prevent inadvertent scroll-on-touch
    >
      {/* Color picker popup */}
      {showColors && (
        <div className="flex gap-1.5 rounded-2xl border border-gray-200 bg-white/95 px-3 py-2 shadow-xl backdrop-blur-sm dark:border-zinc-600 dark:bg-zinc-800/95">
          {COLOR_PRESETS.map(({ hex, label }) => (
            <button
              key={hex}
              title={label}
              onClick={() => { onColorChange(hex); setShowColors(false); }}
              className={`h-6 w-6 rounded-full transition-transform hover:scale-110 ${
                currentColor === hex ? 'ring-2 ring-offset-1 ring-violet-500 scale-110' : ''
              }`}
              style={{ backgroundColor: hex }}
            />
          ))}
        </div>
      )}

      {/* Main toolbar pill */}
      <div className="flex items-center gap-1 rounded-2xl border border-gray-200 bg-white/95 px-2 py-1.5 shadow-xl backdrop-blur-sm dark:border-zinc-600 dark:bg-zinc-800/95">

        {/* Tool buttons */}
        <ToolBtn
          active={currentTool === 'pen'}
          onClick={() => onToolChange('pen')}
          title="Pen"
          color={currentColor}
        >
          <Pencil size={15} />
        </ToolBtn>

        <ToolBtn
          active={currentTool === 'highlighter'}
          onClick={() => onToolChange('highlighter')}
          title="Highlighter"
          color={currentColor}
        >
          <Highlighter size={15} />
        </ToolBtn>

        <ToolBtn
          active={currentTool === 'eraser'}
          onClick={() => onToolChange('eraser')}
          title="Eraser"
        >
          <Eraser size={15} />
        </ToolBtn>

        <Divider />

        {/* Color swatch */}
        <button
          onClick={() => setShowColors(v => !v)}
          title="Pick color"
          className="h-6 w-6 rounded-full border-2 border-white shadow-sm transition-transform hover:scale-110 dark:border-zinc-600"
          style={{ backgroundColor: currentColor }}
        />

        {/* Stroke width */}
        <button
          onClick={nextWidth}
          title={`Stroke width: ${currentWidth}px (click to cycle)`}
          className="flex h-7 w-7 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-zinc-700"
        >
          <span
            className="rounded-full bg-gray-700 dark:bg-gray-200"
            style={{ width: `${Math.max(3, currentWidth + 2)}px`, height: `${Math.max(3, currentWidth + 2)}px` }}
          />
        </button>

        <Divider />

        {/* Undo / Redo */}
        <ToolBtn onClick={onUndo} disabled={!canUndo} title="Undo (Ctrl+Z)">
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
          className={`flex h-7 w-7 items-center justify-center rounded-lg transition-colors ${
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
          className={`flex h-7 w-7 items-center justify-center rounded-lg transition-colors ${
            confirmClear
              ? 'bg-rose-100 text-rose-600 dark:bg-rose-900/40 dark:text-rose-400'
              : 'text-gray-400 hover:bg-gray-100 dark:text-gray-500 dark:hover:bg-zinc-700'
          }`}
        >
          <Trash2 size={14} />
        </button>

        <Divider />

        {/* Save status */}
        <div className="flex h-7 w-7 items-center justify-center text-[10px]" title={
          !canSave ? 'Login to save annotations' : isSaving ? 'Saving…' : 'Saved'
        }>
          {!canSave
            ? <span className="text-gray-300 dark:text-gray-600"><Cloud size={13} /></span>
            : isSaving
              ? <span className="animate-pulse text-violet-400"><Cloud size={13} /></span>
              : <span className="text-emerald-500"><Check size={13} /></span>
          }
        </div>

        {/* Exit */}
        <button
          onClick={onExit}
          title="Exit annotation mode"
          className="flex h-7 w-7 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-700 dark:text-gray-500 dark:hover:bg-zinc-700 dark:hover:text-gray-300"
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

function ToolBtn({ active, onClick, disabled, title, color, children }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`flex h-7 w-7 items-center justify-center rounded-lg transition-colors ${
        active
          ? 'bg-violet-100 text-violet-600 dark:bg-violet-900/40 dark:text-violet-300'
          : disabled
            ? 'cursor-not-allowed text-gray-200 dark:text-gray-700'
            : 'text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-zinc-700'
      }`}
      style={active && color ? { color } : undefined}
    >
      {children}
    </button>
  );
}

function Divider() {
  return <div className="mx-0.5 h-4 w-px bg-gray-200 dark:bg-zinc-600" />;
}
