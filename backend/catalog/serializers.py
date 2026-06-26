import jsonschema
from rest_framework import serializers
from rest_framework_gis.fields import GeometryField
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from .models import AdminUnit, Attachment, Basin, Inspection, ObjectType, Structure, WaterBody


class BasinSerializer(serializers.ModelSerializer):
    class Meta:
        model = Basin
        fields = ("id", "name_ru", "name_kk", "name_en")


class AdminUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminUnit
        fields = ("kato", "name_ru", "name_kk", "name_en", "level", "parent")


class ObjectTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObjectType
        fields = ("code", "name_ru", "name_kk", "name_en", "geometry_kind", "schema")


class WaterBodySerializer(serializers.ModelSerializer):
    class Meta:
        model = WaterBody
        fields = ("id", "name_ru", "name_kk", "name_en", "kind")


class InspectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inspection
        fields = (
            "id", "inspected_at", "inspector", "condition_observed",
            "wear_percent", "notes",
        )


class AttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.FileField(source="file", read_only=True)

    class Meta:
        model = Attachment
        fields = ("id", "kind", "file_url", "created_at")


def _validate_attributes_against_type(object_type, attributes):
    """Raise serializers.ValidationError if attributes violate the type schema."""
    schema = getattr(object_type, "schema", None)
    if not schema:
        return
    try:
        jsonschema.validate(instance=attributes, schema=schema)
    except jsonschema.ValidationError as exc:
        raise serializers.ValidationError(
            {"attributes": f"Не соответствует схеме типа: {exc.message}"}
        ) from exc
    except jsonschema.SchemaError as exc:
        raise serializers.ValidationError(
            {"attributes": f"Некорректная JSON-схема типа: {exc.message}"}
        ) from exc


class StructureSerializer(serializers.ModelSerializer):
    """Full Structure representation for CRUD (geometry as GeoJSON)."""

    geom = GeometryField(required=False, allow_null=True)
    type_name = serializers.CharField(source="type.name_ru", read_only=True)
    basin_name = serializers.CharField(source="basin.name_ru", read_only=True)
    admin_unit_name = serializers.CharField(source="admin_unit.name_ru", read_only=True)
    water_body_name = serializers.CharField(source="water_body.name_ru", read_only=True)

    class Meta:
        model = Structure
        fields = (
            "id", "type", "type_name", "name_ru", "name_kk", "name_en",
            "geom", "basin", "basin_name", "admin_unit", "admin_unit_name",
            "water_body", "water_body_name", "commissioning_year", "wear_percent",
            "ownership", "cadastral_number", "state_act", "responsible_org",
            "significance", "condition_status", "status", "attributes",
            "created_at", "updated_at",
        )
        # condition_status is computed by the assessment service (issue #16).
        read_only_fields = ("id", "condition_status", "created_at", "updated_at")

    def validate(self, attrs):
        # Validate attributes against the (possibly new) object type's schema,
        # covering partial updates (PATCH) too.
        object_type = attrs.get("type") or getattr(self.instance, "type", None)
        if "attributes" in attrs:
            attributes = attrs["attributes"]
        elif self.instance is not None:
            attributes = self.instance.attributes
        else:
            attributes = {}
        if object_type is not None and ("attributes" in attrs or self.instance is None):
            _validate_attributes_against_type(object_type, attributes)
        return attrs


class StructureDetailSerializer(StructureSerializer):
    """Retrieve serializer: adds inspections and attachments for the card."""

    inspections = InspectionSerializer(many=True, read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    type_detail = ObjectTypeSerializer(source="type", read_only=True)

    class Meta(StructureSerializer.Meta):
        fields = (*StructureSerializer.Meta.fields, "type_detail", "inspections", "attachments")


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
