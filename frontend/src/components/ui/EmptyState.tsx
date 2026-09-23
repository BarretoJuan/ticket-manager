import type { ReactNode } from 'react'
import { cn } from '../../utils/cn'

interface EmptyStateProps {
  icon?: ReactNode
  title: string
  description?: string
  action?: ReactNode
  className?: string
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'border-navy/25 flex flex-col items-center justify-center gap-2 rounded-2xl border border-dashed bg-white px-6 py-12 text-center',
        className,
      )}
    >
      {icon && <div className="text-primary-dark">{icon}</div>}
      <h3 className="text-royal text-base font-semibold">{title}</h3>
      {description && (
        <p className="text-muted max-w-sm text-sm">{description}</p>
      )}
      {action && <div className="mt-3">{action}</div>}
    </div>
  )
}
