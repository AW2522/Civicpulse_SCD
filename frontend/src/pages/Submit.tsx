import { useState, type FormEvent } from 'react'
import { ApiError, createComplaint } from '../api/client'
import type { Complaint } from '../types'

// Mirrors the server rules stated in the spec (§2.3) so a citizen gets fast
// feedback — but the server re-validates everything; this is UX, not trust.
const TEXT_MIN = 10
const TEXT_MAX = 2000
const LOCATION_MIN = 3
const LOCATION_MAX = 200

interface FieldErrors {
  text?: string
  location?: string
}

function validate(text: string, location: string): FieldErrors {
  const errors: FieldErrors = {}
  if (text.trim().length < TEXT_MIN) {
    errors.text = `Description must be at least ${TEXT_MIN} characters.`
  } else if (text.length > TEXT_MAX) {
    errors.text = `Description must be ${TEXT_MAX} characters or fewer.`
  }
  if (location.trim().length < LOCATION_MIN) {
    errors.location = `Location must be at least ${LOCATION_MIN} characters.`
  } else if (location.length > LOCATION_MAX) {
    errors.location = `Location must be ${LOCATION_MAX} characters or fewer.`
  }
  return errors
}

type SubmitState =
  | { phase: 'idle' }
  | { phase: 'submitting' }
  | { phase: 'done'; complaint: Complaint }
  | { phase: 'error'; message: string; retryAfterSeconds: number | null }

export function Submit() {
  const [text, setText] = useState('')
  const [location, setLocation] = useState('')
  const [reporterContact, setReporterContact] = useState('')
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [state, setState] = useState<SubmitState>({ phase: 'idle' })

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const errors = validate(text, location)
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setState({ phase: 'submitting' })
    const contact = reporterContact.trim()
    try {
      const complaint = await createComplaint({
        text: text.trim(),
        location: location.trim(),
        ...(contact ? { reporter_contact: contact } : {}),
      })
      setState({ phase: 'done', complaint })
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 429) {
          setState({
            phase: 'error',
            message: 'Too many reports submitted from this connection right now.',
            retryAfterSeconds: err.retryAfterSeconds,
          })
          return
        }
        if (err.status === 400 && err.body?.errors) {
          const next: FieldErrors = {}
          for (const fe of err.body.errors) {
            if (fe.field === 'text' || fe.field === 'location') next[fe.field] = fe.message
          }
          setFieldErrors(next)
          setState({ phase: 'idle' })
          return
        }
        setState({ phase: 'error', message: err.body?.detail ?? err.message, retryAfterSeconds: null })
        return
      }
      setState({ phase: 'error', message: 'Could not reach the server. Please try again.', retryAfterSeconds: null })
    }
  }

  function handleReset() {
    setText('')
    setLocation('')
    setReporterContact('')
    setFieldErrors({})
    setState({ phase: 'idle' })
  }

  if (state.phase === 'done') {
    const c = state.complaint
    return (
      <div className="panel" data-testid="submit-success">
        <h2>Report received</h2>
        <p className="muted">Reference: <span className="mono">{c.id}</span></p>
        <dl className="result-grid">
          <dt>Category</dt>
          <dd>{c.category}</dd>
          <dt>Priority</dt>
          <dd>
            <span className={`priority-badge priority-${c.priority}`}>{c.priority}</span>
          </dd>
          <dt>Summary</dt>
          <dd>{c.ai_summary ?? '—'}</dd>
          <dt>Triaged by</dt>
          <dd className="mono">{c.triaged_by}</dd>
        </dl>
        <button type="button" onClick={handleReset}>
          Submit another report
        </button>
      </div>
    )
  }

  const submitting = state.phase === 'submitting'

  return (
    <div className="panel">
      <h2>Report a problem</h2>
      <p className="muted">
        Describe what you're seeing. A short automated triage step reads your report and
        assigns a category and priority — this can take a few seconds.
      </p>
      <form onSubmit={handleSubmit} noValidate>
        <label htmlFor="text">What's happening?</label>
        <textarea
          id="text"
          rows={4}
          value={text}
          onChange={(e) => setText(e.target.value)}
          aria-invalid={Boolean(fieldErrors.text)}
          aria-describedby={fieldErrors.text ? 'text-error' : undefined}
          disabled={submitting}
        />
        {fieldErrors.text && (
          <p className="field-error" id="text-error">{fieldErrors.text}</p>
        )}

        <label htmlFor="location">Location</label>
        <input
          id="location"
          type="text"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          aria-invalid={Boolean(fieldErrors.location)}
          aria-describedby={fieldErrors.location ? 'location-error' : undefined}
          disabled={submitting}
        />
        {fieldErrors.location && (
          <p className="field-error" id="location-error">{fieldErrors.location}</p>
        )}

        <label htmlFor="contact">Contact (optional)</label>
        <input
          id="contact"
          type="text"
          value={reporterContact}
          onChange={(e) => setReporterContact(e.target.value)}
          disabled={submitting}
        />

        {state.phase === 'error' && (
          <p className="field-error" role="alert">
            {state.message}
            {state.retryAfterSeconds !== null && ` Try again in ${state.retryAfterSeconds}s.`}
          </p>
        )}

        <button type="submit" disabled={submitting}>
          {submitting ? 'Triaging your report…' : 'Submit report'}
        </button>
      </form>
    </div>
  )
}
