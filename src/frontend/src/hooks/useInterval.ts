/**
 * useInterval Hook for Polling
 */

import { useEffect, useRef } from 'react';

export function useInterval(callback: () => void, delay: number | null): void {
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (delay === null) return;

    const id = setInterval(() => savedCallback.current(), delay);
    return () => clearInterval(id);
  }, [delay]);
}

/**
 * usePolling Hook - Polls data at regular intervals
 */
export function usePolling(
  fetchFn: () => void | Promise<void>,
  intervalMs: number,
  enabled: boolean = true
): void {
  const fetchRef = useRef(fetchFn);

  useEffect(() => {
    fetchRef.current = fetchFn;
  }, [fetchFn]);

  useEffect(() => {
    if (!enabled) return;

    // Initial fetch
    fetchRef.current();

    const id = setInterval(() => {
      fetchRef.current();
    }, intervalMs);

    return () => clearInterval(id);
  }, [intervalMs, enabled]);
}
