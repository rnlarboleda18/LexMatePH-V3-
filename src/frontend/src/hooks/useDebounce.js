import { useState, useEffect } from 'react';

/**
 * Returns a debounced version of `value` that only updates after
 * `delay` ms have elapsed with no further changes.
 *
 * Useful for throttling API calls and expensive client-side filters
 * triggered by keystrokes.
 *
 * @param {*}      value  The value to debounce.
 * @param {number} delay  Debounce delay in ms (default 300).
 * @returns The debounced value.
 */
export function useDebounce(value, delay = 300) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}
