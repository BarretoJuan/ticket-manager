"""Register a new USER-role account."""

from uuid import uuid4

from domain.entities.user import Role, User
from domain.exceptions import EmailAlreadyExistsError, WeakPasswordError
from domain.repositories.user_repository import UserRepository
from domain.services.password_service import PasswordService
from domain.utils import utcnow

MIN_PASSWORD_LENGTH = 8


class RegisterUser:
    def __init__(
        self,
        user_repository: UserRepository,
        password_service: PasswordService,
    ) -> None:
        self.user_repository = user_repository
        self.password_service = password_service

    def execute(self, *, email: str, password: str) -> User:
        email = (email or "").strip().lower()
        if len(password or "") < MIN_PASSWORD_LENGTH:
            raise WeakPasswordError(
                f"password must be at least {MIN_PASSWORD_LENGTH} characters"
            )

        hashed = self.password_service.hash(password)
        user = User(
            id=uuid4(),
            created_at=utcnow(),
            updated_at=utcnow(),
            deleted_at=None,
            email=email,
            last_login_at=None,
            role=Role.USER,  # registration always creates a regular user
            password_hash=hashed,
        )
        user.validate()  # raises InvalidEmailError / UserValidationError

        if self.user_repository.email_exists(email):
            raise EmailAlreadyExistsError(f"email {email} is already registered")

        return self.user_repository.create(user)
