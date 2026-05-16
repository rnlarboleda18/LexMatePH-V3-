import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { MessageSquare, Trash2, Plus, Clock, X } from 'lucide-react';
import { useLexMateChat } from './useLexMateChat';
import LexMateMessage from './LexMateMessage';

const SUGGESTED_QUESTIONS = [
  'What is the leading case on psychological incapacity under Article 36?',
  'What are the elements of murder under the Revised Penal Code?',
  'What constitutes constructive dismissal under Philippine labor law?',
  'What is the difference between legal separation and annulment?',
  'What are the requisites of a valid contract under the Civil Code?',
];

function formatSessionTime(ts) {
  const diffDays = Math.floor((Date.now() - ts) / 86400000);
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  return new Date(ts).toLocaleDateString('en-PH', { month: 'short', day: 'numeric' });
}

function SessionsList({ sessions, currentSessionId, onSelect, onDelete, onNew }) {
  return (
    <div className="flex flex-col h-full bg-gray-50 border-r border-gray-200 dark:bg-zinc-900 dark:border-zinc-700">
      <div className="p-3 border-b border-gray-200 dark:border-zinc-700 shrink-0">
        <button
          onClick={onNew}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          <Plus size={15} />
          New Chat
        </button>
      </div>
      <div className="flex-1 overflow-y-auto py-1">
        {sessions.length === 0 ? (
          <div className="px-4 py-8 text-center">
            <Clock size={22} className="mx-auto mb-2 text-gray-300 dark:text-zinc-600" />
            <p className="text-xs text-gray-400 dark:text-zinc-500">No past sessions yet</p>
          </div>
        ) : (
          sessions.map(session => (
            <div
              key={session.id}
              className={`group flex items-start gap-2 px-2 py-2 mx-1 rounded-lg cursor-pointer transition-colors ${
                session.id === currentSessionId
                  ? 'bg-indigo-50 dark:bg-indigo-950/40'
                  : 'hover:bg-gray-100 dark:hover:bg-zinc-800'
              }`}
              onClick={() => onSelect(session)}
            >
              <MessageSquare
                size={13}
                className={`mt-0.5 shrink-0 ${session.id === currentSessionId ? 'text-indigo-500' : 'text-gray-400 dark:text-zinc-500'}`}
              />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-gray-800 dark:text-zinc-200 line-clamp-2 leading-snug">
                  {session.title}
                </p>
                <p className="text-[10px] text-gray-400 dark:text-zinc-500 mt-0.5">
                  {formatSessionTime(session.updatedAt)}
                </p>
              </div>
              <button
                onClick={e => { e.stopPropagation(); onDelete(session.id); }}
                className="shrink-0 opacity-0 group-hover:opacity-100 p-0.5 rounded text-gray-400 hover:text-red-500 transition-all"
                title="Delete session"
              >
                <Trash2 size={12} />
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default function LexMateApp({ onClose }) {
  const { isSignedIn } = useAuth();
  const {
    messages, loading, error, rateLimited, sessionId, sessions,
    sendMessage, clearSession, cancelRequest, loadSession, deleteSession,
  } = useLexMateChat();

  const [input, setInput]               = useState('');
  const [showMobileSessions, setShowMobileSessions] = useState(false);
  const bottomRef                        = useRef(null);
  const inputRef                         = useRef(null);

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

  const handleNewChat = () => {
    clearSession();
    setShowMobileSessions(false);
  };

  const handleSelectSession = (session) => {
    loadSession(session);
    setShowMobileSessions(false);
  };

  const sessionPanel = (
    <SessionsList
      sessions={sessions}
      currentSessionId={sessionId}
      onSelect={handleSelectSession}
      onDelete={deleteSession}
      onNew={handleNewChat}
    />
  );

  return (
    <div className="flex h-full bg-gray-50 dark:bg-zinc-950">
      {/* Sessions panel — desktop only */}
      <div className="hidden lg:flex lg:w-56 xl:w-64 shrink-0 flex-col">
        {sessionPanel}
      </div>

      {/* Mobile sessions drawer */}
      {showMobileSessions && (
        <div
          className="lg:hidden fixed inset-0 z-50 bg-black/50"
          onClick={() => setShowMobileSessions(false)}
        >
          <div
            className="absolute left-0 top-0 bottom-0 w-72 max-w-[85vw] bg-white dark:bg-zinc-900 shadow-xl flex flex-col"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-zinc-700 shrink-0">
              <span className="text-sm font-semibold text-gray-800 dark:text-zinc-100">Chat History</span>
              <button
                onClick={() => setShowMobileSessions(false)}
                className="p-1 rounded-lg text-gray-400 hover:bg-gray-100 dark:hover:bg-zinc-800 transition-colors"
              >
                <X size={16} />
              </button>
            </div>
            <div className="flex-1 min-h-0">
              {sessionPanel}
            </div>
          </div>
        </div>
      )}

      {/* Main chat area */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 bg-white dark:bg-zinc-900 border-b border-gray-200 dark:border-zinc-700 shrink-0">
          <div className="flex items-center gap-2">
            {/* Mobile: history button */}
            <button
              onClick={() => setShowMobileSessions(true)}
              className="lg:hidden p-1.5 rounded-lg text-gray-500 dark:text-zinc-400 hover:bg-gray-100 dark:hover:bg-zinc-800 transition-colors"
              title="Chat history"
            >
              <Clock size={17} />
            </button>
            <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-white font-bold text-sm shrink-0">
              L
            </div>
            <div>
              <h2 className="font-semibold text-gray-900 dark:text-zinc-100 text-sm">LexMate Legal Expert</h2>
              <p className="text-xs text-gray-400 dark:text-zinc-500">Powered by Gemini 2.5 · Philippine Law</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {messages.length > 0 && (
              <button
                onClick={clearSession}
                className="text-xs text-gray-400 hover:text-gray-600 dark:text-zinc-500 dark:hover:text-zinc-300 px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-zinc-800"
              >
                New chat
              </button>
            )}
            {onClose && (
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 dark:text-zinc-500 dark:hover:text-zinc-300 p-1 rounded hover:bg-gray-100 dark:hover:bg-zinc-800"
              >
                ✕
              </button>
            )}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {messages.length === 0 && (
            <div className="space-y-6 py-4">
              <div className="text-center space-y-2">
                <div className="w-16 h-16 rounded-full bg-indigo-100 dark:bg-indigo-950 flex items-center justify-center mx-auto">
                  <span className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">L</span>
                </div>
                <h3 className="font-semibold text-gray-800 dark:text-zinc-100">LexMate Legal Expert AI</h3>
                <p className="text-sm text-gray-500 dark:text-zinc-400 max-w-sm mx-auto">
                  Ask any question about Philippine law — cases, statutes, doctrines.
                  I'll cite my sources from the LexMatePH legal corpus.
                </p>
              </div>

              <div className="space-y-2 max-w-lg mx-auto">
                <p className="text-xs font-medium text-gray-400 dark:text-zinc-500 uppercase tracking-wide">Try asking</p>
                {SUGGESTED_QUESTIONS.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => handleSuggest(q)}
                    className="w-full text-left text-sm bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-700 rounded-xl px-4 py-2.5 hover:border-indigo-300 hover:bg-indigo-50 dark:hover:bg-indigo-950/30 transition-colors text-gray-700 dark:text-zinc-300"
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

          {loading && (
            <div className="flex justify-start">
              <div className="bg-white dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
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
        <div className="shrink-0 px-4 py-3 bg-white dark:bg-zinc-900 border-t border-gray-200 dark:border-zinc-700">
          <div className="flex gap-2 items-end">
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a Philippine legal question..."
              rows={1}
              disabled={loading}
              className="flex-1 resize-none rounded-xl border border-gray-300 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100 dark:placeholder-zinc-500 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:opacity-50 min-h-[40px] max-h-[120px] leading-relaxed"
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
          <p className="text-xs text-gray-400 dark:text-zinc-500 mt-1.5 px-1">
            LexMate cites sources from the LexMatePH corpus. Always verify with primary sources.
          </p>
        </div>
      </div>
    </div>
  );
}
