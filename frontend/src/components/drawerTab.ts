import type { CostumeComponent } from '../types';

export interface DrawerTabProps {
  component: CostumeComponent;
  busy: string | null;
  run: (label: string, action: () => Promise<CostumeComponent>) => Promise<void>;
}

export type Tab = 'overview' | 'build' | 'buy' | 'improve';

export const TABS: Tab[] = ['overview', 'build', 'buy', 'improve'];

export function isTab(value: string | null): value is Tab {
  return TABS.includes(value as Tab);
}
