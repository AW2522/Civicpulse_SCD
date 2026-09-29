import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  ApiError,
  createComplaint,
  getComplaint,
  getProviders,
  getStats,
  listComplaints,
  updateStatus,
} from '../api/client'
import type { Complaint } from '../types'

const mockComplaint: Complaint = {
  id: 'abc-123',
  text: 'Burst water main',
  location: 'Street 12',
  reporter_contact: null,
  category: 'water',
  priority: 'high',
  status: 'open',
  ai_summary: 'Burst main flooding street',
  triaged_by: 'llm:groq',
  triage_latency_ms: 400,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

function mockFetchOnce(response: Partial<Response> & { jsonBody?: unknown; rawText?: string }) {
  const { jsonBody, rawText, ...rest } = response
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: rest.ok ?? true,
    status: rest.status ?? 200,
    headers: rest.headers ?? new Headers(),
    json: async () => {
      if (jsonBody === undefined) throw new SyntaxError('Unexpected token in JSON')
      return jsonBody
    },
    text: async () => (rawText !== undefined ? rawText : JSON.stringify(jsonBody ?? {})),
  } as Response)
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('api client', () => {
  it('parses a successful response and returns typed data', async () => {
    mockFetchOnce({
      ok: true,
      status: 201,
      jsonBody: mockComplaint,
    })

    const result = await createComplaint({ text: 'Burst water main flooding', location: 'Street 12' })
    expect(result.id).toBe('abc-123')
    expect(result.category).toBe('water')
    expect(result.priority).toBe('high')
  })

  it('throws an ApiError carrying the parsed body on a non-2xx response', async () => {
    mockFetchOnce({
      ok: false,
      status: 429,
      headers: new Headers({ 'Retry-After': '30' }),
      jsonBody: { detail: 'Rate limit exceeded' },
    })

    await expect(createComplaint({ text: 'x'.repeat(20), location: 'Somewhere' })).rejects.toSatisfy(
      (err: unknown) => {
        expect(err).toBeInstanceOf(ApiError)
        const apiErr = err as ApiError
        expect(apiErr.status).toBe(429)
        expect(apiErr.retryAfterSeconds).toBe(30)
        expect(apiErr.message).toBe('Rate limit exceeded')
        return true
      },
    )
  })

  it('handles non-JSON error responses gracefully', async () => {
    mockFetchOnce({
      ok: false,
      status: 500,
      rawText: 'Internal Server Error',
    })

    await expect(getComplaint('abc-123')).rejects.toSatisfy((err: unknown) => {
      expect(err).toBeInstanceOf(ApiError)
      const apiErr = err as ApiError
      expect(apiErr.status).toBe(500)
      expect(apiErr.body).toBeNull()
      expect(apiErr.message).toBe('Request failed with status 500')
      return true
    })
  })

  it('fetches a single complaint by ID', async () => {
    mockFetchOnce({
      ok: true,
      status: 200,
      jsonBody: mockComplaint,
    })

    const complaint = await getComplaint('abc-123')
    expect(complaint.id).toBe('abc-123')
    expect(complaint.text).toBe('Burst water main')
  })

  it('constructs query strings for listComplaints', async () => {
    mockFetchOnce({
      ok: true,
      status: 200,
      jsonBody: { items: [mockComplaint], total: 1, page: 1, page_size: 20 },
    })

    const result = await listComplaints({ category: 'water', priority: 'high', page: 2 })
    expect(result.total).toBe(1)
    expect(result.items).toHaveLength(1)
    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/complaints?category=water&priority=high&page=2',
      expect.objectContaining({ method: 'GET' }),
    )
  })

  it('updates complaint status via PATCH', async () => {
    const updatedComplaint = { ...mockComplaint, status: 'resolved' as const }
    mockFetchOnce({
      ok: true,
      status: 200,
      jsonBody: updatedComplaint,
    })

    const updated = await updateStatus('abc-123', 'resolved')
    expect(updated.status).toBe('resolved')
    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/complaints/abc-123/status',
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ status: 'resolved' }),
      }),
    )
  })

  it('reads the X-Cache header alongside the stats body', async () => {
    mockFetchOnce({
      ok: true,
      status: 200,
      headers: new Headers({ 'X-Cache': 'HIT' }),
      jsonBody: { by_category: { water: 3 }, by_priority: { high: 1 }, total: 3 },
    })

    const { cacheState, stats } = await getStats()
    expect(cacheState).toBe('HIT')
    expect(stats.total).toBe(3)
  })

  it('fetches providers metadata', async () => {
    mockFetchOnce({
      ok: true,
      status: 200,
      jsonBody: {
        active_provider: 'llm:groq',
        recent_outcomes: [{ provider: 'llm:groq', latency_ms: 350, fallback: false, timestamp: '2026-01-01T00:00:00Z' }],
      },
    })

    const meta = await getProviders()
    expect(meta.active_provider).toBe('llm:groq')
    expect(meta.recent_outcomes).toHaveLength(1)
  })
})
