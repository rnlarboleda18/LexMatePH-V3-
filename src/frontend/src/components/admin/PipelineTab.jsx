import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@clerk/clerk-react';
import {
  Play, SkipForward, Square, RefreshCw,
  AlertCircle, CheckCircle2, FileText, Brain, BookOpen,
  Calendar, TrendingUp,
} from 'lucide-react';
import { MetricCard } from './MetricCard';

function SectionHeading({ children }) {
  return (
    <h3 className="mb-3 text-[10px] font-bold uppercase tracking-widest text-gray-400 dark:text-zinc-500">
      {children}
    </h3>
  );
}

function CoverageBar({ label, pct, color = 'bg-violet-500', tooltip }) {
  const [tip, setTip] = useState(false);
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium text-gray-600 dark:text-zinc-400">{label}</span>
        <span className="tabular-nums font-semibold text-black dark:text-zinc-100">{pct?.toFixed(1)}%</span>
      </div>
      <div className="relative h-2.5 overflow-hidden rounded-full bg-gray-100 dark:bg-zinc-800">
        <div
          className={`h-full rounded-full transition-[width] duration-700 ${color}`}
          style={{ width: `${Math.min(100, pct || 0)}%` }}
        />
      </div>
    </div>
  );
}

function ActionButton({ onClick, disabled, variant = 'default', icon: Icon, children }) {
  const variants = {
    default:  'bg-violet-600 text-white hover:opacity-90',
    secondary:'border border-lex-strong bg-white text-gray-700 hover:bg-gray-50 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800',
    danger:   'border border-red-300 bg-red-50 text-red-700 hover:bg-red-100 dark:border-red-800 dark:bg-red-950/30 dark:text-red-400 dark:hover:bg-red-950/50',
  };
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-semibold shadow-sm transition-all disabled:cursor-not-allowed disabled:opacity-40 ${variants[variant]}`}
    >
      {Icon && <Icon size={13} />}
      {children}
    </button>
  );
}

export default function PipelineTab() {
  const { getToken } = useAuth();

  const [stats, setStats]           = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState(null);
  const [actionErr, setActionErr]   = useState(null);
  const [actionOk, setActionOk]     = useState(null);
  const [actionLoading, setActionLoading] = useState(false);

  const authHdr = useCallback(async () => {
    const token = await getToken();
    return { 'X-Clerk-Authorization': `Bearer ${token}` };
  }, [getToken]);

  const loadStats = useCallback(async () => {
    setStatsLoading(true);
    setStatsError(null);
    try {
      const h = await authHdr();
      const res = await fetch('/api/admin/pipeline-stats', { headers: h });
      if (!res.ok) throw new Error((await res.json()).error || res.statusText);
      setStats(await res.json());
    } catch (e) {
      setStatsError(e.message);
    } finally {
      setStatsLoading(false);
    }
  }, [authHdr]);

  useEffect(() => { loadStats(); }, [loadStats]);

  const callPipeline = async (path, label) => {
    setActionErr(null);
    setActionOk(null);
    setActionLoading(true);
    try {
      const h = await authHdr();
      const res = await fetch(path, { method: 'POST', headers: h });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || `${label} failed (${res.status})`);
      setActionOk(`${label} triggered successfully.`);
      setTimeout(() => setActionOk(null), 6000);
    } catch (e) {
      setActionErr(e.message);
    } finally {
      setActionLoading(false);
    }
  };

  const fmtDate = (d) => d ? new Date(d).toLocaleDateString('en-PH', { year: 'numeric', month: 'short', day: 'numeric' }) : '—';

  return (
    <div className="space-y-7 px-4 py-5 sm:px-6 lg:px-8">

      {/* ── Header ── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-base font-bold text-black dark:text-zinc-100">Digest Pipeline</h2>
          <p className="mt-1 max-w-lg text-sm text-gray-500 dark:text-zinc-400">
            Scrapes new Supreme Court decisions from eLib, converts them to Markdown,
            ingests to the database, and generates AI digests via Gemini.
          </p>
        </div>
        <button
          onClick={loadStats}
          disabled={statsLoading}
          className="flex shrink-0 items-center gap-1.5 self-start rounded-lg border border-lex-strong bg-white px-3 py-2 text-xs font-medium text-gray-600 shadow-sm transition-colors hover:bg-gray-50 disabled:opacity-50 dark:bg-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800"
        >
          <RefreshCw size={13} className={statsLoading ? 'animate-spin' : ''} />
          Refresh Stats
        </button>
      </div>

      {/* ── Pipeline controls ── */}
      <div className="rounded-xl border border-lex bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <SectionHeading>Pipeline Controls</SectionHeading>

        <div className="mb-5 flex flex-wrap gap-3">
          <ActionButton
            onClick={() => callPipeline('/api/admin/pipeline/start', 'Full pipeline')}
            disabled={actionLoading}
            icon={Play}
          >
            Full Run
            <span className="ml-1 text-[10px] font-normal opacity-70">scrape → convert → ingest → digest</span>
          </ActionButton>

          <ActionButton
            onClick={() => callPipeline('/api/admin/pipeline/resume', 'Resume pipeline')}
            disabled={actionLoading}
            variant="secondary"
            icon={SkipForward}
          >
            Resume
            <span className="ml-1 text-[10px] font-normal opacity-70">skip scrape/convert</span>
          </ActionButton>

          <ActionButton
            onClick={() => callPipeline('/api/admin/pipeline/stop', 'Stop pipeline')}
            disabled={actionLoading}
            variant="danger"
            icon={Square}
          >
            Stop Pipeline
          </ActionButton>
        </div>

        <div className="rounded-lg border border-lex bg-gray-50 p-3 text-xs text-gray-500 dark:border-zinc-700 dark:bg-zinc-800/50 dark:text-zinc-400">
          <strong className="font-semibold text-gray-700 dark:text-zinc-300">Full Run</strong>
          {' '}— fetches new cases from eLib, converts HTML to Markdown, uploads to DB, then runs Gemini digest on all pending cases.{' '}
          <strong className="font-semibold text-gray-700 dark:text-zinc-300">Resume</strong>
          {' '}— skips scraping and conversion; re-runs only ingest + digest on already-converted files.
        </div>

        {/* Feedback banners */}
        {(actionErr || actionOk) && (
          <div className={`mt-4 flex items-center gap-2 rounded-lg border px-4 py-3 text-sm ${
            actionErr
              ? 'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-400'
              : 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-400'
          }`}>
            {actionErr ? <AlertCircle size={15} /> : <CheckCircle2 size={15} />}
            {actionErr || actionOk}
          </div>
        )}
      </div>

      {/* ── Stats ── */}
      {statsError ? (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-400">
          <AlertCircle size={15} className="shrink-0" />
          {statsError}
        </div>
      ) : (
        <>
          <div>
            <SectionHeading>Corpus Overview</SectionHeading>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
              <MetricCard
                label="Total Cases"
                value={stats ? stats.total_cases.toLocaleString() : null}
                loading={statsLoading}
                tooltip="Total number of Supreme Court decisions stored in the database across all years."
              />
              <MetricCard
                label="With Digest"
                value={stats ? stats.with_digest.toLocaleString() : null}
                loading={statsLoading}
                tooltip="Cases that have been processed through the Gemini AI digest pipeline — metadata, statutes cited, holding, and ratio decidendi extracted."
              />
              <MetricCard
                label="Pending Digest"
                value={stats ? stats.without_digest.toLocaleString() : null}
                loading={statsLoading}
                tooltip="Cases in the database that have not yet been digested by the AI pipeline. Run the pipeline to process these."
                highlight={stats?.without_digest > 100 ? 'warn' : undefined}
              />
              <MetricCard
                label="With Full Text"
                value={stats ? stats.with_full_text_md.toLocaleString() : null}
                loading={statsLoading}
                tooltip="Cases where the full decision text has been converted to Markdown and stored. These are ready for AI digest."
              />
              {stats?.legal_concepts != null && (
                <MetricCard
                  label="Legal Concepts"
                  value={stats.legal_concepts.toLocaleString()}
                  loading={statsLoading}
                  tooltip="Total distinct legal concepts extracted from digested cases. These power the Flashcards and LexCode linking features."
                />
              )}
              <MetricCard
                label="Oldest Case"
                value={fmtDate(stats?.oldest_case_date)}
                loading={statsLoading}
                tooltip="The date of the earliest Supreme Court decision currently in the database."
              />
              <MetricCard
                label="Newest Case"
                value={fmtDate(stats?.latest_case_date)}
                loading={statsLoading}
                tooltip="The most recent Supreme Court decision date in the database. Gaps here indicate new cases on eLib not yet scraped."
              />
            </div>
          </div>

          {/* Coverage bars */}
          {!statsLoading && stats && (
            <div className="rounded-xl border border-lex bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
              <SectionHeading>Coverage</SectionHeading>
              <div className="space-y-4">
                <div>
                  <CoverageBar
                    label="Digest Coverage"
                    pct={stats.digest_coverage_pct}
                    color={stats.digest_coverage_pct >= 80 ? 'bg-emerald-500' : stats.digest_coverage_pct >= 50 ? 'bg-amber-500' : 'bg-red-500'}
                  />
                  <p className="mt-1 text-[11px] text-gray-400 dark:text-zinc-500">
                    {stats.with_digest.toLocaleString()} of {stats.total_cases.toLocaleString()} cases digested
                  </p>
                </div>
                <div>
                  <CoverageBar
                    label="Full-Text Markdown"
                    pct={stats.md_coverage_pct}
                    color={stats.md_coverage_pct >= 80 ? 'bg-blue-500' : stats.md_coverage_pct >= 50 ? 'bg-amber-500' : 'bg-red-500'}
                  />
                  <p className="mt-1 text-[11px] text-gray-400 dark:text-zinc-500">
                    {stats.with_full_text_md.toLocaleString()} of {stats.total_cases.toLocaleString()} cases have Markdown text
                  </p>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
