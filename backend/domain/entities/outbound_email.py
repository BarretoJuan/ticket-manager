"""Outbound email value objects — pure data, no framework dependencies."""

from dataclasses import dataclass

from domain.exceptions import InvalidEmailError


@dataclass(frozen=True)
class EmailAttachment:
    """A file (or inline image) carried by an outbound email.

    ``inline=True`` marks the payload as an embedded resource referenceable
    from the HTML body via ``cid:<cid>``. When ``cid`` is omitted the sender
    falls back to using ``name`` as the Content-ID.
    """

    name: str
    content: bytes
    content_type: str
    inline: bool = False
    cid: str | None = None


@dataclass(frozen=True)
class OutboundEmail:
    """A fully composed message ready to be delivered by an EmailService."""

    to: str
    subject: str
    text_body: str
    html_body: str
    attachments: tuple[EmailAttachment, ...] = ()

    def validate(self) -> None:
        if not self.to or "@" not in self.to:
            raise InvalidEmailError(f"invalid outbound email recipient: {self.to!r}")
        if not self.subject:
            raise ValueError("outbound email subject cannot be empty")
