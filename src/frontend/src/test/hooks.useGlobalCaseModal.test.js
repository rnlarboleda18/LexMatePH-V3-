import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useGlobalCaseModal } from '../hooks/useGlobalCaseModal';

const CASE_A = { id: 101, title: 'Case A' };
const CASE_B = { id: 202, title: 'Case B' };

describe('useGlobalCaseModal', () => {
  it('opens a case', () => {
    const { result } = renderHook(() => useGlobalCaseModal());
    act(() => result.current.selectCase(CASE_A));
    expect(result.current.selectedCase).toEqual(CASE_A);
  });

  it('closes the modal', () => {
    const { result } = renderHook(() => useGlobalCaseModal());
    act(() => result.current.selectCase(CASE_A));
    act(() => result.current.closeModal());
    expect(result.current.selectedCase).toBeNull();
  });

  it('allows opening a different case immediately after closing', () => {
    const { result } = renderHook(() => useGlobalCaseModal());
    act(() => result.current.selectCase(CASE_A));
    act(() => result.current.closeModal());
    act(() => result.current.selectCase(CASE_B));
    expect(result.current.selectedCase).toEqual(CASE_B);
  });

  it('suppresses reopening the same case within 750 ms', () => {
    const { result } = renderHook(() => useGlobalCaseModal());
    act(() => result.current.selectCase(CASE_A));
    act(() => result.current.closeModal());
    act(() => result.current.selectCase(CASE_A)); // same case — should be suppressed
    expect(result.current.selectedCase).toBeNull();
  });
});
