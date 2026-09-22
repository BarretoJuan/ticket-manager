"""Log repository port."""

from abc import ABC, abstractmethod

from domain.entities.log_entry import LogEntry


class LogRepository(ABC):
    @abstractmethod
    def create(self, entry: LogEntry) -> LogEntry:
        """Persist a log entry."""