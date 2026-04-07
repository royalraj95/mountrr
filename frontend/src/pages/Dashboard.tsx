import {useQuery, useQueryClient} from '@tanstack/react-query'
import {AlertTriangle, Link2, RefreshCw, Trash2} from 'lucide-react'
import {useState} from 'react'
import {api} from '@/lib/api'
import {StatCard} from '@/components/StatCard'
import {MountHealthBadge} from '@/components/MountHealthBadge'
import {formatRelative} from '@/lib/utils'

export default function Dashboard() {
  const queryClient = useQueryClient()
  const [scanning, setScanning] = useState(false)
  const [cleaning, setCleaning] = useState(false)
  const [cleanResult, setCleanResult] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: api.dashboard,
    refetchInterval: 30_000,
  })

  async function handleScan() {
    setScanning(true)
    try {
      await api.scans.start('full')
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    } finally {
      setScanning(false)
    }
  }

  async function handleClean() {
    setCleaning(true)
    setCleanResult(null)
    try {
      const result = await api.deletions.cleanup(false)
      setCleanResult(`Deleted ${result.deleted} symlink(s), skipped ${result.skipped}`)
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['symlinks'] })
      queryClient.invalidateQueries({ queryKey: ['deletions'] })
    } finally {
      setCleaning(false)
    }
  }

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <div className="h-8 w-40 bg-muted rounded animate-pulse" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 bg-muted rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          {data.last_scan && (
            <p className="text-sm text-muted-foreground mt-0.5">
              Last scan {formatRelative(data.last_scan.started_at)}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleScan}
            disabled={scanning}
            className="flex items-center gap-2 px-3 py-2 rounded-md bg-secondary text-secondary-foreground text-sm hover:bg-accent transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${scanning ? 'animate-spin' : ''}`} />
            {scanning ? 'Scanning…' : 'Scan Now'}
          </button>
          {data.broken_symlinks > 0 && (
            <button
              onClick={handleClean}
              disabled={cleaning}
              className="flex items-center gap-2 px-3 py-2 rounded-md bg-destructive/80 text-destructive-foreground text-sm hover:bg-destructive transition-colors disabled:opacity-50"
            >
              <Trash2 className="w-4 h-4" />
              {cleaning ? 'Cleaning…' : `Clean ${data.broken_symlinks} Broken`}
            </button>
          )}
        </div>
      </div>

      {cleanResult && (
        <div className="rounded-md border border-emerald-500/20 bg-emerald-500/10 text-emerald-400 px-4 py-2 text-sm">
          {cleanResult}
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Symlinks"
          value={data.total_symlinks.toLocaleString()}
          icon={Link2}
          variant="default"
        />
        <StatCard
          label="Broken"
          value={data.broken_symlinks.toLocaleString()}
          icon={AlertTriangle}
          variant={data.broken_symlinks > 0 ? 'danger' : 'success'}
        />
        <StatCard
          label="Real-Debrid"
          value={data.by_source.rd.toLocaleString()}
          icon={Link2}
          variant="default"
          sub="symlinks"
        />
        <StatCard
          label="NzbDAV"
          value={data.by_source.nzb.toLocaleString()}
          icon={Link2}
          variant="default"
          sub="symlinks"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Mount Health */}
        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="text-sm font-semibold mb-3">Mount Health</h2>
          <div className="space-y-2">
            <MountHealthBadge mount="rd" status={data.mount_health.rd} />
            <MountHealthBadge mount="nzb" status={data.mount_health.nzb} />
          </div>
          {(data.mount_health.rd !== 'healthy' || data.mount_health.nzb !== 'healthy') && (
            <p className="mt-3 text-xs text-amber-400">
              Symlinks will not be marked broken while a mount is unreachable or empty.
            </p>
          )}
        </div>

        {/* Recent Activity */}
        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="text-sm font-semibold mb-3">Recent Activity</h2>
          {data.recent_activity.length === 0 ? (
            <p className="text-sm text-muted-foreground">No recent activity</p>
          ) : (
            <ul className="space-y-1.5">
              {data.recent_activity.slice(0, 8).map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-xs">
                  <span className="text-muted-foreground shrink-0 mt-0.5">
                    {formatRelative(item.timestamp)}
                  </span>
                  <span className="text-foreground truncate">{item.symlink_path ?? item.event}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Last scan details */}
      {data.last_scan && (
        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="text-sm font-semibold mb-3">Last Scan</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground text-xs">Started</p>
              <p>{formatRelative(data.last_scan.started_at)}</p>
            </div>
            <div>
              <p className="text-muted-foreground text-xs">Type</p>
              <p className="capitalize">{data.last_scan.scan_type.replace('_', ' ')}</p>
            </div>
            <div>
              <p className="text-muted-foreground text-xs">Scanned</p>
              <p>{data.last_scan.total_symlinks?.toLocaleString() ?? '—'}</p>
            </div>
            <div>
              <p className="text-muted-foreground text-xs">Broken Found</p>
              <p className={data.last_scan.broken_found ? 'text-red-400' : 'text-emerald-400'}>
                {data.last_scan.broken_found?.toLocaleString() ?? '—'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
