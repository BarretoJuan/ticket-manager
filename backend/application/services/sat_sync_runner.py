"""Background executor for the SAT sync.

Runs the heavy work of :class:`SatSync` on a daemon thread so the HTTP request
returns immediately with a ``processing`` status. The concurrency guard in the
repository (advisory xact lock + ``processing`` row) prevents overlapping runs
even if the request process is ever replaced by multi-worker or single-threaded
production WSGI servers.
"""

import logging
import threading
from uuid import UUID

from django.db import connections

from application.use_cases.sat_sync import SatSync, SatSyncResult
from domain.entities.log_entry import AuditContext

logger = logging.getLogger("application")


class SatSyncRunner:
    def __init__(self, use_case: SatSync) -> None:
        self.use_case = use_case

    def start(
        self,
        *,
        force: bool,
        user_id: UUID | None,
        audit: AuditContext | None = None,
    ) -> SatSyncResult:
        result = self.use_case.start(force=force, user_id=user_id, audit=audit)
        if result.status == "started":
            self._enqueue(result.history.id, user_id, audit)
        return result

    def _enqueue(
        self, history_id: UUID, user_id: UUID | None, audit: AuditContext | None
    ) -> None:
        thread = threading.Thread(
            target=self._work,
            args=(history_id, user_id, audit),
            name=f"sat-sync-{history_id}",
            daemon=True,
        )
        thread.start()

    def _work(
        self, history_id: UUID, user_id: UUID | None, audit: AuditContext | None
    ) -> None:
        try:
            self.use_case.run(history_id=history_id, user_id=user_id, audit=audit)
        except Exception:  # noqa: BLE001 - belt & braces: never crash the process
            logger.exception("SAT sync worker crashed for history %s", history_id)
        finally:
            # The worker owns a thread-local DB connection; release it.
            connections.close_all()
