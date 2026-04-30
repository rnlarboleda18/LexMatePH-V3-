import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@clerk/clerk-react';
import {
  Database, Zap, Globe, RefreshCw, AlertCircle,
  Settings, DollarSign, MessageSquarePlus, Trash2,
  ChevronRight, TrendingUp, TrendingDown, Minus,
} from 'lucide-react';
import { MetricCard, Sparkline } from './MetricCard';

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtUSD(n) {
  if (n == null) return '—';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(n);
}

function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-PH', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

/** Extract average timeseries points from Azure Monitor metric value array. */
function extractSeries(metrics, metricName) {
  const m = metrics?.find(m => m.name?.value === metricName || m.name?.localizedValue === metricName);
  if (!m?.timeseries?.[0]?.data) return [];
  return m.timeseries[0].data
    .map(d => d.average ?? d.total ?? null)
    .filter(v => v != null);
}

function extractLatest(metrics, metricName) {
  const series = extractSeries(metrics, metricName);
  return series.length ? series[series.length - 1] : null;
}

/** Sum a time series (for counts like execution count). */
function extractSum(metrics, metricName) {
  const m = metrics?.find(m => m.name?.value === metricName || m.name?.localizedValue === metricName);
  if (!m?.timeseries?.[0]?.data) return null;
  return m.timeseries[0].data.reduce((acc, d) => acc + (d.total ?? d.average ?? 0), 0);
}

// ── SKU Badge ─────────────────────────────────────────────────────────────────

