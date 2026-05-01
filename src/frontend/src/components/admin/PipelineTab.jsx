import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@clerk/clerk-react';
import {
  Play, SkipForward, Square, RefreshCw,
  AlertCircle, CheckCircle2, Link2,
} from 'lucide-react';
import { MetricCard } from './MetricCard';

function SectionHeading({ children }) {
  return (
    <h3 className="mb-3 text-[10px] font-bold uppercase tracking-widest text-gray-400 dark:text-zinc-500">
      {children}
    </h3>
  );
}

function CoverageBar({ label, pct, color = 'bg-violet-500' }) {
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
    default:   'bg-violet-600 text-white hover:opacity-90',
    secondary: 'border border-lex-strong bg-white text-gray-700 hover:bg-gray-50 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800',
    danger:    'border border-red-300 bg-red-50 text-red-700 hover:bg-red-100 dark:border-red-800 dark:bg-red-950/30 dark:text-red-400 dark:hover:bg-red-950/50',
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

// Ordered statute labels for the badge row
const STATUTE_ORDER = ['RPC', 'CIV', 'LAB', 'CONST', 'FAM', 'ROC', 'RCC'];
const STATUTE_COLORS = {
  RPC:   'bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-400',
  CIV:   'bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400',
  LAB:   'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400',
  CONST: 'bg-violet-100 text-violet-700 dark:bg-violet-950/40 dark:text-violet-400',
  FAM:   'bg-pink-100 text-pink-700 dark:bg-pink-950/40 dark:text-pink-400',
  ROC:   'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400',
  RCC:   'bg-cyan-100 text-cyan-700 dark:bg-cyan-950/40 dark:text-cyan-400',
};

export default function PipelineTab() {
  const { getToken } = useAuth();

  const [stats, setStats]               = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError]     = useState(null);
  const [actionErr, setActionErr]       = useState(null);
  const [actionOk, setActionOk]         = useState(null);
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
      const res = await fetch('/api/ops/pipeline-stats', { headers: h });
      if (!res.ok) {
        let m = res.statusText;
        try { m = (await res.json()).error || m; } catch (_) {}
        throw new Error(m);
      }
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

  const fmtDate = (d) =>
    d ? new Date(d).toLocaleDateString('en-PH', { year: 'numeric', month: 'short', day: 'numeric' }) : '—';
  const fmtNum = (n) => (n != null ? n.toLocaleString() : null);

  return (
    <div className="space-y-7 px-4 py-5 sm:px-6 lg:px-8">

      {/* ── Header ── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-base font-bold text-black dark:text-zinc-100">Digest Pipeline</h2>
          <p className="mt-1 max-w-lg text-sm text-gray-500 dark:text-zinc-400">
            Scrapes new Supreme Court decisions from eLib, converts them to Markdown,
            ingests to the database, generates AI digests via Gemini, then links each
            case to the relevant LexCode codal articles via Vertex AI.
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
            onClick={() => callPipeline('/api/ops/pipeline/start', 'Full pipeline')}
            disabled={actionLoading}
            icon={Play}
          >
            Full Run
            <span className="ml-1 text-[10px] font-normal opacity-70">
              scrape → convert → ingest → digest → link
            </span>
          </ActionButton>

          <ActionButton
            onClick={() => callPipeline('/api/ops/pipeline/resume', 'Resume pipeline')}
            disabled={actionLoading}
            variant="secondary"
            icon={SkipForward}
          >
            Resume
            <span className="ml-1 text-[10px] font-normal opacity-70">
              digest + link unfinished cases
            </span>
          </ActionButton>

          <ActionButton
            onClick={() => callPipeline('/api/ops/pipeline/stop', 'Stop pipeline')}
            disabled={actionLoading}
            variant="danger"
            icon={Square}
          >
            Stop Pipeline
          </ActionButton>
        </div>

        <div className="rounded-lg border border-lex bg-gray-50 p-3 text-xs text-gray-500 dark:border-zinc-700 dark:bg-zinc-800/50 dark:text-zinc-400">
          <strong className="font-semibold text-gray-700 dark:text-zinc-300">Full Run</strong>
          {' '}— fetches new cases from eLib, converts HTML to Markdown, uploads to DB,
          runs Gemini digest, then links each case to all 7 LexCode codals via Vertex AI.{' '}
          <strong className="font-semibold text-gray-700 dark:text-zinc-300">Resume</strong>
          {' '}— skips scraping; re-runs digest on incomplete rows, then links any unlinked
          digested cases (capped at 500 per run).
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
          {/* ── Corpus Overview ── */}
          <div>
            <SectionHeading>Corpus Overview</SectionHeading>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
              <MetricCard
                label="Total Cases"
                value={fmtNum(stats?.total_cases)}
                loading={statsLoading}
                tooltip="Total number of Supreme Court decisions stored in the database."
              />
              <MetricCard
                label="With Digest"
                value={fmtNum(stats?.with_digest)}
                loading={statsLoading}
                tooltip="Cases processed by the Gemini AI digest pipeline — facts, issues, ruling, ratio, and metadata extracted."
              />
              <MetricCard
                label="Pending Digest"
                value={fmtNum(stats?.without_digest)}
                loading={statsLoading}
                tooltip="Cases not yet digested. Run Full Run to process these."
                highlight={stats?.without_digest > 100 ? 'warn' : undefined}
              />
              <MetricCard
                label="With Full Text"
                value={fmtNum(stats?.with_full_text_md)}
                loading={statsLoading}
                tooltip="Cases where the full decision text has been converted to Markdown and stored."
              />
              {stats?.legal_concepts != null && (
                <MetricCard
                  label="Legal Concepts"
                  value={fmtNum(stats.legal_concepts)}
                  loading={statsLoading}
                  tooltip="Total distinct legal concepts extracted from digested cases."
                />
              )}
              <MetricCard
                label="Oldest Case"
                value={fmtDate(stats?.oldest_case_date)}
                loading={statsLoading}
                tooltip="The date of the earliest Supreme Court decision in the database."
              />
              <MetricCard
                label="Newest Case"
                value={fmtDate(stats?.latest_case_date)}
                loading={statsLoading}
                tooltip="The most recent Supreme Court decision date. Gaps indicate new cases on eLib not yet scraped."
              />
            </div>
          </div>

          {/* ── Coverage bars ── */}
          {!statsLoading && stats && (
            <div className="rounded-xl border border-lex bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
              <SectionHeading>Coverage</SectionHeading>
              <div className="space-y-4">
                <div>
                  <CoverageBar
                    label="Digest Coverage"
                    pct={stats.digest_coverage_pct}
                    color={
                      stats.digest_coverage_pct >= 80 ? 'bg-emerald-500'
                      : stats.digest_coverage_pct >= 50 ? 'bg-amber-500'
                      : 'bg-red-500'
                    }
                  />
                  <p className="mt-1 text-[11px] text-gray-400 dark:text-zinc-500">
                    {stats.with_digest.toLocaleString()} of {stats.total_cases.toLocaleString()} cases digested
                  </p>
                </div>
                <div>
                  <CoverageBar
                    label="Full-Text Markdown"
                    pct={stats.md_coverage_pct}
                    color={
                      stats.md_coverage_pct >= 80 ? 'bg-blue-500'
                      : stats.md_coverage_pct >= 50 ? 'bg-amber-500'
                      : 'bg-red-500'
                    }
                  />
                  <p className="mt-1 text-[11px] text-gray-400 dark:text-zinc-500">
                    {stats.with_full_text_md.toLocaleString()} of {stats.total_cases.toLocaleString()} cases have Markdown text
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* ── Codal Links ── */}
          {!statsLoading && stats && stats.linked_cases != null && (
            <div className="rounded-xl border border-lex bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
              <SectionHeading>
                <span className="flex items-center gap-1.5">
                  <Link2 size={11} />
                  Codal Links
                </span>
              </SectionHeading>

              {/* Metric cards */}
              <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
                <MetricCard
                  label="Linked Cases"
                  value={fmtNum(stats.linked_cases)}
                  loading={false}
                  tooltip="Cases linked to at least one LexCode codal article via Vertex AI."
                />
                <MetricCard
                  label="Total Links"
                  value={fmtNum(stats.total_links)}
                  loading={false}
                  tooltip="Total case-to-article links across all 7 codals in codal_case_links."
                />
                <MetricCard
                  label="Unlinked Cases"
                  value={fmtNum(stats.total_cases - stats.linked_cases)}
                  loading={false}
                  tooltip="Digested cases not yet linked to any codal article. Run Resume to process."
                  highlight={(stats.total_cases - stats.linked_cases) > 1000 ? 'warn' : undefined}
                />
              </div>

              {/* Link coverage bar */}
              <div className="mb-4 space-y-1.5">
                <CoverageBar
                  label="Link Coverage"
                  pct={stats.link_coverage_pct}
                  color={
                    stats.link_coverage_pct >= 80 ? 'bg-violet-500'
                    : stats.link_coverage_pct >= 40 ? 'bg-amber-500'
                    : 'bg-red-500'
                  }
                />
                <p className="text-[11px] text-gray-400 dark:text-zinc-500">
                  {stats.linked_cases.toLocaleString()} of {stats.total_cases.toLocaleString()} cases linked to LexCode codals
                </p>
              </div>

              {/* Per-statute badge row */}
              {stats.links_by_statute && Object.keys(stats.links_by_statute).length > 0 && (
                <div>
                  <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-gray-400 dark:text-zinc-500">
                    Links by Codal
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {STATUTE_ORDER.map((code) => {
                      const n = stats.links_by_statute[code];
                      if (n == null) return null;
                      return (
                        <span
                          key={code}
                          className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${STATUTE_COLORS[code] ?? 'bg-gray-100 text-gray-600'}`}
                        >
                          {code}
                          <span className="tabular-nums opacity-80">{n.toLocaleString()}</span>
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
