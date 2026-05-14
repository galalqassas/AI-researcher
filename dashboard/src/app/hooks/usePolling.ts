import { useEffect, useRef } from 'react';

/**
 * Calls `callback` on a recurring interval while the document is visible.
 * Pauses when the tab is hidden, and instantly refreshes when it returns.
 * The next tick is scheduled only after the current callback resolves,
 * preventing overlapping requests.
 */
export function usePollingEffect(
  callback: () => void | Promise<void>,
  intervalMs: number,
  deps: React.DependencyList = []
) {
  const cbRef = useRef(callback);
  cbRef.current = callback;

  useEffect(() => {
    if (!intervalMs || intervalMs <= 0) return;

    let active = true;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let executing = false;

    const schedule = (delay: number) => {
      timer = setTimeout(async () => {
        if (!active || document.hidden || executing) return;
        executing = true;
        try {
          await cbRef.current();
        } catch {
          /* caller handles errors */
        }
        executing = false;
        if (active) {
          schedule(intervalMs);
        }
      }, delay);
    };

    schedule(intervalMs);

    const onVis = () => {
      if (document.hidden || !active) return;
      if (timer) clearTimeout(timer);
      schedule(0); // instant refresh on tab focus
    };

    document.addEventListener('visibilitychange', onVis);

    return () => {
      active = false;
      if (timer) clearTimeout(timer);
      document.removeEventListener('visibilitychange', onVis);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs, ...deps]);
}

/**
 * Computes the adaptive poll interval based on pipeline run state.
 * Fast (3s) when any run is 'running', slow (30s) otherwise.
 */
export function getAdaptiveInterval(runs: { status: string }[] | undefined): number {
  if (!runs) return 30000;
  return runs.some(r => r.status === 'running') ? 3000 : 30000;
}
