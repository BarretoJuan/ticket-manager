"""SAT open-data download port. Adapters live in the infrastructure layer."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SatDownloadResult:
    """A downloaded "Cancelados" file on local disk."""

    file_path: Path  # path to the CSV (streamed to disk, never fully in RAM)
    file_hash: str  # sha256 of the raw file bytes


class SatDataService(ABC):
    """Port implemented by the SAT scraper + streaming downloader."""

    @abstractmethod
    def download(self, dest_dir: Path) -> SatDownloadResult:
        """Scrape the SAT page, download the "Cancelados" CSV into ``dest_dir``
        and return its path plus a sha256 hash. Raises ``SatDownloadError`` on
        any network/HTML/format failure."""
