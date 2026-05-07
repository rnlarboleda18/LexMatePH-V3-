import React, { useState } from 'react';
import { Scale, Globe, Briefcase, FileText, Users, Sword, BookOpen } from 'lucide-react';
import PurpleGlassAmbient from './PurpleGlassAmbient';
import CardVioletInnerWash from './CardVioletInnerWash';

const SUBJECTS = [
  {
    id: 'political',
    label: 'Political & PIL',
    fullLabel: 'Political and Public International Law',
    weight: '15%',
    icon: Globe,
    color: 'text-blue-600 dark:text-blue-400',
    bgActive: 'border-blue-600 dark:border-blue-400 text-blue-700 dark:text-blue-300',
    topics: [
      'Constitutional Law',
      'Administrative Law',
      'Law on Public Officers',
      'Election Law',
      'Local Government Code',
      'Public International Law',
      'International Humanitarian Law',
      'Law of Treaties',
    ],
  },
  {
    id: 'commercial',
    label: 'Commercial & Tax',
    fullLabel: 'Commercial and Taxation Laws',
    weight: '20%',
    icon: Briefcase,
    color: 'text-emerald-600 dark:text-emerald-400',
    bgActive: 'border-emerald-600 dark:border-emerald-400 text-emerald-700 dark:text-emerald-300',
    topics: [
      'Negotiable Instruments Law',
      'Corporation Code',
      'Securities Regulation Code',
      'Intellectual Property Code',
      'Insurance Law',
      'Banking Laws',
      'National Internal Revenue Code',
      'Customs Modernization and Tariff Act',
      'Real Estate Investment Trust Act',
    ],
  },
  {
    id: 'civil',
    label: 'Civil Law & Land',
    fullLabel: 'Civil Law and Land Titles and Deeds',
    weight: '20%',
    icon: FileText,
    color: 'text-violet-600 dark:text-violet-400',
    bgActive: 'border-violet-600 dark:border-violet-400 text-violet-700 dark:text-violet-300',
    topics: [
      'Civil Code of the Philippines',
      'Family Code',
      'Law on Property',
      'Law on Obligations and Contracts',
      'Law on Sales',
      'Law on Agency',
      'Law on Partnership',
      'Land Registration Decree (PD 1529)',
      'Property Registration Authority Rules',
    ],
  },
  {
    id: 'labor',
    label: 'Labor & Social',
    fullLabel: 'Labor Law and Social Legislation',
    weight: '10%',
    icon: Users,
    color: 'text-amber-600 dark:text-amber-400',
    bgActive: 'border-amber-600 dark:border-amber-400 text-amber-700 dark:text-amber-300',
    topics: [
      'Labor Code of the Philippines',
      'Social Security Act',
      'Government Service Insurance System Act',
      'Employees\' Compensation and State Insurance Fund',
      'Retirement Pay Law',
      'Magna Carta for Women',
      'Solo Parents\' Welfare Act',
      'Anti-Sexual Harassment Act',
      'Migrant Workers Act',
    ],
  },
  {
    id: 'criminal',
    label: 'Criminal Law',
    fullLabel: 'Criminal Law',
    weight: '10%',
    icon: Sword,
    color: 'text-rose-600 dark:text-rose-400',
    bgActive: 'border-rose-600 dark:border-rose-400 text-rose-700 dark:text-rose-300',
    topics: [
      'Revised Penal Code (Book I — Principles)',
      'Revised Penal Code (Book II — Specific Crimes)',
      'Anti-Plunder Act',
      'Comprehensive Dangerous Drugs Act',
      'Anti-Violence Against Women and Children Act',
      'Cybercrime Prevention Act',
      'Anti-Trafficking in Persons Act',
      'Anti-Money Laundering Act',
      'Special Penal Laws',
    ],
  },
  {
    id: 'remedial',
    label: 'Remedial & Ethics',
    fullLabel: 'Remedial Law, Legal and Judicial Ethics',
    weight: '25%',
    icon: BookOpen,
    color: 'text-indigo-600 dark:text-indigo-400',
    bgActive: 'border-indigo-600 dark:border-indigo-400 text-indigo-700 dark:text-indigo-300',
    topics: [
      'Rules of Court (Civil Procedure)',
      'Rules of Court (Criminal Procedure)',
      'Rules of Court (Evidence)',
      'Rules of Court (Special Proceedings)',
      'Alternative Dispute Resolution',
      'Judicial Affidavit Rule',
      'Rules on Electronic Evidence',
      'Code of Professional Responsibility and Accountability',
      'Notarial Practice Rules',
      'Practical Exercises',
    ],
  },
];

const EXAM_DATE = 'September 6, 9 & 13, 2026';

