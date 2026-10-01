import { Check, Layers, Sparkles, Wand2 } from 'lucide-react';
import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';

import { api } from '../api';
import { useApp } from '../appContext';
import { ImageDropzone } from '../components/ImageDropzone';
import { SegmentedControl } from '../components/SegmentedControl';
import { MODE_LABELS, formatUsd } from '../labels';
import type { BudgetTier, CostumeSummary, StartMode } from '../types';

type Intent = 'references' | 'variants';
type Phase = 'form' | 'analyzing' | 'pick' | 'finalizing';

const ANALYSIS_STEPS = [
  'Concept agent is grouping your images',
  'Component agent is breaking down the character',
  'Fabrication agent is planning methods and budget',
];

const FINALIZE_STEPS = [
  'Modeling agent is designing 3D parts to your size',
  'Shopping agent is finding products',
  'Sizing agent is checking fit against reviews',
];

export function NewCostumePage() {
  const { profile, info } = useApp();
  const navigate = useNavigate();
  const [images, setImages] = useState<File[]>([]);
  const [name, setName] = useState('');
  const [hint, setHint] = useState('');
  const [intent, setIntent] = useState<Intent>('references');
  const [tier, setTier] = useState<BudgetTier>(profile?.budget_tier ?? 'standard');
  const [mode, setMode] = useState<StartMode>(profile?.default_mode ?? 'mixed');
  const [phase, setPhase] = useState<Phase>('form');
  const [concepts, setConcepts] = useState<CostumeSummary[]>([]);
  const [chosen, setChosen] = useState<number | null>(null);
  const [keep, setKeep] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [activeStep, setActiveStep] = useState(0);

  const busy = phase === 'analyzing' || phase === 'finalizing';
  useEffect(() => {
    if (!busy) return;
    const timer = window.setInterval(() => setActiveStep((s) => Math.min(s + 1, 2)), 2600);
    return () => window.clearInterval(timer);
  }, [busy]);

  async function finalize(costumeId: number, keepIds: number[]) {
    setActiveStep(0);
    setPhase('finalizing');
    try {
      const detail = await api.selectConcept(costumeId, keepIds);
      navigate(`/costumes/${detail.id}?decide=1`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save the costume.');
      setPhase('pick');
    }
  }

  async function analyze(event: FormEvent) {
    event.preventDefault();
    if (images.length === 0) {
      setError('Add at least one image of the character.');
      return;
    }
    setError(null);
    setActiveStep(0);
    setPhase('analyzing');
    try {
      const result = await api.analyze({ images, name, hint, intent, budgetTier: tier, startMode: mode });
      if (result.concepts.length === 1) {
        await finalize(result.concepts[0].id, []);
        return;
      }
      setConcepts(result.concepts);
      setChosen(result.concepts[0].id);
      setPhase('pick');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed.');
      setPhase('form');
    }
  }

  if (busy) {
    const steps = phase === 'analyzing' ? ANALYSIS_STEPS : FINALIZE_STEPS;
    return (
      <div className="page page-narrow">
        <div className="card analyzing">
          <span className="empty-icon">
            <Sparkles size={24} />
          </span>
          <h2>{phase === 'analyzing' ? 'Analyzing your character' : 'Building your plan'}</h2>
          <div className="agent-steps">
            {steps.map((step, index) => (
              <div
                key={step}
                className={`agent-step${index < activeStep ? ' done' : index === activeStep ? ' active' : ''}`}
              >
                {index < activeStep ? <Check size={16} /> : <span className="spinner" />}
                {step}
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (phase === 'pick') {
    return (
      <div className="page">
        <div className="page-header">
          <div>
            <h1>Pick a version to start</h1>
            <p className="subtitle">
              We found {concepts.length} costume versions. Your pick is saved automatically; keep
              others in your collection for later.
            </p>
          </div>
          <button
            className="btn btn-primary btn-lg"
            disabled={chosen === null}
            onClick={() => chosen !== null && finalize(chosen, keep.filter((id) => id !== chosen))}
          >
            <Wand2 size={16} /> Start this costume
          </button>
        </div>
        {error && <div className="error">{error}</div>}
        <div className="concept-grid">
          {concepts.map((concept, index) => (
            <div
              key={concept.id}
              role="button"
              tabIndex={0}
              className={`concept-card${chosen === concept.id ? ' selected' : ''}`}
              onClick={() => setChosen(concept.id)}
              onKeyDown={(e) => e.key === 'Enter' && setChosen(concept.id)}
            >
              <div className="concept-images">
                {concept.image_urls.slice(0, 3).map((url) => (
                  <img key={url} src={url} alt="" />
                ))}
              </div>
              <div className="costume-body">
                <div className="row">
                  <span className="tag">#{index + 1}</span>
                  <h3>{concept.name}</h3>
                </div>
                <p className="muted">{concept.summary}</p>
                <p className="faint">
                  {concept.progress.total} pieces, about {formatUsd(concept.estimated_cost)}
                </p>
                <label className="check-row" onClick={(e) => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={chosen === concept.id || keep.includes(concept.id)}
                    disabled={chosen === concept.id}
                    onChange={(e) =>
                      setKeep((current) =>
                        e.target.checked
                          ? [...current, concept.id]
                          : current.filter((id) => id !== concept.id),
                      )
                    }
                  />
                  Save to collection
                </label>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <form className="page page-narrow" onSubmit={analyze}>
      <div className="page-header">
        <div>
          <h1>New costume</h1>
          <p className="subtitle">
            Upload or snap a picture of a character. Agents break it into components, plan each
            piece, and model printable parts to your size.
          </p>
        </div>
      </div>

      {!info?.ai_enabled && (
        <div className="callout-note">
          Offline mode: components are inferred from your description below. Add an API key to
          the backend to enable image-reading agents.
        </div>
      )}

      <section className="card">
        <ImageDropzone files={images} onChange={setImages} />
        <div className="row" style={{ marginTop: 16 }}>
          <span className="field-label">These images show</span>
          <SegmentedControl<Intent>
            ariaLabel="Image intent"
            value={intent}
            onChange={setIntent}
            options={[
              { value: 'references', label: <><Layers size={14} /> One costume</> },
              { value: 'variants', label: <><Sparkles size={14} /> Different versions</> },
            ]}
          />
        </div>
        <p className="faint" style={{ marginTop: 6 }}>
          {intent === 'references'
            ? 'Extra angles help agents see details more clearly.'
            : 'Agents group images into up to 3 versions and you pick one to start.'}
        </p>
      </section>

      <section className="card">
        <div className="grid-2">
          <label className="field">
            <span className="field-label">Character name</span>
            <input
              className="input"
              placeholder="e.g. Link, Breath of the Wild"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label className="field">
            <span className="field-label">Budget for this costume</span>
            <select
              className="select"
              value={tier}
              onChange={(e) => setTier(e.target.value as BudgetTier)}
            >
              {info?.budget_tiers.map((t) => (
                <option key={t.tier} value={t.tier}>
                  {t.label} ·{' '}
                  {t.max_usd === null ? `${formatUsd(t.min_usd)}+` : `up to ${formatUsd(t.max_usd)}`}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label className="field" style={{ marginTop: 16 }}>
          <span className="field-label">Notes for the agents (optional)</span>
          <textarea
            className="textarea"
            placeholder="e.g. silver helmet, blue cape, leather boots, tribal face paint"
            value={hint}
            onChange={(e) => setHint(e.target.value)}
          />
        </label>
        <p className="field-label" style={{ margin: '16px 0 8px' }}>
          Start by
        </p>
        <div className="tiles">
          {(Object.keys(MODE_LABELS) as StartMode[]).map((option) => (
            <button
              type="button"
              key={option}
              disabled={option === 'buy_all' && !profile?.allowed_methods.includes('buy')}
              className={`tile${mode === option ? ' selected' : ''}`}
              onClick={() => setMode(option)}
            >
              <span className="tile-title">{MODE_LABELS[option].label}</span>
              <span className="tile-hint">{MODE_LABELS[option].hint}</span>
            </button>
          ))}
        </div>
      </section>

      {error && <div className="error">{error}</div>}
      <div className="row">
        <span className="spacer" />
        <button className="btn btn-primary btn-lg">
          <Sparkles size={16} /> Analyze character
        </button>
      </div>
    </form>
  );
}
