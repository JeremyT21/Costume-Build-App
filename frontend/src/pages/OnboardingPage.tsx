import { Check, ChevronDown } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';

import { api } from '../api';
import { useApp } from '../appContext';
import { SegmentedControl } from '../components/SegmentedControl';
import { BUILD_LABELS, METHOD_LABELS, MODE_LABELS, formatUsd } from '../labels';
import type { BudgetTier, Build, Measurements, Method, ProfileInput, StartMode } from '../types';

const ALL_METHODS = Object.keys(METHOD_LABELS) as Method[];

const METHOD_PRESETS: { label: string; methods: Method[] }[] = [
  { label: 'Everything', methods: ALL_METHODS },
  { label: '3D print + Amazon', methods: ['3d_print', 'buy'] },
  { label: '3D print only', methods: ['3d_print'] },
  { label: 'Amazon only', methods: ['buy'] },
];

const OVERRIDE_FIELDS: { key: keyof Measurements; label: string }[] = [
  { key: 'chest_cm', label: 'Chest' },
  { key: 'waist_cm', label: 'Waist' },
  { key: 'hips_cm', label: 'Hips' },
  { key: 'head_cm', label: 'Head' },
  { key: 'shoulder_cm', label: 'Shoulder width' },
  { key: 'inseam_cm', label: 'Inseam' },
];

const CM_PER_INCH = 2.54;
const KG_PER_LB = 0.453592;

type Units = 'metric' | 'imperial';

