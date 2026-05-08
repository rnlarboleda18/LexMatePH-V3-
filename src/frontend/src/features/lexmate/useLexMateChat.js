import { useState, useCallback, useRef } from 'react';
import { useAuth } from '@clerk/clerk-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export function useLexMateChat() {
  const { getToken } = useAuth();
  const [messages, setMessages]     = useState([]);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState(null);
  const [sessionId, setSessionId]   = useState(null);
  const [rateLimited, setRateLimited] = useState(false);
  const abortRef = useRef(null);

  const sendMessage = useCallback(async (question) => {
    if (!question.trim() || loading) return;

    setError(null);
    setRateLimited(false);

    // Optimistically add user message
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
        setMessages(prev => prev.slice(0, -1)); // remove optimistic message
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

  const cancelRequest = useCallback(() => {
    abortRef.current?.abort();
    setLoading(false);
  }, []);

  return {
    messages, loading, error, sessionId,
    rateLimited, sendMessage, clearSession, cancelRequest,
  };
}
