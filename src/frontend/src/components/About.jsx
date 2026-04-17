import React from 'react';
import {
  Brain,
  SquareStack,
  Headphones,
  Gavel,
  Library,
  Book,
  Shield,
  FileCheck,
  ScanEye,
  ListChecks,
  Scale,
} from 'lucide-react';
import FeaturePageShell from './FeaturePageShell';

/** Feature cards (excludes About / Updates in nav). Purple-forward accents on glass. */
const FEATURES = [
  {
    icon: Brain,
    title: 'Lexify',
    accent:
      'bg-gradient-to-br from-fuchsia-500/20 to-purple-600/10 text-fuchsia-700 ring-1 ring-fuchsia-500/20 dark:text-fuchsia-300 dark:ring-fuchsia-400/20',
    description:
      'Timed mock-bar sessions modeled on the exam format for stamina, focus, and self-assessment (where your plan allows).',
  },
  {
    icon: SquareStack,
    title: 'Flashcards',
    accent:
      'bg-gradient-to-br from-violet-500/20 to-indigo-600/10 text-violet-700 ring-1 ring-violet-500/20 dark:text-violet-300 dark:ring-violet-400/20',
    description: 'Flip through concept decks tied to your materials to reinforce doctrines and definitions.',
  },
  {
    icon: Headphones,
    title: 'LexPlay',
    accent:
      'bg-gradient-to-br from-purple-500/25 to-violet-600/10 text-purple-700 ring-1 ring-purple-500/25 dark:text-purple-300 dark:ring-purple-400/25',
    description: 'Listen to LexMatePH audio content alongside your study flow.',
  },
  {
    icon: Gavel,
    title: 'Case Digest',
    accent:
      'bg-gradient-to-br from-rose-500/15 to-purple-600/10 text-rose-700 ring-1 ring-rose-500/15 dark:text-rose-300 dark:ring-rose-400/20',
    description:
      'Browse Supreme Court decisions and evidence-grounded case digests. Our engine analyzes every decision with literal fidelity to official sources.',
  },
  {
    icon: Library,
    title: 'LexCode',
    accent:
      'bg-gradient-to-br from-indigo-500/20 to-purple-600/10 text-indigo-700 ring-1 ring-indigo-500/20 dark:text-indigo-300 dark:ring-indigo-400/20',
    description:
      'Read major codals and statutes (RPC, Civil Code, Rules of Court, Constitution, Labor Code, and more) in one place.',
  },
  {
    icon: Book,
    title: 'Bar Questions',
    accent:
      'bg-gradient-to-br from-amber-500/15 to-violet-600/10 text-amber-800 ring-1 ring-amber-500/20 dark:text-amber-300 dark:ring-amber-400/20',
    description:
      'Actual past Philippine Bar Examination questions with suggested answers for structured review.',
  },
];

const STANDARD_PILLARS = [
  {
    icon: Shield,
    title: 'Professional persona',
    body: 'Our engine acts as a senior legal editor, surfacing doctrine shifts and bar-relevant traps that generic tools often miss.',
  },
  {
    icon: FileCheck,
    title: 'Evidence-based',
    body: 'Classifications like new doctrine or abandonment require direct support from the decision text, not invention.',
  },
  {
    icon: ScanEye,
    title: 'Full decision context',
    body: 'Large-context analysis reads entire decisions together so reasoning stays coherent end to end.',
  },
  {
    icon: ListChecks,
    title: 'Structured ratio',
    body: 'Each issue is unpacked with clear reasoning chains so you keep the clinical language of the law.',
  },
];

