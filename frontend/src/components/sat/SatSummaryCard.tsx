import type { SatHistory } from '../../types'
import { formatDateTime, formatDuration } from '../../utils/format'
import { Badge } from '../ui/Badge'

const statusBadge = {
  completed: <Badge tone="success">Completed</Badge>,
  error: <Badge tone="error">Error</Badge>,
  processing: <Badge tone="processing">Processing</Badge>,
} as const

/** Post-execution summary card for the latest SAT automation run. */
export function SatSummaryCard({ run }: { run: SatHistory }) {
  return (
    <div className="border-navy/15 shadow-card rounded-2xl border bg-white p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-royal text-base font-semibold">
          Latest automation
        </h2>
        {statusBadge[run.status]}
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm sm:grid-cols-4">
        <div>
          <dt className="text-muted text-xs">Records imported</dt>
          <dd className="text-royal mt-0.5 text-lg font-semibold">
            {run.record_number.toLocaleString()}
          </dd>
        </div>
        <div>
          <dt className="text-muted text-xs">Omitted / errors</dt>
          <dd className="text-royal mt-0.5 text-lg font-semibold">
            {run.omitted_number.toLocaleString()}
          </dd>
        </div>
        <div>
          <dt className="text-muted text-xs">Processing time</dt>
          <dd className="text-royal mt-0.5 text-lg font-semibold">
            {run.processing_time !== null
              ? formatDuration(run.processing_time)
              : '—'}
          </dd>
        </div>
        <div>
          <dt className="text-muted text-xs">Finished at</dt>
          <dd className="text-royal mt-0.5 text-sm">
            {run.completed_at ? formatDateTime(run.completed_at) : '—'}
          </dd>
        </div>
      </dl>
    </div>
  )
}
