import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Dashboard } from '../pages/Dashboard'

const complaint = {
  id: 'c-1',
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

function jsonResponse(ok: boolean, status: number, body: unknown) {
  return {
    ok,
    status,
    headers: new Headers(),
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as Response
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('Dashboard view', () => {
  it('lists complaints returned by the API with their category and priority', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse(true, 200, { items: [complaint], total: 1, page: 1, page_size: 20 }),
    )
    render(<Dashboard />)

    expect(await screen.findByText('Street 12')).toBeInTheDocument()
    const row = screen.getByText('Street 12').closest('tr')
    expect(row).not.toBeNull()
    expect(within(row as HTMLElement).getByText('water')).toBeInTheDocument()
  })

  it('surfaces the server 409 message verbatim when a status transition is rejected', async () => {
    globalThis.fetch = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(true, 200, { items: [complaint], total: 1, page: 1, page_size: 20 }))
      .mockResolvedValueOnce(
        jsonResponse(false, 409, { detail: "Cannot transition from 'open' to 'resolved'" }),
      )

    const user = userEvent.setup()
    render(<Dashboard />)

    await screen.findByText('Street 12')
    // "open" only offers in_progress / rejected buttons in the UI, so we
    // simulate the server rejecting an in_progress attempt with its own 409.
    await user.click(screen.getByRole('button', { name: /mark in progress/i }))

    expect(await screen.findByText("Cannot transition from 'open' to 'resolved'")).toBeInTheDocument()
  })
})
