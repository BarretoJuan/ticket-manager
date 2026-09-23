"""SAT open-data downloader (stdlib only).

Scrapes the "Cancelados" download link from the SAT article-69 page and streams
the CSV to disk while computing its sha256 hash. This is the only component
aware of SAT's HTML/URL layout — the download link is always discovered from the
page HTML (it may change).

Guardrails:
  * the page download and the CSV stream both honour a timeout;
  * a hard byte cap (``max_file_bytes``) stops runaway/zip-bomb downloads;
  * download failures raise ``SatDownloadError`` (recorded as an ``error`` run,
    never crashing the server).
"""

import hashlib
import logging
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

from domain.exceptions import SatDownloadError
from domain.services.sat_data_service import SatDataService, SatDownloadResult

logger = logging.getLogger("application")

_USER_AGENT = "Mozilla/5.0 (compatible; TicketManagerSATSync/1.0)"
_CHUNK_SIZE = 64 * 1024


class _CanceladosLinkParser(HTMLParser):
    """Finds the first ``<a>`` whose visible text equals the target label."""

    def __init__(self, target_text: str):
        super().__init__(convert_charrefs=True)
        self.target = target_text.strip().lower()
        self.href: str | None = None
        self._in_anchor = False
        self._depth = 0
        self._current_href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            if self._in_anchor:
                self._depth += 1
            else:
                self._in_anchor = True
                self._depth = 1
                self._current_href = dict(attrs).get("href")
                self._text = []

    def handle_endtag(self, tag):
        if tag == "a" and self._in_anchor:
            self._depth -= 1
            if self._depth == 0:
                self._in_anchor = False
                if self.href is None and self._current_href:
                    text = " ".join("".join(self._text).split()).lower()
                    if text == self.target:
                        self.href = self._current_href

    def handle_data(self, data):
        if self._in_anchor:
            self._text.append(data)


class HttpSatDataService(SatDataService):
    def __init__(
        self,
        page_url: str | None = None,
        link_text: str = "Cancelados",
        timeout_seconds: int = 60,
        max_file_bytes: int = 512 * 1024 * 1024,
    ) -> None:
        self.page_url = page_url or (
            "https://www.sat.gob.mx/minisitio/DatosAbiertos/"
            "contribuyentes_publicados.html"
        )
        self.link_text = link_text
        self.timeout_seconds = timeout_seconds
        self.max_file_bytes = max_file_bytes

    def download(self, dest_dir: Path) -> SatDownloadResult:
        csv_url = self._find_cancelados_link()
        logger.info("SAT sync: downloading Cancelados from %s", csv_url)
        file_path = dest_dir / "cancelados.csv"
        file_hash = self._stream_download(csv_url, file_path)
        return SatDownloadResult(file_path=file_path, file_hash=file_hash)

    # -- internals ------------------------------------------------------- #
    def _find_cancelados_link(self) -> str:
        html = self._fetch(self.page_url)
        parser = _CanceladosLinkParser(self.link_text)
        parser.feed(html)
        parser.close()
        if not parser.href:
            raise SatDownloadError(
                f'no "{self.link_text}" download link found on {self.page_url}'
            )
        return urljoin(self.page_url, parser.href)

    def _fetch(self, url: str) -> str:
        try:
            request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                payload = response.read()
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise SatDownloadError(f"failed to fetch {url}: {exc}") from exc
        if len(payload) > self.max_file_bytes:
            raise SatDownloadError(
                f"page at {url} exceeds max size ({len(payload)} bytes)"
            )
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError:
            return payload.decode("latin-1")

    def _stream_download(self, url: str, file_path: Path) -> str:
        sha = hashlib.sha256()
        written = 0
        try:
            request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                with open(file_path, "wb") as out:
                    while True:
                        chunk = response.read(_CHUNK_SIZE)
                        if not chunk:
                            break
                        written += len(chunk)
                        if written > self.max_file_bytes:
                            raise SatDownloadError(
                                "download exceeds max size "
                                f"({self.max_file_bytes} bytes)"
                            )
                        sha.update(chunk)
                        out.write(chunk)
        except SatDownloadError:
            raise
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise SatDownloadError(f"failed to download {url}: {exc}") from exc
        return sha.hexdigest()
