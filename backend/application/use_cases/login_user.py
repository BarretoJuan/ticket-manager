"""Login: verify credentials and update last_login_at."""

from dataclasses import replace

from domain.entities.user import User
from domain.exceptions import InvalidCredentialsError
from domain.repositories.user_repository import UserRepository
from domain.services.password_service import PasswordService
from domain.utils import utcnow


class LoginUser:
    def __init__(
        self,
        user_repository: UserRepository,
        password_service: PasswordService,
    ) -> None:
        self.user_repository = user_repository
        self.password_service = password_service

    def execute(self, *, email: str, password: str) -> User:
        email = (email or "").strip().lower()
        user = self.user_repository.get_by_email(email)
        if user is None:
            raise InvalidCredentialsError("invalid email or password")
        if not self.password_service.verify(password, user.password_hash):
            raise InvalidCredentialsError("invalid email or password")

        now = utcnow()
        updated = replace(
            user,
            last_login_at=now,
            updated_at=now,
        )
        return self.user_repository.update(updated)