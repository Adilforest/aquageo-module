from rest_framework import serializers

from .models import HydropostReading


class HydropostReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = HydropostReading
        fields = (
            "id", "ts", "water_level", "danger_level", "discharge",
            "water_temp", "status_code", "synthetic",
        )
