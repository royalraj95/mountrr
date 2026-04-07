import {cn} from '@/lib/utils'
import type {LucideIcon} from 'lucide-react'

interface StatCardProps {
  label: string
  value: string | number
  icon: LucideIcon
  variant?: 'default' | 'danger' | 'warning' | 'success'
  sub?: string
}

const variantStyles = {
  default: 'text-foreground',
  danger: 'text-red-400',
  warning: 'text-amber-400',
  success: 'text-emerald-400',
}

const iconStyles = {
  default: 'bg-primary/10 text-primary',
  danger: 'bg-red-500/10 text-red-400',
  warning: 'bg-amber-500/10 text-amber-400',
  success: 'bg-emerald-500/10 text-emerald-400',
}

export function StatCard({ label, value, icon: Icon, variant = 'default', sub }: StatCardProps) {
  return (
    <div className="rounded-lg border border-border bg-card p-4 flex items-start gap-4">
      <div className={cn('p-2 rounded-md shrink-0', iconStyles[variant])}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="min-w-0">
        <p className="text-sm text-muted-foreground truncate">{label}</p>
        <p className={cn('text-2xl font-bold tabular-nums', variantStyles[variant])}>{value}</p>
        {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}
