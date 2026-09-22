"""Django implementation of the PasswordService port."""

from django.contrib.auth.hashers import check_password, make_password

from domain.services.password_service import PasswordService


class DjangoPasswordService(PasswordService):
    def hash(self, raw_password: str) -> str:
        return make_password(raw_password)

    def verify(self, raw_password: str, hashed: str) -> bool:
        return check_password(raw_password, hashed)
