"""Booking confirmation email composer + dispatcher (application service).

Builds the confirmation message (event details, ticket count, thank-you note
and a QR code encoding the booking reference) using only domain ports, so the
application layer stays framework-free. Delivery failures propagate to the
caller, which decides how to handle them (see ``BookTicket``).
"""

import logging
from html import escape
from uuid import UUID

from domain.entities.booking import Booking
from domain.entities.event import Event
from domain.entities.outbound_email import EmailAttachment, OutboundEmail
from domain.repositories.user_repository import UserRepository
from domain.services.email_service import EmailService
from domain.services.qr_code_service import QrCodeGenerator

logger = logging.getLogger("application")

# Content-ID the HTML body uses for the inline QR image; the adapter maps it
# to an RFC 822 ``Content-ID`` header.
QR_CONTENT_ID = "booking-qr"

THANK_YOU_MESSAGE = (
    "Thank you for booking with Ticket Manager — we look forward to seeing "
    "you at the event. Please present the QR code included in this email at "
    "the entrance."
)


class BookingNotifier:
    """Sends booking confirmation e-mails with an embedded event QR code."""

    def __init__(
        self,
        user_repository: UserRepository,
        email_service: EmailService,
        qr_code_generator: QrCodeGenerator,
    ) -> None:
        self.user_repository = user_repository
        self.email_service = email_service
        self.qr_code_generator = qr_code_generator

    def send_booking_confirmation(
        self, *, booking: Booking, event: Event, user_id: UUID
    ) -> None:
        user = self.user_repository.get_by_id(user_id)
        if user is None:
            logger.warning(
                "confirmation e-mail skipped for booking %s: user %s not found",
                booking.id,
                user_id,
            )
            return
        self.email_service.send(self._build_message(booking, event, user.email))

    def _build_message(
        self, booking: Booking, event: Event, recipient: str
    ) -> OutboundEmail:
        qr_png = self.qr_code_generator.generate_png(str(booking.id))
        attachment = EmailAttachment(
            name=f"booking-{booking.id}.png",
            content=qr_png,
            content_type="image/png",
            inline=True,
            cid=QR_CONTENT_ID,
        )
        return OutboundEmail(
            to=recipient,
            subject=f"Booking confirmed: {event.name}",
            text_body=self._text_body(booking, event, recipient),
            html_body=self._html_body(booking, event, recipient),
            attachments=(attachment,),
        )

    def _date_label(self, event: Event) -> str:
        return event.date.strftime("%B %d, %Y at %H:%M %Z")

    def _text_body(self, booking: Booking, event: Event, recipient: str) -> str:
        return (
            f"Hello {recipient},\n\n"
            f"{THANK_YOU_MESSAGE}\n\n"
            f"Event: {event.name}\n"
            f"Code: {event.code}\n"
            f"Date: {self._date_label(event)}\n"
            f"Email: {recipient}\n"
            f"Tickets: {booking.ticket_quantity}\n"
            f"Booking reference: {booking.id}\n\n"
            "See you there!\n"
            "Ticket Manager"
        )

    def _html_body(self, booking: Booking, event: Event, recipient: str) -> str:
        rows = "".join(
            self._row(label, value)
            for label, value in (
                ("Event", escape(event.name)),
                ("Code", escape(event.code)),
                ("Date", self._date_label(event)),
                ("Email", escape(recipient)),
                ("Tickets", str(booking.ticket_quantity)),
            )
        )
        return (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n'
            '<body style="font-family: Arial, Helvetica, sans-serif; '
            'background: #f4f4f4; padding: 24px;">\n'
            '<div style="max-width: 520px; margin: 0 auto; '
            'background: #ffffff; border-radius: 8px; overflow: hidden;">\n'
            '<div style="background: #1f6feb; color: #ffffff; padding: 24px;">\n'
            '<h1 style="margin: 0; font-size: 22px;">Booking confirmed</h1>\n'
            "</div>\n"
            '<div style="padding: 24px;">\n'
            f"<p>{escape(THANK_YOU_MESSAGE)}</p>\n"
            '<table style="width: 100%; border-collapse: collapse; '
            'margin: 16px 0;">\n'
            f"{rows}</table>\n"
            f'<p style="text-align: center; margin: 24px 0;">\n'
            f'<img src="cid:{QR_CONTENT_ID}" alt="Booking QR code" '
            'width="180" height="180" />\n'
            "</p>\n"
            f'<p style="text-align: center; color: #888; font-size: '
            f'12px;">Booking reference: {booking.id}</p>\n'
            "</div>\n"
            "</div>\n"
            "</body>\n"
            "</html>"
        )

    def _row(self, label: str, value: str) -> str:
        label_cell = "padding: 6px 0; color: #555; width: 80px;"
        value_cell = "padding: 6px 0;"
        return (
            "<tr>"
            f'<td style="{label_cell}">{label}</td>'
            f'<td style="{value_cell}"><strong>{value}</strong></td>'
            "</tr>"
        )
