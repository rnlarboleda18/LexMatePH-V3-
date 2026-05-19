import React, { useState, lazy, Suspense } from 'react';
import { Database, GitBranch, Activity } from 'lucide-react';
import PageLoadingFallback from '../PageLoadingFallback';
import FeaturePageShell from '../FeaturePageShell';

const BackupTab   = lazy(() => import('./BackupTab'));
const PipelineTab = lazy(() => import('./PipelineTab'));
const MonitorTab  = lazy(() => import('./MonitorTab'));

const TABS = [
  { id: 'backup',   label: 'Local Back-Up',    icon: Database,   component: BackupTab },
  { id: 'pipeline', label: 'Digest Pipeline',  icon: GitBranch,  component: PipelineTab },
  { id: 'monitor',  label: 'Monitor',          icon: Activity,   component: MonitorTab },
];

export default function AdminTools() {
  const [activeTab, setActiveTab] = useState('backup');
  const ActiveComponent = TABS.find(t => t.id === activeTab)?.component ?? BackupTab;

  return (
    <FeaturePageShell>
      <div className="animate-in fade-in relative pb-12 duration-700 font-sans text-gray-900 dark:text-gray-100">
        <div className="pointer-events-none absolute -left-20 top-0 h-80 w-80 rounded-full bg-purple-500/25 blur-3xl dark:bg-purple-600/20" aria-hidden />
        <div className="pointer-events-none absolute right-0 top-40 h-72 w-72 rounded-full bg-violet-500/20 blur-3xl dark:bg-fuchsia-600/15" aria-hidden />
        <div className="pointer-events-none absolute bottom-20 left-1/3 h-64 w-96 rounded-full bg-indigo-400/15 blur-3xl dark:bg-indigo-500/10" aria-hidden />
        
        <div className="relative mx-auto w-full max-w-7xl space-y-tile">
          {/* Hero Header */}
          <header className="relative overflow-hidden rounded-lg border border-lex bg-gradient-to-br from-white via-white to-slate-50/60 px-6 py-8 shadow-lg dark:border-lex dark:from-zinc-900 dark:via-zinc-900 dark:to-zinc-950 dark:shadow-[0_24px_80px_-28px_rgba(0,0,0,0.45)] sm:px-10">
            <div className="pointer-events-none absolute -right-16 -top-24 h-56 w-56 rounded-full bg-gradient-to-br from-rose-400/30 to-fuchsia-500/20 blur-2xl" />
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-rose-500 to-rose-600 text-white shadow-lg shadow-rose-500/30">
                  <Activity size={24} />
                </div>
                <div>
                  <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-2xl">
                    Admin Tools
                  </h1>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    Administrator access only
                  </p>
                </div>
              </div>
            </div>
          </header>

          <div className="grid min-w-0 grid-cols-1 gap-tile lg:grid-cols-12">
            <div className="min-w-0 space-y-4 lg:col-span-12">
              <section className="relative overflow-hidden rounded-lg border border-lex bg-white p-4 shadow-xl dark:border-lex dark:bg-zinc-900 sm:p-6">
                {/* Tab bar */}
                <div className="mb-6 flex flex-wrap gap-2 rounded-2xl border border-lex bg-neutral-50 p-1 dark:border-lex dark:bg-zinc-800/80">
                  {TABS.map(({ id, label, icon: Icon }) => (
                    <button
                      key={id}
                      onClick={() => setActiveTab(id)}
                      className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold uppercase tracking-wider transition-all sm:px-5 ${
                        activeTab === id
                          ? 'bg-rose-600 text-white shadow-md shadow-rose-600/25 dark:bg-rose-500'
                          : 'text-slate-500 hover:bg-white/80 dark:text-slate-400 dark:hover:bg-white/5'
                      }`}
                    >
                      <Icon size={16} className={activeTab === id ? 'text-white' : ''} />
                      <span className="hidden sm:inline">{label}</span>
                      <span className="sm:hidden">{id === 'backup' ? 'Backup' : id === 'pipeline' ? 'Pipeline' : 'Monitor'}</span>
                    </button>
                  ))}
                </div>

                {/* ── Tab content ── */}
                <Suspense fallback={<PageLoadingFallback label={`Loading ${TABS.find(t => t.id === activeTab)?.label}…`} />}>
                  <ActiveComponent />
                </Suspense>
              </section>
            </div>
          </div>
        </div>
      </div>
    </FeaturePageShell>
  );
}
