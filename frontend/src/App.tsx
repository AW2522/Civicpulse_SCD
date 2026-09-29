import { useState } from 'react'
import { Dashboard } from './pages/Dashboard'
import { Stats } from './pages/Stats'
import { Submit } from './pages/Submit'
import { ErrorBoundary } from './ErrorBoundary'

type View = 'submit' | 'dashboard' | 'stats'

const VIEWS: { id: View; label: string }[] = [
  { id: 'submit', label: 'Report a problem' },
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'stats', label: 'Stats' },
]

export default function App() {
  const [view, setView] = useState<View>('submit')

  return (
    <div className="app-shell">
      <header className="app-header">
        <span className="app-title">CivicPulse</span>
        <nav aria-label="Views">
          {VIEWS.map((v) => (
            <button
              key={v.id}
              type="button"
              className={v.id === view ? 'nav-tab active' : 'nav-tab'}
              onClick={() => setView(v.id)}
              aria-current={v.id === view ? 'page' : undefined}
            >
              {v.label}
            </button>
          ))}
        </nav>
      </header>
      <main>
        <ErrorBoundary key={view}>
          {view === 'submit' && <Submit />}
          {view === 'dashboard' && <Dashboard />}
          {view === 'stats' && <Stats />}
        </ErrorBoundary>
      </main>
    </div>
  )
}
