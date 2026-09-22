"""QR-code generation port. Adapters live in the infrastructure layer."""

from abc import ABC, abstractmethod


class QrCodeGenerator(ABC):
    """Port implemented by image libraries (e.g. ``qrcode`` + Pillow)."""

    @abstractmethod
    def generate_png(self, data: str, *, box_size: int = 8) -> bytes:
        """Return a PNG-encoded image (bytes) that encodes ``data``."""
