import {
  cloneElement,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type ReactElement,
  type ReactNode,
} from 'react'
import { cn } from '../../utils/cn'
import { Spinner } from './Spinner'

type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'
type ButtonSize = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  icon?: ReactNode
  fullWidth?: boolean
  /** Render a single child element (e.g. a router <Link>) with the button styles. */
  asChild?: boolean
}

const variants: Record<ButtonVariant, string> = {
  // Teal with royal text keeps WCAG AA contrast on the light brand teal.
  primary:
    'bg-primary text-royal font-semibold shadow-sm hover:bg-primary-dark hover:text-white',
  secondary: 'bg-royal text-white font-semibold shadow-sm hover:bg-navy',
  outline:
    'border border-navy/30 bg-white font-medium text-royal hover:bg-offwhite hover:border-navy/50',
  ghost: 'font-medium text-royal hover:bg-offwhite',
  danger: 'bg-red-600 text-white font-semibold shadow-sm hover:bg-red-700',
}

const sizes: Record<ButtonSize, string> = {
  sm: 'gap-1.5 px-3 py-1.5 text-sm',
  md: 'gap-2 px-4 py-2 text-sm',
  lg: 'gap-2 px-5 py-2.5 text-base',
}

/** Merge Button's classes/props onto exactly one child element. */
interface SlotProps extends Omit<HTMLAttributes<HTMLElement>, 'children'> {
  className?: string
  children: ReactElement
}

function Slot({ className, children, ...props }: SlotProps) {
  const childProps = children.props as { className?: string }
  return cloneElement(children, {
    ...props,
    className: cn(className, childProps.className),
  } as HTMLAttributes<HTMLElement>)
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  fullWidth = false,
  asChild = false,
  className,
  children,
  disabled,
  ...props
}: ButtonProps) {
  const classes = cn(
    'inline-flex items-center justify-center rounded-lg transition-colors',
    'disabled:cursor-not-allowed disabled:opacity-55',
    variants[variant],
    sizes[size],
    fullWidth && 'w-full',
    className,
  )

  if (asChild) {
    const child = children as ReactElement
    return (
      <Slot className={classes} aria-busy={loading || undefined} {...props}>
        {child}
      </Slot>
    )
  }

  return (
    <button
      type="button"
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={classes}
      {...props}
    >
      {loading ? <Spinner /> : icon}
      {children}
    </button>
  )
}
