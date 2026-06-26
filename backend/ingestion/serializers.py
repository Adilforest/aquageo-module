from rest_framework import serializers

from .models import ParseJob


class ParseJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParseJob
        fields = (
            "id", "source_kind", "file", "status", "raw_extract", "confidence",
            "error_message", "result_structure", "match_status", "matched_structure",
            "created_at",
        )
        read_only_fields = (
            "id", "status", "raw_extract", "confidence", "error_message",
            "result_structure", "match_status", "matched_structure", "created_at",
        )
