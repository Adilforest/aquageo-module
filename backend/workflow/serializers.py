from rest_framework import serializers

from .models import Application


class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = (
            "id", "structure", "kind", "status", "submitted_by", "reviewer",
            "submitted_at", "decided_at", "comment", "created_at",
        )
        read_only_fields = (
            "id", "status", "submitted_by", "reviewer",
            "submitted_at", "decided_at", "created_at",
        )
