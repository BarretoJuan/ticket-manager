"""Django implementation of the UserRepository port."""

from uuid import UUID

from domain.entities.user import User
from domain.repositories.user_repository import UserRepository

from infrastructure.orm.models import UserORM
from infrastructure.repositories.mappers import user_domain_to_orm, user_orm_to_domain


class DjangoUserRepository(UserRepository):
    def create(self, user: User) -> User:
        # ``user.password_hash`` already contains a Django-compatible hash.
        row = UserORM.objects.create(**user_domain_to_orm(user))
        row.refresh_from_db()
        return user_orm_to_domain(row)

    def get_by_email(self, email: str) -> User | None:
        row = UserORM.objects.filter(email__iexact=email, deleted_at__isnull=True).first()
        return user_orm_to_domain(row) if row else None

    def get_by_id(self, user_id: UUID) -> User | None:
        row = UserORM.objects.filter(pk=user_id, deleted_at__isnull=True).first()
        return user_orm_to_domain(row) if row else None

    def email_exists(self, email: str) -> bool:
        return UserORM.objects.filter(email__iexact=email, deleted_at__isnull=True).exists()

    def update(self, user: User) -> User:
        UserORM.objects.filter(pk=user.id).update(**user_domain_to_orm(user))
        row = UserORM.objects.get(pk=user.id)
        return user_orm_to_domain(row)