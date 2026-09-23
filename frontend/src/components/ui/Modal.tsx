import { useEffect, useId, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { cn } from '../../utils/cn'
import { IconX } from './icons'

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'

interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  description?: string
  children: ReactNode
  footer?: ReactNode
  /** Disables Escape/backdrop dismissal while an async action is running. */
  busy?: boolean
}

/**
 * Accessible dialog: role=dialog + aria-modal, focus trap, Escape to close,
 * focus restored to the trigger on close, body scroll locked while open.
 */
export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  busy = false,
}: ModalProps) {
  const titleId = useId()
  const panelRef = useRef<HTMLDivElement>(null)
  const previousFocus = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (!open) return
    previousFocus.current = document.activeElement as HTMLElement | null

    const panel = panelRef.current
    if (panel) {
      const first = panel.querySelector<HTMLElement>(FOCUSABLE_SELECTOR)
      ;(first ?? panel).focus()
    }
    document.body.style.overflow = 'hidden'

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !busy) {
        event.preventDefault()
        onClose()
        return
      }
      if (event.key === 'Tab' && panel) {
        const focusable = Array.from(
          panel.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
        )
        if (focusable.length === 0) return
        const first = focusable[0]
        const last = focusable[focusable.length - 1]
        const active = document.activeElement
        if (event.shiftKey && (active === first || !panel.contains(active))) {
          event.preventDefault()
          last.focus()
        } else if (!event.shiftKey && active === last) {
          event.preventDefault()
          first.focus()
        }
      }
    }

    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = ''
      previousFocus.current?.focus()
    }
  }, [open, onClose, busy])

  if (!open) return null

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center">
      <div
        className="bg-obsidian/60 absolute inset-0"
        aria-hidden="true"
        onClick={busy ? undefined : onClose}
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="shadow-lift relative max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-6"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id={titleId} className="text-royal text-lg font-semibold">
              {title}
            </h2>
            {description && (
              <p className="text-muted mt-1 text-sm">{description}</p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            aria-label="Close dialog"
            className={cn(
              'text-muted hover:bg-offwhite hover:text-royal rounded-lg p-1.5 transition-colors',
              busy && 'cursor-not-allowed opacity-50',
            )}
          >
            <IconX className="h-5 w-5" />
          </button>
        </div>
        <div className="mt-5">{children}</div>
        {footer && (
          <div className="mt-6 flex flex-col-reverse justify-end gap-2 sm:flex-row sm:gap-3">
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body,
  )
}
