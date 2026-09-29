import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Stats } from '../pages/Stats'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('Stats view', () => {
  it('renders the cache badge from the X-Cache response header', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'X-Cache': 'MISS' }),
      json: async () => ({ by_category: { water: 2 }, by_priority: { high: 1 }, total: 2 }),
      text: async () => JSON.stringify({ by_category: { water: 2 }, by_priority: { high: 1 }, total: 2 }),
    } as Response)

    render(<Stats />)

    expect(await screen.findByText(/cache: MISS/i)).toBeInTheDocument()
    expect(screen.getByText('2 complaints total')).toBeInTheDocument()
  })
})
