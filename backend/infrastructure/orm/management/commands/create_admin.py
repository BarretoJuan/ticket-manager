"""Management command: create (or promote) an admin user.

Usage:  python manage.py create_admin --email admin@example.com --password 'secret123'
"""

from django.core.management.base import BaseCommand

from infrastructure.orm.models import UserORM, UserRole


class Command(BaseCommand):
    help = "Create an ADMIN user (or promote an existing user to ADMIN)."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Admin email")
        parser.add_argument("--password", required=True, help="Admin password")

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        password = options["password"]

        user, created = UserORM.objects.get_or_create(
            email=email, defaults={"role": UserRole.ADMIN, "is_active": True}
        )
        if not created:
            user.role = UserRole.ADMIN
            user.is_active = True
            user.deleted_at = None

        user.set_password(password)
        user.save(update_fields=["role", "is_active", "deleted_at", "password"])

        action = "created" if created else "promoted to ADMIN"
        self.stdout.write(self.style.SUCCESS(f"Admin user {email} {action}"))
