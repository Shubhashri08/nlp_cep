import { useCallback, useEffect, useRef, useState } from 'react';

export interface ApiState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
  setData: (d: T | null) => void;
}

/** Runs an async loader on mount / when deps change; exposes loading, error and reload. Ignores stale responses. */
export function useApi<T>(loader: () => Promise<T>, deps: unknown[] = [], enabled = true): ApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(enabled);
  const [tick, setTick] = useState(0);
  const seq = useRef(0);

  useEffect(() => {
    if (!enabled) { setLoading(false); return; }
    const id = ++seq.current;
    setLoading(true);
    setError(null);
    loader()
      .then((d) => { if (id === seq.current) setData(d); })
      .catch((e: Error) => { if (id === seq.current) setError(e.message || 'Request failed'); })
      .finally(() => { if (id === seq.current) setLoading(false); });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick, enabled]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading, reload, setData };
}

export function useDebounced<T>(value: T, ms = 400): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}
