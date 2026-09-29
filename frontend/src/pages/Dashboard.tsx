import { useEffect, useState } from 'react'
import { ApiError, listComplaints, updateStatus } from '../api/client'
import { CATEGORIES, PRIORITIES, STATUSES, type Category, type Complaint, type Priority, type Status } from '../types'

const PAGE_SIZE = 20

// The frontend does not decide which transitions are valid — it only offers
// the ones a human would plausibly pick next, and surfaces the server's
// verdict (including its 409 message) rather than duplicating the rules.
const NEXT_STATUS_OPTIONS: Record<Status, Status[]> = {
  open: ['in_progress', 'rejected'],
  in_progress: ['resolved', 'rejected'],
  resolved: [],
  rejected: [],
}

interface Filters {
  category: Category | ''
  priority: Priority | ''
  status: Status | ''
}

export function Dashboard() {
  const [filters, setFilters] = useState<Filters>({ category: '', priority: '', status: '' })
  const [page, setPage] = useState(1)
  const [items, setItems] = useState<Complaint[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [transitionErrors, setTransitionErrors] = useState<Record<string, string>>({})

  // Fetch whenever filters/page change. No setState runs synchronously in
  // the effect body itself — the async `run` function's first meaningful
  // statement is the `await`, so every state update happens after that,
  // in a later microtask. `cancelled` guards against a stale response
  // (e.g. from a fast double filter change) overwriting a newer one.
  useEffect(() => {
    let cancelled = false

    async function run() {
      try {
        const result = await listComplaints({
          ...(filters.category ? { category: filters.category } : {}),
          ...(filters.priority ? { priority: filters.priority } : {}),
          ...(filters.status ? { status: filters.status } : {}),
          page,
          page_size: PAGE_SIZE,
        })
        if (cancelled) return
        setItems(result.items)
        setTotal(result.total)
        setLoadError(null)
      } catch (err) {
        if (cancelled) return
        setLoadError(err instanceof ApiError ? err.body?.detail ?? err.message : 'Could not load complaints.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    run()
    return () => {
      cancelled = true
    }
  }, [filters, page])

  function updateFilters(next: Partial<Filters>) {
    setLoading(true)
    setPage(1)
    setFilters((f) => ({ ...f, ...next }))
  }

  function goToPage(next: number) {
    setLoading(true)
    setPage(next)
  }

  async function handleTransition(id: string, next: Status) {
    setTransitionErrors((prev) => ({ ...prev, [id]: '' }))
    try {
      const updated = await updateStatus(id, next)
      setItems((prev) => prev.map((c) => (c.id === id ? updated : c)))
    } catch (err) {
      // The 409 body's `detail` names the attempted transition — shown
      // verbatim, not replaced with a generic "error" string.
      const message =
        err instanceof ApiError && err.status === 409
          ? err.body?.detail ?? 'Invalid status transition.'
          : 'Could not update status. Please try again.'
      setTransitionErrors((prev) => ({ ...prev, [id]: message }))
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="panel">
      <h2>Operations dashboard</h2>

      <div className="filter-bar">
        <label>
          Category
          <select
            value={filters.category}
            onChange={(e) => updateFilters({ category: e.target.value as Category | '' })}
          >
            <option value="">All</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </label>
        <label>
          Priority
          <select
            value={filters.priority}
            onChange={(e) => updateFilters({ priority: e.target.value as Priority | '' })}
          >
            <option value="">All</option>
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </label>
        <label>
          Status
          <select
            value={filters.status}
            onChange={(e) => updateFilters({ status: e.target.value as Status | '' })}
          >
            <option value="">All</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </label>
      </div>

      {loading && <p className="muted">Loading…</p>}
      {loadError && <p className="field-error" role="alert">{loadError}</p>}

      {!loading && !loadError && items.length === 0 && (
        <p className="muted">No complaints match these filters.</p>
      )}

      <table className="complaint-table">
        <thead>
          <tr>
            <th>Location</th>
            <th>Category</th>
            <th>Priority</th>
            <th>Status</th>
            <th>Summary</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {items.map((c) => (
            <tr key={c.id}>
              <td>{c.location}</td>
              <td>{c.category}</td>
              <td><span className={`priority-badge priority-${c.priority}`}>{c.priority}</span></td>
              <td>{c.status}</td>
              <td>{c.ai_summary ?? '—'}</td>
              <td>
                {NEXT_STATUS_OPTIONS[c.status].map((next) => (
                  <button key={next} type="button" onClick={() => handleTransition(c.id, next)}>
                    Mark {next.replace('_', ' ')}
                  </button>
                ))}
                {transitionErrors[c.id] && (
                  <p className="field-error" role="alert">{transitionErrors[c.id]}</p>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="pagination">
        <button type="button" disabled={page <= 1} onClick={() => goToPage(page - 1)}>
          Previous
        </button>
        <span>Page {page} of {totalPages} · {total} total</span>
        <button type="button" disabled={page >= totalPages} onClick={() => goToPage(page + 1)}>
          Next
        </button>
      </div>
    </div>
  )
}
