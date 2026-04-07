import {useQuery, useQueryClient} from '@tanstack/react-query'
import {Search, Trash2} from 'lucide-react'
import {useState} from 'react'
import type {SymlinkRow} from '@/lib/api'
import {api} from '@/lib/api'
import {SourceBadge, StatusBadge} from '@/components/StatusBadge'
import {formatBytes, formatRelative} from '@/lib/utils'

type StatusFilter = 'all' | 'ok' | 'broken' | 'unknown'
type SourceFilter = 'all' | 'rd' | 'nzb' | 'other'

export default function Symlinks() {
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>('all')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [deleting, setDeleting] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['symlinks', statusFilter, sourceFilter, search],
    queryFn: () =>
      api.symlinks.list({
        status: statusFilter,
        source: sourceFilter,
        search: search || undefined,
        limit: 100,
      }),
  })

  function toggleSelect(id: number) {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function selectAll() {
    if (!data) return
    setSelected(new Set(data.items.map((i) => i.id)))
  }

  function clearSelection() {
    setSelected(new Set())
  }

  async function deleteSelected() {
    if (selected.size === 0) return
    setDeleting(true)
    try {
      await api.symlinks.deleteBulk(Array.from(selected))
      setSelected(new Set())
      queryClient.invalidateQueries({ queryKey: ['symlinks'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Symlinks</h1>
        {data && (
          <span className="text-sm text-muted-foreground">
            {data.total.toLocaleString()} total
          </span>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        {/* Search */}
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search paths…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-sm rounded-md border border-input bg-background focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </div>

        {/* Status filter */}
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
          className="px-2 py-1.5 text-sm rounded-md border border-input bg-background focus:outline-none focus:ring-1 focus:ring-ring"
        >
          <option value="all">All statuses</option>
          <option value="ok">OK</option>
          <option value="broken">Broken</option>
          <option value="unknown">Unknown</option>
        </select>

        {/* Source filter */}
        <select
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value as SourceFilter)}
          className="px-2 py-1.5 text-sm rounded-md border border-input bg-background focus:outline-none focus:ring-1 focus:ring-ring"
        >
          <option value="all">All sources</option>
          <option value="rd">Real-Debrid</option>
          <option value="nzb">NzbDAV</option>
          <option value="other">Other</option>
        </select>

        {/* Bulk actions */}
        {selected.size > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">{selected.size} selected</span>
            <button
              onClick={deleteSelected}
              disabled={deleting}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md bg-destructive/80 text-destructive-foreground hover:bg-destructive transition-colors disabled:opacity-50"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Delete
            </button>
            <button
              onClick={clearSelection}
              className="px-2 py-1.5 text-sm rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            >
              Clear
            </button>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="rounded-lg border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/30">
              <th className="w-8 px-3 py-2">
                <input
                  type="checkbox"
                  className="rounded border-input"
                  onChange={(e) => (e.target.checked ? selectAll() : clearSelection())}
                  checked={selected.size > 0 && selected.size === (data?.items.length ?? 0)}
                />
              </th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">Path</th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground w-20">Source</th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground w-24">Status</th>
              <th className="px-3 py-2 text-right font-medium text-muted-foreground w-20">Size</th>
              <th className="px-3 py-2 text-right font-medium text-muted-foreground w-24">Checked</th>
              <th className="w-10" />
            </tr>
          </thead>
          <tbody>
            {isLoading &&
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i} className="border-b border-border/50">
                  <td colSpan={7} className="px-3 py-2">
                    <div className="h-4 bg-muted rounded animate-pulse" />
                  </td>
                </tr>
              ))}
            {!isLoading && data?.items.length === 0 && (
              <tr>
                <td colSpan={7} className="px-3 py-8 text-center text-muted-foreground">
                  No symlinks found
                </td>
              </tr>
            )}
            {data?.items.map((row: SymlinkRow) => (
              <tr
                key={row.id}
                className="border-b border-border/50 hover:bg-muted/20 transition-colors"
              >
                <td className="px-3 py-2">
                  <input
                    type="checkbox"
                    className="rounded border-input"
                    checked={selected.has(row.id)}
                    onChange={() => toggleSelect(row.id)}
                  />
                </td>
                <td className="px-3 py-2 font-mono text-xs max-w-xs truncate" title={row.symlink_path}>
                  {row.symlink_path}
                </td>
                <td className="px-3 py-2">
                  <SourceBadge source={row.source} />
                </td>
                <td className="px-3 py-2">
                  <StatusBadge status={row.status} />
                </td>
                <td className="px-3 py-2 text-right text-muted-foreground tabular-nums">
                  {formatBytes(row.target_size)}
                </td>
                <td className="px-3 py-2 text-right text-muted-foreground">
                  {formatRelative(row.last_checked)}
                </td>
                <td className="px-3 py-2">
                  <button
                    onClick={async () => {
                      await api.symlinks.deleteOne(row.id)
                      queryClient.invalidateQueries({ queryKey: ['symlinks'] })
                      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
                    }}
                    className="p-1 rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                    title="Delete symlink"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
