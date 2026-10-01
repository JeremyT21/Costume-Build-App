import { Check, Hammer, ShoppingCart, X } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';

import { api } from '../api';
import {
  BUILD_METHODS,
  CATEGORY_LABELS,
  METHOD_LABELS,
  formatUsd,
  thumbnailFor,
  zoneLabel,
} from '../labels';
import type { CostumeComponent, Method, Status } from '../types';
import { BuildTab } from './BuildTab';
import { BuyTab } from './BuyTab';
import { ImproveTab } from './ImproveTab';
import { CategoryIcon } from './CategoryIcon';
import { SegmentedControl } from './SegmentedControl';
import { SpecItem } from './SpecItem';
import { StatusBadge } from './StatusBadge';
import { TABS, type Tab } from './drawerTab';
import { motionEnabled } from '../motion';

interface ComponentDrawerProps {
  component: CostumeComponent;
  initialTab?: Tab;
  allowedMethods: Method[];
  onChange: (component: CostumeComponent) => void;
  onClose: () => void;
}

export function ComponentDrawer({
  component,
  initialTab,
  allowedMethods,
  onChange,
  onClose,
}: ComponentDrawerProps) {
  const [tab, setTab] = useState<Tab>(
    initialTab ?? (component.status === 'buying' ? 'buy' : 'overview'),
  );
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [closing, setClosing] = useState(false);

  // Plays the exit animation before unmounting.
  const close = useCallback(() => {
    if (!motionEnabled()) {
      onClose();
      return;
    }
    setClosing(true);
    window.setTimeout(onClose, 240);
  }, [onClose]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === 'Escape' && close();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [close]);

  async function run(label: string, action: () => Promise<CostumeComponent>) {
    setBusy(label);
    setError(null);
    try {
      onChange(await action());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.');
    } finally {
      setBusy(null);
    }
  }

  const setStatus = (status: Status, via?: 'buy' | 'build') =>
    run(status, () => api.updateComponent(component.id, { status, acquired_via: via }));

  const thumb = thumbnailFor(component);
  const canBuy = allowedMethods.includes('buy');
  const buildMethods = BUILD_METHODS.filter((m) => allowedMethods.includes(m));
  const action = component.status === 'buying' ? 'buy' : component.status === 'building' ? 'build' : null;

  return createPortal(
    <>
      <div className={`drawer-backdrop${closing ? ' closing' : ''}`} onClick={close} />
      <aside
        className={`drawer${closing ? ' closing' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label={component.name}
      >
        <header className="drawer-header">
          <div className="component-thumb" style={{ width: 64, height: 64 }}>
            {thumb ? <img src={thumb} alt="" /> : <CategoryIcon category={component.category} />}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="row">
              <h2>{component.name}</h2>
              <StatusBadge status={component.status} />
            </div>
            <div className="facts">
              <span>{CATEGORY_LABELS[component.category]}</span>
              <span>{zoneLabel(component.body_zone)}</span>
              <span>{component.needs_fabrication ? 'Made or bought' : 'Applied to skin'}</span>
            </div>
          </div>
          <button className="btn btn-ghost icon-btn" aria-label="Close" onClick={close}>
            <X size={18} />
          </button>
        </header>

        <nav className="drawer-tabs">
          {TABS.map((t) => (
            <button
              key={t}
              className={`drawer-tab${tab === t ? ' active' : ''}`}
              onClick={() => setTab(t)}
            >
              {t[0].toUpperCase() + t.slice(1)}
            </button>
          ))}
        </nav>

        <div className="drawer-body">
          {error && <div className="error">{error}</div>}
          <div className="tab-panel" key={tab}>

          {tab === 'overview' && (
            <>
              <p>{component.description}</p>
              {component.colors.length > 0 && (
                <div className="row">
                  {component.colors.map((color) => (
                    <span
                      key={color}
                      title={color}
                      style={{
                        width: 22,
                        height: 22,
                        borderRadius: 6,
                        background: color,
                        border: '1px solid var(--border-strong)',
                      }}
                    />
                  ))}
                </div>
              )}
              <div className="card" style={{ padding: 16 }}>
                <p className="eyebrow">Recommended by the fabrication agent</p>
                <h3 style={{ margin: '4px 0 6px' }}>
                  {component.recommended_action === 'buy' ? 'Buy it' : `Build it: ${METHOD_LABELS[component.method].toLowerCase()}`}
                </h3>
                <p className="muted">{component.rationale}</p>
              </div>
              <div className="spec-grid">
                <SpecItem label="Build cost" value={formatUsd(component.estimated_build_cost)} />
                <SpecItem label="Buy cost" value={formatUsd(component.estimated_buy_cost)} />
                <SpecItem label="Difficulty" value={`${component.difficulty} / 5`} />
                <SpecItem label="Progress" value={`${Math.round(component.progress * 100)}%`} />
              </div>
              <div>
                <p className="field-label" style={{ marginBottom: 8 }}>
                  How will you get this piece?
                </p>
                <SegmentedControl
                  ariaLabel="Buy or build"
                  value={action}
                  onChange={(value) => setStatus(value === 'buy' ? 'buying' : 'building')}
                  options={[
                    { value: 'buy', label: <><ShoppingCart size={14} /> Buy</>, disabled: !canBuy },
                    { value: 'build', label: <><Hammer size={14} /> Build</>, disabled: buildMethods.length === 0 },
                  ]}
                />
              </div>
              <div className="row">
                {component.status !== 'completed' ? (
                  <>
                    <button
                      className="btn btn-primary"
                      disabled={busy !== null}
                      onClick={() => setStatus('completed', action === 'buy' ? 'buy' : 'build')}
                    >
                      <Check size={16} /> {action === 'buy' ? 'I bought this' : 'Mark as done'}
                    </button>
                    {component.status !== 'undecided' && (
                      <button className="btn" onClick={() => setStatus('undecided')}>
                        Reset to undecided
                      </button>
                    )}
                  </>
                ) : (
                  <button className="btn" onClick={() => setStatus(component.acquired_via === 'buy' ? 'buying' : 'building')}>
                    Reopen
                  </button>
                )}
              </div>
            </>
          )}

          {tab === 'build' && (
            <BuildTab
              component={component}
              buildMethods={buildMethods}
              busy={busy}
              run={run}
            />
          )}

          {tab === 'buy' && (
            <BuyTab
              component={component}
              canBuy={canBuy}
              busy={busy}
              run={run}
              onBought={() => setStatus('completed', 'buy')}
            />
          )}

          {tab === 'improve' && <ImproveTab component={component} />}
          </div>
        </div>
      </aside>
    </>,
    document.body,
  );
}
