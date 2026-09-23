import { useState } from 'react'
import { useSatSync } from '../hooks/useSatSync'
import { Button } from '../components/ui/Button'
import { Spinner } from '../components/ui/Spinner'
import { Pagination } from '../components/ui/Pagination'
import { SatSummaryCard } from '../components/sat/SatSummaryCard'
import { SatHistoryTable } from '../components/sat/SatHistoryTable'
import { IconRefresh, IconRobot, IconSparkles } from '../components/ui/icons'
import { formatDateTime } from '../utils/format'

export function SatAutomationPage() {
  const {
    starting,
    current,
    polling,
    history,
    count,
    page,
    setPage,
    historyLoading,
    start,
    reloadHistory,
  } = useSatSync()

  const [force, setForce] = useState(false)

  const running = current?.status === 'processing'
  const summary =
    current && current.status !== 'processing' ? (
      <SatSummaryCard run={current} />
    ) : null

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-royal flex items-center gap-2 text-2xl font-bold sm:text-3xl">
            <IconRobot className="text-primary-dark h-7 w-7" />
            SAT Automation
          </h1>
          <p className="text-muted mt-1 max-w-2xl text-sm">
            Downloads the SAT “Cancelados” open-data list (art. 69 CFF) and
            imports it in the background. Runs are asynchronous — you can keep
            working while it executes.
          </p>
        </div>
      </header>

      {/* Start automation */}
      <section
        aria-label="Start SAT automation"
        className="border-navy/15 shadow-card rounded-2xl border bg-white p-5"
      >
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-royal text-base font-semibold">
              Start a new automation
            </h2>
            <p className="text-muted mt-1 text-sm">
              Already ran within the last 30 minutes? It will be skipped unless
              forced.
            </p>
            <label className="text-royal mt-3 inline-flex cursor-pointer items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={force}
                onChange={(e) => setForce(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 accent-[#00CBAA]"
              />
              Force run (bypass cooldown)
            </label>
          </div>
          <Button
            variant="primary"
            size="lg"
            icon={<IconSparkles className="h-4 w-4" />}
            loading={starting}
            onClick={() => void start(force)}
            disabled={running}
          >
            {running ? 'Running…' : 'Start SAT automation'}
          </Button>
        </div>

        {polling && running && (
          <div
            role="status"
            className="bg-offwhite text-royal mt-4 flex items-center gap-3 rounded-xl p-4 text-sm"
          >
            <Spinner className="text-primary-dark h-5 w-5" />
            <span>
              Automation in progress — started at{' '}
              {current ? formatDateTime(current.started_at) : ''} and it may
              take several minutes. Checking the status every 5 seconds…
            </span>
          </div>
        )}
      </section>

      {summary}

      {/* History */}
      <section aria-label="SAT automation history" className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-royal text-lg font-semibold">History</h2>
          <Button
            variant="outline"
            size="sm"
            icon={<IconRefresh className="h-4 w-4" />}
            loading={historyLoading}
            onClick={reloadHistory}
            aria-label="Reload SAT history"
          >
            Reload
          </Button>
        </div>

        {historyLoading && history.length === 0 ? (
          <div
            className="border-navy/15 text-muted flex items-center justify-center gap-2 rounded-2xl border bg-white py-12"
            aria-live="polite"
          >
            <Spinner className="h-5 w-5" />
            <span>Loading history…</span>
          </div>
        ) : (
          <>
            <SatHistoryTable history={history} />
            <Pagination
              page={page}
              totalPages={Math.max(1, Math.ceil(count / 20))}
              totalItems={count}
              onPageChange={setPage}
              disabled={historyLoading}
            />
          </>
        )}
      </section>
    </div>
  )
}
