import type { ReactNode } from 'react'
import { cn } from '../../utils/cn'

type BadgeTone = 'success' | 'processing' | 'error' | 'info' | 'neutral'

const tones: Record<BadgeTone, string> = {
  success: 'bg-emerald-50 text-emerald-800 ring-emerald-600/25',
  processing: 'bg-amber-50 text-amber-800 ring-amber-600/25',
  error: 'bg-red-50 text-red-800 ring-red-600/25',
  info: 'bg-royal/10 text-royal ring-royal/25',
  neutral: 'bg-gray-100 text-gray-700 ring-gray-500/20',
}

interface BadgeProps {
  tone?: BadgeTone
  children: ReactNode
  className?: string
}

export function Badge({ tone = 'neutral', children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset',
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  )
}
