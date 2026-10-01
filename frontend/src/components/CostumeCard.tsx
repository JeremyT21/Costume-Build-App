import type { CSSProperties } from 'react';
import { Link } from 'react-router-dom';

import { formatUsd } from '../labels';
import { useCostumeHue } from '../theme';
import type { CostumeSummary } from '../types';
import { ProgressBar } from './ProgressBar';

interface CostumeCardProps {
  costume: CostumeSummary;
}

export function CostumeCard({ costume }: CostumeCardProps) {
  const hue = useCostumeHue(costume);

  return (
    <Link
      to={`/costumes/${costume.id}`}
      className="costume-card"
      style={{ '--card-h': hue } as CSSProperties}
    >
      <div className="costume-cover">
        {costume.image_urls[0] && <img src={costume.image_urls[0]} alt="" />}
        <span className="costume-percent">{Math.round(costume.progress.percent)}%</span>
      </div>
      <div className="costume-body">
        <div>
          <h3>{costume.name}</h3>
          <div className="facts">
            <span>{costume.progress.total} pieces</span>
            <span>{formatUsd(costume.estimated_cost)} planned</span>
          </div>
        </div>
        <ProgressBar progress={costume.progress} />
      </div>
    </Link>
  );
}
