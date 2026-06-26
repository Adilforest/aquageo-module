from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id", "kind", "kind_display", "message",
            "related_entity_type", "related_entity_id",
            "read", "created_at",
        )
        # Clients may only toggle ``read``; everything else is event-derived.
        read_only_fields = (
            "id", "kind", "kind_display", "message",
            "related_entity_type", "related_entity_id", "created_at",
        )
