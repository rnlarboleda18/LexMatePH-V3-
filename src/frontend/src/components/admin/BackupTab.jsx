import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@clerk/clerk-react';
import {
  Database, Download, Play, RefreshCw,
  AlertCircle, CheckCircle2, Clock, Table2,
} from 'lucide-react';
import { MetricCard } from './MetricCard';

function fmtBytes(bytes) {
  if (!bytes && bytes !== 0) return '—';
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sz = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sz[i]}`;
}

function fmtSecs(s) {
  if (!s && s !== 0) return '—';
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return m > 0 ? `${m}m ${sec}s` : `${sec}s`;
}

function SectionHeading({ children }) {
  return (
    <h3 className="mb-3 text-[10px] font-bold uppercase tracking-widest text-gray-400 dark:text-zinc-500">
      {children}
    </h3>
  );
}

export default function BackupTab() {
  const { getToken } = useAuth();

  const [stats, setStats]           = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState(null);

  const [jobId, setJobId]           = useState(null);
  const [job, setJob]               = useState(null);
  const [backupErr, setBackupErr]   = useState(null);
  const [elapsed, setElapsed]       = useState(0);

  const authHdr = useCallback(async () => {
    const token = await getToken();
    return { 'X-Clerk-Authorization': `Bearer ${token}` };
  }, [getToken]);

  const loadStats = useCallback(async () => {
    setStatsLoading(true);
    setStatsError(null);
    try {
      const h = await authHdr();
      const res = await fetch('/api/admin/db-stats', { headers: h });
      if (!res.ok) throw new Error((await res.json()).error || res.statusText);
      setStats(await res.json());
    } catch (e) {
      setStatsError(e.message);
    } finally {
      setStatsLoading(false);
    }
  }, [authHdr]);

  useEffect(() => { loadStats(); }, [loadStats]);

  // Poll job progress
  useEffect(() => {
    if (!jobId || job?.done) return;
    const id = setInterval(async () => {
      try {
        const h = await authHdr();
        const res = await fetch(`/api/admin/backup/status?job_id=${jobId}`, { headers: h });
        if (res.ok) setJob(await res.json());
      } catch (_) {}
    }, 800);
    return () => clearInterval(id);
  }, [jobId, job?.done, authHdr]);

  // Elapsed timer while running
  useEffect(() => {
    if (!jobId || job?.done) return;
    setElapsed(0);
    const id = setInterval(() => setElapsed(s => s + 1), 1000);
    return () => clearInterval(id);
  }, [jobId, job?.done]);

  const startBackup = async () => {
    setBackupErr(null);
    setJob(null);
    setJobId(null);
    try {
      const h = await authHdr();
      const res = await fetch('/api/admin/backup/start', { method: 'POST', headers: h });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to start backup');
      setJobId(data.job_id);
      setJob({ status: 'running', pct: 0, done: false });
    } catch (e) {
      setBackupErr(e.message);
    }
  };

  const downloadBackup = async () => {
    const h = await authHdr();
    const res = await fetch(`/api/admin/backup/download?job_id=${jobId}`, { headers: h });
    if (!res.ok) return;
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = job?.filename || 'backup.zip';
    a.click();
    URL.revokeObjectURL(url);
  };

  const isRunning = job && !job.done;
  const isDone    = job?.done && job?.status === 'done';
  const isFailed  = job?.done && job?.status === 'error';
  const pct       = job?.pct ?? 0;

  return (
    <div className="space-y-7 px-4 py-5 sm:px-6 lg:px-8">

      {/* ── Header ── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-base font-bold text-black dark:text-zinc-100">Local Back-Up</h2>
          <p className="mt-1 max-w-lg text-sm text-gray-500 dark:text-zinc-400">
            Exports every database table as CSV files bundled into a ZIP archive,
            then downloads it directly to your machine.
          </p>
        </div>
        <div className="flex shrink-0 gap-2">
          <button
            onClick={loadStats}
            disabled={statsLoading}
            className="flex items-center gap-1.5 rounded-lg border border-lex-strong bg-white px-3 py-2 text-xs font-medium text-gray-600 shadow-sm transition-colors hover:bg-gray-50 disabled:opacity-50 dark:bg-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800"
          >
            <RefreshCw size={13} className={statsLoading ? 'animate-spin' : ''} />
            Refresh
          </button>
          <button
            onClick={startBackup}
            disabled={isRunning}
            className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-4 py-2 text-xs font-semibold text-white shadow-sm transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Play size={13} />
            {isRunning ? 'Running…' : 'Start Backup'}
          </button>
        </div>
      </div>

      {/* ── Backup error ── */}
      {backupErr && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-400">
          <AlertCircle size={15} className="shrink-0" />
          {backupErr}
        </div>
      )}

      {/* ── Progress panel ── */}
      {(isRunning || isDone || isFailed) && (
        <div
          className={`rounded-xl border-2 p-5 transition-colors ${
            isDone   ? 'border-emerald-300 bg-emerald-50/70 dark:border-emerald-800 dark:bg-emerald-950/20'
            : isFailed ? 'border-red-300 bg-red-50/70 dark:border-red-800 dark:bg-red-950/20'
            : 'border-violet-200 bg-violet-50/70 dark:border-violet-800/60 dark:bg-violet-950/20'
          }`}
        >
          {/* Status row */}
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              {isRunning && <div className="h-3 w-3 animate-pulse rounded-full bg-violet-500" />}
              {isDone    && <CheckCircle2 size={16} className="text-emerald-600 dark:text-emerald-400" />}
              {isFailed  && <AlertCircle size={16} className="text-red-600" />}
              <span className="font-semibold text-black dark:text-zinc-100">
                {isRunning && `Backing up… ${pct}%`}
                {isDone    && `Backup complete · ${fmtBytes(job.size_bytes)}`}
                {isFailed  && 'Backup failed'}
              </span>
            </div>
            <div className="flex items-center gap-3">
              {isRunning && (
                <span className="flex items-center gap-1 text-xs text-gray-400 dark:text-zinc-500">
                  <Clock size={11} /> {fmtSecs(elapsed)}
                </span>
              )}
              {isDone && (
                <button
                  onClick={downloadBackup}
                  className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition-opacity hover:opacity-90"
                >
                  <Download size={12} />
                  Download {job?.filename}
                </button>
              )}
            </div>
          </div>

          {/* Progress bar */}
          <div className="relative h-3 overflow-hidden rounded-full bg-white/70 dark:bg-black/30">
            <div
              className={`absolute inset-y-0 left-0 rounded-full transition-[width] duration-500 ${
                isDone   ? 'bg-emerald-500'
                : isFailed ? 'bg-red-500'
                : 'bg-violet-500'
              }`}
              style={{ width: `${pct}%` }}
            />
          </div>

          {/* Table progress detail */}
          {isRunning && (
            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500 dark:text-zinc-400">
              {job?.current_table && (
                <span className="flex items-center gap-1.5">
                  <Table2 size={11} />
                  Dumping&nbsp;
                  <span className="font-mono font-medium text-violet-700 dark:text-violet-400">
                    {job.current_table}
                  </span>
                </span>
              )}
              {job?.total_tables > 0 && (
                <span>
                  {job.done_tables} / {job.total_tables} tables
                </span>
              )}
            </div>
          )}

          {isFailed && (
            <p className="mt-2 text-xs text-red-600 dark:text-red-400">{job.error}</p>
          )}
        </div>
      )}

      {/* ── DB Stats ── */}
      {statsError ? (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-400">
          <AlertCircle size={15} className="shrink-0" />
          {statsError}
        </div>
      ) : (
        <>
          <div>
            <SectionHeading>Database Overview</SectionHeading>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
              <MetricCard
                label="Total DB Size"
                value={stats?.db_size}
                loading={statsLoading}
                tooltip="Total disk space your PostgreSQL database occupies, including tables, indexes, and metadata."
              />
              <MetricCard
                label="Cache Hit Ratio"
                value={stats?.cache_hit_ratio}
                unit="%"
                loading={statsLoading}
                showBar
                warn={10}
                crit={30}
                inverted
                tooltip="How often the database finds data in memory rather than reading from disk. Anything above 90% is healthy — below that, your DB is doing extra disk I/O on every query."
              />
              <MetricCard
                label="Index Hit Ratio"
                value={stats?.index_hit_ratio}
                unit="%"
                loading={statsLoading}
                showBar
                warn={10}
                crit={30}
                inverted
                tooltip="How often your queries use an index instead of scanning the whole table. Below 90% means some queries are slow because they're checking every single row."
              />
              <MetricCard
                label="Active Connections"
                value={stats?.active_connections}
                loading={statsLoading}
                sub={stats ? `of ${stats.max_connections} max allowed` : undefined}
                showBar
                barPct={stats ? (stats.active_connections / stats.max_connections) * 100 : null}
                warn={75}
                crit={90}
                tooltip="Number of clients currently connected and running queries. If this hits your tier's maximum, new connections will be rejected — your app will show database errors."
              />
              <MetricCard
                label="Dead Tuples"
                value={stats ? stats.total_dead_tuples.toLocaleString() : null}
                loading={statsLoading}
                tooltip="Rows that were deleted or updated but not yet cleaned up. PostgreSQL removes these during VACUUM. Very high counts (100k+) slow down queries and waste disk space."
              />
              <MetricCard
                label="Total Transactions"
                value={stats ? stats.total_transactions.toLocaleString() : null}
                loading={statsLoading}
                tooltip="Cumulative count of all committed and rolled-back database transactions since the server last restarted. Gives a rough sense of total database workload."
              />
            </div>
          </div>

          {/* Table breakdown */}
          {!statsLoading && stats?.tables?.length > 0 && (
            <div>
              <SectionHeading>Table Breakdown</SectionHeading>
              <div className="overflow-x-auto overflow-hidden rounded-xl border border-lex bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
                <table className="w-full min-w-[520px] text-xs">
                  <thead>
                    <tr className="border-b border-lex bg-gray-50 dark:border-zinc-700/60 dark:bg-zinc-800/60">
                      {['Table', 'Live Rows', 'Dead Rows', 'Table Size', 'Index Size', 'Total'].map(h => (
                        <th
                          key={h}
                          className={`px-4 py-2.5 text-[10px] font-bold uppercase tracking-widest text-gray-400 dark:text-zinc-500 ${h === 'Table' ? 'text-left' : 'text-right'}`}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-lex dark:divide-zinc-800">
                    {stats.tables.map(t => {
                      const deadHigh = (t.dead_rows || 0) > 10_000;
                      return (
                        <tr
                          key={t.table_name}
                          className="transition-colors hover:bg-gray-50 dark:hover:bg-zinc-800/50"
                        >
                          <td className="px-4 py-2.5 font-mono text-xs font-medium text-black dark:text-zinc-100">
                            {t.table_name}
                          </td>
                          <td className="px-4 py-2.5 text-right tabular-nums text-gray-600 dark:text-zinc-400">
                            {(t.live_rows || 0).toLocaleString()}
                          </td>
                          <td className={`px-4 py-2.5 text-right tabular-nums ${deadHigh ? 'font-semibold text-amber-600 dark:text-amber-400' : 'text-gray-400 dark:text-zinc-500'}`}>
                            {(t.dead_rows || 0) > 0 ? (t.dead_rows || 0).toLocaleString() : '—'}
                          </td>
                          <td className="px-4 py-2.5 text-right tabular-nums text-gray-600 dark:text-zinc-400">
                            {t.table_size || '—'}
                          </td>
                          <td className="px-4 py-2.5 text-right tabular-nums text-gray-400 dark:text-zinc-500">
                            {t.index_size || '—'}
                          </td>
                          <td className="px-4 py-2.5 text-right tabular-nums font-semibold text-black dark:text-zinc-100">
                            {t.total_size || '—'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <p className="mt-2 text-[10px] text-gray-400 dark:text-zinc-500">
                <Database size={9} className="mr-1 inline" />
                Sizes include all indexes. Last auto-vacuum runs automatically in the background.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
