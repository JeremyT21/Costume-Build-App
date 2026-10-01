import { Check, ExternalLink, RefreshCw, ShoppingCart, Star } from 'lucide-react';

import { api } from '../api';
import { formatUsd } from '../labels';
import type { DrawerTabProps } from './drawerTab';

interface BuyTabProps extends DrawerTabProps {
  canBuy: boolean;
  onBought: () => void;
}

export function BuyTab({ component, canBuy, busy, run, onBought }: BuyTabProps) {
  if (!canBuy) {
    return <div className="callout-note">Buying is turned off in your sizing & budget preferences.</div>;
  }
  return (
    <>
      <div className="section-title" style={{ marginBottom: 0 }}>
        <h3>Recommended products</h3>
        <button
          className="btn btn-sm"
          disabled={busy !== null}
          onClick={() => run('products', () => api.refreshProducts(component.id))}
        >
          <RefreshCw size={14} /> {busy === 'products' ? 'Searching…' : 'Search again'}
        </button>
      </div>
      {component.products.length === 0 && <p className="muted">No products yet. Search to find options.</p>}
      {component.products.map((product) => (
        <div className="product" key={product.url}>
          <div className="product-img">
            {product.image_url ? <img src={product.image_url} alt="" /> : <ShoppingCart size={20} />}
          </div>
          <div style={{ minWidth: 0 }}>
            <strong style={{ display: 'block' }}>{product.title}</strong>
            <span className="faint">
              {product.price != null && `${formatUsd(product.price)}  `}
              {product.rating != null && (
                <>
                  <Star size={11} /> {product.rating} ({product.review_count ?? 0})
                </>
              )}
              {product.source === 'search_link' && 'Opens Amazon search results'}
            </span>
            {product.reason && <p className="muted" style={{ fontSize: 13 }}>{product.reason}</p>}
          </div>
          <a className="btn btn-sm" href={product.url} target="_blank" rel="noreferrer">
            <ExternalLink size={14} /> View
          </a>
        </div>
      ))}
      {component.sizing && (
        <div className="card" style={{ padding: 16 }}>
          <p className="eyebrow">Size advice from the fit agent</p>
          <h3 style={{ margin: '4px 0' }}>
            Order {component.sizing.recommended_size}{' '}
            <span className="faint">({component.sizing.confidence} confidence)</span>
          </h3>
          <p className="muted">{component.sizing.fit_notes}</p>
          {component.sizing.review_insights.length > 0 && (
            <ul className="list muted" style={{ marginTop: 8 }}>
              {component.sizing.review_insights.map((insight) => (
                <li key={insight}>{insight}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      {component.status !== 'completed' && (
        <button className="btn btn-primary" onClick={onBought}>
          <Check size={16} /> I bought this
        </button>
      )}
    </>
  );
}
