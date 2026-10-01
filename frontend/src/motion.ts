import { useCallback, useEffect, useState } from 'react';

const STORAGE_KEY = 'cospal-motion';

function systemPrefersReduced(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function readStored(): boolean | null {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    return value === null ? null : value === 'on';
  } catch {
    return null;
  }
}

/** True when animations should play, honoring the saved choice over the system setting. */
export function motionEnabled(): boolean {
  return document.documentElement.dataset.motion !== 'off';
}

export function useMotionPreference(): [boolean, (enabled: boolean) => void] {
  const [enabled, setEnabled] = useState(() => readStored() ?? !systemPrefersReduced());

  useEffect(() => {
    document.documentElement.dataset.motion = enabled ? 'on' : 'off';
  }, [enabled]);

  const update = useCallback((next: boolean) => {
    setEnabled(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next ? 'on' : 'off');
    } catch {
      // Storage can be blocked; the choice still applies for this visit.
    }
  }, []);

  return [enabled, update];
}
