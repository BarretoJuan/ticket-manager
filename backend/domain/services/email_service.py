"""E-mail delivery port. Adapters live in the infrastructure layer."""

from abc import ABC, abstractmethod

from domain.entities.outbound_email import OutboundEmail


class EmailService(ABC):
    """Port implemented by SMTP / local backends (e.g. Django's mail engine)."""

    @abstractmethod
    def send(self, message: OutboundEmail) -> None:
        """Deliver ``message``; raise on hard failure (handled upstream)."""
