import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Submit } from '../pages/Submit'

function mockFetchOnce(ok: boolean, status: number, jsonBody: unknown, headers = new Headers()) {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok,
    status,
    headers,
    json: async () => jsonBody,
    text: async () => JSON.stringify(jsonBody),
  } as Response)
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('Submit view', () => {
  it('blocks submission and shows a field error when the description is too short', async () => {
    const user = userEvent.setup()
    render(<Submit />)

    await user.type(screen.getByLabelText(/what's happening/i), 'too short')
    await user.type(screen.getByLabelText(/location/i), 'Street 12')
    await user.click(screen.getByRole('button', { name: /submit report/i }))

    expect(await screen.findByText(/at least 10 characters/i)).toBeInTheDocument()
  })

  it('renders the returned category, priority, summary and provider on success', async () => {
    mockFetchOnce(true, 201, {
      id: 'c-1',
      category: 'water',
      priority: 'high',
      ai_summary: 'Burst main flooding street',
      triaged_by: 'llm:groq',
    })
    const user = userEvent.setup()
    render(<Submit />)

    await user.type(screen.getByLabelText(/what's happening/i), 'Burst water main flooding Street 12')
    await user.type(screen.getByLabelText(/location/i), 'Street 12')
    await user.click(screen.getByRole('button', { name: /submit report/i }))

    expect(await screen.findByTestId('submit-success')).toBeInTheDocument()
    expect(screen.getByText('water')).toBeInTheDocument()
    expect(screen.getByText('llm:groq')).toBeInTheDocument()
  })

  it('shows the Retry-After delay when the server returns 429', async () => {
    mockFetchOnce(false, 429, { detail: 'Rate limit exceeded' }, new Headers({ 'Retry-After': '15' }))
    const user = userEvent.setup()
    render(<Submit />)

    await user.type(screen.getByLabelText(/what's happening/i), 'Burst water main flooding Street 12')
    await user.type(screen.getByLabelText(/location/i), 'Street 12')
    await user.click(screen.getByRole('button', { name: /submit report/i }))

    expect(await screen.findByText(/try again in 15s/i)).toBeInTheDocument()
  })
})
