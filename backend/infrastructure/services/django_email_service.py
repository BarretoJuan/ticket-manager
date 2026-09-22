"""SMTP adapter for the ``EmailService`` port built on Django's mail engine.

This adapter is the only component aware of the Django e-mail configuration.
When the stock SMTP backend is selected but no ``EMAIL_HOST`` is configured,
sends are silently dropped with an info log so the feature no-ops in plain
local development. Other backends (``locmem`` in tests, ``console`` while
debugging) are honoured regardless.
"""

import logging
from email.mime.image import MIMEImage

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from domain.entities.outbound_email import EmailAttachment, OutboundEmail
from domain.services.email_service import EmailService

logger = logging.getLogger("application")

_SMTP_BACKEND = "django.core.mail.backends.smtp.EmailBackend"


class DjangoEmailService(EmailService):
    def send(self, message: OutboundEmail) -> None:
        # Reject malformed messages before any backend is touched, so every
        # adapter lands on the same contract (raised here, handled upstream).
        message.validate()
        if self._smtp_unconfigured():
            logger.info(
                "e-mail not configured (SMTP backend without EMAIL_HOST); "
                "skipping message for %s",
                message.to,
            )
            return
        email = EmailMultiAlternatives(
            subject=message.subject,
            body=message.text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[message.to],
        )
        email.attach_alternative(message.html_body, "text/html")
        for attachment in message.attachments:
            if attachment.inline:
                email.attach(self._inline_mime(attachment))
            else:
                email.attach(
                    attachment.name, attachment.content, attachment.content_type
                )
        email.send()

    def _smtp_unconfigured(self) -> bool:
        # Only the stock SMTP backend needs a host; test/debug backends are
        # intentionally selected through EMAIL_BACKEND and always used.
        return settings.EMAIL_BACKEND == _SMTP_BACKEND and not settings.EMAIL_HOST

    def _inline_mime(self, attachment: EmailAttachment) -> MIMEImage:
        _, subtype = attachment.content_type.split("/", 1)
        image = MIMEImage(attachment.content, _subtype=subtype)
        cid = attachment.cid or attachment.name
        image.add_header("Content-ID", f"<{cid}>")
        image.add_header("Content-Disposition", "inline", filename=attachment.name)
        return image