function SkuBadge({ tier, name, freeWarnings = [] }) {
  const isFree = tier?.toLowerCase().includes('free') || tier?.toLowerCase().includes('burstable');
  return (
    <div className={`flex flex-wrap items-center gap-3 rounded-xl border-2 p-4 ${isFree ? 'border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-950/20' : 'border-emerald-300 bg-emerald-50 dark:border-emerald-700 dark:bg-emerald-950/20'}`}>
      <div>
        <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400 dark:text-zinc-500">SKU / Tier</p>
        <p className="font-bold text-black dark:text-zinc-100">{name || '—'}</p>
        <p className={`text-xs font-medium ${isFree ? 'text-amber-700 dark:text-amber-400' : 'text-emerald-700 dark:text-emerald-400'}`}>{tier || '—'}</p>
      </div>
      {freeWarnings.length > 0 && (
        <div className="flex-1 space-y-1 text-xs text-amber-700 dark:text-amber-300">
          {freeWarnings.map((w, i) => (
            <p key={i} className="flex items-start gap-1.5">
              <AlertCircle size={12} className="mt-0.5 shrink-0" />
              {w}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Cost Card ─────────────────────────────────────────────────────────────────

function CostCard({ billing, costData }) {
  const rows = costData?.properties?.rows || [];
  const cols = costData?.properties?.columns?.map(c => c.name) || [];
  const costIdx  = cols.indexOf('Cost');
  const nameIdx  = cols.indexOf('ServiceName');
  const dateIdx  = cols.indexOf('UsageDate');

  // Group by service
  const byService = {};
  const byDate    = {};
  for (const row of rows) {
    const name = nameIdx >= 0 ? String(row[nameIdx]) : 'Other';
    const cost = costIdx >= 0 ? parseFloat(row[costIdx]) || 0 : 0;
    const date = dateIdx >= 0 ? String(row[dateIdx]) : '';
    byService[name] = (byService[name] || 0) + cost;
    byDate[date]    = (byDate[date] || 0) + cost;
  }

  const totalBilled = Object.values(byService).reduce((a, b) => a + b, 0);
  const dailyBurn   = billing ? totalBilled / Math.max(billing.days_elapsed, 1) : 0;
  const projected   = billing ? dailyBurn * billing.days_in_month : null;
  const remaining   = projected != null ? projected - totalBilled : null;

  // Daily sparkline
  const sortedDates = Object.keys(byDate).sort();
  const sparkData   = sortedDates.map(d => byDate[d]);

  const isError = !!costData?.error;

  return (
    <div className="rounded-xl border border-lex bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="mb-4 flex items-center justify-between">
        <h4 className="flex items-center gap-2 text-sm font-bold text-black dark:text-zinc-100">
          <DollarSign size={14} className="text-emerald-600" />
          Azure Cost — {billing ? `${billing.period_start} to ${billing.period_end}` : 'This Month'}
        </h4>
        {billing && (
          <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-[10px] font-semibold text-gray-500 dark:bg-zinc-800 dark:text-zinc-400">
            {billing.days_remaining} days remaining
          </span>
        )}
      </div>

      {isError ? (
        <p className="text-xs text-amber-600 dark:text-amber-400">{costData.error}</p>
      ) : (
        <>
          {/* Key figures */}
          <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="flex flex-col gap-0.5">
              <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400 dark:text-zinc-500">Billed So Far</span>
              <span className="text-xl font-bold tabular-nums text-black dark:text-zinc-100">{fmtUSD(totalBilled)}</span>
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400 dark:text-zinc-500">Projected Total</span>
              <span className="text-xl font-bold tabular-nums text-violet-700 dark:text-violet-400">{fmtUSD(projected)}</span>
              <span className="text-[10px] text-gray-400 dark:text-zinc-500">perceived cycle cost</span>
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400 dark:text-zinc-500">Daily Burn Rate</span>
              <span className="text-xl font-bold tabular-nums text-black dark:text-zinc-100">{fmtUSD(dailyBurn)}<span className="text-sm font-normal text-gray-400">/day</span></span>
            </div>
            <div className="flex flex-col justify-center">
              {sparkData.length > 1 && <Sparkline data={sparkData} color="#8b5cf6" height={36} />}
              <span className="mt-1 text-[10px] text-gray-400 dark:text-zinc-500">daily spend trend</span>
            </div>
          </div>

          {/* By service */}
          {Object.keys(byService).length > 0 && (
            <div className="overflow-hidden rounded-lg border border-lex dark:border-zinc-700">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-lex bg-gray-50 dark:border-zinc-700 dark:bg-zinc-800/60">
                    <th className="px-3 py-2 text-left text-[10px] font-bold uppercase tracking-widest text-gray-400 dark:text-zinc-500">Service</th>
                    <th className="px-3 py-2 text-right text-[10px] font-bold uppercase tracking-widest text-gray-400 dark:text-zinc-500">Billed</th>
                    <th className="px-3 py-2 text-right text-[10px] font-bold uppercase tracking-widest text-gray-400 dark:text-zinc-500">Share</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-lex dark:divide-zinc-800">
                  {Object.entries(byService)
                    .sort(([, a], [, b]) => b - a)
                    .map(([svc, cost]) => (
                      <tr key={svc} className="hover:bg-gray-50 dark:hover:bg-zinc-800/50">
                        <td className="px-3 py-2 text-gray-700 dark:text-zinc-300">{svc}</td>
                        <td className="px-3 py-2 text-right tabular-nums font-medium text-black dark:text-zinc-100">{fmtUSD(cost)}</td>
                        <td className="px-3 py-2 text-right tabular-nums text-gray-400 dark:text-zinc-500">
                          {totalBilled > 0 ? `${((cost / totalBilled) * 100).toFixed(0)}%` : '—'}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}
          {Object.keys(byService).length === 0 && (
            <p className="text-xs text-gray-400 dark:text-zinc-500">No cost data yet for this billing period.</p>
          )}
        </>
      )}
    </div>
  );
}

// ── Observations ──────────────────────────────────────────────────────────────

function ObservationsPanel({ resource, authHdr }) {
  const [items, setItems]       = useState([]);
  const [loading, setLoading]   = useState(true);
  const [text, setText]         = useState('');
  const [posting, setPosting]   = useState(false);
  const [error, setError]       = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const h = await authHdr();
      const res = await fetch(`/api/admin/observations?resource=${encodeURIComponent(resource)}`, { headers: h });
      if (res.ok) setItems(await res.json());
    } catch (_) {}
    setLoading(false);
  }, [resource, authHdr]);

  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    if (!text.trim()) return;
    setPosting(true);
    setError(null);
    try {
      const h = await authHdr();
      const res = await fetch('/api/admin/observations', {
        method: 'POST',
        headers: { ...h, 'Content-Type': 'application/json' },
        body: JSON.stringify({ resource, body: text.trim() }),
      });
      if (!res.ok) { let m = 'Failed to save'; try { m = (await res.json()).error || m; } catch (_) {} throw new Error(m); }
      setText('');
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setPosting(false);
    }
  };

  const del = async (id) => {
    const h = await authHdr();
    await fetch(`/api/admin/observations/${id}`, { method: 'DELETE', headers: h });
    setItems(prev => prev.filter(i => i.id !== id));
  };

  return (
    <div className="rounded-xl border border-lex bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <h4 className="mb-4 flex items-center gap-2 text-sm font-bold text-black dark:text-zinc-100">
        <MessageSquarePlus size={14} className="text-violet-600" />
        Observations & Notes
      </h4>

      {/* Composer */}
      <div className="mb-4 space-y-2">
        <textarea
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="e.g. DB may crash under heavy load — active connections approaching limit. Monitor during peak hours."
          rows={3}
          className="w-full resize-none rounded-lg border border-lex-strong bg-gray-50 px-3 py-2.5 text-sm text-black placeholder-gray-400 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-500/25 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:placeholder-zinc-500 dark:focus:border-zinc-500"
        />
        {error && <p className="text-xs text-red-600 dark:text-red-400">{error}</p>}
        <div className="flex justify-end">
          <button
            onClick={submit}
            disabled={posting || !text.trim()}
            className="rounded-lg bg-violet-600 px-4 py-2 text-xs font-semibold text-white shadow-sm transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {posting ? 'Saving…' : 'Add Note'}
          </button>
        </div>
      </div>

      {/* Thread */}
      {loading ? (
        <div className="space-y-2">
          {[1, 2].map(i => (
            <div key={i} className="h-14 animate-pulse rounded-lg bg-gray-100 dark:bg-zinc-800" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <p className="text-center text-xs text-gray-400 dark:text-zinc-500 py-4">
          No observations yet. Add a note above to log issues or findings.
        </p>
      ) : (
        <div className="divide-y divide-lex dark:divide-zinc-800">
          {items.map(item => (
            <div key={item.id} className="group flex items-start justify-between gap-3 py-3">
              <div className="min-w-0 flex-1">
                <p className="text-sm text-black dark:text-zinc-100">{item.body}</p>
                <p className="mt-1 text-[10px] text-gray-400 dark:text-zinc-500">{fmtDate(item.created_at)}</p>
              </div>
              <button
                onClick={() => del(item.id)}
                className="shrink-0 rounded p-1 text-gray-300 opacity-0 transition-all hover:text-red-500 group-hover:opacity-100 dark:text-zinc-600 dark:hover:text-red-400"
                aria-label="Delete observation"
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Sub-tab panels ────────────────────────────────────────────────────────────

function PostgreSQLPanel({ data, skus, billing, costData, authHdr }) {
  const res     = data?.resources?.postgresql;
  const sku     = skus?.postgresql;
  const metrics = res?.metrics || [];

  const cpuPct    = extractLatest(metrics, 'cpu_percent');
  const memPct    = extractLatest(metrics, 'memory_percent');
  const storagePct = extractLatest(metrics, 'storage_percent');
  const conns     = extractLatest(metrics, 'active_connections');
  const iops      = extractLatest(metrics, 'iops');

  const cpuSeries = extractSeries(metrics, 'cpu_percent');
  const memSeries = extractSeries(metrics, 'memory_percent');

  const freeWarnings = [];
  if (sku?.tier === 'Burstable') {
    if (storagePct != null && storagePct > 70) freeWarnings.push(`Storage at ${storagePct.toFixed(0)}% of ${sku.max_storage_gb} GB free tier limit.`);
    if (conns != null && conns > 35)           freeWarnings.push(`${Math.round(conns)} active connections — nearing free tier max of ${sku.max_connections}.`);
  }

  return (
    <div className="space-y-5">
      <SkuBadge
        name={res?.sku?.name || sku?.name || 'Burstable B1ms'}
        tier={res?.tier || sku?.tier || 'Free / Burstable'}
        freeWarnings={freeWarnings}
      />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
        <MetricCard label="CPU Usage" value={cpuPct != null ? cpuPct.toFixed(1) : null} unit="%" showBar warn={70} crit={90} sparkData={cpuSeries}
          tooltip="How much of the server's processor your database is using. Above 70% under sustained load means you may need a larger tier." />
        <MetricCard label="Memory Usage" value={memPct != null ? memPct.toFixed(1) : null} unit="%" showBar warn={70} crit={90} sparkData={memSeries}
          tooltip="RAM usage percentage. High memory usage means the database has less room to cache data in memory — expect more disk reads and slower queries." />
        <MetricCard label="Storage Used" value={storagePct != null ? storagePct.toFixed(1) : null} unit="%"
          sub={sku ? `of ${sku.max_storage_gb} GB (${sku.tier === 'Burstable' ? 'free tier' : 'paid tier'})` : undefined}
          showBar warn={70} crit={90}
          tooltip={`Percentage of your allocated storage used. Your ${sku?.tier || 'free'} tier allows ${sku?.max_storage_gb || 32} GB. Hitting this limit will cause write failures.`} />
        <MetricCard label="Active Connections" value={conns != null ? Math.round(conns) : null}
          sub={sku ? `of ${sku.max_connections} max (${sku.tier} tier)` : undefined}
          showBar barPct={sku && conns != null ? (conns / sku.max_connections) * 100 : null} warn={70} crit={90}
          tooltip="Simultaneous client connections to the database. Your tier has a hard limit — exceeding it causes connection errors in the app." />
        <MetricCard label="IOPS" value={iops != null ? Math.round(iops) : null}
          tooltip="Input/Output Operations Per Second — how many read/write operations the disk is handling. Sustained high IOPS can throttle your free tier." />
      </div>
      <CostCard billing={billing} costData={costData} />
      <ObservationsPanel resource="postgresql" authHdr={authHdr} />
    </div>
  );
}

function FunctionAppPanel({ data, skus, billing, costData, authHdr }) {
  const res     = data?.resources?.function_app;
  const sku     = skus?.function_app;
  const metrics = res?.metrics || [];

  const execCount  = extractSum(metrics, 'FunctionExecutionCount');
  const execUnits  = extractSum(metrics, 'FunctionExecutionUnits');
  const http5xx    = extractSum(metrics, 'Http5xx');
  const http4xx    = extractSum(metrics, 'Http4xx');
  const avgResp    = extractLatest(metrics, 'AverageResponseTime');
  const memWS      = extractLatest(metrics, 'MemoryWorkingSet');

  const errRate = execCount && (http5xx != null)
    ? ((http5xx / execCount) * 100).toFixed(2)
    : null;

  const freeWarnings = [];
  if (sku?.free_executions_per_month && execCount != null && execCount > sku.free_executions_per_month * 0.7)
    freeWarnings.push(`${(execCount / 1e6).toFixed(2)}M executions — approaching ${sku.free_executions_per_month / 1e6}M free monthly limit.`);

  return (
    <div className="space-y-5">
      <SkuBadge
        name={res?.kind || 'functionapp,linux'}
        tier={sku?.plan || 'Consumption (Serverless)'}
        freeWarnings={freeWarnings}
      />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
        <MetricCard label="Executions (24h)" value={execCount != null ? Math.round(execCount).toLocaleString() : null}
          sub={sku ? `of ${(sku.free_executions_per_month / 1e6).toFixed(0)}M free/month` : undefined}
          tooltip="Total number of times your API functions ran in the last 24 hours. Consumption plan gives you 1 million free executions per month before billing starts." />
        <MetricCard label="GB-Seconds (24h)" value={execUnits != null ? (execUnits / 1e6).toFixed(2) : null}
          sub={sku ? `of ${(sku.free_gb_seconds_per_month / 1000).toFixed(0)}K free/month` : undefined}
          tooltip="A measure of how much memory your functions used and for how long. Think of it as your compute bill unit — Azure gives 400,000 GB-seconds free per month." />
        <MetricCard label="5xx Errors (24h)" value={http5xx != null ? Math.round(http5xx).toLocaleString() : null}
          highlight={http5xx > 10 ? 'warn' : undefined}
          tooltip="Server-side errors returned by your API in the last 24 hours. These represent failures your users saw. Any sustained 5xx rate needs investigation." />
        <MetricCard label="4xx Errors (24h)" value={http4xx != null ? Math.round(http4xx).toLocaleString() : null}
          tooltip="Client errors (not found, unauthorized, etc.) in the last 24 hours. A high 4xx count can indicate broken links, auth issues, or API misuse." />
        <MetricCard label="Avg Response Time" value={avgResp != null ? avgResp.toFixed(0) : null} unit="ms"
          showBar barPct={avgResp != null ? Math.min(100, (avgResp / 3000) * 100) : null} warn={50} crit={80}
          tooltip="Average time your API took to respond to requests. Under 500ms is good; above 2 seconds means users notice slowness." />
        <MetricCard label="Error Rate" value={errRate} unit="%"
          showBar warn={1} crit={5}
          tooltip="Percentage of requests that resulted in a server error (5xx). Even 1% means 1 in 100 users hit a broken API." />
        {memWS != null && (
          <MetricCard label="Memory (Working Set)" value={(memWS / 1048576).toFixed(0)} unit="MB"
            tooltip="RAM your function app is currently using. Consumption plan allocates up to 1.5 GB per instance — sustained high usage can lead to timeouts." />
        )}
      </div>
      <CostCard billing={billing} costData={costData} />
      <ObservationsPanel resource="function_app" authHdr={authHdr} />
    </div>
  );
}

function StaticWebAppPanel({ data, skus, billing, costData, authHdr }) {
  const res = data?.resources?.static_web_app;
  const sku = skus?.static_web_app;

  return (
    <div className="space-y-5">
      <SkuBadge
        name={res?.sku?.name || 'Free'}
        tier={sku?.tier || 'Free'}
        freeWarnings={sku?.tier === 'Free' ? [
          `Free tier allows ${sku.free_bandwidth_gb} GB bandwidth/month — monitor during traffic spikes.`,
          `Max ${sku.free_builds_per_month} GitHub Actions builds/month included.`,
        ] : []}
      />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <MetricCard label="Bandwidth Limit" value={`${sku?.free_bandwidth_gb || 100} GB`}
          tooltip="Maximum data transfer your Static Web App can serve per month on the free tier. Exceeding this may result in your site being throttled or billed." />
        <MetricCard label="Free Builds/Month" value={sku?.free_builds_per_month || 2}
          tooltip="Number of automated deployments (GitHub Actions builds) included in your plan per month. Each push to your deployment branch uses one build." />
        <MetricCard label="Custom Domains" value="Unlimited"
          tooltip="Static Web Apps on the free tier support unlimited custom domains with free SSL certificates." />
      </div>
      <p className="rounded-lg border border-lex bg-gray-50 px-4 py-3 text-xs text-gray-500 dark:border-zinc-700 dark:bg-zinc-800/50 dark:text-zinc-400">
        Azure Monitor metrics are limited for Static Web Apps. Bandwidth and request-level telemetry
        can be viewed in the Azure Portal under Monitoring → Metrics for your SWA resource.
      </p>
      <CostCard billing={billing} costData={costData} />
      <ObservationsPanel resource="static_web_app" authHdr={authHdr} />
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

const SUB_TABS = [
  { id: 'postgresql',      label: 'PostgreSQL',      icon: Database },
  { id: 'function_app',    label: 'Function App',    icon: Zap },
  { id: 'static_web_app',  label: 'Static Web App',  icon: Globe },
];

export default function MonitorTab() {
  const { getToken } = useAuth();
  const [activeResource, setActiveResource] = useState('postgresql');
  const [data, setData]         = useState(null);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState(null);

  const authHdr = useCallback(async () => {
    const token = await getToken();
    return { 'X-Clerk-Authorization': `Bearer ${token}` };
  }, [getToken]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const h = await authHdr();
      const res = await fetch('/api/admin/azure-metrics', { headers: h });
      if (!res.ok) { let m = res.statusText; try { m = (await res.json()).error || m; } catch (_) {} throw new Error(m); }
      setData(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [authHdr]);

  useEffect(() => { load(); }, [load]);

  const notConfigured = data && !data.configured;

  return (
    <div className="space-y-6 px-4 py-5 sm:px-6 lg:px-8">

      {/* ── Header ── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-base font-bold text-black dark:text-zinc-100">Azure Monitor</h2>
          <p className="mt-1 max-w-lg text-sm text-gray-500 dark:text-zinc-400">
            Live metrics, SKU limits, cost tracking, and observations for your Azure resources.
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="flex shrink-0 items-center gap-1.5 self-start rounded-lg border border-lex-strong bg-white px-3 py-2 text-xs font-medium text-gray-600 shadow-sm transition-colors hover:bg-gray-50 disabled:opacity-50 dark:bg-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* ── Not configured ── */}
      {notConfigured && (
        <div className="rounded-xl border-2 border-amber-300 bg-amber-50 p-5 dark:border-amber-700 dark:bg-amber-950/20">
          <div className="mb-3 flex items-center gap-2">
            <Settings size={16} className="text-amber-600" />
            <h3 className="font-semibold text-amber-800 dark:text-amber-300">Azure Credentials Not Configured</h3>
          </div>
          <p className="mb-3 text-sm text-amber-700 dark:text-amber-400">{data.message}</p>
          <div className="rounded-lg bg-amber-100 p-3 text-xs font-mono text-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
            <p className="mb-1 font-semibold not-italic">Required Application Settings:</p>
            {['AZURE_SUBSCRIPTION_ID', 'AZURE_RESOURCE_GROUP', 'AZURE_POSTGRES_SERVER_NAME',
              'AZURE_FUNCTION_APP_NAME', 'AZURE_STATIC_WEB_APP_NAME',
              'AZURE_TENANT_ID', 'AZURE_CLIENT_ID', 'AZURE_CLIENT_SECRET'].map(k => (
              <p key={k}>{k}</p>
            ))}
          </div>
        </div>
      )}

      {/* ── Error ── */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-400">
          <AlertCircle size={15} className="shrink-0" />
          {error}
        </div>
      )}

      {/* ── Resource sub-tabs ── */}
      {(data?.configured || loading) && (
        <>
          {/* Sub-tab bar */}
          <div className="flex gap-1 rounded-xl border border-lex bg-gray-50 p-1 dark:border-zinc-700 dark:bg-zinc-800/50">
            {SUB_TABS.map(({ id, label, icon: Icon }) => {
              const hasResource = data?.resources?.[id] || !data;
              return (
                <button
                  key={id}
                  onClick={() => setActiveResource(id)}
                  className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-xs font-semibold transition-all ${
                    activeResource === id
                      ? 'bg-white shadow-sm text-black dark:bg-zinc-900 dark:text-zinc-100'
                      : 'text-gray-500 hover:text-gray-700 dark:text-zinc-400 dark:hover:text-zinc-200'
                  } ${!hasResource && !loading ? 'opacity-40' : ''}`}
                  disabled={!hasResource && !loading}
                >
                  <Icon size={13} />
                  <span className="hidden sm:inline">{label}</span>
                </button>
              );
            })}
          </div>

          {/* Loading skeleton */}
          {loading && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="h-20 animate-pulse rounded-xl border border-lex bg-white dark:border-zinc-800 dark:bg-zinc-900" />
              ))}
            </div>
          )}

          {/* Panel content */}
          {!loading && data && activeResource === 'postgresql' && (
            <PostgreSQLPanel data={data} skus={data.skus} billing={data.billing} costData={data.cost} authHdr={authHdr} />
          )}
          {!loading && data && activeResource === 'function_app' && (
            <FunctionAppPanel data={data} skus={data.skus} billing={data.billing} costData={data.cost} authHdr={authHdr} />
          )}
          {!loading && data && activeResource === 'static_web_app' && (
            <StaticWebAppPanel data={data} skus={data.skus} billing={data.billing} costData={data.cost} authHdr={authHdr} />
          )}
        </>
      )}
    </div>
  );
}
