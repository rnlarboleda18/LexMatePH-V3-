import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';

// Mock the cache module before importing the hook
vi.mock('../utils/cache', () => ({
  lexCache: {
    swr: vi.fn((_store, _key, fetcher, onData) =>
      fetcher().then((data) => { onData(data); return data; })
    ),
    set: vi.fn(),
  },
}));

import { useBarQuestions } from '../hooks/useBarQuestions';

const MOCK_QUESTIONS = [
  { id: 1, subject: 'Civil Law', question: 'Q1', answer: 'A1', year: 2023 },
  { id: 2, subject: 'Criminal Law', question: 'Q2', answer: 'A2', year: 2022 },
];

describe('useBarQuestions', () => {
  beforeEach(() => {
    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => MOCK_QUESTIONS,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('delivers questions array after fetch completes', async () => {
    const { result } = renderHook(() => useBarQuestions());
    await waitFor(() => !result.current.loading, { timeout: 3000 });
    expect(Array.isArray(result.current.questions)).toBe(true);
  });

  it('sets error when fetch fails', async () => {
    vi.spyOn(global, 'fetch').mockRejectedValueOnce(new Error('Network error'));
    const { result } = renderHook(() => useBarQuestions());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBeTruthy();
  });
});
