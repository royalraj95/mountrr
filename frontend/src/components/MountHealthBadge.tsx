import {cn} from '@/lib/utils'
import type {MountStatus} from '@/lib/api'

const config: Record<MountStatus, { label: string; dot: string; text: string }> = {
  healthy: { label: 'Healthy', dot: 'bg-emerald-400', text: 'text-emerald-400' },
  empty: { label: 'Empty', dot: 'bg-amber-400', text: 'text-amber-400' },
  unreachable: { label: 'Unreachable', dot: 'bg-red-400', text: 'text-red-400' },
}

interface MountHealthBadgeProps {
  mount: string
  status: MountStatus
}

export function MountHealthBadge({ mount, status }: MountHealthBadgeProps) {
  const { label, dot, text } = config[status]
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-muted-foreground font-mono uppercase text-xs w-8">{mount}</span>
      <span className={cn('flex items-center gap-1.5 font-medium', text)}>
        <span className={cn('w-2 h-2 rounded-full', dot)} />
        {label}
      </span>
    </div>
  )
}
