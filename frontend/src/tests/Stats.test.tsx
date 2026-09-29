import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Stats } from '../pages/Stats'

function jsonResponse(ok: boolean, status: number, body: unknown, headers = new Headers()) {
  return {
    ok,
    status,
    headers,
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as Response
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('Stats view', () => {
  it('displays loading state initially', () => {
    globalThis.fetch = vi.fn().mockImplementation(() => new Promise(() => {}))
    render(<Stats />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('renders error message when fetching stats fails', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(jsonResponse(false, 500, { detail: 'Server Error' }))
    render(<Stats />)

    expect(await screen.findByRole('alert')).toHaveTextContent(/could not load stats right now/i)
  })

  it('renders the cache badge from the X-Cache response header and displays metrics', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse(true, 200, { by_category: { water: 2 }, by_priority: { high: 1 }, total: 2 }, new Headers({ 'X-Cache': 'MISS' })),
    )

    render(<Stats />)

    expect(await screen.findByText(/cache: MISS/i)).toBeInTheDocument()
    expect(screen.getByText('2 complaints total')).toBeInTheDocument()
    expect(screen.getByText('water')).toBeInTheDocument()
    expect(screen.getByText('high')).toBeInTheDocument()
  })

  it('triggers a refetch when clicking the refresh button', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse(true, 200, { by_category: { water: 2 }, by_priority: { high: 1 }, total: 2 }, new Headers({ 'X-Cache': 'MISS' })),
      )
      .mockResolvedValueOnce(
        jsonResponse(true, 200, { by_category: { water: 3 }, by_priority: { high: 2 }, total: 3 }, new Headers({ 'X-Cache': 'HIT' })),
      )
    globalThis.fetch = fetchMock

    const user = userEvent.setup()
    render(<Stats />)

    expect(await screen.findByText(/cache: MISS/i)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /refresh/i }))

    expect(await screen.findByText(/cache: HIT/i)).toBeInTheDocument()
    expect(screen.getByText('3 complaints total')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})
