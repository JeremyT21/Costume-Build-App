import { useMemo, useState, type CSSProperties } from 'react';

import { METHOD_LABELS, STATUS_LABELS, thumbnailFor } from '../labels';
import type { BodyZone, CostumeComponent, Status } from '../types';
import { CategoryIcon } from './CategoryIcon';

const WIDTH = 640;
const HEIGHT = 500;
const BOX_W = 178;
const BOX_H = 52;
const GAP = 8;
const MARGIN = 12;
const FIGURE_OFFSET_X = 20;
const FIGURE_OFFSET_Y = 18;

// Anchor points on the silhouette before the figure offset is applied.
const ZONE_ANCHORS: Record<BodyZone, [number, number]> = {
  head: [300, 40],
  face: [300, 64],
  neck: [300, 96],
  shoulders: [246, 124],
  torso: [300, 165],
  back: [326, 196],
  arms: [222, 214],
  hands: [214, 306],
  waist: [300, 238],
  legs: [280, 350],
  feet: [276, 446],
  held: [386, 306],
};

const PREFERRED_SIDE: Record<BodyZone, 'left' | 'right'> = {
  head: 'left',
  face: 'right',
  neck: 'left',
  shoulders: 'left',
  torso: 'right',
  back: 'right',
  arms: 'left',
  hands: 'left',
  waist: 'right',
  legs: 'left',
  feet: 'right',
  held: 'right',
};

const STATUS_COLORS: Record<Status, string> = {
  undecided: 'var(--text-faint)',
  buying: 'var(--info)',
  building: 'var(--accent)',
  completed: 'var(--success)',
};

const SILHOUETTE_PATH =
  'M290,104 C270,106 250,108 240,114 C228,120 224,134 222,150 L212,236 L204,296 ' +
  'C202,306 206,316 214,316 C222,316 226,306 224,296 L232,240 L250,162 L258,200 ' +
  'C262,222 262,232 260,240 C254,256 250,266 250,280 L262,430 C262,440 254,448 256,454 ' +
  'L292,454 L294,430 L298,296 Q300,290 302,296 L306,430 L308,454 L344,454 ' +
  'C346,448 338,440 338,430 L350,280 C350,266 346,256 340,240 C338,232 338,222 342,200 ' +
  'L350,162 L368,240 L376,296 C374,306 378,316 386,316 C394,316 398,306 396,296 ' +
  'L388,236 L378,150 C376,134 372,120 360,114 C350,108 330,106 310,104 Z';

interface Placed {
  component: CostumeComponent;
  anchor: [number, number];
  side: 'left' | 'right';
  y: number;
}

function layout(components: CostumeComponent[]): Placed[] {
  const items = components.map((component) => {
    const zone = ZONE_ANCHORS[component.body_zone] ? component.body_zone : 'torso';
    const [ax, ay] = ZONE_ANCHORS[zone];
    return {
      component,
      anchor: [ax + FIGURE_OFFSET_X, ay + FIGURE_OFFSET_Y] as [number, number],
      side: PREFERRED_SIDE[zone],
      y: 0,
    };
  });
  // Balance columns so neither side overflows.
  const capacity = Math.floor((HEIGHT - MARGIN) / (BOX_H + GAP));
  for (const side of ['left', 'right'] as const) {
    const other = side === 'left' ? 'right' : 'left';
    const onSide = items.filter((i) => i.side === side).sort((a, b) => a.anchor[0] - b.anchor[0]);
    while (onSide.length > capacity && items.filter((i) => i.side === other).length < capacity) {
      const moved = onSide.pop();
      if (moved) moved.side = other;
    }
  }
  for (const side of ['left', 'right'] as const) {
    const column = items.filter((i) => i.side === side).sort((a, b) => a.anchor[1] - b.anchor[1]);
    let cursor = MARGIN;
    for (const item of column) {
      item.y = Math.max(item.anchor[1] - BOX_H / 2, cursor);
      cursor = item.y + BOX_H + GAP;
    }
    let limit = HEIGHT - MARGIN;
    for (const item of [...column].reverse()) {
      item.y = Math.min(item.y, limit - BOX_H);
      limit = item.y - GAP;
    }
  }
  return items;
}

interface BodyMapProps {
  components: CostumeComponent[];
  activeId: number | null;
  onSelect: (id: number) => void;
}

