import { Check, Download, RefreshCw } from 'lucide-react';
import { Suspense, lazy } from 'react';

import { api } from '../api';
import { METHOD_LABELS, formatBytes } from '../labels';
import type { Method } from '../types';
import type { DrawerTabProps } from './drawerTab';
import { Loading } from './Loading';
import { SpecItem } from './SpecItem';

const ModelViewer = lazy(() =>
  import('./ModelViewer').then((module) => ({ default: module.ModelViewer })),
);

interface BuildTabProps extends DrawerTabProps {
  buildMethods: Method[];
}

export function BuildTab({ component, buildMethods, busy, run }: BuildTabProps) {
  const model = component.model3d;
  const done = new Set(component.steps_done);

  function toggleStep(index: number) {
    const next = done.has(index)
      ? component.steps_done.filter((i) => i !== index)
      : [...component.steps_done, index];
    run('steps', () =>
      api.updateComponent(component.id, {
        steps_done: next,
        status: component.status === 'undecided' ? 'building' : undefined,
      }),
    );
  }

  return (
    <>
      <div>
        <p className="field-label" style={{ marginBottom: 8 }}>
          Build method
        </p>
        <div className="row">
          {buildMethods.map((method) => (
            <button
              key={method}
              className={`chip${component.method === method ? ' active' : ''}`}
              disabled={busy !== null}
              onClick={() => run('method', () => api.updateComponent(component.id, { method }))}
            >
              {METHOD_LABELS[method]}
            </button>
          ))}
        </div>
        {busy === 'method' && <p className="faint">Switching method and regenerating files…</p>}
      </div>

      {model && (
        <section>
          <div className="section-title">
            <h3>3D model, scaled to you</h3>
            <div className="row">
              <button
                className="btn btn-sm"
                disabled={busy !== null}
                onClick={() => run('model', () => api.regenerateModel(component.id))}
              >
                <RefreshCw size={14} /> {busy === 'model' ? 'Designing…' : 'Redesign'}
              </button>
              <a className="btn btn-sm btn-primary" href={api.stlUrl(component.id)} download>
                <Download size={14} /> STL
              </a>
            </div>
          </div>
          <Suspense fallback={<div className="viewer"><Loading label="Loading 3D viewer" /></div>}>
            <ModelViewer url={model.stl_url} color={component.colors[0]} />
          </Suspense>
          <div className="spec-grid" style={{ marginTop: 12 }}>
            <SpecItem label="File" value={`${component.name.toLowerCase().replace(/ /g, '-')}.stl`} />
            <SpecItem
              label="File size"
              value={component.stl_size_bytes ? formatBytes(component.stl_size_bytes) : '—'}
            />
            <SpecItem label="Template" value={model.template.replace('_', ' ')} />
            <SpecItem label="Triangles" value={model.triangle_count.toLocaleString()} />
            <SpecItem
              label="Dimensions"
              value={model.dimensions_mm.map((d) => Math.round(d)).join(' × ') + ' mm'}
            />
            <SpecItem
              label="Print bed (256 mm)"
              value={model.fits_bed ? 'Fits in one piece' : `Split into ~${model.parts_suggested}`}
            />
            <SpecItem label="Filament" value={`${Math.round(model.estimated_filament_grams)} g PLA`} />
            <SpecItem label="Print time" value={`~${model.estimated_print_hours} h`} />
          </div>
          <p className="faint" style={{ marginTop: 8 }}>
            Scaled to:{' '}
            {Object.entries(model.scaled_to)
              .map(([key, value]) => `${key.replace(/_mm$/, '').replace(/_/g, ' ')} ${value} mm`)
              .join(', ')}
          </p>
          {model.print_notes.length > 0 && (
            <ul className="list muted" style={{ marginTop: 10 }}>
              {model.print_notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          )}
        </section>
      )}

      {component.pattern_available && (
        <section className="card" style={{ padding: 16 }}>
          <div className="section-title" style={{ marginBottom: 6 }}>
            <h3>Sewing pattern for a {component.garment_type}</h3>
            <a className="btn btn-sm btn-primary" href={api.patternUrl(component.id)} target="_blank" rel="noreferrer">
              <Download size={14} /> Pattern SVG
            </a>
          </div>
          <p className="faint">1:1 scale drafted from your measurements with 1.5 cm seam allowance.</p>
        </section>
      )}

      {component.knit_pattern && (
        <section>
          <h3 style={{ marginBottom: 8 }}>Knitting pattern</h3>
          <pre className="pre">{component.knit_pattern}</pre>
        </section>
      )}

      <section>
        <div className="section-title">
          <h3>Steps</h3>
          <span className="faint">
            {done.size} / {component.build_steps.length} done
          </span>
        </div>
        <ol className="steps">
          {component.build_steps.map((step, index) => (
            <li
              key={step}
              className={`step${done.has(index) ? ' done' : ''}`}
              onClick={() => toggleStep(index)}
            >
              <span className="check">{done.has(index) && <Check size={13} />}</span>
              <span>{step}</span>
            </li>
          ))}
        </ol>
      </section>

      {(component.materials.length > 0 || component.tools.length > 0) && (
        <div className="grid-2">
          <section>
            <h3 style={{ marginBottom: 6 }}>Materials</h3>
            <ul className="list muted">
              {component.materials.map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
          </section>
          <section>
            <h3 style={{ marginBottom: 6 }}>Tools</h3>
            <ul className="list muted">
              {component.tools.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </>
  );
}
