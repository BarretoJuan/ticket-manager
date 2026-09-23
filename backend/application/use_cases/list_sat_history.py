"""List SAT sync history (paginated, newest first)."""

from domain.repositories.sat_repository import (
    SatHistoryPage,
    SatHistoryQuery,
    SatRepository,
)


class SatListHistory:
    def __init__(self, repository: SatRepository) -> None:
        self.repository = repository

    def execute(self, query: SatHistoryQuery) -> SatHistoryPage:
        return self.repository.list_history(query)