export default function Bar2026() {
  const [activeTab, setActiveTab] = useState('political');

  const active = SUBJECTS.find((s) => s.id === activeTab) ?? SUBJECTS[0];

  return (
    <PurpleGlassAmbient showAmbient className="min-h-screen w-full min-w-0 pb-8 font-sans text-gray-900 dark:text-gray-100">
      <div className="w-full min-w-0 max-w-7xl px-3 py-4 sm:px-5 sm:py-5 lg:px-6">

        {/* Header */}
        <div className="mb-5 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-purple-700 shadow-md shadow-violet-900/30">
              <Scale size={20} className="text-white" />
            </div>
            <div>
              <h1 className="text-xl font-black tracking-tight text-gray-900 dark:text-white sm:text-2xl">
                BAR 2026
              </h1>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
                Philippine Bar Examination · {EXAM_DATE}
              </p>
            </div>
          </div>
          <div className="mt-1 flex items-center gap-2 rounded-lg border border-lex bg-white/70 px-3 py-1.5 shadow-sm backdrop-blur-sm dark:bg-zinc-900/70 sm:mt-0">
            <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500">Format</span>
            <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">20 essay questions · 75% passing</span>
          </div>
        </div>

        {/* Tab Bar */}
        <div className="mb-4 flex gap-0.5 overflow-x-auto rounded-xl border border-lex bg-white/60 p-1 shadow-sm backdrop-blur-sm dark:bg-zinc-900/60 no-scrollbar">
          {SUBJECTS.map(({ id, label, weight, icon: Icon, color, bgActive }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`relative flex shrink-0 flex-col items-center gap-0.5 rounded-lg border-b-2 px-3 py-2 text-center text-xs font-semibold transition-all sm:flex-row sm:gap-2 sm:text-sm ${
                activeTab === id
                  ? `bg-white shadow-sm dark:bg-zinc-800 ${bgActive}`
                  : 'border-transparent text-gray-500 hover:bg-white/60 hover:text-gray-700 dark:text-zinc-400 dark:hover:bg-zinc-800/60 dark:hover:text-zinc-200'
              }`}
            >
              <Icon size={15} className={activeTab === id ? color : ''} />
              <span className="leading-tight">{label}</span>
              <span className={`text-[10px] font-bold ${activeTab === id ? color : 'text-gray-400 dark:text-zinc-500'}`}>
                {weight}
              </span>
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="relative min-w-0 overflow-hidden rounded-xl border border-lex bg-white p-5 shadow-sm dark:bg-zinc-900 sm:p-6">
          <div className="pointer-events-none absolute inset-0">
            <CardVioletInnerWash />
          </div>
          <div className="relative z-[1]">
            {/* Subject Header */}
            <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <div className={`mb-1 flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider ${active.color}`}>
                  <active.icon size={13} />
                  Subject {SUBJECTS.findIndex((s) => s.id === activeTab) + 1} of 6
                </div>
                <h2 className="text-lg font-black tracking-tight text-gray-900 dark:text-white sm:text-xl">
                  {active.fullLabel}
                </h2>
              </div>
              <div className={`flex shrink-0 items-center justify-center rounded-xl border-2 px-4 py-2 ${active.bgActive.replace('border-', 'border-').replace('text-', '')} border-current bg-white/60 dark:bg-zinc-800/60`}>
                <div className="text-center">
                  <p className={`text-2xl font-black ${active.color}`}>{active.weight}</p>
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">of exam</p>
                </div>
              </div>
            </div>

            {/* Topic Coverage */}
            <div>
              <h3 className="mb-3 text-xs font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                Coverage Areas
              </h3>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {active.topics.map((topic, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-2.5 rounded-lg border border-lex bg-white/50 px-3 py-2.5 dark:bg-zinc-800/50"
                  >
                    <span className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${active.color} bg-current/10`}>
                      <span className="text-[9px]">{i + 1}</span>
                    </span>
                    <span className="text-sm font-medium text-gray-800 dark:text-gray-200">{topic}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* All subjects weight summary */}
            <div className="mt-6 rounded-lg border border-lex bg-white/40 p-4 dark:bg-zinc-800/40">
              <p className="mb-3 text-[11px] font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500">
                Weight Distribution — All Subjects
              </p>
              <div className="flex flex-wrap gap-2">
                {SUBJECTS.map(({ id, label, weight, color, icon: Icon }) => (
                  <button
                    key={id}
                    onClick={() => setActiveTab(id)}
                    className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold transition-colors ${
                      id === activeTab
                        ? `border-current ${color} bg-current/5`
                        : 'border-lex text-gray-500 hover:border-gray-400 dark:text-zinc-400'
                    }`}
                  >
                    <Icon size={11} className={id === activeTab ? color : ''} />
                    {label} · {weight}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </PurpleGlassAmbient>
  );
}
