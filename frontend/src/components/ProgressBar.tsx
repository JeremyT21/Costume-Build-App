import type { ProgressBreakdown } from '../types';

interface ProgressBarProps {
  progress: ProgressBreakdown;
  showLegend?: boolean;
}

/** Splits completion into built, bought, and in-progress building. */
export function ProgressBar({ progress, showLegend = false }: ProgressBarProps) {
  const total = Math.max(progress.total, 1);
  const builtWidth = (progress.built / total) * 100;
  const boughtWidth = (progress.bought / total) * 100;
  const partialWidth = Math.max(0, progress.percent - builtWidth - boughtWidth);
  const segments = [
    { width: builtWidth, color: 'var(--success)', label: `${progress.built} built` },
    { width: boughtWidth, color: 'var(--info)', label: `${progress.bought} bought` },
    { width: partialWidth, color: 'var(--accent)', label: `${progress.building} building` },
  ];

  return (
    <div>
      <div
        className="progress"
        role="progressbar"
        aria-valuenow={progress.percent}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        {segments.map((segment) => (
          <div
            key={segment.label}
            className="progress-segment"
            style={{ width: `${segment.width}%`, background: segment.color }}
          />
        ))}
      </div>
      {showLegend && (
        <div className="progress-legend">
          {segments.map((segment) => (
            <span key={segment.label}>
              <span className="legend-dot" style={{ background: segment.color }} />
              {segment.label}
            </span>
          ))}
          <span>
            <span className="legend-dot" style={{ background: 'var(--info)', opacity: 0.4 }} />
            {progress.buying} to buy
          </span>
          <span>
            <span className="legend-dot" style={{ background: 'var(--surface-3)' }} />
            {progress.undecided} undecided
          </span>
        </div>
      )}
    </div>
  );
}
