import { createContext, useContext } from 'react';

import type { AppInfo, Profile } from './types';

export interface AppState {
  info: AppInfo | null;
  profile: Profile | null;
  setProfile: (profile: Profile) => void;
}

export const AppContext = createContext<AppState | null>(null);

export function useApp(): AppState {
  const state = useContext(AppContext);
  if (!state) throw new Error('useApp must be used inside AppContext.');
  return state;
}
