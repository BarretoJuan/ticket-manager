import { useContext } from 'react'
import { ToastContext, type ToastType } from '../../context/toast'
import { cn } from '../../utils/cn'
import { IconAlertCircle, IconCheckCircle, IconInfo, IconX } from './icons'

const toastStyles: Record<
  ToastType,
  { icon: React.ReactNode; border: string }
> = {
  success: {
    icon: <IconCheckCircle className="h-5 w-5 text-emerald-600" />,
    border: 'border-emerald-200',
  },
  error: {
    icon: <IconAlertCircle className="h-5 w-5 text-red-600" />,
    border: 'border-red-200',
  },
  info: {
    icon: <IconInfo className="text-royal h-5 w-5" />,
    border: 'border-navy/20',
  },
}

/**
 * Fixed viewport that renders toasts with polite/assertive announcements.
 */
export function ToastViewport() {
  const ctx = useContext(ToastContext)
  if (!ctx) return null
  const { toasts, dismiss } = ctx

  if (toasts.length === 0) return null

  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed inset-x-0 bottom-4 z-[70] flex flex-col items-center gap-2 px-4 sm:right-4 sm:left-auto sm:items-end"
    >
      {toasts.map((toast) => {
        const style = toastStyles[toast.type]
        return (
          <div
            key={toast.id}
            role={toast.type === 'error' ? 'alert' : 'status'}
            className={cn(
              'shadow-lift pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-xl border bg-white p-4',
              style.border,
            )}
          >
            {style.icon}
            <p className="text-royal flex-1 text-sm">{toast.message}</p>
            <button
              type="button"
              onClick={() => dismiss(toast.id)}
              aria-label="Dismiss notification"
              className="text-muted hover:bg-offwhite hover:text-royal rounded-md p-1 transition-colors"
            >
              <IconX className="h-4 w-4" />
            </button>
          </div>
        )
      })}
    </div>
  )
}
