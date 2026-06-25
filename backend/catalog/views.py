from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .filters import StructureFilter
from .models import Structure
from .permissions import ReadOnlyOrEngineer
from .serializers import StructureGeoSerializer, StructureSerializer


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

    @extend_schema(responses=StructureGeoSerializer)
    @action(detail=False, methods=["get"], pagination_class=None)
    def geojson(self, request):
        """Filtered FeatureCollection for the map (not paginated)."""
        qs = self.filter_queryset(self.get_queryset())
        return Response(StructureGeoSerializer(qs, many=True).data)
