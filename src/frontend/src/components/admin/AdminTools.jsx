import React, { useState, lazy, Suspense } from 'react';
import { Database, GitBranch, Activity } from 'lucide-react';
import PageLoadingFallback from '../PageLoadingFallback';

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
    <div className="min-h-screen w-full bg-white font-sans text-gray-900 dark:bg-zinc-950 dark:text-gray-100">
      {/* ── Top bar ── */}
      <div className="sticky top-0 z-10 border-b border-lex bg-white/95 shadow-sm backdrop-blur-sm dark:border-zinc-800 dark:bg-zinc-950/95">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          {/* Title row */}
          <div className="flex items-center gap-3 py-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-rose-100 dark:bg-rose-950/40">
              <Activity size={16} className="text-rose-600 dark:text-rose-400" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-black dark:text-zinc-100">Admin Tools</h1>
              <p className="text-[10px] text-gray-400 dark:text-zinc-500">
                Administrator access only
              </p>
            </div>
          </div>

          {/* Tab bar */}
          <div className="flex gap-0.5">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`relative flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-semibold transition-colors ${
                  activeTab === id
                    ? 'border-violet-600 text-violet-700 dark:border-violet-400 dark:text-violet-400'
                    : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 dark:text-zinc-400 dark:hover:border-zinc-600 dark:hover:text-zinc-200'
                }`}
              >
                <Icon size={15} className={activeTab === id ? 'text-violet-600 dark:text-violet-400' : ''} />
                <span className="hidden sm:inline">{label}</span>
                <span className="sm:hidden">{id === 'backup' ? 'Backup' : id === 'pipeline' ? 'Pipeline' : 'Monitor'}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Tab content ── */}
      <div className="mx-auto max-w-7xl">
        <Suspense fallback={<PageLoadingFallback label={`Loading ${TABS.find(t => t.id === activeTab)?.label}…`} />}>
          <ActiveComponent />
        </Suspense>
      </div>
    </div>
  );
}
