"""Notification API (issue #28).

A user sees ONLY their own notifications. Supported operations:
- GET  /api/v1/notifications/             — list own (filter ?read=true/false)
- GET  /api/v1/notifications/{id}/        — retrieve own
- PATCH /api/v1/notifications/{id}/       — mark read/unread ({"read": true})
- POST /api/v1/notifications/{id}/read/   — mark a single one read
- POST /api/v1/notifications/read-all/    — mark all own as read
- GET  /api/v1/notifications/unread-count/ — {"unread": N}
"""
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


@extend_schema(tags=["notifications"])
class NotificationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Own notifications: list, mark read, unread counter."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["read", "kind"]
    http_method_names = ["get", "patch", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Notification.objects.none()
        return Notification.objects.filter(recipient=user)

    @extend_schema(request=None, responses=NotificationSerializer)
    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        notification = self.get_object()
        if not notification.read:
            notification.read = True
            notification.save(update_fields=["read", "updated_at"])
        return Response(self.get_serializer(notification).data)

    @extend_schema(request=None, responses={200: dict})
    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        updated = self.get_queryset().filter(read=False).update(read=True)
        return Response({"updated": updated})

    @extend_schema(responses={200: dict})
    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        return Response({"unread": self.get_queryset().filter(read=False).count()})
