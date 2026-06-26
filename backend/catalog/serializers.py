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
            "significance", "condition_status", "status", "needs_geocoding",
            "attributes", "created_at", "updated_at",
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
    """Retrieve serializer: adds inspections, attachments, assessment breakdown."""

    inspections = InspectionSerializer(many=True, read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    type_detail = ObjectTypeSerializer(source="type", read_only=True)
    repair_status = serializers.SerializerMethodField()
    next_inspection_due = serializers.SerializerMethodField()
    assessment_breakdown = serializers.SerializerMethodField()
    latest_reading = serializers.SerializerMethodField()
    risk = serializers.SerializerMethodField()

    class Meta(StructureSerializer.Meta):
        fields = (
            *StructureSerializer.Meta.fields,
            "type_detail", "inspections", "attachments",
            "repair_status", "next_inspection_due", "assessment_breakdown",
            "latest_reading", "risk",
        )

    def _latest_assessment(self, obj):
        if not hasattr(self, "_assessment_cache"):
            self._assessment_cache = {}
        if obj.pk not in self._assessment_cache:
            self._assessment_cache[obj.pk] = obj.assessments.first()
        return self._assessment_cache[obj.pk]

    def get_repair_status(self, obj):
        a = self._latest_assessment(obj)
        return a.repair_status if a else None

    def get_next_inspection_due(self, obj):
        a = self._latest_assessment(obj)
        return a.next_inspection_due if a else None

    def get_assessment_breakdown(self, obj):
        a = self._latest_assessment(obj)
        return a.risk_scores if a else None

    def get_risk(self, obj):
        a = self._latest_assessment(obj)
        if a and isinstance(a.risk_scores, dict):
            return a.risk_scores.get("risk")
        return None

    def get_latest_reading(self, obj):
        r = obj.readings.order_by("-ts").first()
        if not r:
            return None
        return {
            "ts": r.ts,
            "water_level": r.water_level,
            "danger_level": r.danger_level,
            "discharge": r.discharge,
            "water_temp": r.water_temp,
            "status_code": r.status_code,
            "synthetic": r.synthetic,
        }


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
