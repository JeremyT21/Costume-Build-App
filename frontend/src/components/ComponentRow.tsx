import { ChevronRight, Hammer, ShoppingCart } from 'lucide-react';

import { CATEGORY_LABELS, METHOD_LABELS, formatUsd, plannedCost, thumbnailFor } from '../labels';
import type { CostumeComponent, Status } from '../types';
import { CategoryIcon } from './CategoryIcon';
import { SegmentedControl } from './SegmentedControl';
import { StatusBadge } from './StatusBadge';

interface ComponentRowProps {
  component: CostumeComponent;
  active: boolean;
  canBuy: boolean;
  canBuild: boolean;
  onOpen: () => void;
  onDecide: (status: Status) => void;
}

export function ComponentRow({
  component,
  active,
  canBuy,
  canBuild,
  onOpen,
  onDecide,
}: ComponentRowProps) {
  const thumb = thumbnailFor(component);
  const decision =
    component.status === 'buying' ? 'buy' : component.status === 'building' ? 'build' : null;

  return (
    <div
      className={`component-row${active ? ' active' : ''}`}
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(e) => e.key === 'Enter' && onOpen()}
    >
      <div className="component-thumb">
        {thumb ? <img src={thumb} alt="" loading="lazy" /> : <CategoryIcon category={component.category} />}
      </div>
      <div style={{ minWidth: 0 }}>
        <div className="component-title">
          {component.name}
          <StatusBadge status={component.status} />
        </div>
        <div className="component-meta">
          <span>{CATEGORY_LABELS[component.category]}</span>
          <span>{component.status === 'buying' ? 'Buy' : METHOD_LABELS[component.method]}</span>
          <span>{formatUsd(plannedCost(component))}</span>
          {component.status === 'undecided' && (
            <span>Suggested: {component.recommended_action}</span>
          )}
        </div>
        {component.status === 'building' && (
          <div className="mini-progress">
            <div style={{ width: `${component.progress * 100}%` }} />
          </div>
        )}
      </div>
      <div className="row" style={{ flexWrap: 'nowrap' }}>
        {component.status !== 'completed' && (
          <SegmentedControl
            ariaLabel={`Buy or build ${component.name}`}
            value={decision}
            onChange={(value) => onDecide(value === 'buy' ? 'buying' : 'building')}
            options={[
              { value: 'buy', label: <ShoppingCart size={14} aria-label="Buy" />, disabled: !canBuy },
              { value: 'build', label: <Hammer size={14} aria-label="Build" />, disabled: !canBuild },
            ]}
          />
        )}
        <ChevronRight size={16} className="faint" />
      </div>
    </div>
  );
}
