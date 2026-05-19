import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { useLexMateChat } from './useLexMateChat';
import LexMateMessage from './LexMateMessage';
import FeaturePageShell from '../../components/FeaturePageShell';

const SUGGESTED_QUESTIONS = [
  'What is the leading case on psychological incapacity under Article 36?',
  'What are the elements of murder under the Revised Penal Code?',
  'What constitutes constructive dismissal under Philippine labor law?',
  'What is the difference between legal separation and annulment?',
  'What are the requisites of a valid contract under the Civil Code?',
];

export default function LexMateApp({ onClose }) {
  const { isSignedIn } = useAuth();
  const {
    messages, loading, error, rateLimited,
    sendMessage, clearSession, cancelRequest,
  } = useLexMateChat();

  const [input, setInput]     = useState('');
  const bottomRef             = useRef(null);
  const inputRef              = useRef(null);

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSend = () => {
    const q = input.trim();
    if (!q || loading) return;
    setInput('');
    sendMessage(q);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSuggest = (q) => {
    setInput(q);
    inputRef.current?.focus();
  };

  return (
    <FeaturePageShell>
      <div className="animate-in fade-in relative pb-12 duration-700 font-sans text-gray-900 dark:text-gray-100">
        <div className="pointer-events-none absolute -left-20 top-0 h-80 w-80 rounded-full bg-purple-500/25 blur-3xl dark:bg-purple-600/20" aria-hidden />
        <div className="pointer-events-none absolute right-0 top-40 h-72 w-72 rounded-full bg-violet-500/20 blur-3xl dark:bg-fuchsia-600/15" aria-hidden />
        <div className="pointer-events-none absolute bottom-20 left-1/3 h-64 w-96 rounded-full bg-indigo-400/15 blur-3xl dark:bg-indigo-500/10" aria-hidden />
        
        <div className="relative mx-auto w-full max-w-7xl space-y-tile">
          <div className="flex flex-col overflow-hidden rounded-2xl border border-lex bg-white/90 shadow-2xl backdrop-blur-sm dark:border-lex dark:bg-zinc-900/90" style={{ height: 'calc(100vh - 120px)' }}>
            {/* Header */}
            <div className="flex shrink-0 items-center justify-between border-b border-lex px-4 py-3 dark:border-lex">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-white font-bold text-sm">
            L
          </div>
          <div>
            <h2 className="text-sm font-bold tracking-tight text-gray-900 dark:text-white">LexMate Legal Expert</h2>
            <p className="text-xs text-gray-500 dark:text-gray-400">Powered by Gemini 2.5 · Philippine Law</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <button
              onClick={clearSession}
              className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-100"
            >
              New chat
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-zinc-800 dark:hover:text-gray-300"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4 sm:px-6">
        {messages.length === 0 && (
          <div className="space-y-6 py-4">
            <div className="text-center space-y-2">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-indigo-100 dark:bg-indigo-500/20">
                <span className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">L</span>
              </div>
              <h3 className="font-bold tracking-tight text-gray-900 dark:text-white">LexMate Legal Expert AI</h3>
              <p className="mx-auto max-w-sm text-sm text-gray-600 dark:text-gray-400">
                Ask any question about Philippine law — cases, statutes, doctrines.
                I'll cite my sources from the LexMatePH legal corpus.
              </p>
            </div>

            {/* Suggested questions */}
            <div className="mx-auto max-w-lg space-y-2">
              <p className="text-xs font-bold uppercase tracking-wide text-gray-500 dark:text-gray-400">Try asking</p>
              {SUGGESTED_QUESTIONS.map((q, i) => (
                <button
                  key={i}
                  onClick={() => handleSuggest(q)}
                  className="w-full rounded-xl border border-lex bg-white px-4 py-2.5 text-left text-sm text-gray-700 transition-colors hover:border-indigo-300 hover:bg-indigo-50 dark:border-lex dark:bg-zinc-800/80 dark:text-gray-200 dark:hover:border-indigo-500/30 dark:hover:bg-indigo-500/10"
                >
                  {q}
                </button>
              ))}
            </div>

            {!isSignedIn && (
              <p className="text-center text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-4 py-2 max-w-sm mx-auto">
                Sign in to unlock more questions per day and access to Gemini 2.5 Pro analysis.
              </p>
            )}
          </div>
        )}

        {messages.map(msg => (
          <LexMateMessage key={msg.id} message={msg} />
        ))}

        {/* Loading indicator */}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-full bg-indigo-600 flex items-center justify-center text-white text-xs font-bold">L</div>
                <div className="flex gap-1">
                  {[0, 1, 2].map(i => (
                    <span
                      key={i}
                      className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce"
                      style={{ animationDelay: `${i * 150}ms` }}
                    />
                  ))}
                </div>
                <button
                  onClick={cancelRequest}
                  className="text-xs text-gray-400 hover:text-gray-600 ml-2"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className={`text-sm px-4 py-3 rounded-xl border text-center ${
            rateLimited
              ? 'bg-amber-50 border-amber-200 text-amber-700'
              : 'bg-red-50 border-red-200 text-red-700'
          }`}>
            {rateLimited ? (
              <>
                {error} · <a href="/pricing" className="underline font-medium">Upgrade to Amicus</a> for unlimited questions.
              </>
            ) : error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

        {/* Input */}
        <div className="shrink-0 border-t border-lex bg-white px-4 py-3 dark:border-lex dark:bg-zinc-900 sm:px-6">
          <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a Philippine legal question..."
            rows={1}
              disabled={loading}
              className="min-h-[40px] max-h-[120px] flex-1 resize-none rounded-xl border border-lex-strong bg-white px-4 py-2.5 text-sm leading-relaxed text-gray-900 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/25 disabled:opacity-50 dark:border-lex-strong dark:bg-zinc-800 dark:text-gray-100"
              style={{ height: 'auto' }}
            onInput={e => {
              e.target.style.height = 'auto';
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
            }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="shrink-0 w-10 h-10 rounded-xl bg-indigo-600 text-white flex items-center justify-center hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          </button>
        </div>
          <p className="mt-1.5 px-1 text-xs text-gray-500 dark:text-gray-400">
            LexMate cites sources from the LexMatePH corpus. Always verify with primary sources.
          </p>
        </div>
          </div>
        </div>
      </div>
    </FeaturePageShell>
  );
}
