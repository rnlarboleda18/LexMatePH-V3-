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
    title: 'Case Digest',
    color: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400',
    description:
      'Browse Supreme Court decisions and evidence-grounded case digests. Our engine analyzes every decision with literal fidelity to official sources.',
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
    <FeaturePageShell>
      <div className="mx-auto max-w-4xl space-y-8">
        <div className="glass rounded-xl border-2 border-slate-300/85 bg-white/90 p-6 shadow-sm dark:border-white/10 dark:bg-slate-900/35 sm:p-8">
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

        {/* The LexMatePH Standard Section */}
        <div className="glass rounded-xl border-2 border-slate-300/85 bg-white/90 p-6 shadow-sm dark:border-white/10 dark:bg-slate-900/35 sm:p-8">
          <h3 className="mb-4 text-center text-lg font-bold text-gray-900 dark:text-white uppercase tracking-wider">
            🛡️ The LexMatePH Standard: Engineered Case Digests
          </h3>
          <p className="mb-6 text-sm leading-relaxed text-gray-600 dark:text-gray-400 text-center italic">
            Built specifically for the Philippine Bar: Our high-fidelity legal engine ensures every digest is grounded in literal fidelity.
          </p>
          
          <div className="grid gap-6 sm:grid-cols-2">
            <div>
              <h4 className="mb-2 text-sm font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <span className="text-rose-500">👨‍⚖️</span> Professional Persona
              </h4>
              <p className="text-xs leading-relaxed text-gray-600 dark:text-gray-400">
                Our engine acts as a Senior Legal Editor, identifying shifts in doctrine and "Bar Traps" that generic tools miss.
              </p>
            </div>
            
            <div>
              <h4 className="mb-2 text-sm font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <span className="text-blue-500">📜</span> Evidence-Based
              </h4>
              <p className="text-xs leading-relaxed text-gray-600 dark:text-gray-400">
                We enforce a "Zero-Hallucination" rule. All classifications (New Doctrine, Abandonment, etc.) require direct quotes from the text.
              </p>
            </div>

            <div>
              <h4 className="mb-2 text-sm font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <span className="text-purple-500">👁️</span> 1M Token Context
              </h4>
              <p className="text-xs leading-relaxed text-gray-600 dark:text-gray-400">
                We leverage a massive 1-million-token context window to analyze entire decisions at once, ensuring perfect contextual continuity.
              </p>
            </div>

            <div>
              <h4 className="mb-2 text-sm font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <span className="text-amber-500">🔬</span> Exhaustive Ratio
              </h4>
              <p className="text-xs leading-relaxed text-gray-600 dark:text-gray-400">
                Every issue identified includes at least 5-7 sentences of Reasoning, maintaining the clinical "Language of the Law."
              </p>
            </div>
          </div>
        </div>

        <p className="text-center text-sm font-medium uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">
          LexMate Features at a glance
        </p>

        <div className="grid gap-4 sm:grid-cols-2">
          {FEATURES.map(({ icon: Icon, title, description, color }) => (
            <div
              key={title}
              className="glass rounded-xl border-2 border-slate-300/85 bg-white/90 p-5 shadow-sm dark:border-white/10 dark:bg-slate-900/35"
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
