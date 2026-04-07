import {useQuery} from '@tanstack/react-query'
import {Search} from 'lucide-react'
import {useState} from 'react'
import {api} from '@/lib/api'
import {SourceBadge} from '@/components/StatusBadge'
import {formatDate} from '@/lib/utils'

export default function DeletionHistory() {
  const [search, setSearch] = useState('')
  const [sourceFilter, setSourceFilter] = useState('all')

  const { data, isLoading } = useQuery({
    queryKey: ['deletions', search, sourceFilter],
    queryFn: () =>
      api.deletions.list({
        search: search || undefined,
        source: sourceFilter,
        limit: 100,
      }),
  })

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Deletion History</h1>
        {data && (
          <span className="text-sm text-muted-foreground">
            {data.total.toLocaleString()} total deletions
          </span>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
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
        <select
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
          className="px-2 py-1.5 text-sm rounded-md border border-input bg-background focus:outline-none focus:ring-1 focus:ring-ring"
        >
          <option value="all">All sources</option>
          <option value="rd">Real-Debrid</option>
          <option value="nzb">NzbDAV</option>
          <option value="other">Other</option>
        </select>
      </div>

      {/* Table */}
      <div className="rounded-lg border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/30">
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">Symlink Path</th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground w-20">Source</th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground w-32">Reason</th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground w-40">Deleted At</th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground w-20">Arr Search</th>
            </tr>
          </thead>
          <tbody>
            {isLoading &&
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i} className="border-b border-border/50">
                  <td colSpan={5} className="px-3 py-2">
                    <div className="h-4 bg-muted rounded animate-pulse" />
                  </td>
                </tr>
              ))}
            {!isLoading && data?.items.length === 0 && (
              <tr>
                <td colSpan={5} className="px-3 py-8 text-center text-muted-foreground">
                  No deletions recorded yet
                </td>
              </tr>
            )}
            {data?.items.map((row) => (
              <tr
                key={row.id}
                className="border-b border-border/50 hover:bg-muted/20 transition-colors"
              >
                <td
                  className="px-3 py-2 font-mono text-xs max-w-xs truncate"
                  title={row.symlink_path}
                >
                  {row.symlink_path}
                </td>
                <td className="px-3 py-2">
                  {row.source ? (
                    <SourceBadge source={row.source as 'rd' | 'nzb' | 'other'} />
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </td>
                <td className="px-3 py-2 text-muted-foreground">
                  {row.reason.replace(/_/g, ' ')}
                </td>
                <td className="px-3 py-2 text-muted-foreground text-xs">
                  {formatDate(row.deleted_at)}
                </td>
                <td className="px-3 py-2">
                  {row.arr_search_triggered ? (
                    <span className="text-xs text-emerald-400">
                      {row.arr_search_result ?? 'yes'}
                    </span>
                  ) : (
                    <span className="text-xs text-muted-foreground">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
