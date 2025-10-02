/**
 * useDebounce Hook
 * Debounce a value to avoid excessive re-renders or API calls
 */

import { useEffect, useState } from 'react';

/**
 * Debounce a value by a specified delay
 * Useful for search inputs and other high-frequency updates
 */
export function useDebounce<T>(value: T, delay: number = 500): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}
