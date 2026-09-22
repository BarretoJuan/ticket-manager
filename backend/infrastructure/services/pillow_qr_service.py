"""QR-code generation adapter using the ``qrcode`` library + Pillow (PNG)."""

import io

import qrcode

from domain.services.qr_code_service import QrCodeGenerator


class PillowQrCodeGenerator(QrCodeGenerator):
    def generate_png(self, data: str, *, box_size: int = 8) -> bytes:
        image = qrcode.make(data, box_size=box_size, border=2)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
