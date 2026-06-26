from datetime import timedelta

from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from common.audit import AuditEvent, record
from monitoring.serializers import HydropostReadingSerializer

from .filters import StructureFilter
from .models import AdminUnit, Basin, ObjectType, Structure, WaterBody
from .permissions import ReadOnlyOrEngineer
from .serializers import (
    AdminUnitSerializer,
    BasinSerializer,
    ObjectTypeSerializer,
    StructureDetailSerializer,
    StructureGeoSerializer,
    StructureSerializer,
    WaterBodySerializer,
)


def _json_safe(value):
    """Make a field value JSON-serialisable for the audit payload."""
    if value is None or isinstance(value, (str, int, float, bool, dict, list)):
        return value
    pk = getattr(value, "pk", None)
    if pk is not None:
        return str(pk)
    return str(value)

# Shared filter parameters, documented on the GeoJSON action (the list endpoint
# gets them automatically from the FilterSet).
GEOJSON_FILTER_PARAMS = [
    OpenApiParameter(
        "type", str, many=True,
        description="Тип объекта (повторяемый, OR): ?type=dam&type=dike",
    ),
    OpenApiParameter(
        "condition", str, many=True,
        description="Состояние (повторяемый, OR): ?condition=repair&condition=emergency",
    ),
    OpenApiParameter("basin", str, description="UUID бассейна"),
    OpenApiParameter("district", str, description="КАТО района (admin_unit)"),
    OpenApiParameter("search", str, description="Поиск по названию"),
]


class StructureViewSet(ModelViewSet):
    """CRUD for hydro structures, with filters, search and a GeoJSON map feed."""

    queryset = Structure.objects.select_related(
        "type", "basin", "admin_unit", "water_body"
    ).all()
    serializer_class = StructureSerializer
    permission_classes = [ReadOnlyOrEngineer]
    filterset_class = StructureFilter
    search_fields = ["name_ru", "name_kk", "name_en", "cadastral_number"]
    ordering_fields = ["created_at", "name_ru", "wear_percent", "commissioning_year"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return StructureDetailSerializer
        return StructureSerializer

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(created_by=user if user.is_authenticated else None)

    def perform_update(self, serializer):
        instance = serializer.instance
        changed = {}
        for field, new in serializer.validated_data.items():
            if getattr(instance, field, None) != new:
                changed[field] = _json_safe(new)
        obj = serializer.save()
        if changed:
            user = self.request.user
            record(
                AuditEvent(
                    actor=str(user) if user.is_authenticated else "anonymous",
                    action="update",
                    entity_type="structure",
                    entity_id=str(obj.pk),
                    payload={"changed": changed},
                )
            )

    @extend_schema(parameters=GEOJSON_FILTER_PARAMS, responses=StructureGeoSerializer)
    @action(detail=False, methods=["get"], pagination_class=None)
    def geojson(self, request):
        """Filtered FeatureCollection for the map (same filters as the list).

        Only structures with geometry are returned — objects awaiting geocoding
        (needs_geocoding) have no geom and never appear on the map.
        """
        qs = self.filter_queryset(self.get_queryset()).filter(geom__isnull=False)
        return Response(StructureGeoSerializer(qs, many=True).data)

    @extend_schema(
        parameters=[OpenApiParameter("days", int, description="Окно (последние N дней)")],
        responses=HydropostReadingSerializer(many=True),
    )
    @action(detail=True, methods=["get"])
    def readings(self, request, pk=None):
        """Hydropost time series (ascending by ts), paginated; optional ?days=N."""
        structure = self.get_object()
        qs = structure.readings.all()
        days = request.query_params.get("days")
        if days:
            try:
                since = timezone.now() - timedelta(days=int(days))
                qs = qs.filter(ts__gte=since)
            except ValueError:
                pass
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(HydropostReadingSerializer(page, many=True).data)
        return Response(HydropostReadingSerializer(qs, many=True).data)


class BasinViewSet(ReadOnlyModelViewSet):
    """Basins — territory filter options."""

    queryset = Basin.objects.all().order_by("name_ru")
    serializer_class = BasinSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class AdminUnitViewSet(ReadOnlyModelViewSet):
    """Administrative units (КАТО) — filterable by level (e.g. ?level=district)."""

    queryset = AdminUnit.objects.all().order_by("name_ru")
    serializer_class = AdminUnitSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    filterset_fields = ["level", "parent"]


class ObjectTypeViewSet(ReadOnlyModelViewSet):
    """Object types — filter chip options and edit-form schemas."""

    queryset = ObjectType.objects.all().order_by("code")
    serializer_class = ObjectTypeSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class WaterBodyViewSet(ReadOnlyModelViewSet):
    """Water bodies — options for the structure edit form."""

    queryset = WaterBody.objects.all().order_by("name_ru")
    serializer_class = WaterBodySerializer
    permission_classes = [AllowAny]
    pagination_class = None
    filterset_fields = ["kind", "basin"]
