from django.apps import AppConfig


class TicketingConfig(AppConfig):
    name = "infrastructure.orm"
    label = "ticketing"
    verbose_name = "Ticket Manager ORM"
    default_auto_field = "django.db.models.BigAutoField"
