from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .filters import StructureFilter
from .models import AdminUnit, Basin, ObjectType, Structure
from .permissions import ReadOnlyOrEngineer
from .serializers import (
    AdminUnitSerializer,
    BasinSerializer,
    ObjectTypeSerializer,
    StructureGeoSerializer,
    StructureSerializer,
)

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

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(created_by=user if user.is_authenticated else None)

    @extend_schema(parameters=GEOJSON_FILTER_PARAMS, responses=StructureGeoSerializer)
    @action(detail=False, methods=["get"], pagination_class=None)
    def geojson(self, request):
        """Filtered FeatureCollection for the map (same filters as the list)."""
        qs = self.filter_queryset(self.get_queryset())
        return Response(StructureGeoSerializer(qs, many=True).data)


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
    """Object types — filter chip options."""

    queryset = ObjectType.objects.all().order_by("code")
    serializer_class = ObjectTypeSerializer
    permission_classes = [AllowAny]
    pagination_class = None
