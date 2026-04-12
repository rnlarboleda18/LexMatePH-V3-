import { useState, useEffect, useCallback } from 'react';
import { lexCache } from '../utils/cache';
import { buildBalancedQuestions } from '../utils/barQuestionsTransform';
import { apiUrl } from '../utils/apiUrl';

const QUESTIONS_CACHE_KEY = 'bar_questions_limit5000';

/**
 * Fetches bar exam questions via IndexedDB SWR.
 * Cached data is delivered first; network refresh runs in the background.
 */
export function useBarQuestions() {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    lexCache
      .swr(
        'questions',
        QUESTIONS_CACHE_KEY,
        async () => {
          const response = await fetch(apiUrl('/api/questions?limit=5000'));
          if (!response.ok) throw new Error('Failed to fetch questions');
          return response.json();
        },
        (data) => {
          if (cancelled) return;
          setQuestions(buildBalancedQuestions(Array.isArray(data) ? data : []));
          setLoading(false);
        }
      )
      .catch((err) => {
        if (!cancelled) {
          setError(err.message || 'Failed to load questions');
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const retry = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const response = await fetch(apiUrl('/api/questions?limit=5000'));
      if (!response.ok) throw new Error('Failed to fetch questions');
      const data = await response.json();
      await lexCache.set('questions', QUESTIONS_CACHE_KEY, data);
      setQuestions(buildBalancedQuestions(data));
    } catch (err) {
      setError(err.message || 'Failed to fetch questions');
    } finally {
      setLoading(false);
    }
  }, []);

  return { questions, loading, error, retry };
}
