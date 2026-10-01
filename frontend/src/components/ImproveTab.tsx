import { Sparkles } from 'lucide-react';
import { useState } from 'react';

import { api } from '../api';
import type { CostumeComponent, ImprovementAdvice } from '../types';
import { ImageDropzone } from './ImageDropzone';

interface ImproveTabProps {
  component: CostumeComponent;
}

export function ImproveTab({ component }: ImproveTabProps) {
  const [notes, setNotes] = useState('');
  const [photos, setPhotos] = useState<File[]>([]);
  const [advice, setAdvice] = useState<ImprovementAdvice | null>(component.improvement);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function ask() {
    setLoading(true);
    setError(null);
    try {
      setAdvice(await api.improve(component.id, notes, photos));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not get advice.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <p className="muted">
        Upload photos of what you have built and the critic agent compares it with the character
        reference.
      </p>
      <ImageDropzone files={photos} onChange={setPhotos} max={4} label="Add photos of your build" />
      <textarea
        className="textarea"
        placeholder="What do you want to improve? e.g. paint looks flat, seams visible"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
      />
      <button className="btn btn-primary" disabled={loading} onClick={ask}>
        <Sparkles size={16} /> {loading ? 'Reviewing…' : 'Get improvement advice'}
      </button>
      {error && <div className="error">{error}</div>}
      {advice && (
        <div className="card" style={{ padding: 16 }}>
          <h3>{advice.summary}</h3>
          <ol className="list" style={{ marginTop: 8 }}>
            {advice.tips.map((tip) => (
              <li key={tip}>{tip}</li>
            ))}
          </ol>
          {advice.next_level.length > 0 && (
            <>
              <p className="eyebrow" style={{ marginTop: 12 }}>
                To take it further
              </p>
              <ul className="list muted">
                {advice.next_level.map((tip) => (
                  <li key={tip}>{tip}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </>
  );
}
