import React from 'react';
import { Link } from 'react-router-dom';
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
  FileText,
} from 'lucide-react';
import FeaturePageShell from './FeaturePageShell';
import { CHROME_INTERACTIVE_TILE_HOVER } from '../utils/filterChromeClasses';

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

        <div className="relative mx-auto w-full max-w-7xl space-y-tile">
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
                  <div className="min-w-0 flex-1 text-left">
                    <h1 className="text-3xl font-bold tracking-tight text-black dark:text-white sm:text-4xl">
                      Your Legal Companion
                    </h1>
                  </div>
                </div>
                <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400 sm:text-base">
                  Built for law students, teachers, bar candidates, and practitioners: codals, past bar questions,
                  Supreme Court materials, and study tools in one purple-tinted glass workspace.
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-500">
                  Official Judiciary RSS and social embeds (SC news) live on the{' '}
                  <Link to="/updates" className="font-semibold text-indigo-600 underline-offset-2 hover:underline dark:text-indigo-400">
                    Updates
                  </Link>{' '}
                  page.
                </p>
              </div>
            </div>
          </header>

          <div className="grid grid-cols-1 items-stretch gap-tile lg:grid-cols-12">
            <div className="flex min-h-0 flex-col lg:col-span-7 lg:h-full">
              <section className="relative flex h-full min-h-0 flex-col overflow-hidden rounded-lg border border-lex bg-white p-6 shadow-xl sm:p-8 dark:border-lex dark:bg-zinc-900">
                <div className="pointer-events-none absolute right-0 top-0 h-32 w-32 rounded-full bg-purple-500/10 blur-2xl" />
                <h2 className="relative shrink-0 text-lg font-bold text-black dark:text-white sm:text-xl">
                  What you are using
                </h2>
                <p className="relative mt-2 shrink-0 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                  LexMatePH is built for more than bar review alone. Explore codals, past bar questions, Supreme Court
                  materials, and study aids together without hopping between siloed sites.
                </p>
                <ul className="relative mt-3 shrink-0 space-y-1.5 text-sm text-slate-600 dark:text-slate-400">
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
                <div className="relative mt-3 flex min-h-0 flex-1 flex-col justify-center overflow-auto rounded-2xl border border-amber-200/40 bg-amber-50/50 px-5 py-6 text-sm leading-relaxed text-amber-950/90 backdrop-blur-sm sm:px-6 sm:py-8 sm:text-base sm:leading-relaxed dark:border-amber-500/20 dark:bg-amber-950/20 dark:text-amber-100/90">
                  <p className="max-w-none text-pretty">
                    <strong className="text-base font-bold text-amber-950 sm:text-lg dark:text-amber-50">
                      Disclaimer:
                    </strong>{' '}
                    Content is for education and research, not legal advice. Verify critical points with primary
                    sources, current jurisprudence, and applicable statutes. LexMatePH does not replace professional
                    judgment or counsel.
                  </p>
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
                <div className="relative grid flex-1 grid-cols-1 content-start gap-tile sm:grid-cols-2">
                  {STANDARD_PILLARS.map(({ icon: Icon, title, body }) => (
                    <div
                      key={title}
                      className={`rounded-2xl border border-lex bg-white p-4 shadow-sm dark:border-lex dark:bg-zinc-800/70 dark:hover:bg-zinc-800 ${CHROME_INTERACTIVE_TILE_HOVER}`}
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
            <h2 className="text-xl font-bold text-slate-900 dark:text-white sm:text-2xl">Tools at a glance</h2>
            <div className="grid grid-cols-1 gap-tile sm:grid-cols-2 xl:grid-cols-3">
              {FEATURES.map(({ icon: Icon, title, description, accent }) => (
                <div
                  key={title}
                  className={`group relative overflow-hidden rounded-2xl border border-lex bg-white p-5 shadow-md dark:border-lex dark:bg-zinc-900 ${CHROME_INTERACTIVE_TILE_HOVER}`}
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

          <section
            id="legal-terms"
            className="relative scroll-mt-6 overflow-hidden rounded-lg border border-lex bg-white p-6 shadow-xl sm:p-8 lg:p-10 dark:border-lex dark:bg-zinc-900"
            aria-labelledby="legal-terms-heading"
          >
            <div
              className="pointer-events-none absolute -right-8 top-0 h-40 w-40 rounded-full bg-slate-400/10 blur-3xl dark:bg-slate-500/10"
              aria-hidden
            />
            <div className="pointer-events-none absolute bottom-0 left-0 h-32 w-64 rounded-full bg-violet-500/10 blur-3xl" aria-hidden />

            <div className="relative">
              <div className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-start sm:gap-4">
                <div
                  className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-slate-800 text-white shadow-lg dark:bg-slate-700"
                  aria-hidden
                >
                  <FileText className="h-6 w-6" strokeWidth={2} />
                </div>
                <div className="min-w-0">
                  <h2
                    id="legal-terms-heading"
                    className="text-xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-2xl"
                  >
                    Legal Information &amp; Terms of Use
                  </h2>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    Please read this page carefully. It governs your use of LexMatePH and related notices.
                  </p>
                </div>
              </div>

              <ol className="list-none space-y-10 p-0">
                <li className="m-0">
                  <h3 className="text-base font-bold text-slate-900 dark:text-white sm:text-lg">
                    <span className="mr-2 text-violet-600 dark:text-violet-400">1.</span>
                    Intellectual Property &amp; Copyright Notice
                  </h3>
                  <p className="mt-3 text-sm font-semibold text-slate-800 dark:text-slate-200">
                    © 2026 Lexfluxion Technologies Inc. All Rights Reserved.
                  </p>
                  <p className="mt-3 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                    The LexMatePH application, including its design, the LexMatePH standard pipeline, user interface,
                    software code, branding, and original mock bar examination questions, is the exclusive property of
                    Lexfluxion Technologies Inc. and is protected by Philippine and international copyright laws.
                  </p>
                  <div className="mt-4 rounded-xl border border-slate-200/80 bg-slate-50/80 p-4 dark:border-slate-600/50 dark:bg-slate-800/50">
                    <h4 className="text-xs font-bold uppercase tracking-wide text-slate-800 dark:text-slate-200">
                      Public domain materials
                    </h4>
                    <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                      This application contains public legal records, including but not limited to: Republic Acts,
                      statutes, and Supreme Court decisions. These specific materials are part of the public domain and
                      are not subject to copyright by Lexfluxion Technologies Inc. Our use of these materials is for
                      educational and review purposes.
                    </p>
                  </div>
                </li>

                <li className="m-0">
                  <h3 className="text-base font-bold text-slate-900 dark:text-white sm:text-lg">
                    <span className="mr-2 text-violet-600 dark:text-violet-400">2.</span>
                    AI-Generated Case Digests &amp; the LexMatePH standard
                  </h3>
                  <div className="mt-4 space-y-4">
                    <div>
                      <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Our engineering commitment</h4>
                      <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                        Case digests within this application are processed using the proprietary LexMatePH standard.
                        This is a high-fidelity pipeline engineered to ensure digests stay grounded in the actual text
                        you would cite in practice. Our large-context engine analyzes every decision with literal
                        fidelity to official sources, unpacking issues with clear reasoning chains and maintaining the
                        clinical language of the law.
                      </p>
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                        Disclaimer regarding AI and verification
                      </h4>
                      <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                        While the LexMatePH pipeline is built for precision, the generation of digests is still assisted
                        by artificial intelligence (AI). Legal doctrines are complex, and AI-generated outputs, even
                        within our high-fidelity pipeline, may occasionally misinterpret nuance. Users are reminded of
                        their professional duty to verify any AI-assisted digest against the official full text of the
                        Supreme Court decision. LexMatePH is an advanced review aid, not a substitute for the Official
                        Gazette.
                      </p>
                    </div>
                  </div>
                </li>

                <li className="m-0">
                  <h3 className="text-base font-bold text-slate-900 dark:text-white sm:text-lg">
                    <span className="mr-2 text-violet-600 dark:text-violet-400">3.</span>
                    General disclaimers &amp; professional use
                  </h3>
                  <div className="mt-4 space-y-4 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                    <p>
                      <strong className="font-semibold text-slate-800 dark:text-slate-200">Not legal advice. </strong>
                      The content provided by LexMatePH is for study, education, and research purposes only. It does not
                      constitute legal advice and does not create a lawyer–client relationship.
                    </p>
                    <p>
                      <strong className="font-semibold text-slate-800 dark:text-slate-200">Accuracy of information. </strong>
                      LexMatePH strives to be the standard for precision. However, legal doctrines and statutes are
                      dynamic and subject to change. Lexfluxion Technologies Inc. does not guarantee that materials are
                      free of errors and shall not be held liable for any academic or legal consequences resulting from
                      the use of this tool. Users are encouraged to cross-reference with authoritative sources such as
                      the{' '}
                      <a
                        href="https://elibrary.judiciary.gov.ph/"
                        target="_blank"
                        rel="noreferrer"
                        className="font-medium text-violet-600 underline decoration-violet-500/30 underline-offset-2 hover:decoration-violet-500 dark:text-violet-400"
                      >
                        Supreme Court E-Library
                      </a>
                      .
                    </p>
                  </div>
                </li>

                <li className="m-0">
                  <h3 className="text-base font-bold text-slate-900 dark:text-white sm:text-lg">
                    <span className="mr-2 text-violet-600 dark:text-violet-400">4.</span>
                    Privacy notice &amp; data handling
                  </h3>
                  <p className="mt-3 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                    Lexfluxion Technologies Inc. is committed to protecting your data in compliance with the Data
                    Privacy Act of 2012.
                  </p>
                  <div className="mt-5 space-y-5 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                    <div>
                      <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                        Authentication &amp; registration
                      </h4>
                      <p className="mt-2">
                        We use <strong className="font-medium text-slate-800 dark:text-slate-200">Clerk</strong> as our
                        third-party identity provider. When you register, your email and login credentials are managed
                        by Clerk to help ensure industry-standard security and encryption. You can review Clerk’s
                        privacy standards on{' '}
                        <a
                          href="https://clerk.com/legal/privacy"
                          target="_blank"
                          rel="noreferrer"
                          className="font-medium text-violet-600 underline decoration-violet-500/30 underline-offset-2 hover:decoration-violet-500 dark:text-violet-400"
                        >
                          Clerk’s official site
                        </a>
                        .
                      </p>
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Academic data</h4>
                      <p className="mt-2">
                        Your mock bar scores and study progress are stored securely in our Azure-hosted database and are
                        used solely for your personal performance analytics.
                      </p>
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Data security</h4>
                      <p className="mt-2">
                        We do not store your raw passwords. Your data will not be shared with third parties for
                        marketing purposes without your explicit consent.
                      </p>
                    </div>
                  </div>
                  <div className="mt-6 rounded-xl border border-violet-200/60 bg-violet-50/50 p-4 dark:border-violet-500/20 dark:bg-violet-950/20">
                    <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Contact &amp; support</h4>
                    <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                      For legal inquiries, data privacy concerns, or technical support, please contact us at:
                    </p>
                    <a
                      href="mailto:fluxiontechinc@gmail.com"
                      className="mt-2 inline-block text-sm font-semibold text-violet-600 underline decoration-violet-500/30 underline-offset-2 hover:decoration-violet-500 dark:text-violet-400"
                    >
                      fluxiontechinc@gmail.com
                    </a>
                  </div>
                </li>
              </ol>
            </div>
          </section>
        </div>
      </div>
    </FeaturePageShell>
  );
};

export default About;
