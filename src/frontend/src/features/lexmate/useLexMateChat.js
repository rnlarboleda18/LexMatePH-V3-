import { useState, useCallback, useRef, useEffect } from 'react';
import { useAuth } from '@clerk/clerk-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';
const STORAGE_KEY = 'lx_lexmate_sessions';
const MAX_SESSIONS = 20;

function loadStoredSessions() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveStoredSessions(sessions) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  } catch {}
}

export function useLexMateChat() {
  const { getToken } = useAuth();
  const [sessions, setSessions]     = useState(() => loadStoredSessions());
  const [messages, setMessages]     = useState([]);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState(null);
  const [sessionId, setSessionId]   = useState(null);
  const [rateLimited, setRateLimited] = useState(false);
  const abortRef = useRef(null);

  // Persist current session to localStorage whenever messages or sessionId changes
  useEffect(() => {
    if (!sessionId || messages.length === 0) return;
    const title = messages.find(m => m.role === 'user')?.content?.slice(0, 60) || 'New conversation';
    setSessions(prev => {
      const existing = prev.find(s => s.id === sessionId);
      let next;
      if (existing) {
        next = prev.map(s =>
          s.id === sessionId ? { ...s, messages, title, updatedAt: Date.now() } : s
        );
      } else {
        const newSession = { id: sessionId, title, messages, updatedAt: Date.now() };
        next = [newSession, ...prev].slice(0, MAX_SESSIONS);
      }
      saveStoredSessions(next);
      return next;
    });
  }, [messages, sessionId]);

  const sendMessage = useCallback(async (question) => {
    if (!question.trim() || loading) return;

    setError(null);
    setRateLimited(false);

    const userMsg = { role: 'user', content: question, id: Date.now() };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const token = await getToken().catch(() => null);
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      abortRef.current = new AbortController();
      const resp = await fetch(`${API_BASE}/legal-chat`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ message: question, session_id: sessionId }),
        signal: abortRef.current.signal,
      });

      let data;
      try {
        data = await resp.json();
      } catch {
        data = {};
      }

      if (resp.status === 429) {
        setRateLimited(true);
        setError(data.error || 'Daily limit reached');
        setMessages(prev => prev.slice(0, -1));
        return;
      }

      if (!resp.ok) {
        throw new Error(data?.error || `Server error (${resp.status})`);
      }

      if (data.session_id && !sessionId) {
        setSessionId(data.session_id);
      }

      const assistantMsg = {
        role:       'assistant',
        content:    data.answer,
        citations:  data.citations || [],
        sources:    data.sources || [],
        intent:     data.intent,
        modelUsed:  data.model_used,
        cached:     data.cached || false,
        warning:    data.warning,
        id:         Date.now() + 1,
      };
      setMessages(prev => [...prev, assistantMsg]);

    } catch (err) {
      if (err.name === 'AbortError') return;
      setError(err.message || 'Something went wrong. Please try again.');
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  }, [loading, sessionId, getToken]);

  const clearSession = useCallback(async () => {
    if (sessionId) {
      fetch(`${API_BASE}/legal-chat-clear`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      }).catch(() => {});
    }
    setMessages([]);
    setSessionId(null);
    setError(null);
    setRateLimited(false);
  }, [sessionId]);

  const loadSession = useCallback((session) => {
    setMessages(session.messages || []);
    setSessionId(session.id);
    setError(null);
    setRateLimited(false);
  }, []);

  const deleteSession = useCallback((sid) => {
    setSessions(prev => {
      const next = prev.filter(s => s.id !== sid);
      saveStoredSessions(next);
      return next;
    });
    if (sid === sessionId) {
      setMessages([]);
      setSessionId(null);
      setError(null);
    }
  }, [sessionId]);

  const cancelRequest = useCallback(() => {
    abortRef.current?.abort();
    setLoading(false);
  }, []);

  return {
    messages, loading, error, sessionId, sessions,
    rateLimited, sendMessage, clearSession, loadSession, deleteSession, cancelRequest,
  };
}
