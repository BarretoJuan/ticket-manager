"""Password hashing port (implemented with Django's hashers in infrastructure)."""

from abc import ABC, abstractmethod


class PasswordService(ABC):
    @abstractmethod
    def hash(self, raw_password: str) -> str:
        """Hash a raw password."""

    @abstractmethod
    def verify(self, raw_password: str, hashed: str) -> bool:
        """Check a raw password against a stored hash."""