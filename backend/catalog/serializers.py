from rest_framework import serializers
from rest_framework_gis.fields import GeometryField
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from .models import Structure


class StructureSerializer(serializers.ModelSerializer):
    """Full Structure representation for CRUD (geometry as GeoJSON)."""

    geom = GeometryField(required=False, allow_null=True)
    type_name = serializers.CharField(source="type.name_ru", read_only=True)
    basin_name = serializers.CharField(source="basin.name_ru", read_only=True)
    admin_unit_name = serializers.CharField(source="admin_unit.name_ru", read_only=True)

    class Meta:
        model = Structure
        fields = (
            "id", "type", "type_name", "name_ru", "name_kk", "name_en",
            "geom", "basin", "basin_name", "admin_unit", "admin_unit_name",
            "water_body", "commissioning_year", "wear_percent", "ownership",
            "cadastral_number", "state_act", "responsible_org", "significance",
            "condition_status", "status", "attributes", "created_at", "updated_at",
        )
        # condition_status is computed by the assessment service (issue #16).
        read_only_fields = ("id", "condition_status", "created_at", "updated_at")


class StructureGeoSerializer(GeoFeatureModelSerializer):
    """Lightweight GeoJSON FeatureCollection serializer for the map."""

    type = serializers.CharField(source="type_id")
    type_name = serializers.CharField(source="type.name_ru", read_only=True)

    class Meta:
        model = Structure
        geo_field = "geom"
        fields = (
            "id", "name_ru", "type", "type_name",
            "condition_status", "status", "significance",
        )
