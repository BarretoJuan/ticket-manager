import type { ReactNode } from 'react'
import { cn } from '../../utils/cn'

interface FieldProps {
  id: string
  label: string
  error?: string
  hint?: string
  required?: boolean
  className?: string
  children: ReactNode
}

/** Labelled form field with a hint and an inline, announced error. */
export function Field({
  id,
  label,
  error,
  hint,
  required,
  className,
  children,
}: FieldProps) {
  const errorId = `${id}-error`
  const hintId = `${id}-hint`
  return (
    <div className={cn('space-y-1.5', className)}>
      <label htmlFor={id} className="text-royal block text-sm font-medium">
        {label}
        {required && (
          <span className="ml-0.5 text-red-600" aria-hidden="true">
            *
          </span>
        )}
      </label>
      {children}
      {!error && hint && (
        <p id={hintId} className="text-muted text-xs">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
