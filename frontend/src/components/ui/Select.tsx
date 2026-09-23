import { forwardRef, type SelectHTMLAttributes } from 'react'
import { cn } from '../../utils/cn'

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  invalid?: boolean
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  function Select({ invalid, className, children, ...props }, ref) {
    return (
      <select
        ref={ref}
        aria-invalid={invalid || undefined}
        className={cn(
          'text-royal w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm',
          'focus-visible:outline-2 focus-visible:outline-offset-0',
          invalid && 'border-red-500',
          className,
        )}
        {...props}
      >
        {children}
      </select>
    )
  },
)
