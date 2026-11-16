/** Shared async data-loading hook with loading, error and refetch states. */

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../services/api";

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: ApiError | null;
  refetch: () => void;
  setData: (value: T | null) => void;
}

export function useAsync<T>(loader: () => Promise<T>, deps: unknown[] = []): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [tick, setTick] = useState(0);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    loaderRef
      .current()
      .then((value) => {
        if (active) setData(value);
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setError(
          reason instanceof ApiError
            ? reason
            : new ApiError("UNEXPECTED_ERROR", "An unexpected client error occurred."),
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const refetch = useCallback(() => setTick((value) => value + 1), []);

  return { data, loading, error, refetch, setData };
}

/** Poll a callback while `enabled` is true. */
export function usePolling(callback: () => void, intervalMs: number, enabled: boolean) {
  const callbackRef = useRef(callback);
  callbackRef.current = callback;

  useEffect(() => {
    if (!enabled) return;
    const handle = window.setInterval(() => callbackRef.current(), intervalMs);
    return () => window.clearInterval(handle);
  }, [enabled, intervalMs]);
}
