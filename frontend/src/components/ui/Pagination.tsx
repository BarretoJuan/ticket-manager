import { cn } from '../../utils/cn'
import { Button } from './Button'
import { IconChevronLeft, IconChevronRight } from './icons'

interface PaginationProps {
  page: number
  totalPages: number
  totalItems: number
  onPageChange: (page: number) => void
  disabled?: boolean
  className?: string
}

export function Pagination({
  page,
  totalPages,
  totalItems,
  onPageChange,
  disabled = false,
  className,
}: PaginationProps) {
  const hasPrev = page > 1
  const hasNext = page < totalPages

  return (
    <nav
      aria-label="Pagination"
      className={cn(
        'flex flex-wrap items-center justify-between gap-3',
        className,
      )}
    >
      <p className="text-muted text-sm" aria-live="polite">
        {totalItems === 0
          ? 'No results'
          : `${totalItems} item${totalItems === 1 ? '' : 's'} · page ${page} of ${totalPages}`}
      </p>
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={disabled || !hasPrev}
          onClick={() => onPageChange(page - 1)}
          aria-label="Previous page"
          icon={<IconChevronLeft className="h-4 w-4" />}
        >
          <span className="sm:hidden">Prev</span>
          <span className="hidden sm:inline">Previous</span>
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={disabled || !hasNext}
          onClick={() => onPageChange(page + 1)}
          aria-label="Next page"
          icon={<IconChevronRight className="h-4 w-4" />}
        >
          <span className="sm:hidden">Next</span>
          <span className="hidden sm:inline">Next</span>
        </Button>
      </div>
    </nav>
  )
}
