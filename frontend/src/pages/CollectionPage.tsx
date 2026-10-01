import { Plus, Shirt } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { api } from '../api';
import { CostumeCard } from '../components/CostumeCard';
import { Loading } from '../components/Loading';
import type { CostumeSummary } from '../types';

export function CollectionPage() {
  const [costumes, setCostumes] = useState<CostumeSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listCostumes()
      .then(setCostumes)
      .catch((err: Error) => setError(err.message));
  }, []);

  const finished = costumes?.filter((c) => c.progress.percent >= 100).length ?? 0;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Costume collection</h1>
          <p className="subtitle">
            {costumes
              ? `${costumes.length} costumes, ${finished} finished`
              : 'Your saved builds and their progress.'}
          </p>
        </div>
        <Link to="/new" className="btn btn-primary">
          <Plus size={16} /> New costume
        </Link>
      </div>

      {error && <div className="error">{error}</div>}
      {!costumes && !error && <Loading label="Loading collection" />}
      {costumes?.length === 0 && (
        <div className="empty-state">
          <span className="empty-icon">
            <Shirt size={24} />
          </span>
          <h2>No costumes yet</h2>
          <p className="muted">Upload a character image and Cospal will plan the whole build.</p>
          <Link to="/new" className="btn btn-primary">
            <Plus size={16} /> Start your first costume
          </Link>
        </div>
      )}

      <div className="costume-grid">
        {costumes?.map((costume) => (
          <CostumeCard key={costume.id} costume={costume} />
        ))}
      </div>
    </div>
  );
}
