import { LayoutGrid, Plus, Ruler, Sparkles } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom';

import { api } from './api';
import { AppContext, type AppState } from './appContext';
import { Loading } from './components/Loading';
import { useMotionPreference } from './motion';
import { CollectionPage } from './pages/CollectionPage';
import { CostumePage } from './pages/CostumePage';
import { NewCostumePage } from './pages/NewCostumePage';
import { OnboardingPage } from './pages/OnboardingPage';
import type { AppInfo, Profile } from './types';

const NAV_ITEMS = [
  { to: '/', label: 'Collection', icon: LayoutGrid },
  { to: '/new', label: 'New costume', icon: Plus },
  { to: '/profile', label: 'Sizing & budget', icon: Ruler },
];

export function App() {
  const [info, setInfo] = useState<AppInfo | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loaded, setLoaded] = useState(false);
  const location = useLocation();
  const [motion, setMotion] = useMotionPreference();

  useEffect(() => {
    Promise.all([api.info(), api.getProfile()])
      .then(([appInfo, savedProfile]) => {
        setInfo(appInfo);
        setProfile(savedProfile);
      })
      .finally(() => setLoaded(true));
  }, []);

  const state = useMemo<AppState>(() => ({ info, profile, setProfile }), [info, profile]);

  if (!loaded) return <Loading label="Loading Cospal" />;
  const needsOnboarding = !profile && location.pathname !== '/profile';

  return (
    <AppContext.Provider value={state}>
      <div className="app-shell">
        <aside className="sidebar">
          <div className="brand">
            <span className="brand-mark">
              <Sparkles size={16} />
            </span>
            Cospal
          </div>
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
            >
              <Icon size={17} />
              <span>{label}</span>
            </NavLink>
          ))}
          <div className="sidebar-footer">
            <button
              type="button"
              className="toggle"
              role="switch"
              aria-checked={motion}
              onClick={() => setMotion(!motion)}
            >
              Animations
              <span className="toggle-track" />
            </button>
            <span>{info?.ai_enabled ? `Agents on ${info.model.split(':').pop()}` : 'Offline mode'}</span>
          </div>
        </aside>
        <main className="main">
          {needsOnboarding ? (
            <Navigate to="/profile" replace />
          ) : (
            <Routes>
              <Route path="/" element={<CollectionPage />} />
              <Route path="/new" element={<NewCostumePage />} />
              <Route path="/profile" element={<OnboardingPage />} />
              <Route path="/costumes/:costumeId" element={<CostumePage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          )}
        </main>
      </div>
    </AppContext.Provider>
  );
}
