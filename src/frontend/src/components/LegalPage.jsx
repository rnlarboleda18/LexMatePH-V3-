import React from 'react';
import { FileText } from 'lucide-react';

const T = 'text-[15px] sm:text-base leading-[1.65] text-slate-800 dark:text-slate-200';
const M = 'text-[15px] sm:text-base leading-[1.65] text-slate-600 dark:text-slate-300';

const LegalPage = () => {
  return (
    <article
      className="animate-in fade-in relative mx-auto w-full max-w-4xl pb-4 duration-500"
      id="lexmate-legal"
    >
      <header className="mb-8 sm:mb-10">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:gap-5">
          <div
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-slate-800 text-white shadow-md dark:bg-slate-700"
            aria-hidden
          >
            <FileText className="h-6 w-6" strokeWidth={2} />
          </div>
          <div className="min-w-0">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-3xl">
              Legal information &amp; terms of use
            </h1>
            <p className="mt-2 text-sm sm:text-base text-slate-600 dark:text-slate-400">
              Terms, privacy, and data notices for LexMatePH. You can share this page as{' '}
              <span className="whitespace-nowrap font-medium text-slate-800 dark:text-slate-200">
                https://www.lexmateph.com/legal
              </span>{' '}
              for Clerk and sign-up compliance.
            </p>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-500">
              This document may be updated. Lexfluxion Technologies Inc. publishes the current version at this address.
            </p>
          </div>
        </div>
      </header>

      <ol className="list-none space-y-10 sm:space-y-12 p-0">
        <li className="m-0">
          <h2 className="text-lg font-bold text-slate-900 dark:text-white sm:text-xl">
            <span className="mr-2 text-violet-600 dark:text-violet-400" aria-hidden>1.</span>
            Intellectual property &amp; copyright notice
          </h2>
          <p className={`${T} mt-3 font-semibold`}>© 2026 Lexfluxion Technologies Inc. All rights reserved.</p>
          <p className={`${M} mt-3`}>
            The LexMatePH application, including its design, the LexMatePH standard pipeline, user interface, software
            code, branding, and original mock bar examination questions, is the exclusive property of Lexfluxion
            Technologies Inc. and is protected by Philippine and international copyright laws.
          </p>
          <div className="mt-4 rounded-xl border-2 border-slate-200/90 bg-slate-50/90 p-4 dark:border-slate-600/60 dark:bg-slate-800/60">
            <h3 className="text-xs font-bold uppercase tracking-wide text-slate-900 dark:text-slate-100">Public domain materials</h3>
            <p className={`${M} mt-2`}>
              This application contains public legal records, including but not limited to: Republic Acts, statutes, and
              Supreme Court decisions. These specific materials are part of the public domain and are not subject to
              copyright by Lexfluxion Technologies Inc. Our use of these materials is for educational and review
              purposes.
            </p>
          </div>
        </li>

        <li className="m-0">
          <h2 className="text-lg font-bold text-slate-900 dark:text-white sm:text-xl">
            <span className="mr-2 text-violet-600 dark:text-violet-400" aria-hidden>2.</span>
            AI-generated case digests &amp; the LexMatePH standard
          </h2>
          <div className="mt-4 space-y-5 text-slate-800 dark:text-slate-200">
            <div>
              <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 sm:text-lg">Our engineering commitment</h3>
              <p className={`${M} mt-2`}>
                Case digests within this application are processed using the proprietary LexMatePH standard. This is a
                high-fidelity pipeline engineered to ensure digests stay grounded in the actual text you would cite in
                practice. Our large-context engine analyzes every decision with literal fidelity to official sources,
                unpacking issues with clear reasoning chains and maintaining the clinical language of the law.
              </p>
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 sm:text-lg">Disclaimer regarding AI and verification</h3>
              <p className={`${M} mt-2`}>
                While the LexMatePH pipeline is built for precision, the generation of digests is still assisted by
                artificial intelligence (AI). Legal doctrines are complex, and AI-generated outputs, even within our
                high-fidelity pipeline, may occasionally misinterpret nuance. Users are reminded of their professional
                duty to verify any AI-assisted digest against the official full text of the Supreme Court decision.
                LexMatePH is an advanced review aid, not a substitute for the Official Gazette.
              </p>
            </div>
          </div>
        </li>

        <li className="m-0">
          <h2 className="text-lg font-bold text-slate-900 dark:text-white sm:text-xl">
            <span className="mr-2 text-violet-600 dark:text-violet-400" aria-hidden>3.</span>
            General disclaimers &amp; professional use
          </h2>
          <div className="mt-4 space-y-4 text-slate-800 dark:text-slate-200">
            <p className={M}>
              <strong className="font-semibold text-slate-900 dark:text-slate-100">Not legal advice. </strong>
              The content provided by LexMatePH is for study, education, and research purposes only. It does not
              constitute legal advice and does not create a lawyer–client relationship.
            </p>
            <p className={M}>
              <strong className="font-semibold text-slate-900 dark:text-slate-100">Accuracy of information. </strong>
              LexMatePH strives to be the standard for precision. However, legal doctrines and statutes are dynamic and
              subject to change. Lexfluxion Technologies Inc. does not guarantee that materials are free of errors and
              shall not be held liable for any academic or legal consequences resulting from the use of this tool.
              Users are encouraged to cross-reference with authoritative sources such as the{' '}
              <a
                href="https://elibrary.judiciary.gov.ph/"
                target="_blank"
                rel="noreferrer"
                className="font-medium text-violet-700 underline decoration-violet-500/50 underline-offset-[3px] hover:decoration-violet-600 dark:text-violet-400"
              >
                Supreme Court E-Library
              </a>
              .
            </p>
          </div>
        </li>

        <li className="m-0">
          <h2 className="text-lg font-bold text-slate-900 dark:text-white sm:text-xl">
            <span className="mr-2 text-violet-600 dark:text-violet-400" aria-hidden>4.</span>
            Privacy notice &amp; data handling
          </h2>
          <p className={`${M} mt-3`}>
            Lexfluxion Technologies Inc. is committed to protecting your data in compliance with the Data Privacy Act of
            2012.
          </p>
          <div className="mt-5 space-y-5 text-slate-800 dark:text-slate-200">
            <div>
              <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 sm:text-lg">Authentication &amp; registration</h3>
              <p className={`${M} mt-2`}>
                We use <strong className="font-medium text-slate-900 dark:text-slate-100">Clerk</strong> as our
                third-party identity provider. When you register, your email and login credentials are managed by Clerk
                to help ensure industry-standard security and encryption. You can review Clerk’s privacy standards on{' '}
                <a
                  href="https://clerk.com/legal/privacy"
                  target="_blank"
                  rel="noreferrer"
                  className="font-medium text-violet-700 underline decoration-violet-500/50 underline-offset-[3px] hover:decoration-violet-600 dark:text-violet-400"
                >
                  Clerk’s official site
                </a>
                .
              </p>
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 sm:text-lg">Academic data</h3>
              <p className={`${M} mt-2`}>
                Your mock bar scores and study progress are stored securely in our Azure-hosted database and are used
                solely for your personal performance analytics.
              </p>
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 sm:text-lg">Data security</h3>
              <p className={`${M} mt-2`}>
                We do not store your raw passwords. Your data will not be shared with third parties for marketing
                purposes without your explicit consent.
              </p>
            </div>
          </div>
          <div className="mt-6 rounded-xl border-2 border-violet-200/80 bg-violet-50/80 p-4 sm:p-5 dark:border-violet-500/30 dark:bg-violet-950/30">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100 sm:text-base">Contact &amp; support</h3>
            <p className={`${M} mt-2`}>
              For legal inquiries, data privacy concerns, or technical support, please contact us at:
            </p>
            <a
              href="mailto:fluxiontechinc@gmail.com"
              className="mt-2 inline-block text-base font-semibold text-violet-700 underline decoration-violet-500/50 underline-offset-[3px] hover:decoration-violet-600 dark:text-violet-400"
            >
              fluxiontechinc@gmail.com
            </a>
          </div>
        </li>
      </ol>
    </article>
  );
};

export default LegalPage;
