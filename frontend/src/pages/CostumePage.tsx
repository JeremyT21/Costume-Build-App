import { ArrowLeft, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';

import { api } from '../api';
import { useApp } from '../appContext';
import { BodyMap } from '../components/BodyMap';
import { ComponentDrawer } from '../components/ComponentDrawer';
import { ComponentRow } from '../components/ComponentRow';
import { isTab } from '../components/drawerTab';
import { Loading } from '../components/Loading';
import { ProgressBar } from '../components/ProgressBar';
import { SegmentedControl } from '../components/SegmentedControl';
import { BUILD_METHODS, ZONE_ORDER, formatUsd, plannedCost } from '../labels';
import { useCostumeTheme } from '../theme';
import type { CostumeComponent, CostumeDetail, StartMode, Status } from '../types';

type Filter =
  | 'all'
  | 'undecided'
  | 'buying'
  | 'building'
  | 'completed'
  | 'suggest_buy'
  | 'suggest_build'
  | 'polish';

type Sort = 'body' | 'name' | 'cost' | 'difficulty' | 'progress';

const FILTERS: { value: Filter; label: string; test: (c: CostumeComponent) => boolean }[] = [
  { value: 'all', label: 'All', test: () => true },
  { value: 'undecided', label: 'Undecided', test: (c) => c.status === 'undecided' },
  { value: 'buying', label: 'Buying', test: (c) => c.status === 'buying' },
  { value: 'building', label: 'Building', test: (c) => c.status === 'building' },
  { value: 'completed', label: 'Completed', test: (c) => c.status === 'completed' },
  {
    value: 'suggest_buy',
    label: 'Suggested to buy',
    test: (c) => c.status !== 'completed' && c.recommended_action === 'buy',
  },
  {
    value: 'suggest_build',
    label: 'Suggested to build',
    test: (c) => c.status !== 'completed' && c.recommended_action === 'build',
  },
  {
    value: 'polish',
    label: 'Ready to improve',
    test: (c) => c.status === 'completed' && c.acquired_via === 'build',
  },
];

const SORTERS: Record<Sort, (a: CostumeComponent, b: CostumeComponent) => number> = {
  body: (a, b) => ZONE_ORDER.indexOf(a.body_zone) - ZONE_ORDER.indexOf(b.body_zone),
  name: (a, b) => a.name.localeCompare(b.name),
  cost: (a, b) => plannedCost(b) - plannedCost(a),
  difficulty: (a, b) => b.difficulty - a.difficulty,
  progress: (a, b) => b.progress - a.progress,
};

export function CostumePage() {
  const { costumeId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { profile, info } = useApp();
  const [costume, setCostume] = useState<CostumeDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pieceParam = searchParams.get('piece');
  const tabParam = searchParams.get('tab');
  const [openId, setOpenId] = useState<number | null>(pieceParam ? Number(pieceParam) : null);
  const [filter, setFilter] = useState<Filter>('all');
  const [sort, setSort] = useState<Sort>('body');

  const id = Number(costumeId);
  const reload = useCallback(
    () =>
      api
        .getCostume(id)
        .then(setCostume)
        .catch((err: Error) => setError(err.message)),
    [id],
  );

  useEffect(() => {
    reload();
  }, [reload]);

  const allowed = profile?.allowed_methods ?? [];
  const canBuy = allowed.includes('buy');
  const canBuild = BUILD_METHODS.some((m) => allowed.includes(m));

  const componentColors = useMemo(
    () => costume?.components.flatMap((c) => c.colors) ?? [],
    [costume],
  );
  useCostumeTheme(costume, componentColors);

  const visible = useMemo(() => {
    if (!costume) return [];
    const test = FILTERS.find((f) => f.value === filter)?.test ?? (() => true);
    return costume.components.filter(test).sort(SORTERS[sort]);
  }, [costume, filter, sort]);

  if (error) return <div className="page"><div className="error">{error}</div></div>;
  if (!costume) return <Loading label="Loading costume" />;

  const open = costume.components.find((c) => c.id === openId) ?? null;
  const tier = info?.budget_tiers.find((t) => t.tier === costume.budget_tier);
  const undecided = costume.progress.undecided;
  const showDecision = searchParams.has('decide') && undecided > 0;

  function replaceComponent(updated: CostumeComponent) {
    setCostume((current) =>
      current && {
        ...current,
        components: current.components.map((c) => (c.id === updated.id ? updated : c)),
      },
    );
    reload();
  }

  async function decide(component: CostumeComponent, status: Status) {
    replaceComponent(await api.updateComponent(component.id, { status }));
  }

  async function changeMode(mode: StartMode) {
    setCostume(await api.setMode(costume!.id, mode));
  }

  async function remove() {
    if (!window.confirm(`Delete ${costume!.name}? This removes its files and progress.`)) return;
    await api.deleteCostume(costume!.id);
    navigate('/');
  }

  return (
    <div className="page">
      <section className="hero">
        {costume.image_urls[0] && (
          <div
            className="hero-backdrop"
            style={{ backgroundImage: `url(${costume.image_urls[0]})` }}
            aria-hidden
          />
        )}
        <div className="hero-top">
          <div>
            <Link to="/" className="back-link">
              <ArrowLeft size={14} /> Collection
            </Link>
            <h1 className="hero-title">{costume.name}</h1>
            <p className="subtitle">{costume.summary}</p>
          </div>
          <div className="row">
            <SegmentedControl<StartMode>
              ariaLabel="Costume mode"
              value={costume.start_mode}
              onChange={changeMode}
              options={[
                { value: 'mixed', label: 'Per piece' },
                { value: 'build_all', label: 'Build all', disabled: !canBuild },
                { value: 'buy_all', label: 'Buy all', disabled: !canBuy },
              ]}
            />
            <button className="btn btn-ghost icon-btn" aria-label="Delete costume" onClick={remove}>
              <Trash2 size={16} />
            </button>
          </div>
        </div>
        <div className="hero-progress">
          <span className="hero-percent">{Math.round(costume.progress.percent)}%</span>
          <div>
            <ProgressBar progress={costume.progress} showLegend />
          </div>
          <span />
          <div className="facts">
            <span>
              {costume.progress.completed} of {costume.progress.total} pieces done
            </span>
            <span>{formatUsd(costume.estimated_cost)} planned</span>
            <span>{tier?.label ?? costume.budget_tier} budget</span>
          </div>
        </div>
      </section>

      {showDecision && (
        <div className="decision-banner">
          <div style={{ flex: 1 }}>
            <h3>Decide how to get each piece</h3>
            <p className="muted">
              {undecided} components are undecided. Use the buy and build toggles, or open a piece
              to compare products and build instructions.
            </p>
          </div>
          <button className="btn" onClick={() => setSearchParams({})}>
            Later
          </button>
        </div>
      )}

      <div className="workspace">
        <div className="stage sticky">
          <div className="stage-header">
            <h2>Body map</h2>
            <span className="faint">Tap a piece for details</span>
          </div>
          <BodyMap components={costume.components} activeId={openId} onSelect={setOpenId} />
        </div>

        <div className="stack">
          <div className="toolbar">
            {FILTERS.map((option) => {
              const count = costume.components.filter(option.test).length;
              return (
                <button
                  key={option.value}
                  className={`chip${filter === option.value ? ' active' : ''}`}
                  onClick={() => setFilter(option.value)}
                >
                  {option.label}
                  <span className="chip-count">{count}</span>
                </button>
              );
            })}
            <span className="spacer" />
            <select
              className="select"
              style={{ width: 'auto', height: 32 }}
              aria-label="Sort components"
              value={sort}
              onChange={(e) => setSort(e.target.value as Sort)}
            >
              <option value="body">Sort: head to toe</option>
              <option value="name">Sort: name</option>
              <option value="cost">Sort: cost</option>
              <option value="difficulty">Sort: difficulty</option>
              <option value="progress">Sort: progress</option>
            </select>
          </div>
          <div className="component-list">
            {visible.map((component) => (
              <ComponentRow
                key={component.id}
                component={component}
                active={component.id === openId}
                canBuy={canBuy}
                canBuild={canBuild}
                onOpen={() => setOpenId(component.id)}
                onDecide={(status) => decide(component, status)}
              />
            ))}
            {visible.length === 0 && <p className="muted">No components match this filter.</p>}
          </div>
          {costume.budget_notes && <p className="faint">{costume.budget_notes}</p>}
        </div>
      </div>

      {open && (
        <ComponentDrawer
          component={open}
          initialTab={isTab(tabParam) ? tabParam : undefined}
          allowedMethods={allowed}
          onChange={replaceComponent}
          onClose={() => setOpenId(null)}
        />
      )}
    </div>
  );
}
