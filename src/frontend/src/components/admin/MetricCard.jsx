import React, { useState, useRef } from 'react';
import { Info } from 'lucide-react';

/** Inline sparkline from a flat array of numbers. */
function Sparkline({ data, color = '#8b5cf6', height = 32 }) {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const w = 80;
  const h = height;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / range) * (h - 4) - 2;
    return `${x},${y}`;
  });
  return (
    <svg width={w} height={h} className="shrink-0">
      <polyline
        points={pts.join(' ')}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.8"
      />
    </svg>
  );
}

/** Thin horizontal progress bar. */
function MiniBar({ pct, warn = 80, crit = 95, inverted = false }) {
  const safeP = Math.min(100, Math.max(0, pct ?? 0));
  const isWarn = inverted ? safeP < (100 - warn) : safeP >= warn;
  const isCrit = inverted ? safeP < (100 - crit) : safeP >= crit;
  const color = isCrit
    ? 'bg-red-500'
    : isWarn
    ? 'bg-amber-500'
    : 'bg-emerald-500';
  return (
    <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-zinc-800">
      <div
        className={`h-full rounded-full transition-all duration-700 ${color}`}
        style={{ width: `${safeP}%` }}
      />
    </div>
  );
}

/** Status dot: green / amber / red */
function StatusDot({ pct, warn = 80, crit = 95, inverted = false }) {
  if (pct == null) return null;
  const isWarn = inverted ? pct < (100 - warn) : pct >= warn;
  const isCrit = inverted ? pct < (100 - crit) : pct >= crit;
  return (
    <span
      className={`inline-block h-2 w-2 shrink-0 rounded-full ${
        isCrit
          ? 'bg-red-500'
          : isWarn
          ? 'bg-amber-400'
          : 'bg-emerald-500'
      }`}
    />
  );
}

/**
 * Reusable admin metric card.
 *
 * Props:
 *   label        – card title (uppercase tracking)
 *   value        – primary display value (string or number)
 *   unit         – suffix shown after value (e.g. '%', 'MB')
 *   sub          – secondary line below value
 *   tooltip      – layman explanation shown on ⓘ hover
 *   showBar      – render a mini progress bar
 *   barPct       – explicit pct for bar (falls back to value when unit==='%')
 *   max          – max for bar calc when barPct not given
 *   warn         – warn threshold pct (default 80)
 *   crit         – crit threshold pct (default 95)
 *   inverted     – lower pct = worse (e.g. cache hit ratio)
 *   sparkData    – array of numbers for sparkline
 *   loading      – show skeleton
 *   highlight    – override border color: 'warn' | 'crit' | 'ok'
 */
export function MetricCard({
  label,
  value,
  unit = '',
  sub,
  tooltip,
  showBar = false,
  barPct,
  max,
  warn = 80,
  crit = 95,
  inverted = false,
  sparkData,
  loading = false,
  highlight,
}) {
  const [tipOpen, setTipOpen] = useState(false);
  const tipRef = useRef(null);

  const pct =
    barPct != null
      ? barPct
      : unit === '%' && value != null
      ? parseFloat(value)
      : max && value != null
      ? (parseFloat(value) / max) * 100
      : null;

  const borderColor =
    highlight === 'crit'
      ? 'border-red-300 dark:border-red-700'
      : highlight === 'warn'
      ? 'border-amber-300 dark:border-amber-700'
      : 'border-lex dark:border-zinc-800';

  if (loading) {
    return (
      <div className="flex animate-pulse flex-col gap-2 rounded-xl border border-lex bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <div className="h-2.5 w-16 rounded bg-gray-200 dark:bg-zinc-700" />
        <div className="h-6 w-20 rounded bg-gray-200 dark:bg-zinc-700" />
        {showBar && <div className="h-1.5 w-full rounded-full bg-gray-100 dark:bg-zinc-800" />}
      </div>
    );
  }

  return (
    <div
      className={`relative flex flex-col gap-1 rounded-xl border bg-white p-4 shadow-sm transition-shadow hover:shadow-md dark:bg-zinc-900 ${borderColor}`}
    >
      {/* Label row */}
      <div className="flex items-center justify-between gap-1">
        <div className="flex items-center gap-1.5">
          {pct != null && showBar && (
            <StatusDot pct={pct} warn={warn} crit={crit} inverted={inverted} />
          )}
          <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400 dark:text-zinc-500">
            {label}
          </span>
        </div>
        {tooltip && (
          <div className="relative shrink-0" ref={tipRef}>
            <button
              type="button"
              className="rounded p-0.5 text-gray-300 transition-colors hover:text-gray-500 dark:text-zinc-600 dark:hover:text-zinc-400"
              onMouseEnter={() => setTipOpen(true)}
              onMouseLeave={() => setTipOpen(false)}
              onFocus={() => setTipOpen(true)}
              onBlur={() => setTipOpen(false)}
              aria-label={`Info: ${label}`}
            >
              <Info size={12} />
            </button>
            {tipOpen && (
              <div className="absolute bottom-full right-0 z-50 mb-2 w-60 rounded-lg border border-lex bg-white p-3 text-[11px] leading-relaxed text-gray-600 shadow-xl dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                {tooltip}
                <span className="absolute -bottom-1 right-2 h-2 w-2 rotate-45 border-b border-r border-lex bg-white dark:border-zinc-700 dark:bg-zinc-800" />
              </div>
            )}
          </div>
        )}
      </div>

      {/* Value row */}
      <div className="flex items-end justify-between gap-2">
        <div className="flex items-end gap-1">
          <span className="text-2xl font-bold leading-none tabular-nums text-black dark:text-zinc-100">
            {value ?? '—'}
          </span>
          {unit && (
            <span className="mb-0.5 text-sm text-gray-400 dark:text-zinc-500">{unit}</span>
          )}
        </div>
        {sparkData && <Sparkline data={sparkData} />}
      </div>

      {/* Sub line */}
      {sub && (
        <p className="text-[11px] leading-snug text-gray-400 dark:text-zinc-500">{sub}</p>
      )}

      {/* Bar */}
      {showBar && pct != null && (
        <MiniBar pct={pct} warn={warn} crit={crit} inverted={inverted} />
      )}
    </div>
  );
}

export { Sparkline, MiniBar, StatusDot };
