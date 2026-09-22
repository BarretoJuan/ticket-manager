"""User entity and role enumeration."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import re
from uuid import UUID

from domain.exceptions import InvalidEmailError, UserValidationError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Role(StrEnum):
    USER = "USER"
    ADMIN = "ADMIN"


@dataclass(frozen=True)
class User:
    """A registered user (spectator or administrator)."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    email: str
    last_login_at: datetime | None
    role: str  # Role.USER | Role.ADMIN
    password_hash: str

    def validate(self) -> None:
        if not self.email or not EMAIL_RE.match(self.email):
            raise InvalidEmailError(f"invalid email address: {self.email!r}")
        if self.role not in (Role.USER, Role.ADMIN):
            raise UserValidationError(f"role must be USER or ADMIN, got {self.role!r}")
        if not self.password_hash:
            raise UserValidationError("password_hash cannot be empty")

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN
