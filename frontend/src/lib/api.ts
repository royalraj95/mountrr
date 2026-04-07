/**
 * Typed API client. All fetch calls go through here — never call fetch directly from pages.
 */

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status} ${text}`)
  }
  return res.json() as Promise<T>
}

// ---- Types ----------------------------------------------------------------

export type Source = 'rd' | 'nzb' | 'other'
export type SymlinkStatus = 'ok' | 'broken' | 'unknown'
export type MountStatus = 'healthy' | 'empty' | 'unreachable'
export type ScanType = 'full' | 'broken_only'

export interface SymlinkRow {
  id: number
  symlink_path: string
  target_path: string
  source: Source
  status: SymlinkStatus
  first_seen: string
  last_checked: string | null
  target_size: number | null
}

export interface SymlinkListResponse {
  items: SymlinkRow[]
  next_cursor: number | null
  total: number
}

export interface ScanHistoryRow {
  id: number
  started_at: string
  completed_at: string | null
  total_symlinks: number | null
  broken_found: number | null
  cleaned: number
  scan_type: ScanType
}

export interface DashboardData {
  total_symlinks: number
  broken_symlinks: number
  by_source: { rd: number; nzb: number; other: number }
  mount_health: { rd: MountStatus; nzb: MountStatus }
  last_scan: ScanHistoryRow | null
  recent_activity: Array<{ event: string; symlink_path: string | null; timestamp: string }>
}

export interface DeletionRow {
  id: number
  symlink_path: string
  target_path: string
  source: string | null
  deleted_at: string
  reason: string
  arr_search_triggered: boolean
  arr_instance: string | null
  arr_search_result: string | null
}

export interface DeletionListResponse {
  items: DeletionRow[]
  next_cursor: number | null
  total: number
}

export interface Settings {
  scan_interval_minutes: number
  dry_run: boolean
  rd_patterns: string[]
  nzb_patterns: string[]
  media_dirs: string[]
  rd_mount_path: string
  nzb_mount_path: string
  log_level: string
}

export interface ScanStatus {
  running: boolean
  scan_id: number | null
  progress: { scanned: number; total_estimate: number } | null
}

// ---- Endpoints ------------------------------------------------------------

export const api = {
  health: () => request<{ status: string; version: string }>('/health'),

  dashboard: () => request<DashboardData>('/dashboard'),

  symlinks: {
    list: (params?: {
      status?: string
      source?: string
      search?: string
      cursor?: number
      limit?: number
    }) => {
      const q = new URLSearchParams()
      if (params?.status) q.set('status', params.status)
      if (params?.source) q.set('source', params.source)
      if (params?.search) q.set('search', params.search)
      if (params?.cursor) q.set('cursor', String(params.cursor))
      if (params?.limit) q.set('limit', String(params.limit))
      return request<SymlinkListResponse>(`/symlinks?${q}`)
    },
    deleteOne: (id: number, dry_run = false) =>
      request<{ deleted: number; skipped: number; dry_run: boolean }>(
        `/symlinks/${id}?dry_run=${dry_run}`,
        { method: 'DELETE' },
      ),
    deleteBulk: (ids: number[], dry_run = false) =>
      request<{ deleted: number; skipped: number; dry_run: boolean }>('/symlinks', {
        method: 'DELETE',
        body: JSON.stringify({ ids, dry_run }),
      }),
  },

  scans: {
    start: (scan_type: ScanType = 'full') =>
      request<{ scan_id: number; status: string }>('/scans/start', {
        method: 'POST',
        body: JSON.stringify({ scan_type }),
      }),
    status: () => request<ScanStatus>('/scans/status'),
    history: (limit = 20) => request<{ items: ScanHistoryRow[] }>(`/scans/history?limit=${limit}`),
  },

  deletions: {
    list: (params?: { cursor?: number; limit?: number; source?: string; search?: string }) => {
      const q = new URLSearchParams()
      if (params?.cursor) q.set('cursor', String(params.cursor))
      if (params?.limit) q.set('limit', String(params.limit))
      if (params?.source) q.set('source', params.source)
      if (params?.search) q.set('search', params.search)
      return request<DeletionListResponse>(`/deletions?${q}`)
    },
    cleanup: (dry_run = false, symlink_ids?: number[]) =>
      request<{ deleted: number; skipped: number; dry_run: boolean }>('/deletions/cleanup', {
        method: 'POST',
        body: JSON.stringify({ dry_run, symlink_ids: symlink_ids ?? null }),
      }),
  },

  settings: {
    get: () => request<Settings>('/settings'),
    update: (patch: Partial<Settings>) =>
      request<{ ok: boolean }>('/settings', {
        method: 'PUT',
        body: JSON.stringify(patch),
      }),
  },

  arr: {
    instances: () => request<{ items: unknown[] }>('/arr/instances'),
    test: (url: string, api_key: string) =>
      request<{ ok: boolean; reachable: boolean }>('/arr/test', {
        method: 'POST',
        body: JSON.stringify({ url, api_key }),
      }),
  },
}