const About = () => {
  return (
    <FeaturePageShell>
      <div className="animate-in fade-in relative pb-12 duration-700">
        <div
          className="pointer-events-none absolute -left-20 top-0 h-80 w-80 rounded-full bg-purple-500/25 blur-3xl dark:bg-purple-600/20"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute right-0 top-40 h-72 w-72 rounded-full bg-violet-500/20 blur-3xl dark:bg-fuchsia-600/15"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute bottom-20 left-1/3 h-64 w-96 rounded-full bg-indigo-400/15 blur-3xl dark:bg-indigo-500/10"
          aria-hidden
        />

        <div className="relative mx-auto w-full max-w-7xl space-y-5">
          <header className="relative overflow-hidden rounded-lg border border-lex bg-gradient-to-br from-white via-white to-slate-50/60 px-6 py-10 shadow-lg dark:border-lex dark:from-zinc-900 dark:via-zinc-900 dark:to-zinc-950 dark:shadow-[0_24px_80px_-28px_rgba(0,0,0,0.45)] sm:px-10">
            <div className="pointer-events-none absolute -right-12 -top-20 h-48 w-48 rounded-full bg-gradient-to-br from-purple-400/35 to-fuchsia-500/25 blur-2xl" />
            <div className="pointer-events-none absolute bottom-0 left-1/4 h-28 w-56 rounded-full bg-violet-400/15 blur-2xl" />
            <div className="relative flex flex-col gap-4">
              <div className="flex max-w-2xl flex-col gap-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:gap-4">
                  <div
                    className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-purple-600 to-violet-600 text-white shadow-lg shadow-purple-600/35"
                    aria-hidden
                  >
                    <Scale className="h-7 w-7" strokeWidth={2} />
                  </div>
                  <div className="min-w-0 flex-1 space-y-2 text-left">
                    <h1 className="text-3xl font-bold tracking-tight text-black dark:text-white sm:text-4xl">
                      Your Legal Companion
                    </h1>
                    <p className="text-xs font-bold uppercase tracking-wider text-purple-700 dark:text-purple-300">
                      Philippine law focus
                    </p>
                    <p className="text-sm text-slate-500 dark:text-slate-400">Official sources first, always.</p>
                  </div>
                </div>
                <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400 sm:text-base">
                  Built for law students, teachers, bar candidates, and practitioners: codals, past bar questions,
                  Supreme Court materials, and study tools in one purple-tinted glass workspace.
                </p>
              </div>
            </div>
          </header>

          <div className="grid grid-cols-1 items-stretch gap-4 lg:grid-cols-12 lg:gap-5">
            <div className="flex min-h-0 flex-col lg:col-span-7 lg:h-full">
              <section className="relative flex h-full min-h-0 flex-col overflow-hidden rounded-lg border border-lex bg-white p-6 shadow-xl sm:p-8 dark:border-lex dark:bg-zinc-900">
                <div className="pointer-events-none absolute right-0 top-0 h-32 w-32 rounded-full bg-purple-500/10 blur-2xl" />
                <h2 className="relative text-lg font-bold text-black dark:text-white sm:text-xl">
                  What you are using
                </h2>
                <p className="relative mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                  LexMatePH is built for more than bar review alone. Explore codals, past bar questions, Supreme Court
                  materials, and study aids together without hopping between siloed sites.
                </p>
                <ul className="relative mt-3 space-y-1.5 text-sm text-slate-600 dark:text-slate-400">
                  <li className="flex gap-2.5 rounded-xl border border-lex bg-white p-3 shadow-sm dark:border-lex dark:bg-zinc-800/60">
                    <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-purple-600/15 text-purple-700 dark:text-purple-300">
                      <Book className="h-3.5 w-3.5" />
                    </span>
                    <span>
                      <span className="font-semibold text-slate-800 dark:text-slate-200">Bar Questions</span> are
                      actual past Philippine Bar Examination questions, with suggested answers to support your review.
                    </span>
                  </li>
                  <li className="flex gap-2.5 rounded-xl border border-lex bg-white p-3 shadow-sm dark:border-lex dark:bg-zinc-800/60">
                    <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-violet-600/15 text-violet-700 dark:text-violet-300">
                      <Gavel className="h-3.5 w-3.5" />
                    </span>
                    <span>
                      <span className="font-semibold text-slate-800 dark:text-slate-200">Case digests</span> and
                      related summaries may be produced or assisted by AI. Use them for quick orientation only—read the
                      full decisions and verify against official reporters and current law.
                    </span>
                  </li>
                </ul>
                <div className="min-h-3 flex-1" aria-hidden />
                <div className="relative mt-3 rounded-2xl border border-amber-200/40 bg-amber-50/50 p-4 text-xs leading-relaxed text-amber-950/90 backdrop-blur-sm dark:border-amber-500/20 dark:bg-amber-950/20 dark:text-amber-100/90">
                  <strong className="font-bold">Disclaimer:</strong> Content is for education and research, not legal
                  advice. Verify critical points with primary sources, current jurisprudence, and applicable statutes.
                  LexMatePH does not replace professional judgment or counsel.
                </div>
              </section>
            </div>

            <aside className="flex min-h-0 flex-col lg:col-span-5 lg:h-full">
              <section className="relative flex h-full min-h-0 flex-col overflow-hidden rounded-lg border border-lex bg-white p-6 shadow-xl sm:p-8 dark:border-lex dark:bg-zinc-900">
                <div className="pointer-events-none absolute -left-8 bottom-0 h-40 w-40 rounded-full bg-violet-500/15 blur-2xl" />
                <div className="relative mb-3 flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-purple-600 to-indigo-600 text-white shadow-lg shadow-purple-600/30">
                    <Shield className="h-5 w-5" />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-black dark:text-white sm:text-lg">
                      The LexMatePH standard
                    </h2>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Engineered case digests</p>
                  </div>
                </div>
                <p className="relative mb-3 text-xs leading-relaxed text-slate-600 dark:text-slate-400 sm:text-sm">
                  Built for the Philippine bar: a high-fidelity pipeline so digests stay grounded in the text you
                  would cite in practice.
                </p>
                <div className="relative grid flex-1 grid-cols-1 content-start gap-1.5 sm:grid-cols-2">
                  {STANDARD_PILLARS.map(({ icon: Icon, title, body }) => (
                    <div
                      key={title}
                      className="rounded-2xl border border-lex bg-white p-4 shadow-sm transition hover:border-lex-strong hover:shadow-md dark:border-lex dark:bg-zinc-800/70 dark:hover:border-lex-strong dark:hover:bg-zinc-800"
                    >
                      <div className="mb-2 flex h-9 w-9 items-center justify-center rounded-lg bg-purple-500/15 text-purple-700 dark:text-purple-300">
                        <Icon className="h-4 w-4" strokeWidth={2} />
                      </div>
                      <h3 className="text-xs font-bold text-black dark:text-white">{title}</h3>
                      <p className="mt-1.5 text-[11px] leading-relaxed text-slate-600 dark:text-slate-400">{body}</p>
                    </div>
                  ))}
                </div>
              </section>
            </aside>
          </div>

          <section className="space-y-2">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white sm:text-2xl">Tools at a glance</h2>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-purple-600/80 dark:text-purple-400/90">
                Same app, one glass surface
              </p>
            </div>
            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 xl:grid-cols-3">
              {FEATURES.map(({ icon: Icon, title, description, accent }) => (
                <div
                  key={title}
                  className="group relative overflow-hidden rounded-2xl border border-lex bg-white p-5 shadow-md transition hover:-translate-y-0.5 hover:border-lex-strong hover:shadow-xl dark:border-lex dark:bg-zinc-900 dark:hover:border-lex-strong"
                >
                  <div className="pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full bg-purple-400/10 blur-2xl transition group-hover:bg-purple-400/20" />
                  <div
                    className={`relative mb-3 flex h-12 w-12 items-center justify-center rounded-xl ${accent}`}
                  >
                    <Icon className="h-6 w-6" strokeWidth={2} />
                  </div>
                  <h3 className="relative text-base font-bold text-black dark:text-white">{title}</h3>
                  <p className="relative mt-1.5 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                    {description}
                  </p>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </FeaturePageShell>
  );
};

export default About;
