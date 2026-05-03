import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@clerk/clerk-react';
import {
  Play, SkipForward, Square, RefreshCw,
  AlertCircle, CheckCircle2, Link2, Search, ExternalLink, Clock,
} from 'lucide-react';
import { MetricCard } from './MetricCard';
import { adminApiUrl, formatAdminApiError } from '../../utils/adminApi';

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

  // AI platform selection
  const [aiPlatform, setAiPlatform] = useState('vertex');

  // Scan state
  const [scanState,   setScanState]   = useState(null);
  const [scanResults, setScanResults] = useState(null);
  const [scanLoading, setScanLoading] = useState(false);
  const [scanErr,     setScanErr]     = useState(null);
  const [pipelineRun, setPipelineRun] = useState(null);
  const pollRef = useRef(null);
  const pipelinePollRef = useRef(null);

  const authHdr = useCallback(async () => {
    const token = await getToken();
    return { 'X-Clerk-Authorization': `Bearer ${token}` };
  }, [getToken]);

  const loadStats = useCallback(async () => {
    setStatsLoading(true);
    setStatsError(null);
    try {
      const h = await authHdr();
      const res = await fetch(adminApiUrl('/api/ops/pipeline-stats'), { headers: h });
      if (!res.ok) {
        let m = res.statusText;
        try { m = (await res.json()).error || m; } catch (_) {}
        throw new Error(formatAdminApiError(res, m));
      }
      setStats(await res.json());
    } catch (e) {
      setStatsError(e.message);
    } finally {
      setStatsLoading(false);
    }
  }, [authHdr]);

  useEffect(() => { loadStats(); }, [loadStats]);

  // ── Scan helpers ────────────────────────────────────────────────────────
  const authHdrRef = useRef(authHdr);
  useEffect(() => { authHdrRef.current = authHdr; }, [authHdr]);

  const fetchScanResults = useCallback(async () => {
    try {
      const h = await authHdr();
      const res = await fetch(adminApiUrl('/api/ops/pipeline/scan-results'), { headers: h });
      if (!res.ok) return;
      const data = await res.json();
      setScanState(data.scan);
      if (data.results) setScanResults(data.results);
      if (!data.scan?.running && pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    } catch (_) {}
  }, [authHdr]);

  const startPolling = useCallback(() => {
    if (pollRef.current) return;
    pollRef.current = setInterval(fetchScanResults, 4000);
  }, [fetchScanResults]);

  const fetchPipelineStatus = useCallback(async () => {
    try {
      const h = await authHdr();
      const res = await fetch(adminApiUrl('/api/ops/pipeline/status'), { headers: h });
      if (!res.ok) return;
      const data = await res.json();
      setPipelineRun(data);
      const alive = data.running === true
        || data.status === 'running'
        || data.status === 'stopping';
      if (!alive && pipelinePollRef.current) {
        clearInterval(pipelinePollRef.current);
        pipelinePollRef.current = null;
        loadStats();
      }
    } catch (_) {}
  }, [authHdr, loadStats]);

  const startPipelinePolling = useCallback(() => {
    if (pipelinePollRef.current) return;
    pipelinePollRef.current = setInterval(fetchPipelineStatus, 2000);
    fetchPipelineStatus();
  }, [fetchPipelineStatus]);

  useEffect(() => {
    fetchScanResults();
    (async () => {
      try {
        const h = await authHdrRef.current();
        const res = await fetch(adminApiUrl('/api/ops/pipeline/status'), { headers: h });
        if (res.ok) setPipelineRun(await res.json());
      } catch (_) {}
    })();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (pipelinePollRef.current) clearInterval(pipelinePollRef.current);
    };
  }, [fetchScanResults]);

  const startScan = async () => {
    setScanErr(null);
    setScanLoading(true);
    try {
      const h = await authHdr();
      const res = await fetch(adminApiUrl('/api/ops/pipeline/scan'), { method: 'POST', headers: h });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(formatAdminApiError(res, data.error || `Scan failed (${res.status})`));
      }
      setScanState({ running: true, status: 'running', started_at: data.started_at });
      startPolling();
    } catch (e) {
      setScanErr(e.message);
    } finally {
      setScanLoading(false);
    }
  };

  const callPipeline = async (path, label) => {
    setActionErr(null);
    setActionOk(null);
    setActionLoading(true);
    try {
      const h = await authHdr();
      const res = await fetch(adminApiUrl(path), {
        method: 'POST',
        headers: { ...h, 'Content-Type': 'application/json' },
        body: JSON.stringify({ platform: aiPlatform }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(formatAdminApiError(res, data.error || `${label} failed (${res.status})`));
      }
      setActionOk(`${label} triggered successfully.`);
      if (path.endsWith('/pipeline/start') || path.endsWith('/pipeline/resume')) {
        startPipelinePolling();
      }
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
  const fmtTs  = (iso) => iso ? new Date(iso).toLocaleString('en-PH') : '—';

  return (
    <div className="space-y-7 px-4 py-5 sm:px-6 lg:px-8">

      {/* ── Header ── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-base font-bold text-black dark:text-zinc-100">Digest Pipeline</h2>
          <p className="mt-1 max-w-lg text-sm text-gray-500 dark:text-zinc-400">
            Scrapes new Supreme Court decisions from eLib, converts them to Markdown,
            ingests to the database, generates AI digests, then links each
            case to the relevant LexCode codal articles.
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

        {/* AI Platform selector */}
        <div className="mb-4 flex items-center gap-3">
          <label className="shrink-0 text-xs font-semibold text-gray-600 dark:text-zinc-400">
            AI Platform
          </label>
          <select
            value={aiPlatform}
            onChange={e => setAiPlatform(e.target.value)}
            className="rounded-lg border border-lex-strong bg-white px-3 py-1.5 text-xs font-medium text-gray-700 shadow-sm transition-colors focus:outline-none focus:ring-2 focus:ring-violet-500 dark:bg-zinc-900 dark:text-zinc-300 dark:border-zinc-700"
          >
            <option value="vertex">Google Vertex AI — free trial credits</option>
            <option value="studio">Google AI Studio — API key</option>
          </select>
          {aiPlatform === 'vertex' && (
            <span className="text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
              Billed to project gen-lang-client-0176283199
            </span>
          )}
        </div>

        <div className="mb-5 flex flex-wrap gap-3">
          <ActionButton
            onClick={startScan}
            disabled={scanLoading || scanState?.running}
            variant="secondary"
            icon={Search}
          >
            {scanState?.running ? 'Scanning…' : 'Scan eLib'}
            <span className="ml-1 text-[10px] font-normal opacity-70">
              find new cases
            </span>
          </ActionButton>

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
          runs AI digest, then links each case to all 7 LexCode codals.{' '}
          <strong className="font-semibold text-gray-700 dark:text-zinc-300">Resume</strong>
          {' '}— skips scraping; re-runs digest on incomplete rows, then links any unlinked
          digested cases (capped at 500 per run).{' '}
          <strong className="font-semibold text-gray-700 dark:text-zinc-300">Scan eLib</strong>
          {' '}— read-only probe; discovers new case URLs not yet in the database without
          ingesting anything. Results appear below.
        </div>

        {/* Scan anchor info */}
        {stats?.last_elib_case && (
          <div className="mt-3 flex flex-wrap items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 py-2.5 text-xs dark:border-blue-800 dark:bg-blue-950/20">
            <Search size={12} className="shrink-0 text-blue-500" />
            <span className="font-semibold text-blue-700 dark:text-blue-400">Scan anchor:</span>
            <span className="text-blue-600 dark:text-blue-300">
              Last case in DB is{' '}
              <a
                href={stats.last_elib_case.sc_url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-mono font-bold underline underline-offset-2"
              >
                eLib #{stats.last_elib_case.elib_id}
              </a>
              {stats.last_elib_case.case_label ? ` — ${stats.last_elib_case.case_label}` : ''}
              {stats.last_elib_case.date ? ` (${stats.last_elib_case.date})` : ''}
            </span>
            <span className="ml-auto text-blue-500 dark:text-blue-400">
              Next scan starts at{' '}
              <strong className="font-mono">#{stats.last_elib_case.next_scan_id}</strong>
            </span>
          </div>
        )}

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
        {scanErr && (
          <div className="mt-4 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-400">
            <AlertCircle size={15} />
            {scanErr}
          </div>
        )}

        {pipelineRun && (
          <div className="mt-5 space-y-3 rounded-lg border border-violet-200 bg-violet-50/50 p-4 dark:border-violet-900/50 dark:bg-violet-950/20">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <Play size={13} className="text-violet-600 dark:text-violet-400" />
                <span className="text-xs font-bold uppercase tracking-wide text-violet-800 dark:text-violet-300">
                  Pipeline run status
                </span>
                <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                  pipelineRun.running || pipelineRun.status === 'stopping'
                    ? 'bg-blue-100 text-blue-800 dark:bg-blue-950/50 dark:text-blue-300'
                    : pipelineRun.status === 'done'
                    ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300'
                    : pipelineRun.status === 'failed'
                    ? 'bg-red-100 text-red-800 dark:bg-red-950/50 dark:text-red-300'
                    : 'bg-gray-100 text-gray-600 dark:bg-zinc-800 dark:text-zinc-400'
                }`}>
                  {(pipelineRun.running || pipelineRun.status === 'stopping') && (
                    <Clock size={10} className="animate-pulse" />
                  )}
                  {pipelineRun.running || pipelineRun.status === 'stopping' ? 'Running' : (pipelineRun.status ?? 'idle')}
                </span>
                {pipelineRun.mode && (
                  <span className="text-[11px] font-medium text-violet-600 dark:text-violet-400">
                    Mode: {pipelineRun.mode === 'full' ? 'full scrape + digest + link' : pipelineRun.mode}
                  </span>
                )}
              </div>
              <button
                type="button"
                onClick={() => fetchPipelineStatus()}
                className="flex items-center gap-1 rounded-md px-2 py-1 text-[11px] text-violet-700 hover:bg-violet-100 dark:text-violet-300 dark:hover:bg-violet-950/40"
              >
                <RefreshCw size={11} className={pipelineRun.running ? 'animate-spin' : ''} />
                Refresh
              </button>
            </div>

            {Boolean((pipelineRun.progress_message || pipelineRun.progress?.message || '').trim()) && (
              <p className="text-sm text-gray-700 dark:text-zinc-300">
                {pipelineRun.progress_message || pipelineRun.progress?.message}
              </p>
            )}

            {(() => {
              const op = pipelineRun.overall_percent ?? pipelineRun.progress?.overall_percent;
              const hasCases = (pipelineRun.progress?.cases?.length || 0) > 0;
              if (op == null && !hasCases && !pipelineRun.running) return null;
              const n = Number(op);
              const safe = Number.isFinite(n) ? n : 0;
              return (
                <CoverageBar
                  label="Overall (weighted across active cases)"
                  pct={safe}
                  color={
                    pipelineRun.progress?.status === 'failed' || pipelineRun.status === 'failed'
                      ? 'bg-red-500'
                      : 'bg-violet-500'
                  }
                />
              );
            })()}

            {(pipelineRun.progress?.cases?.length || 0) > 0 && (
              <div className="max-h-72 space-y-4 overflow-y-auto pr-1 pt-1">
                <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400 dark:text-zinc-500">
                  Per-case progress
                </p>
                {pipelineRun.progress.cases.map((c) => (
                  <div
                    key={`c-${c.db_row_id ?? '-'}-${c.elib_id ?? '-'}-${c.updated_at}`}
                    className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm dark:border-zinc-700 dark:bg-zinc-900/80"
                  >
                    <div className="mb-1.5 flex flex-wrap items-start justify-between gap-2 text-xs">
                      <div className="min-w-0">
                        <span className="font-semibold text-gray-900 dark:text-zinc-100">
                          {c.label || (c.db_row_id ? `Database row ${c.db_row_id}` : (c.elib_id != null ? `eLib ${c.elib_id}` : 'Case'))}
                        </span>
                        <div className="mt-0.5 flex flex-wrap gap-2 font-mono text-[11px] text-gray-500 dark:text-zinc-400">
                          {c.elib_id != null && <span># eLib {c.elib_id}</span>}
                          {c.db_row_id != null && <span>db {c.db_row_id}</span>}
                          {c.outcome && <span>{c.outcome}</span>}
                        </div>
                      </div>
                      <span className="shrink-0 rounded-md bg-violet-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-violet-800 dark:bg-violet-950/50 dark:text-violet-300">
                        {c.stage_label || c.stage}
                      </span>
                    </div>
                    {c.detail && (
                      <p className="mb-2 text-[11px] text-gray-500 dark:text-zinc-400">{c.detail}</p>
                    )}
                    <div className="flex items-center justify-between text-[11px] text-gray-600 dark:text-zinc-400">
                      <span>Pipeline step</span>
                      <span className="tabular-nums font-semibold">{Number(c.percent) || 0}%</span>
                    </div>
                    <div className="relative mt-1 h-2 overflow-hidden rounded-full bg-gray-100 dark:bg-zinc-800">
                      <div
                        className="h-full rounded-full bg-emerald-500 transition-[width] duration-500"
                        style={{ width: `${Math.min(100, Number(c.percent) || 0)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {pipelineRun.last_exit_code != null && pipelineRun.status === 'done' && (
              <p className="text-[11px] text-gray-400 dark:text-zinc-500">
                Subprocess exited with code {pipelineRun.last_exit_code}
              </p>
            )}

            {pipelineRun.log_tail && (
              <details className="text-[11px] text-gray-500 dark:text-zinc-400">
                <summary className="cursor-pointer font-semibold text-gray-600 dark:text-zinc-300">
                  Subprocess log (tail)
                </summary>
                <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap break-all rounded-md bg-black/80 p-2 font-mono text-[10px] text-emerald-100">
                  {pipelineRun.log_tail}
                </pre>
              </details>
            )}
          </div>
        )}
      </div>

      {/* ── Scan Results Panel ── */}
      {(scanState || scanResults) && (
        <div className="rounded-xl border border-lex bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
          <div className="mb-4 flex items-center justify-between">
            <SectionHeading>
              <span className="flex items-center gap-1.5">
                <Search size={11} />
                eLib Scan Results
              </span>
            </SectionHeading>
            <button
              onClick={fetchScanResults}
              className="flex items-center gap-1 rounded-md px-2 py-1 text-[11px] text-gray-500 hover:bg-gray-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
            >
              <RefreshCw size={11} className={scanState?.running ? 'animate-spin' : ''} />
              Refresh
            </button>
          </div>

          {/* Status badge */}
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${
              scanState?.running
                ? 'bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400'
                : scanState?.status === 'done'
                ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400'
                : scanState?.status === 'failed'
                ? 'bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-400'
                : 'bg-gray-100 text-gray-600 dark:bg-zinc-800 dark:text-zinc-400'
            }`}>
              {scanState?.running && <Clock size={10} className="animate-pulse" />}
              {scanState?.running ? 'Scanning…' : (scanState?.status ?? 'idle')}
            </span>
            {scanResults?.scanned_at && (
              <span className="text-[11px] text-gray-400 dark:text-zinc-500">
                Last scan: {fmtTs(scanResults.scanned_at)}
              </span>
            )}
          </div>

          {/* last_in_db anchor line in results */}
          {scanResults?.last_in_db?.elib_id > 0 && (
            <div className="mb-4 flex flex-wrap items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-[11px] text-gray-500 dark:border-zinc-700 dark:bg-zinc-800/40 dark:text-zinc-400">
              <span className="font-semibold text-gray-600 dark:text-zinc-300">Scan started after:</span>
              <a
                href={scanResults.last_in_db.sc_url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-mono font-semibold text-violet-600 hover:underline dark:text-violet-400"
              >
                eLib #{scanResults.last_in_db.elib_id}
              </a>
              {scanResults.last_in_db.case_label && (
                <span className="truncate max-w-xs">— {scanResults.last_in_db.case_label}</span>
              )}
              {scanResults.last_in_db.date && (
                <span className="ml-auto text-gray-400">{scanResults.last_in_db.date}</span>
              )}
            </div>
          )}

          {/* Summary metrics */}
          {scanResults && (
            <>
              <div className="mb-4 grid grid-cols-3 gap-3 sm:grid-cols-4">
                <MetricCard
                  label="IDs Probed"
                  value={fmtNum(scanResults.total_probed)}
                  loading={scanState?.running}
                  tooltip={`Probed eLib IDs ${scanResults.probed_from}–${scanResults.probed_to}`}
                />
                <MetricCard
                  label="New Cases Found"
                  value={fmtNum(scanResults.total_new_found)}
                  loading={scanState?.running}
                  tooltip="New G.R. cases found on eLib that are not yet in the database."
                  highlight={scanResults.total_new_found > 0 ? 'warn' : undefined}
                />
                <MetricCard
                  label="DB High-Water ID"
                  value={fmtNum(scanResults.max_elib_id_in_db)}
                  loading={false}
                  tooltip="The highest eLib numeric ID already stored in sc_decided_cases."
                />
                {scanResults.stopped_reason && (
                  <MetricCard
                    label="Stopped"
                    value={scanResults.stopped_reason === 'consecutive_misses' ? '35 misses' : 'max probe'}
                    loading={false}
                    tooltip={`Scan stopped because: ${scanResults.stopped_reason}`}
                  />
                )}
              </div>

              {/* Case list */}
              {scanResults.cases && scanResults.cases.length > 0 ? (
                <div>
                  <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-gray-400 dark:text-zinc-500">
                    {scanResults.total_new_found} new case{scanResults.total_new_found !== 1 ? 's' : ''} pending ingestion
                  </p>
                  <div className="max-h-80 overflow-y-auto rounded-lg border border-lex bg-gray-50 dark:border-zinc-700 dark:bg-zinc-800/40">
                    <table className="w-full text-xs">
                      <thead className="sticky top-0 bg-gray-100 dark:bg-zinc-800">
                        <tr>
                          <th className="px-3 py-2 text-left font-semibold text-gray-500 dark:text-zinc-400">eLib ID</th>
                          <th className="px-3 py-2 text-left font-semibold text-gray-500 dark:text-zinc-400">G.R. No.</th>
                          <th className="px-3 py-2 text-left font-semibold text-gray-500 dark:text-zinc-400">Date Decided</th>
                          <th className="px-3 py-2 text-right font-semibold text-gray-500 dark:text-zinc-400">Link</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100 dark:divide-zinc-700">
                        {scanResults.cases.map((c) => (
                          <tr key={c.elib_id} className="hover:bg-gray-100 dark:hover:bg-zinc-700/50">
                            <td className="px-3 py-2 tabular-nums font-mono text-gray-500 dark:text-zinc-400">
                              #{c.elib_id}
                            </td>
                            <td className="px-3 py-2 font-medium text-gray-800 dark:text-zinc-200">
                              {c.gr_number || c.case_label || '—'}
                            </td>
                            <td className="px-3 py-2 text-gray-600 dark:text-zinc-400">
                              {c.date_decided || '—'}
                            </td>
                            <td className="px-3 py-2 text-right">
                              {c.sc_url ? (
                                <a
                                  href={c.sc_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center gap-1 text-violet-600 hover:underline dark:text-violet-400"
                                >
                                  <ExternalLink size={11} />
                                  eLib
                                </a>
                              ) : <span className="text-gray-400">—</span>}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : scanResults.total_new_found === 0 && !scanState?.running ? (
                <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-400">
                  <CheckCircle2 size={15} />
                  No new cases found — the database is up to date with eLib.
                </div>
              ) : null}
            </>
          )}
        </div>
      )}

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
                tooltip="Cases processed by the AI digest pipeline — facts, issues, ruling, ratio, and metadata extracted."
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
