"""ORM models — strictly implementation details of the infrastructure layer.

Never import these from domain/ or application/: use the repository ports.
"""

import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models


class UserRole(models.TextChoices):
    USER = "USER", "User"
    ADMIN = "ADMIN", "Admin"


class LogLevel(models.TextChoices):
    INFO = "info", "Info"
    WARNING = "warning", "Warning"
    ERROR = "error", "Error"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The email address must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", UserRole.USER)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", UserRole.ADMIN)
        extra_fields.setdefault("is_active", True)
        return self._create_user(email, password, **extra_fields)


class UserORM(AbstractBaseUser):
    """Custom auth user: UUID pk, email login, role, soft deletion."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=16, choices=UserRole.choices, default=UserRole.USER
    )
    is_active = models.BooleanField(default=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"{self.email} ({self.role})"

    class Meta:
        db_table = "users"


class EventORM(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    date = models.DateTimeField()  # always stored in UTC (settings.USE_TZ=True)
    total_capacity = models.PositiveIntegerField()
    available_tickets = models.PositiveIntegerField()
    ticket_price = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.code} ({self.name})"

    class Meta:
        db_table = "events"
        ordering = ["date"]


class BookingORM(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        EventORM, on_delete=models.PROTECT, related_name="bookings"
    )
    user = models.ForeignKey(UserORM, on_delete=models.PROTECT, related_name="bookings")
    ticket_quantity = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Booking {self.id} ({self.ticket_quantity})"

    class Meta:
        db_table = "bookings"


class LogORM(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.TextField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    endpoint = models.TextField(null=True, blank=True)
    http_method = models.CharField(max_length=10, null=True, blank=True)
    status_code = models.CharField(max_length=10, null=True, blank=True)
    stack_trace = models.TextField(null=True, blank=True)
    user = models.ForeignKey(
        UserORM, null=True, blank=True, on_delete=models.SET_NULL, related_name="logs"
    )
    event = models.ForeignKey(
        EventORM, null=True, blank=True, on_delete=models.SET_NULL, related_name="logs"
    )
    type = models.CharField(max_length=10, choices=LogLevel.choices)
    name = models.CharField(max_length=255)
    content = models.TextField()

    def __str__(self):
        return f"{self.type}: {self.name}"

    class Meta:
        db_table = "logs"
