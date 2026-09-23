import type { SatHistory } from '../../types'
import {
  formatDateTime,
  formatDuration,
  truncateMiddle,
} from '../../utils/format'
import { Badge } from '../ui/Badge'
import { EmptyState } from '../ui/EmptyState'
import { IconRobot } from '../ui/icons'

const statusBadge: Record<SatHistory['status'], React.ReactNode> = {
  completed: <Badge tone="success">Completed</Badge>,
  error: <Badge tone="error">Error</Badge>,
  processing: <Badge tone="processing">Processing</Badge>,
}

interface SatHistoryTableProps {
  history: SatHistory[]
}

/** SAT automation history — desktop table + stacked cards on mobile. */
export function SatHistoryTable({ history }: SatHistoryTableProps) {
  if (history.length === 0) {
    return (
      <EmptyState
        icon={<IconRobot className="h-8 w-8" />}
        title="No automations yet"
        description="Run the SAT automation once and its history will appear here."
      />
    )
  }

  return (
    <>
      {/* Desktop table */}
      <div className="border-navy/15 shadow-card hidden overflow-hidden rounded-2xl border bg-white md:block">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">
            SAT automation history — started, status, records, omitted, duration
            and file
          </caption>
          <thead className="border-navy/10 bg-offwhite text-muted border-b text-xs tracking-wide uppercase">
            <tr>
              <th scope="col" className="px-4 py-3 font-semibold">
                Started
              </th>
              <th scope="col" className="px-4 py-3 font-semibold">
                Status
              </th>
              <th scope="col" className="px-4 py-3 text-right font-semibold">
                Records
              </th>
              <th scope="col" className="px-4 py-3 text-right font-semibold">
                Omitted
              </th>
              <th scope="col" className="px-4 py-3 font-semibold">
                Duration
              </th>
              <th scope="col" className="px-4 py-3 font-semibold">
                File
              </th>
            </tr>
          </thead>
          <tbody className="divide-navy/10 divide-y">
            {history.map((run) => (
              <tr key={run.id} className="hover:bg-offwhite/60">
                <td className="text-royal px-4 py-3 whitespace-nowrap">
                  {formatDateTime(run.started_at)}
                </td>
                <td className="px-4 py-3">{statusBadge[run.status]}</td>
                <td className="text-royal px-4 py-3 text-right tabular-nums">
                  {run.record_number.toLocaleString()}
                </td>
                <td className="text-royal px-4 py-3 text-right tabular-nums">
                  {run.omitted_number.toLocaleString()}
                </td>
                <td className="text-royal px-4 py-3 whitespace-nowrap">
                  {run.processing_time !== null
                    ? formatDuration(run.processing_time)
                    : '—'}
                </td>
                <td className="text-muted px-4 py-3 font-mono text-xs">
                  {truncateMiddle(run.file_hash)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile stacked cards */}
      <ul className="space-y-3 md:hidden">
        {history.map((run) => (
          <li
            key={run.id}
            className="border-navy/15 shadow-card rounded-2xl border bg-white p-4"
          >
            <div className="flex items-center justify-between gap-2">
              <p className="text-royal text-sm font-medium">
                {formatDateTime(run.started_at)}
              </p>
              {statusBadge[run.status]}
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
              <div>
                <dt className="text-muted text-xs">Records</dt>
                <dd className="text-royal tabular-nums">
                  {run.record_number.toLocaleString()}
                </dd>
              </div>
              <div>
                <dt className="text-muted text-xs">Omitted</dt>
                <dd className="text-royal tabular-nums">
                  {run.omitted_number.toLocaleString()}
                </dd>
              </div>
              <div>
                <dt className="text-muted text-xs">Duration</dt>
                <dd className="text-royal">
                  {run.processing_time !== null
                    ? formatDuration(run.processing_time)
                    : '—'}
                </dd>
              </div>
              <div>
                <dt className="text-muted text-xs">File</dt>
                <dd className="text-muted font-mono text-xs">
                  {truncateMiddle(run.file_hash)}
                </dd>
              </div>
            </dl>
          </li>
        ))}
      </ul>
    </>
  )
}
