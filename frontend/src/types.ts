// Mirrors the backend contract exactly (assignment §2.2 / §2.3).
// This file is the single source of truth for shapes on the frontend —
// the frontend never re-decides business rules like valid transitions.

export type Category =
  | 'water'
  | 'electricity'
  | 'sanitation'
  | 'roads'
  | 'streetlights'
  | 'other'

export type Priority = 'high' | 'normal' | 'low'

export type Status = 'open' | 'in_progress' | 'resolved' | 'rejected'

export type TriageProviderType = 'llm:groq' | 'llm:ollama' | 'rules' | 'rules:fallback'

export interface Complaint {
  id: string
  text: string
  location: string
  reporter_contact: string | null
  category: Category
  priority: Priority
  status: Status
  ai_summary: string | null
  triaged_by: TriageProviderType
  triage_latency_ms: number
  created_at: string
  updated_at: string
}

/** Form data payload for submitting a new civic complaint */
export interface ComplaintSubmissionForm {
  text: string
  location: string
  reporter_contact?: string | null
  category?: Category | null
}

/** Request payload for updating a complaint status */
export interface ComplaintUpdateStatusRequest {
  status: Status
}

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface FieldError {
  field: string
  message: string
}

export interface ApiErrorBody {
  detail: string
  errors?: FieldError[]
}

export interface StatsResponse {
  by_category: Record<Category, number>
  by_priority: Record<Priority, number>
  total: number
}

export interface TriageOutcome {
  provider: string
  latency_ms: number
  fallback: boolean
  timestamp: string
}

export interface ProvidersMeta {
  active_provider: string
  recent_outcomes: TriageOutcome[]
}

/** System telemetry metrics response */
export interface TelemetryMetricsResponse {
  active_provider: string
  request_count: number
  average_latency_ms: number
  error_rate: number
  cache_hit_ratio: number
  outcomes: TriageOutcome[]
}

export const CATEGORIES: Category[] = [
  'water',
  'electricity',
  'sanitation',
  'roads',
  'streetlights',
  'other',
]

export const PRIORITIES: Priority[] = ['high', 'normal', 'low']

export const STATUSES: Status[] = ['open', 'in_progress', 'resolved', 'rejected']