export function OnboardingPage() {
  const { info, profile, setProfile } = useApp();
  const navigate = useNavigate();
  const [units, setUnits] = useState<Units>('metric');
  const [heightCm, setHeightCm] = useState(profile?.height_cm ?? 170);
  const [weightKg, setWeightKg] = useState(profile?.weight_kg ?? 70);
  const [build, setBuild] = useState<Build>(profile?.build ?? 'average');
  const [tier, setTier] = useState<BudgetTier>(profile?.budget_tier ?? 'standard');
  const [mode, setMode] = useState<StartMode>(profile?.default_mode ?? 'mixed');
  const [methods, setMethods] = useState<Method[]>(profile?.allowed_methods ?? ALL_METHODS);
  const [overrides, setOverrides] = useState(profile?.measurement_overrides ?? {});
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const feet = Math.floor(heightCm / CM_PER_INCH / 12);
  const inches = Math.round(heightCm / CM_PER_INCH - feet * 12);

  function toggleMethod(method: Method) {
    setMethods((current) =>
      current.includes(method) ? current.filter((m) => m !== method) : [...current, method],
    );
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (methods.length === 0) {
      setError('Pick at least one way to make or source components.');
      return;
    }
    setSaving(true);
    setError(null);
    const input: ProfileInput = {
      height_cm: Math.round(heightCm * 10) / 10,
      weight_kg: Math.round(weightKg * 10) / 10,
      build,
      budget_tier: tier,
      default_mode: methods.includes('buy') ? mode : 'build_all',
      allowed_methods: methods,
      measurement_overrides: overrides,
    };
    try {
      const saved = await api.saveProfile(input);
      setProfile(saved);
      if (!profile) navigate('/new');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save your profile.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="page page-narrow" onSubmit={submit}>
      <div className="page-header">
        <div>
          <h1>{profile ? 'Sizing & budget' : 'Welcome to Cospal'}</h1>
          <p className="subtitle">
            A quick survey so every pattern, product, and 3D part is sized to you.
          </p>
        </div>
      </div>

      <section className="card">
        <div className="section-title">
          <h2>Your body</h2>
          <SegmentedControl
            ariaLabel="Units"
            value={units}
            onChange={setUnits}
            options={[
              { value: 'metric', label: 'cm / kg' },
              { value: 'imperial', label: 'ft / lb' },
            ]}
          />
        </div>
        <div className="grid-2">
          <label className="field">
            <span className="field-label">Height</span>
            {units === 'metric' ? (
              <input
                className="input"
                type="number"
                min={100}
                max={240}
                value={heightCm}
                onChange={(e) => setHeightCm(Number(e.target.value))}
              />
            ) : (
              <div className="input-group">
                <input
                  className="input"
                  type="number"
                  min={3}
                  max={7}
                  aria-label="Feet"
                  value={feet}
                  onChange={(e) =>
                    setHeightCm((Number(e.target.value) * 12 + inches) * CM_PER_INCH)
                  }
                />
                <input
                  className="input"
                  type="number"
                  min={0}
                  max={11}
                  aria-label="Inches"
                  value={inches}
                  onChange={(e) => setHeightCm((feet * 12 + Number(e.target.value)) * CM_PER_INCH)}
                />
              </div>
            )}
          </label>
          <label className="field">
            <span className="field-label">Weight</span>
            <input
              className="input"
              type="number"
              min={20}
              max={units === 'metric' ? 300 : 660}
              value={units === 'metric' ? weightKg : Math.round(weightKg / KG_PER_LB)}
              onChange={(e) =>
                setWeightKg(
                  units === 'metric' ? Number(e.target.value) : Number(e.target.value) * KG_PER_LB,
                )
              }
            />
          </label>
        </div>
        <p className="field-label" style={{ margin: '18px 0 8px' }}>
          Overall build
        </p>
        <div className="tiles">
          {(Object.keys(BUILD_LABELS) as Build[]).map((option) => (
            <button
              type="button"
              key={option}
              className={`tile${build === option ? ' selected' : ''}`}
              onClick={() => setBuild(option)}
            >
              <span className="tile-title">{BUILD_LABELS[option].label}</span>
              <span className="tile-hint">{BUILD_LABELS[option].hint}</span>
            </button>
          ))}
        </div>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          style={{ marginTop: 14 }}
          onClick={() => setShowAdvanced((v) => !v)}
        >
          <ChevronDown size={14} style={{ rotate: showAdvanced ? '180deg' : '0deg' }} />
          I know some exact measurements (cm)
        </button>
        {showAdvanced && (
          <div className="grid-3" style={{ marginTop: 10 }}>
            {OVERRIDE_FIELDS.map(({ key, label }) => (
              <label className="field" key={key}>
                <span className="faint">{label}</span>
                <input
                  className="input"
                  type="number"
                  placeholder={profile ? String(profile.measurements[key]) : 'Auto'}
                  value={overrides[key] ?? ''}
                  onChange={(e) =>
                    setOverrides((current) => {
                      const next = { ...current };
                      if (e.target.value) next[key] = Number(e.target.value);
                      else delete next[key];
                      return next;
                    })
                  }
                />
              </label>
            ))}
          </div>
        )}
        {profile && (
          <p className="faint" style={{ marginTop: 14 }}>
            Estimated size {profile.letter_size}: chest {profile.measurements.chest_cm} cm, waist{' '}
            {profile.measurements.waist_cm} cm, head {profile.measurements.head_cm} cm
          </p>
        )}
      </section>

      <section className="card">
        <div className="section-title">
          <h2>Budget</h2>
        </div>
        <div className="tiles">
          {info?.budget_tiers.map((option) => (
            <button
              type="button"
              key={option.tier}
              className={`tile${tier === option.tier ? ' selected' : ''}`}
              onClick={() => setTier(option.tier)}
            >
              <span className="tile-title">{option.label}</span>
              <span className="tile-hint">
                {option.max_usd === null
                  ? `${formatUsd(option.min_usd)}+`
                  : `${formatUsd(option.min_usd)} – ${formatUsd(option.max_usd)}`}
              </span>
            </button>
          ))}
        </div>
        <p className="faint" style={{ marginTop: 10 }}>
          {info?.budget_tiers.find((t) => t.tier === tier)?.guidance}
        </p>
      </section>

      <section className="card">
        <div className="section-title">
          <h2>How do you want to make costumes?</h2>
        </div>
        <div className="row" style={{ marginBottom: 12 }}>
          {METHOD_PRESETS.map((preset) => {
            const active =
              preset.methods.length === methods.length &&
              preset.methods.every((m) => methods.includes(m));
            return (
              <button
                type="button"
                key={preset.label}
                className={`chip${active ? ' active' : ''}`}
                onClick={() => setMethods(preset.methods)}
              >
                {preset.label}
              </button>
            );
          })}
        </div>
        <div className="tiles">
          {ALL_METHODS.map((method) => (
            <button
              type="button"
              key={method}
              className={`tile${methods.includes(method) ? ' selected' : ''}`}
              onClick={() => toggleMethod(method)}
            >
              <span className="row tile-title">
                {methods.includes(method) && <Check size={14} />}
                {METHOD_LABELS[method]}
              </span>
            </button>
          ))}
        </div>
        <p className="field-label" style={{ margin: '18px 0 8px' }}>
          Default starting point
        </p>
        <div className="tiles">
          {(Object.keys(MODE_LABELS) as StartMode[]).map((option) => (
            <button
              type="button"
              key={option}
              disabled={option === 'buy_all' && !methods.includes('buy')}
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
        <button className="btn btn-primary btn-lg" disabled={saving}>
          {saving ? 'Saving…' : profile ? 'Save changes' : 'Continue'}
        </button>
      </div>
    </form>
  );
}
