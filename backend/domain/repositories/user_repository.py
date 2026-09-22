"""User repository port."""

from abc import ABC, abstractmethod
from uuid import UUID

from domain.entities.user import User


class UserRepository(ABC):
    @abstractmethod
    def create(self, user: User) -> User:
        """Persist a new user."""

    @abstractmethod
    def get_by_email(self, email: str) -> User | None:
        """Return a live (not soft-deleted) user by email, or None."""

    @abstractmethod
    def get_by_id(self, user_id: UUID) -> User | None:
        """Return a live user by id, or None."""

    @abstractmethod
    def email_exists(self, email: str) -> bool:
        """True if the email is already registered"""

    @abstractmethod
    def update(self, user: User) -> User:
        """Persist changes to an existing user."""
