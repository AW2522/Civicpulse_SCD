import type {
  ApiErrorBody,
  Category,
  Complaint,
  Paginated,
  Priority,
  ProvidersMeta,
  Status,
  StatsResponse,
} from '../types'

// Relative path only — deliberately no absolute backend origin here.
// In production nginx proxies /api to the backend container; in dev, Vite's
// server.proxy does the same. See docs/adr/0002-frontend-runtime-config.md.
const BASE_URL = '/api'

export class ApiError extends Error {
  status: number
  body: ApiErrorBody | null
  retryAfterSeconds: number | null

  constructor(status: number, body: ApiErrorBody | null, retryAfterSeconds: number | null) {
    super(body?.detail ?? `Request failed with status ${status}`)
    this.name = 'ApiError'
    this.status = status
    this.body = body
    this.retryAfterSeconds = retryAfterSeconds
  }
}

/** Core request handler with headers, interceptors, and error handling */
export async function request<T>(path: string, init?: RequestInit): Promise<{ data: T; headers: Headers }> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  })

  if (!res.ok) {
    let body: ApiErrorBody | null = null
    try {
      body = await res.json()
    } catch {
      // No JSON body on this error response — leave body as null.
    }
    const retryAfterHeader = res.headers.get('Retry-After')
    throw new ApiError(res.status, body, retryAfterHeader ? Number(retryAfterHeader) : null)
  }

  // 204s and similar have no body to parse.
  const text = await res.text()
  const data = (text ? JSON.parse(text) : null) as T
  return { data, headers: res.headers }
}

/** Generic GET helper function */
export function get<T>(path: string, init?: RequestInit): Promise<T> {
  return request<T>(path, { ...init, method: 'GET' }).then((r) => r.data)
}

/** Generic POST helper function */
export function post<T>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
  return request<T>(path, {
    ...init,
    method: 'POST',
    body: body !== undefined ? JSON.stringify(body) : undefined,
  }).then((r) => r.data)
}

export interface CreateComplaintInput {
  text: string
  location: string
  reporter_contact?: string
}

export function createComplaint(input: CreateComplaintInput): Promise<Complaint> {
  return post<Complaint>('/complaints', input)
}

export function getComplaint(id: string): Promise<Complaint> {
  return get<Complaint>(`/complaints/${id}`)
}

export interface ListComplaintsParams {
  category?: Category
  priority?: Priority
  status?: Status
  page?: number
  page_size?: number
}

export function listComplaints(params: ListComplaintsParams = {}): Promise<Paginated<Complaint>> {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') query.set(key, String(value))
  }
  const qs = query.toString()
  return get<Paginated<Complaint>>(`/complaints${qs ? `?${qs}` : ''}`)
}

export function updateStatus(id: string, status: Status): Promise<Complaint> {
  return request<Complaint>(`/complaints/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  }).then((r) => r.data)
}

export interface StatsResult {
  stats: StatsResponse
  cacheState: 'HIT' | 'MISS' | 'UNKNOWN'
}

export async function getStats(): Promise<StatsResult> {
  const { data, headers } = await request<StatsResponse>('/stats')
  const cacheHeader = headers.get('X-Cache')
  const cacheState: StatsResult['cacheState'] =
    cacheHeader === 'HIT' || cacheHeader === 'MISS' ? cacheHeader : 'UNKNOWN'
  return { stats: data, cacheState }
}

export function getProviders(): Promise<ProvidersMeta> {
  return get<ProvidersMeta>('/meta/providers')
}
