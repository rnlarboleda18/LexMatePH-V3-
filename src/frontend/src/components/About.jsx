import React from 'react';
import {
  Brain,
  SquareStack,
  Headphones,
  Gavel,
  Library,
  Book,
  Scale,
} from 'lucide-react';
import FeaturePageShell from './FeaturePageShell';

/** Feature cards (excludes About / Updates — those are separate nav items, not listed here). */
const FEATURES = [
  {
    icon: Brain,
    title: 'Lexify',
    color: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400',
    description:
      'Timed mock-bar sessions modeled on the exam format for stamina, focus, and self-assessment (where your plan allows).',
  },
  {
    icon: SquareStack,
    title: 'Flashcards',
    color: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
    description: 'Flip through concept decks tied to your materials to reinforce doctrines and definitions.',
  },
  {
    icon: Headphones,
    title: 'LexPlay',
    color: 'bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400',
    description: 'Listen to LexMatePH audio content alongside your study flow.',
  },
  {
    icon: Gavel,
    title: 'SC Decisions',
    color: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400',
    description:
      'Browse Supreme Court decisions and case-style digests. Digests may be AI-assisted—verify against full text and official sources.',
  },
  {
    icon: Library,
    title: 'LexCode',
    color: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
    description:
      'Read major codals and statutes (RPC, Civil Code, Rules of Court, Constitution, Labor Code, and more) in one place.',
  },
  {
    icon: Book,
    title: 'Bar Questions',
    color: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-500',
    description:
      'Actual past Philippine Bar Examination questions with suggested answers for structured review.',
  },
];

const About = () => {
  return (
    <FeaturePageShell icon={Scale} title="LEXMATEPH" subtitle="YOUR LEGAL COMPANION">
      <div className="mx-auto max-w-4xl space-y-8">
        <div className="glass rounded-xl border border-white/40 bg-white/45 p-6 shadow-sm dark:border-white/10 dark:bg-slate-900/35 sm:p-8">
          <h3 className="mb-3 text-lg font-bold text-gray-900 dark:text-white">About this App</h3>
          <p className="mb-4 text-sm leading-relaxed text-gray-600 dark:text-gray-400">
            LexMatePH is built for more than bar review alone. Whether you are a law student, professor, bar
            candidate, or practitioner, you can use these tools to explore codals, past bar questions, Supreme Court
            materials, and study aids in one workspace.
          </p>
          <ul className="mb-4 list-inside list-disc space-y-2 text-sm text-gray-600 dark:text-gray-400">
            <li>
              <span className="font-semibold text-gray-800 dark:text-gray-200">Bar Questions</span> are actual past
              Philippine Bar Examination questions, presented with suggested answers to support your review.
            </li>
            <li>
              <span className="font-semibold text-gray-800 dark:text-gray-200">Case digests</span> and related summary
              content may be produced or assisted by AI. They are meant for quick orientation only—always read the
              underlying decisions and verify against official reporters and current law.
            </li>
          </ul>
          <p className="text-xs leading-relaxed text-gray-500 dark:text-gray-500">
            Disclaimer: Content is for education and research, not legal advice. Verify critical points with primary
            sources, the latest jurisprudence, and applicable statutes. LexMatePH does not replace professional judgment
            or counsel.
          </p>
        </div>

        <p className="text-center text-sm font-medium uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">
          LexMate Features at a glance
        </p>

        <div className="grid gap-4 sm:grid-cols-2">
          {FEATURES.map(({ icon: Icon, title, description, color }) => (
            <div
              key={title}
              className="glass rounded-xl border border-white/40 bg-white/45 p-5 shadow-sm dark:border-white/10 dark:bg-slate-900/35"
            >
              <div className={`mb-3 flex h-11 w-11 items-center justify-center rounded-xl ${color}`}>
                <Icon className="h-5 w-5" strokeWidth={2} />
              </div>
              <h3 className="mb-1.5 text-base font-bold text-gray-900 dark:text-white">{title}</h3>
              <p className="text-sm leading-relaxed text-gray-600 dark:text-gray-400">{description}</p>
            </div>
          ))}
        </div>
      </div>
    </FeaturePageShell>
  );
};

export default About;
