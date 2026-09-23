"""API route table for /api/v1."""

from django.urls import path

# Importing this registers the Bearer auth scheme in the OpenAPI schema.
import presentation.spectacular_extension  # noqa: F401

from presentation.views.auth_views import LoginView, RegisterView
from presentation.views.booking_views import BookingCreateView
from presentation.views.event_views import EventCollectionView, EventDetailView
from presentation.views.health_views import HealthView
from presentation.views.sat_views import (
    SatHistoryListView,
    SatSyncStatusView,
    SatSyncView,
)

urlpatterns = [
    # Auth
    path("login", LoginView.as_view(), name="login"),
    path("register", RegisterView.as_view(), name="register"),
    # Events: GET list / POST create (same path, one view class)
    path("events", EventCollectionView.as_view(), name="events"),
    # Events: PATCH update / DELETE soft delete (same path, one view class)
    path("events/<uuid:event_id>", EventDetailView.as_view(), name="event-detail"),
    # Bookings (rate limited)
    path("events/<uuid:event_id>/book", BookingCreateView.as_view(), name="event-book"),
    # Health
    path("health", HealthView.as_view(), name="health"),
    # SAT open-data sync (art. 69 CFF "Cancelados")
    path("sat/sync", SatSyncView.as_view(), name="sat-sync"),
    path(
        "sat/sync/<uuid:history_id>",
        SatSyncStatusView.as_view(),
        name="sat-sync-status",
    ),
    path("sat/history", SatHistoryListView.as_view(), name="sat-history"),
]