/** Shows where each component is worn, with live thumbnails and status. */
export function BodyMap({ components, activeId, onSelect }: BodyMapProps) {
  const [hoverId, setHoverId] = useState<number | null>(null);
  const placed = useMemo(() => layout(components), [components]);
  const focusId = hoverId ?? activeId;
  const focused = placed.find((p) => p.component.id === focusId);

  return (
    <div className="body-map">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Costume body map">
        <defs>
          <linearGradient id="silhouette-shade" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor="var(--silhouette)" stopOpacity="1" />
            <stop offset="1" stopColor="var(--silhouette)" stopOpacity="0.7" />
          </linearGradient>
          {placed.map(({ component, side, y }) => {
            const x = side === 'left' ? MARGIN : WIDTH - MARGIN - BOX_W;
            return (
              <clipPath key={component.id} id={`thumb-clip-${component.id}`}>
                <rect x={x + 7} y={y + 7} width={36} height={36} rx={9} />
              </clipPath>
            );
          })}
        </defs>

        <g transform={`translate(${FIGURE_OFFSET_X} ${FIGURE_OFFSET_Y})`}>
          <ellipse className="silhouette" cx={300} cy={56} rx={24} ry={29} fill="url(#silhouette-shade)" />
          <rect className="silhouette" x={289} y={82} width={22} height={26} rx={6} />
          <path className="silhouette" d={SILHOUETTE_PATH} fill="url(#silhouette-shade)" />
        </g>

        {focused && (
          <circle
            className="zone-glow"
            cx={focused.anchor[0]}
            cy={focused.anchor[1]}
            r={30}
          />
        )}

        {placed.map(({ component, anchor, side, y }, index) => {
          const x = side === 'left' ? MARGIN : WIDTH - MARGIN - BOX_W;
          const edgeX = side === 'left' ? x + BOX_W : x;
          const elbowX = side === 'left' ? edgeX + 14 : edgeX - 14;
          const midY = y + BOX_H / 2;
          const thumb = thumbnailFor(component);
          const active = component.id === activeId;
          const subtitle =
            component.status === 'buying' ||
            (component.status === 'undecided' && component.recommended_action === 'buy')
              ? 'Buy'
              : METHOD_LABELS[component.method];
          return (
            <g
              key={component.id}
              className={`callout callout-${side}${active ? ' active' : ''}`}
              style={{ '--i': index } as CSSProperties}
              role="button"
              tabIndex={0}
              aria-label={`${component.name}, ${STATUS_LABELS[component.status]}`}
              onClick={() => onSelect(component.id)}
              onKeyDown={(e) => e.key === 'Enter' && onSelect(component.id)}
              onMouseEnter={() => setHoverId(component.id)}
              onMouseLeave={() => setHoverId(null)}
            >
              <path
                className="leader"
                d={`M${anchor[0]},${anchor[1]} L${elbowX},${midY} L${edgeX},${midY}`}
              />
              <circle className="anchor" cx={anchor[0]} cy={anchor[1]} r={3.5} />
              <rect className="callout-box" x={x} y={y} width={BOX_W} height={BOX_H} rx={12} />
              {thumb ? (
                <image
                  href={thumb}
                  x={x + 7}
                  y={y + 7}
                  width={36}
                  height={36}
                  preserveAspectRatio="xMidYMid meet"
                  clipPath={`url(#thumb-clip-${component.id})`}
                />
              ) : (
                <>
                  <rect x={x + 7} y={y + 7} width={36} height={36} rx={9} fill="var(--surface-3)" />
                  <CategoryIcon
                    category={component.category}
                    size={18}
                    x={x + 16}
                    y={y + 16}
                    color="var(--text-faint)"
                  />
                </>
              )}
              <rect
                x={x + 7}
                y={y + 7}
                width={36}
                height={36}
                rx={9}
                fill="none"
                stroke={STATUS_COLORS[component.status]}
                strokeWidth={2}
              />
              <text className="callout-title" x={x + 52} y={y + 23}>
                {component.name.length > 15 ? `${component.name.slice(0, 14)}…` : component.name}
              </text>
              <circle cx={x + 55} cy={y + 35} r={3} fill={STATUS_COLORS[component.status]} />
              <text className="callout-sub" x={x + 63} y={y + 39}>
                {STATUS_LABELS[component.status]}, {subtitle.toLowerCase()}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
