"""Dashboard aggregate endpoints (issue #20).

All aggregates honor the same filters as the map (type/condition/basin/district/
search) so the dashboard and map stay consistent. The aggregation itself lives in
:mod:`catalog.stats_service` so the report exports (#31) reuse the same numbers.
"""
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import stats_service
from .stats_service import filtered_structures

FILTER_PARAMS = [
    OpenApiParameter("type", str, many=True),
    OpenApiParameter("condition", str, many=True),
    OpenApiParameter("basin", str),
    OpenApiParameter("district", str),
    OpenApiParameter("search", str),
]


class ByTypeView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=["stats"], parameters=FILTER_PARAMS, responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response(stats_service.by_type(filtered_structures(request)))


class ByConditionView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=["stats"], parameters=FILTER_PARAMS, responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response(stats_service.by_condition(filtered_structures(request)))


class ByTerritoryView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["stats"],
        parameters=[*FILTER_PARAMS, OpenApiParameter("group", str, enum=["basin", "district"])],
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request):
        group = request.GET.get("group", "basin")
        return Response(stats_service.by_territory(filtered_structures(request), group))


class RiskSummaryView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=["stats"], parameters=FILTER_PARAMS, responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response(stats_service.risk_summary(filtered_structures(request)))


class LevelTimeseriesView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["stats"],
        parameters=[*FILTER_PARAMS, OpenApiParameter("days", int)],
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request):
        try:
            days = int(request.GET.get("days", 90))
        except ValueError:
            days = 90
        return Response(stats_service.level_timeseries(filtered_structures(request), days))
