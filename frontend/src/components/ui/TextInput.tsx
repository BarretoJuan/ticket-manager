import { forwardRef, type InputHTMLAttributes } from 'react'
import { cn } from '../../utils/cn'

interface TextInputProps extends InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean
}

export const TextInput = forwardRef<HTMLInputElement, TextInputProps>(
  function TextInput({ invalid, className, ...props }, ref) {
    return (
      <input
        ref={ref}
        aria-invalid={invalid || undefined}
        className={cn(
          'text-royal w-full rounded-lg border bg-white px-3 py-2 text-sm',
          'placeholder:text-muted',
          'focus-visible:outline-2 focus-visible:outline-offset-0',
          invalid ? 'border-red-500' : 'border-gray-300',
          className,
        )}
        {...props}
      />
    )
  },
)
