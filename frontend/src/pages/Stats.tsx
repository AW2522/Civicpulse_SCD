import { useEffect, useState } from 'react'
import { getStats, type StatsResult } from '../api/client'

function Bar({ label, value, max }: { label: string; value: number; max: number }) {
  const pct = max === 0 ? 0 : Math.round((value / max) * 100)
  return (
    <div className="bar-row">
      <span className="bar-label">{label}</span>
      <div className="bar-track">
        <div className="bar-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="bar-value mono">{value}</span>
    </div>
  )
}

export function Stats() {
  const [result, setResult] = useState<StatsResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  // Bumping this triggers the effect below to refetch — used by the
  // Refresh button, which is an event handler and so is free to call
  // setLoading(true) synchronously; the effect itself never does.
  const [refreshToken, setRefreshToken] = useState(0)

  useEffect(() => {
    let cancelled = false

    async function run() {
      try {
        const r = await getStats()
        if (cancelled) return
        setResult(r)
        setError(null)
      } catch {
        if (!cancelled) setError('Could not load stats right now.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    run()
    return () => {
      cancelled = true
    }
  }, [refreshToken])

  function handleRefresh() {
    setLoading(true)
    setRefreshToken((t) => t + 1)
  }

  if (loading) return <div className="panel"><p className="muted">Loading…</p></div>
  if (error) return <div className="panel"><p className="field-error" role="alert">{error}</p></div>
  if (!result) return null

  const { stats, cacheState } = result
  const maxCategory = Math.max(1, ...Object.values(stats.by_category))
  const maxPriority = Math.max(1, ...Object.values(stats.by_priority))

  return (
    <div className="panel">
      <div className="stats-header">
        <h2>Stats</h2>
        {/* Showing cache behaviour in the UI, driven by the real X-Cache header. */}
        <span className={`cache-badge cache-${cacheState.toLowerCase()}`} title="X-Cache header from the last /api/stats response">
          cache: {cacheState}
        </span>
      </div>
      <p className="muted">{stats.total} complaints total</p>

      <h3>By category</h3>
      {Object.entries(stats.by_category).map(([category, value]) => (
        <Bar key={category} label={category} value={value} max={maxCategory} />
      ))}

      <h3>By priority</h3>
      {Object.entries(stats.by_priority).map(([priority, value]) => (
        <Bar key={priority} label={priority} value={value} max={maxPriority} />
      ))}

      <button type="button" onClick={handleRefresh}>Refresh</button>
    </div>
  )
}
