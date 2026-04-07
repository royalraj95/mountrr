import {cn} from '@/lib/utils'
import type {Source, SymlinkStatus} from '@/lib/api'

const statusConfig: Record<SymlinkStatus, { label: string; classes: string }> = {
  ok: { label: 'OK', classes: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
  broken: { label: 'Broken', classes: 'bg-red-500/10 text-red-400 border-red-500/20' },
  unknown: { label: 'Unknown', classes: 'bg-amber-500/10 text-amber-400 border-amber-500/20' },
}

const sourceConfig: Record<Source, { label: string; classes: string }> = {
  rd: { label: 'RD', classes: 'bg-blue-500/10 text-blue-400 border-blue-500/20' },
  nzb: { label: 'NZB', classes: 'bg-purple-500/10 text-purple-400 border-purple-500/20' },
  other: { label: 'Other', classes: 'bg-muted text-muted-foreground border-border' },
}

interface StatusBadgeProps {
  status: SymlinkStatus
}

interface SourceBadgeProps {
  source: Source
}

const badgeBase = 'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border'

export function StatusBadge({ status }: StatusBadgeProps) {
  const { label, classes } = statusConfig[status]
  return <span className={cn(badgeBase, classes)}>{label}</span>
}

export function SourceBadge({ source }: SourceBadgeProps) {
  const { label, classes } = sourceConfig[source]
  return <span className={cn(badgeBase, classes)}>{label}</span>
}
